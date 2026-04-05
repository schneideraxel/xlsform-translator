"""
OpenAI translation engine.

Requires: pip install openai
Env var:  OPENAI_API_KEY
"""

import json
import re

from .base import BaseBackend

# System prompt sent on every API call. The [P1]-style instruction is critical:
# it tells the model to treat placeholder tokens as opaque literals so that
# XLSForm variable references and HTML tags survive translation intact.
_BASE_SYSTEM = (
    "You are a professional survey translator. "
    "You will receive a JSON array of strings to translate. "
    "Return ONLY a valid JSON array of the same length, in the same order. "
    "Preserve any [P1], [P2], ... tokens exactly as-is — do not translate or remove them. "
    "Do not add explanations, markdown, or anything outside the JSON array."
)


class OpenAIEngine(BaseBackend):
    """Translation engine backed by the OpenAI Chat Completions API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def translate_batch(self, strings: list, target_language: str, context: str = "") -> list:
        """
        Send one API call with up to BATCH_SIZE strings and return translations.

        If context is provided it is prepended to the system prompt, which
        improves terminology consistency for domain-specific surveys.
        """
        system = _BASE_SYSTEM
        if context:
            system = f"Context: {context}\n\n" + system

        user_msg = (
            f"Translate each string to {target_language}. "
            "Return a JSON array of the same length.\n\n"
            + json.dumps(strings, ensure_ascii=False)
        )

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
        )
        text = response.choices[0].message.content.strip()
        # Extract the JSON array even if the model wraps it in extra text.
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            raise ValueError("Response contains no JSON array")
        return [str(t) for t in json.loads(match.group())]
