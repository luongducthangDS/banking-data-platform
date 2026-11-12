"""Gemini structured output with key rotation on 429 (pattern from neuro-symbolic-agent/nsa/llm.py)."""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


load_env()
MODELS = os.getenv("ASSISTANT_MODELS", "gemini-3.5-flash-lite,gemini-3.5-flash").split(",")


class Usage:
    calls = 0
    in_tokens = 0
    out_tokens = 0


class Gemini:
    def __init__(self, models: list[str] | None = None):
        from google import genai

        keys = [os.environ[k] for k in ("GOOGLE_API_KEY", "GOOGLE_API_KEY_2", "GOOGLE_API_KEY_3") if os.getenv(k)]
        if not keys:
            raise RuntimeError("GOOGLE_API_KEY is not set")
        self.clients = [genai.Client(api_key=k) for k in keys]
        self.models = models or MODELS
        self.k = 0

    def json(self, prompt: str, schema: type[BaseModel], system: str = "") -> BaseModel:
        from google.genai import types

        cfg = types.GenerateContentConfig(system_instruction=system or None, temperature=0,
                                          response_mime_type="application/json", response_schema=schema)
        last = None
        for model in self.models:
            for attempt in range(3 * len(self.clients)):
                try:
                    r = self.clients[self.k].models.generate_content(model=model, contents=prompt, config=cfg)
                    Usage.calls += 1
                    if r.usage_metadata:
                        Usage.in_tokens += r.usage_metadata.prompt_token_count or 0
                        Usage.out_tokens += r.usage_metadata.candidates_token_count or 0
                    return schema.model_validate_json(r.text)
                except Exception as e:  # 429 -> next key; full rotation -> wait; other -> backoff
                    last, msg = e, str(e)
                    if "404" in msg:
                        break
                    if "429" in msg:
                        self.k = (self.k + 1) % len(self.clients)
                        if self.k == 0:
                            m = re.search(r"retry in ([\d.]+)s", msg)
                            time.sleep(min(float(m.group(1)) + 1, 65) if m else 20)
                    else:
                        time.sleep(2 * 2 ** min(attempt, 3))
        raise RuntimeError(f"all models failed: {last}")
