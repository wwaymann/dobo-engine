from __future__ import annotations

"""Corrected launcher for the DOBO Capability Lab.

Rules:
- Exact basic-family prompts run offline.
- Any edited/free prompt runs through OpenAI interpretation, even if it mentions
  cube/cylinder/sphere/etc.

This preserves the existing UI while fixing the previous `mode=auto` behavior
that collapsed richer prompts into primitive offline fixtures.
"""

import unicodedata

import dobo_capability_lab as lab


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower())
    return "".join(ch for ch in value if not unicodedata.combining(ch)).strip()


_BASIC_PROMPTS = {
    "crea una maceta cubo",
    "crea una maceta cubica",
    "crea una maceta prisma rectangular",
    "crea una maceta rectangular",
    "crea una maceta cilindro",
    "crea una maceta cilindrica",
    "crea una maceta cono",
    "crea una maceta conica",
    "crea una maceta esfera",
    "crea una maceta esferica",
    "crea una maceta ovoide",
    "crea una maceta prisma triangular",
    "crea una maceta triangular",
}

_original_generate = lab.generate


def generate(prompt: str, mode: str = "auto") -> dict:
    normalized = _plain(prompt)
    if mode == "offline" or (mode == "auto" and normalized in _BASIC_PROMPTS):
        return _original_generate(prompt, mode="offline")
    return _original_generate(prompt, mode="openai")


lab.generate = generate


if __name__ == "__main__":
    lab.main()
