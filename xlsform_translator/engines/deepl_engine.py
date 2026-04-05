"""DeepL translation backend."""

import sys

from .base import BaseBackend


class DeepLEngine(BaseBackend):

    def __init__(self, api_key: str):
        import deepl
        self._translator = deepl.Translator(api_key)

    def translate_batch(self, strings: list, target_language: str, context: str = "") -> list:
        if context:
            print(
                "  [info] DeepL does not support free-form translation context. "
                "The --context option is ignored for this backend.",
                file=sys.stderr,
            )

        import deepl
        results = self._translator.translate_text(
            strings,
            target_lang=target_language,
            tag_handling="xml",
            ignore_tags=["x"],
        )

        if isinstance(results, deepl.TextResult):
            results = [results]

        if len(results) != len(strings):
            raise ValueError(
                f"Length mismatch: expected {len(strings)}, got {len(results)}"
            )
        return [r.text for r in results]
