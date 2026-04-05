"""
Google Cloud Translate engine (Translation API v2, REST).

No additional package required beyond 'requests' (already a core dependency).
Env var: GOOGLE_TRANSLATE_API_KEY

Language codes: https://cloud.google.com/translate/docs/languages
"""

import sys
import requests

from .base import BaseBackend

_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"


class GoogleTranslateEngine(BaseBackend):
    """Translation engine backed by the Google Cloud Translation API v2."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    def translate_batch(self, strings: list, target_language: str, context: str = "") -> list:
        """
        Translate a batch of strings via a single POST request.

        'format: text' is set explicitly so the API does not HTML-encode
        special characters in its response (e.g. '&' → '&amp;').
        """
        if context:
            print(
                "  [info] Google Translate does not support translation context. "
                "The --context option is ignored for this engine.",
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
