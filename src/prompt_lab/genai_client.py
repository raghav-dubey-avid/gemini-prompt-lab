from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Resolve repo root:  .../src/prompt_lab/genai_client.py -> parents[2] = repo root
ROOT = Path(__file__).resolve().parents[2]

# Always load .env from repo root (works in Streamlit/CLI/pytest)
load_dotenv(ROOT / ".env", override=False)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def _get_api_key(passed: Optional[str]) -> str:
    if passed:
        return passed
    # Accept both names; GOOGLE_API_KEY is the official one
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "Missing API key. Put GOOGLE_API_KEY=<your_key> (or GEMINI_API_KEY) "
            "in a .env at the repo root, or pass api_key= to GeminiClient()."
        )
    return key


class GeminiClient:
    """
    Thin wrapper around google-genai Client with:
    - .env loading from repo root
    - explicit API key passing
    - simple text generation + token counting
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        key = _get_api_key(api_key)
        self.client = genai.Client(api_key=key)
        self.model = model or DEFAULT_MODEL

    def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 512,
    ):
        cfg = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            system_instruction=system_instruction,
        )
        return self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=cfg,
        )

    def count_tokens(self, contents: str) -> int:
        return self.client.models.count_tokens(
            model=self.model, contents=contents
        ).total_tokens
