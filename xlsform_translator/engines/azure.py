"""Azure Cognitive Services Translator backend (v3 REST API)."""

import sys
import uuid
import requests

from .base import BaseBackend

_ENDPOINT = "https://api.cognitive.microsofttranslator.com/translate"


class AzureTranslatorEngine(BaseBackend):

    def __init__(self, api_key: str, region: str):
        self._api_key = api_key
        self._region = region

    def translate_batch(self, strings: list, target_language: str, context: str = "") -> list:
        if context:
            print(
                "  [info] Azure Translator does not support free-form translation context. "
                "The --context option is ignored for this backend.",
                file=sys.stderr,
            )

        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Ocp-Apim-Subscription-Region": self._region,
            "Content-Type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }
        body = [{"text": s} for s in strings]

        response = requests.post(
            _ENDPOINT,
            params={"api-version": "3.0", "to": target_language},
            headers=headers,
            json=body,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if len(data) != len(strings):
            raise ValueError(
                f"Length mismatch: expected {len(strings)}, got {len(data)}"
            )
        return [item["translations"][0]["text"] for item in data]
