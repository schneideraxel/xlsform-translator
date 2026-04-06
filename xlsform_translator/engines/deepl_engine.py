### DeepL engine : translates batches via the DeepL API using the official Python SDK
### AS 🐚🫧🪼🪸
### 05.04.2026 (Last update)

"""
DeepL translation engine (official deepl-python SDK).

Requires: pip install deepl
Env var:  DEEPL_API_KEY

Language codes: https://support.deepl.com/hc/en-us/articles/360019925219
"""

import sys

from .base import BaseBackend


class DeepLEngine(BaseBackend):
    """Translation engine backed by the DeepL API via the official Python SDK."""

    def __init__(self, api_key: str):
        import deepl
        self._translator = deepl.Translator(api_key)

    def translate_batch(self, strings: list, target_language: str, context: str = "") -> list:
        """
        Translate a batch of strings using the DeepL SDK.

        tag_handling="xml" and ignore_tags=["x"] tell DeepL to treat the text
        as XML and leave any <x>...</x> wrapped content untranslated. This is
        used here as a lightweight way to protect placeholder tokens; the tokens
        themselves ([P1], [P2], ...) are plain text but the XML mode prevents
        DeepL from misinterpreting bracket characters.
        """
        if context:
            print(
                "  [info] DeepL does not support free-form translation context. "
                "The --context option is ignored for this engine.",
                file=sys.stderr,
            )

        import deepl
        results = self._translator.translate_text(
            strings,
            target_lang=target_language,
            tag_handling="xml",
            ignore_tags=["x"],
        )

        # The SDK returns a single TextResult (not a list) when given one string.
        if isinstance(results, deepl.TextResult):
            results = [results]

        if len(results) != len(strings):
            raise ValueError(
                f"Length mismatch: expected {len(strings)}, got {len(results)}"
            )
        return [r.text for r in results]
