from __future__ import annotations

"""Lightweight parsing helpers for explicit multiline text prompts.

This module deliberately has no geometry or pipeline imports so semantic repair,
text consolidation, and native CAD routing can share the same prompt contract
without creating an import cycle.
"""

import re


def prompt_lines(prompt: str | None) -> tuple[str, ...]:
    if not prompt:
        return ()
    raw = str(prompt)

    for match in re.finditer(r'[\"“”]([^\"“”]+)[\"“”]', raw, flags=re.DOTALL):
        payload = match.group(1)
        if "\\n" in payload or "\n" in payload:
            normalized = payload.replace("\\r\\n", "\n").replace("\\n", "\n")
            lines = tuple(part.strip() for part in normalized.splitlines() if part.strip())
            if len(lines) >= 2:
                return tuple(line.upper() for line in lines)

    assignment = re.compile(
        r"(?:linea|línea)\s*(\d+)\s*(?:=|:)\s*[\"'“”]?\s*(.*?)\s*[\"'“”]?\s*"
        r"(?=(?:;|,)?\s*(?:linea|línea)\s*\d+\s*(?:=|:)|(?:[.;]\s*)?$)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    matches = assignment.findall(raw)
    if matches:
        ordered = sorted(
            (int(index), text.strip(" .;,:\"'“”"))
            for index, text in matches
            if text.strip(" .;,:\"'“”")
        )
        if len(ordered) >= 2:
            return tuple(text.upper() for _, text in ordered)
    return ()


# Compatibility alias while callers are migrated from text_surface_consolidation.
_prompt_lines = prompt_lines
