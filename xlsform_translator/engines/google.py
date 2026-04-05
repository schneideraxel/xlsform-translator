"""Google Cloud Translate backend (v2 REST API)."""

import sys
import requests

from .base import BaseBackend

_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"


class GoogleTranslateEngine(BaseBackend):

    def __init__(self, api_key: str):
        self._api_key = api_key

    def translate_batch(self, strings: list, target_language: str, context: str = "") -> list:
        if context:
            print(
                "  [info] Google Translate does not support translation context. "
                "The --context option is ignored for this backend.",
                file=sys.stderr,
            )

        response = requests.post(
            _ENDPOINT,
            params={"key": self._api_key},
            json={"q": strings, "target": target_language, "format": "text"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        translations = data["data"]["translations"]
        if len(translations) != len(strings):
            raise ValueError(
                f"Length mismatch: expected {len(strings)}, got {len(translations)}"
            )
        return [t["translatedText"] for t in translations]
