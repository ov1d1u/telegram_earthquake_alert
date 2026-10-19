"""Tests for earthquake alert parsing."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

_PARSER_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "telegram_earthquake_alert"
    / "parser.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "telegram_earthquake_parser", _PARSER_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
_PARSER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PARSER)


class FindMagnitudeTest(unittest.TestCase):
    """Test magnitude extraction."""

    def test_alert_with_magnitude_range_and_coordinates(self) -> None:
        text = (
            "La data si ora: 2026-10-19 08:51:53.71 UTC s-a produs un cutremur "
            "cu magnitudinea Mw=5.1, in intervalul de magnitudine Mmin=4.9 și "
            "Mmax=5.3. Coordonate eveniment: LAT=45.5357 și LON=26.2753, "
            "la adancimea H=148.769 km."
        )
        self.assertEqual(_PARSER.find_magnitude(text), "5.1")

    def test_decimal_magnitude(self) -> None:
        self.assertEqual(_PARSER.find_magnitude("Cutremur cu magnitudine 4.2"), "4.2")

    def test_decimal_comma_is_normalized(self) -> None:
        self.assertEqual(_PARSER.find_magnitude("Magnitudine estimată: 3,7."), "3.7")

    def test_integer_magnitude(self) -> None:
        self.assertEqual(_PARSER.find_magnitude("magnitudine de 4"), "4")

    def test_checks_only_nearby_words(self) -> None:
        self.assertIsNone(_PARSER.find_magnitude("magnitudine fără o valoare aici 5.1"))

    def test_finds_later_valid_keyword(self) -> None:
        self.assertEqual(
            _PARSER.find_magnitude("magnitudine necunoscută; apoi magnitudinea 2,8"),
            "2.8",
        )

    def test_missing_keyword(self) -> None:
        self.assertIsNone(_PARSER.find_magnitude("Cutremur detectat: 4.1"))


if __name__ == "__main__":
    unittest.main()
