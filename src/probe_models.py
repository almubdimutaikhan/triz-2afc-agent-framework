#!/usr/bin/env python3
"""Probe which candidate models are reachable on the current (free) tier.
Sends a 1-token request to each and reports FREE (200) / GATED (403) / other."""
import os
import sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://ai-gateway.vercel.sh/v1"

CANDIDATES = [
    # GPT-4 class
    "openai/gpt-4o", "openai/gpt-4o-mini", "openai/gpt-4.1", "openai/gpt-4.1-mini",
    "openai/gpt-oss-120b", "openai/gpt-oss-20b",
    # strong open Western
    "meta/llama-3.3-70b", "meta/llama-4-maverick", "meta/llama-4-scout",
    "mistral/mistral-large-3", "mistral/mistral-medium",
    # Chinese frontier
    "deepseek/deepseek-v3.1", "deepseek/deepseek-v3", "deepseek/deepseek-r1",
    "alibaba/qwen3-max", "alibaba/qwen-3-235b", "alibaba/qwen-3-32b",
    "zai/glm-4.6", "zai/glm-4.5", "moonshotai/kimi-k2",
    # google
    "google/gemini-2.5-flash", "google/gemini-2.5-pro",
]


def key():
    k = os.environ.get("AI_GATEWAY_API_KEY")
    if not k and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            if line.strip().startswith("AI_GATEWAY_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not k:
        sys.exit("no AI_GATEWAY_API_KEY")
    return k


def main():
    h = {"Authorization": f"Bearer {key()}", "Content-Type": "application/json"}
    free = []
    for m in CANDIDATES:
        try:
            r = requests.post(f"{BASE}/chat/completions", headers=h, timeout=60,
                              json={"model": m, "messages": [{"role": "user", "content": "hi"}],
                                    "max_tokens": 1})
            if r.status_code == 200:
                tag = "FREE  "; free.append(m)
            elif r.status_code == 403:
                tag = "GATED "
            else:
                tag = f"{r.status_code}   "
            note = "" if r.status_code == 200 else r.text[:90].replace("\n", " ")
            print(f"  {tag} {m:32s} {note}")
        except requests.RequestException as e:
            print(f"  ERR    {m:32s} {e}")
    print("\nFREE models:")
    for m in free:
        print("  -", m)


if __name__ == "__main__":
    main()
