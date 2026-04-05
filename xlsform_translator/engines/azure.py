"""
Azure Cognitive Services Translator engine (Translator v3 REST API).

No additional package required beyond 'requests' (already a core dependency).
Env vars: AZURE_TRANSLATOR_KEY, AZURE_TRANSLATOR_REGION (e.g. "eastus")

Language codes: https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support
"""

import sys
import uuid
import requests

from .base import BaseBackend

_ENDPOINT = "https://api.cognitive.microsofttranslator.com/translate"


class AzureTranslatorEngine(BaseBackend):
    """Translation engine backed by the Azure Cognitive Services Translator v3 API."""

    def __init__(self, api_key: str, region: str):
        self._api_key = api_key
        self._region = region

    def translate_batch(self, strings: list, target_language: str, context: str = "") -> list:
        """Translate a batch of strings via a single POST request to the Azure API."""
        if context:
            print(
                "  [info] Azure Translator does not support free-form translation context. "
                "The --context option is ignored for this engine.",
                file=sys.stderr,
            )

        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Ocp-Apim-Subscription-Region": self._region,
            "Content-Type": "application/json",
            # X-ClientTraceId is optional but recommended by Microsoft for
            # end-to-end tracing of requests in Azure Monitor logs.
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
        # Each item in the response contains a 'translations' list; we always
        # request a single target language, so index [0] is the only result.
        return [item["translations"][0]["text"] for item in data]
