"""
DEPRECATED — this module is no longer used.

Translation logic has been moved to the xlsform_translator/engines/ package,
which provides a common BaseBackend class and separate engine modules for
Claude, OpenAI, Google Translate, DeepL, and Azure Translator.

This file is kept for reference only and can be safely deleted.
"""

import json
import re
import sys

BATCH_SIZE = 50
MAX_RETRIES = 3

SYSTEM_PROMPT = (
    "You are a professional survey translator. "
    "You will receive a JSON array of strings to translate. "
    "Return ONLY a valid JSON array of the same length, in the same order. "
    "Preserve any [P1], [P2], ... tokens exactly as-is — do not translate or remove them. "
    "Do not add explanations, markdown, or anything outside the JSON array."
)


def _build_user_message(strings: list, target_language: str) -> str:
    return (
        f"Translate each string to {target_language}. "
        "Return a JSON array of the same length.\n\n"
        + json.dumps(strings, ensure_ascii=False)
    )


def _validate_response(response_text: str, source_strings: list) -> list:
    """
    Parse and validate the Claude response.
    Returns the translated list on success.
    Raises ValueError with a descriptive message on failure.
    """
    # Extract JSON array robustly (handles leading/trailing whitespace or markdown)
    match = re.search(r'\[[\s\S]*\]', response_text)
    if not match:
        raise ValueError("Response contains no JSON array")

    translations = json.loads(match.group())

    if not isinstance(translations, list):
        raise ValueError("Response is not a JSON array")

    if len(translations) != len(source_strings):
        raise ValueError(
            f"Length mismatch: expected {len(source_strings)}, got {len(translations)}"
        )

    for i, (src, tgt) in enumerate(zip(source_strings, translations)):
        if tgt is None or (isinstance(tgt, str) and not tgt.strip() and src.strip()):
            raise ValueError(f"Empty translation at index {i}")

        # Check all placeholder tokens are preserved
        src_tokens = set(re.findall(r'\[P\d+\]', src))
        tgt_tokens = set(re.findall(r'\[P\d+\]', str(tgt)))
        missing = src_tokens - tgt_tokens
        if missing:
            raise ValueError(f"Missing placeholders {missing} at index {i}")

    return [str(t) for t in translations]


def translate_batch(
    strings: list,
    target_language: str,
    anthropic_client,
    verbose: bool = False,
) -> list:
    """
    Translate a list of (already tokenized) strings to target_language.
    Retries up to MAX_RETRIES times on validation failure.
    Falls back to original strings after exhausting retries.
    """
    if not strings:
        return []

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            user_msg = _build_user_message(strings, target_language)
            if attempt > 1:
                user_msg = (
                    f"[Attempt {attempt}] Previous attempt failed ({last_error}). "
                    "Please try again carefully, ensuring exact length and token preservation.\n\n"
                    + user_msg
                )

            response = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            result = _validate_response(response.content[0].text, strings)
            return result

        except (ValueError, json.JSONDecodeError) as e:
            last_error = str(e)
            if verbose:
                print(f"  [warn] Attempt {attempt}/{MAX_RETRIES} failed: {e}", file=sys.stderr)

    # Fallback: return originals, log warning
    print(
        f"  [warn] Translation failed after {MAX_RETRIES} attempts for a batch of "
        f"{len(strings)} strings. Keeping source text.",
        file=sys.stderr,
    )
    return list(strings)


def translate_all(
    cells: list,
    target_language: str,
    anthropic_client,
    verbose: bool = False,
) -> None:
    """
    Translate all CellRef objects in-place, populating a `translated_text` attribute.
    Processes in batches of BATCH_SIZE.
    """
    total = len(cells)
    warnings = 0

    for batch_start in range(0, total, BATCH_SIZE):
        batch = cells[batch_start: batch_start + BATCH_SIZE]
        tokenized_strings = [c.tokenized_text for c in batch]

        if verbose:
            end = min(batch_start + BATCH_SIZE, total)
            print(f"  Translating strings {batch_start + 1}–{end} of {total}...")

        translated = translate_batch(
            tokenized_strings, target_language, anthropic_client, verbose=verbose
        )

        # Check if fallback was used (translated == source)
        fallback_used = translated == tokenized_strings

        for cell_ref, trans in zip(batch, translated):
            from .parser import detokenize
            cell_ref.translated_text = detokenize(trans, cell_ref.token_map)

        if fallback_used:
            warnings += len(batch)

    return warnings
