"""
Abstract base class for translation backends.
All backends share the same translate_all loop; only translate_batch differs.
"""

import re
import sys
from abc import ABC, abstractmethod

BATCH_SIZE = 50
MAX_RETRIES = 3


class BaseBackend(ABC):

    @abstractmethod
    def translate_batch(
        self,
        strings: list,
        target_language: str,
        context: str = "",
    ) -> list:
        """
        Translate a list of pre-tokenized strings.
        Must return a list of the same length.
        [P1], [P2], ... tokens must be preserved as-is.
        Raise ValueError on unrecoverable errors.
        """

    def translate_all(
        self,
        cells: list,
        target_language: str,
        context: str = "",
        verbose: bool = False,
    ) -> int:
        """
        Translate all CellRef objects in-place (sets .translated_text).
        Returns the number of cells that fell back to source text.
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
        """Retry translate_batch up to MAX_RETRIES times, then fall back."""
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = self.translate_batch(strings, target_language, context)
                _validate(result, strings)
                return result
            except (ValueError, Exception) as e:
                last_error = str(e)
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
    """Shared validation: length, no empty, placeholders preserved."""
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
