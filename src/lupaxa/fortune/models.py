"""Immutable fortune results and public category constants."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Literal

Category = Literal[
    "wisdom",
    "warning",
    "prediction",
    "ominous",
    "encouragement",
    "devops",
    "code",
    "career",
    "friday",
]
Mode = Literal["standard", "dark", "corporate", "oracle"]
RiskLevel = Literal["low", "moderate", "high", "critical"]

CATEGORIES: tuple[Category, ...] = (
    "wisdom",
    "warning",
    "prediction",
    "ominous",
    "encouragement",
    "devops",
    "code",
    "career",
    "friday",
)
MODES: tuple[Mode, ...] = ("standard", "dark", "corporate", "oracle")
RISK_LEVELS: tuple[RiskLevel, ...] = ("low", "moderate", "high", "critical")


def list_categories() -> tuple[Category, ...]:
    """Return ordinary category names in canonical order."""
    return CATEGORIES


def display_text(value: object, *, field: str) -> str:
    """Return text that is safe to print on one line."""
    if not isinstance(value, str) or value == "" or value != value.strip() or _has_control(value):
        raise ValueError(
            f"{field} must be a non-empty single-line string without surrounding whitespace"
        )
    return value


def _has_control(value: str) -> bool:
    return any(unicodedata.category(character).startswith("C") for character in value)


@dataclass(frozen=True, slots=True)
class Fortune:
    """One generated fortune.

    Lucky numbers are a sorted tuple. An empty tuple means numbers were not
    requested. Oracle fields are present only in oracle mode.
    """

    id: str
    text: str
    mode: Mode
    category: Category | None = None
    risk_level: RiskLevel | None = None
    recommended_action: str | None = None
    lucky_numbers: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        """Reject results that break the fortune invariants."""
        display_text(self.id, field="id")
        display_text(self.text, field="text")
        if self.mode not in MODES:
            raise ValueError(f"unknown mode: {self.mode!r}")
        if self.mode == "standard":
            if self.category not in CATEGORIES:
                raise ValueError("standard fortunes require an ordinary category")
        elif self.category is not None:
            raise ValueError("special modes cannot carry a category")
        if self.mode == "oracle":
            if self.risk_level not in RISK_LEVELS:
                raise ValueError("oracle fortunes require a risk level")
            display_text(self.recommended_action, field="recommended_action")
        elif self.risk_level is not None or self.recommended_action is not None:
            raise ValueError("only oracle fortunes have risk and action")
        _validate_numbers(self.lucky_numbers)


def _validate_numbers(numbers: object) -> None:
    if not isinstance(numbers, tuple):
        raise ValueError("lucky numbers must be a tuple")
    seen: set[int] = set()
    previous: int | None = None
    for number in numbers:
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise ValueError("lucky numbers must be non-negative integers")
        if previous is not None and number <= previous:
            raise ValueError("lucky numbers must be unique and sorted")
        seen.add(number)
        previous = number
    if len(seen) != len(numbers):
        raise ValueError("lucky numbers must be unique and sorted")
