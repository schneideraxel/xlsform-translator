"""
Translation engine factory.
Each engine is imported lazily so missing optional dependencies
only raise errors when that specific engine is requested.
"""

import os
import sys


ENGINES = ("claude", "openai", "google", "deepl", "azure")


def get_engine(name: str):
    """
    Instantiate and return the requested translation engine.
    Reads credentials from environment variables.
    Exits with a clear error message if a required key is missing.
    """
    name = name.lower()

    if name == "claude":
        key = _require_env("ANTHROPIC_API_KEY", "Claude")
        from .claude import ClaudeEngine
        return ClaudeEngine(api_key=key)

    if name == "openai":
        key = _require_env("OPENAI_API_KEY", "OpenAI")
        from .openai_engine import OpenAIEngine
        return OpenAIEngine(api_key=key)

    if name == "google":
        key = _require_env("GOOGLE_TRANSLATE_API_KEY", "Google Translate")
        from .google import GoogleTranslateEngine
        return GoogleTranslateEngine(api_key=key)

    if name == "deepl":
        key = _require_env("DEEPL_API_KEY", "DeepL")
        from .deepl_engine import DeepLEngine
        return DeepLEngine(api_key=key)

    if name == "azure":
        key = _require_env("AZURE_TRANSLATOR_KEY", "Azure Translator")
        region = _require_env("AZURE_TRANSLATOR_REGION", "Azure Translator")
        from .azure import AzureTranslatorEngine
        return AzureTranslatorEngine(api_key=key, region=region)

    print(f"Error: unknown engine '{name}'. Choose from: {', '.join(ENGINES)}", file=sys.stderr)
    sys.exit(1)


def _require_env(var: str, engine_name: str) -> str:
    val = os.environ.get(var)
    if not val:
        print(
            f"Error: {engine_name} engine requires {var} to be set. "
            f"Add it to your .env file or environment.",
            file=sys.stderr,
        )
        sys.exit(1)
    return val
