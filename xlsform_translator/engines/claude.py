"""Claude (Anthropic) translation backend."""

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


class ClaudeEngine(BaseBackend):

    def __init__(self, api_key: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)

    def translate_batch(self, strings: list, target_language: str, context: str = "") -> list:
        system = _BASE_SYSTEM
        if context:
            system = f"Context: {context}\n\n" + system

        user_msg = (
            f"Translate each string to {target_language}. "
            "Return a JSON array of the same length.\n\n"
            + json.dumps(strings, ensure_ascii=False)
        )

        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = response.content[0].text.strip()
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            raise ValueError("Response contains no JSON array")
        return [str(t) for t in json.loads(match.group())]
