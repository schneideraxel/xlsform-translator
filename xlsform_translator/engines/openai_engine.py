"""OpenAI (ChatGPT) translation backend."""

import json
import re

from .base import BaseBackend

_BASE_SYSTEM = (
    "You are a professional survey translator. "
    "You will receive a JSON array of strings to translate. "
    "Return ONLY a valid JSON array of the same length, in the same order. "
    "Preserve any [P1], [P2], ... tokens exactly as-is — do not translate or remove them. "
    "Do not add explanations, markdown, or anything outside the JSON array."
)


class OpenAIEngine(BaseBackend):

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def translate_batch(self, strings: list, target_language: str, context: str = "") -> list:
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
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            raise ValueError("Response contains no JSON array")
        return [str(t) for t in json.loads(match.group())]
