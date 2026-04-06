### Base engine : shared batching, retry logic, validation, and fallback behaviour
### AS 🐚🫧🪼🪸
### 05.04.2026 (Last update)

"""
Abstract base class shared by all translation engines.

Each engine implements only translate_batch(). The batching loop, retry logic,
placeholder detokenization, and fallback behaviour are handled here so they
don't need to be duplicated across engines.
"""

import re
import sys
from abc import ABC, abstractmethod

# Number of strings sent to the translation API in a single call.
# Keeping this at 50 balances latency against the risk of hitting token limits.
BATCH_SIZE = 50

# How many times to retry a failed batch before giving up and keeping the
# source text.
MAX_RETRIES = 3


class BaseBackend(ABC):
    """
    Base class for all translation engines.

    To add a new engine, subclass this and implement translate_batch().
    Everything else (batching, retries, detokenization, fallback) is inherited.
    """

    @abstractmethod
    def translate_batch(
        self,
        strings: list,
        target_language: str,
        context: str = "",
    ) -> list:
        """
        Translate a list of pre-tokenized strings to target_language.

        Args:
            strings: List of strings to translate. Strings may contain [P1],
                     [P2], ... placeholder tokens that must be returned verbatim.
            target_language: Target language name or code (e.g. "French", "fr").
            context: Optional domain description to guide LLM-based engines.
                     Non-LLM engines may ignore this.

        Returns:
            A list of translated strings in the same order, same length.

        Raises:
            ValueError: On any unrecoverable API or parsing error. The caller
                        will retry up to MAX_RETRIES times before falling back.
        """

    def translate_all(
        self,
        cells: list,
        target_language: str,
        context: str = "",
        verbose: bool = False,
    ) -> int:
        """
        Translate all CellRef objects in-place, populating .translated_text.

        Splits cells into batches of BATCH_SIZE, calls _translate_with_retry()
        for each batch, then detokenizes the results back into each CellRef.

        Args:
            cells: List of CellRef objects from the parser.
            target_language: Target language name or code.
            context: Optional domain context forwarded to the engine.
            verbose: If True, prints per-batch progress to stdout.

        Returns:
            Number of cells that could not be translated and fell back to
            their source text (0 means full success).
        """
        from xlsform_translator.parser import detokenize

        total = len(cells)
        warnings = 0

        for batch_start in range(0, total, BATCH_SIZE):
            batch = cells[batch_start: batch_start + BATCH_SIZE]
            tokenized = [c.tokenized_text for c in batch]

            if verbose:
                end = min(batch_start + BATCH_SIZE, total)
                print(f"  Translating strings {batch_start + 1}–{end} of {total}...")

            translated = self._translate_with_retry(
                tokenized, target_language, context, verbose
            )

            # Detect fallback: _translate_with_retry returns the original list
            # unchanged when all retries are exhausted.
            fallback = translated == tokenized
            for cell_ref, trans in zip(batch, translated):
                cell_ref.translated_text = detokenize(trans, cell_ref.token_map)
            if fallback:
                warnings += len(batch)

        return warnings

    def _translate_with_retry(
        self,
        strings: list,
        target_language: str,
        context: str,
        verbose: bool,
    ) -> list:
        """
        Call translate_batch up to MAX_RETRIES times.

        Returns the translated list on success, or the original strings list
        unchanged if all attempts fail (so the output file always stays complete).
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = self.translate_batch(strings, target_language, context)
                _validate(result, strings)
                return result
            except Exception as e:
                if verbose:
                    print(
                        f"  [warn] Attempt {attempt}/{MAX_RETRIES} failed: {e}",
                        file=sys.stderr,
                    )

        print(
            f"  [warn] Translation failed after {MAX_RETRIES} attempts "
            f"for a batch of {len(strings)} strings. Keeping source text.",
            file=sys.stderr,
        )
        return list(strings)


def _validate(translations: list, source_strings: list) -> None:
    """
    Verify a batch of translations before accepting it.

    Checks:
    - Result is a list of the same length as the input.
    - No translation is empty when its source string was non-empty.
    - Every [P1], [P2], ... placeholder token present in the source is also
      present in the translation (prevents the engine from dropping XLSForm
      variable references or HTML tags).

    Raises ValueError with a descriptive message on any failure.
    """
    if not isinstance(translations, list):
        raise ValueError("Result is not a list")
    if len(translations) != len(source_strings):
        raise ValueError(
            f"Length mismatch: expected {len(source_strings)}, got {len(translations)}"
        )
    for i, (src, tgt) in enumerate(zip(source_strings, translations)):
        if tgt is None or (isinstance(tgt, str) and not tgt.strip() and src.strip()):
            raise ValueError(f"Empty translation at index {i}")
        src_tokens = set(re.findall(r"\[P\d+\]", src))
        tgt_tokens = set(re.findall(r"\[P\d+\]", str(tgt)))
        missing = src_tokens - tgt_tokens
        if missing:
            raise ValueError(f"Missing placeholders {missing} at index {i}")
