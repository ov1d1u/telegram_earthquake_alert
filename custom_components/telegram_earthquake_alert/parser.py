"""Helpers for parsing Telegram earthquake alerts."""

from __future__ import annotations

import re

MAX_WORD_DISTANCE = 3

_MAGNITUDE_WORD = re.compile(r"magnitudine", re.IGNORECASE)
_NUMBER = re.compile(r"(?<!\d)[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)(?!\d)")


def find_magnitude(text: str) -> str | None:
    """Extract and normalize a magnitude near the Romanian keyword."""
    words = text.split()

    for index, word in enumerate(words):
        if not _MAGNITUDE_WORD.search(word):
            continue

        for candidate in words[index + 1 : index + 1 + MAX_WORD_DISTANCE]:
            if match := _NUMBER.search(candidate):
                magnitude = match.group().replace(",", ".")
                if magnitude.startswith("."):
                    magnitude = f"0{magnitude}"
                elif magnitude.startswith("-."):
                    magnitude = magnitude.replace("-.", "-0.", 1)
                elif magnitude.startswith("+."):
                    magnitude = magnitude.replace("+.", "+0.", 1)
                return magnitude

    return None
