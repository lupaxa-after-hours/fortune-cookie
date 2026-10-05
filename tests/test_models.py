"""Invariants of the immutable fortune model."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from lupaxa.fortune import Fortune
from lupaxa.fortune.models import list_categories


def _fortune(**overrides: object) -> Fortune:
    payload: dict[str, object] = {
        "id": "wisdom-001",
        "text": "A short fortune.",
        "mode": "standard",
        "category": "wisdom",
        "lucky_numbers": (1, 2, 4),
    }
    payload.update(overrides)
    return Fortune(**payload)  # type: ignore[arg-type]


def test_list_categories_is_canonical() -> None:
    """Categories stay in the documented order."""
    assert list_categories() == (
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


def test_frozen_assignment_fails() -> None:
    """A fortune cannot be edited after it is built."""
    fortune = _fortune()
    with pytest.raises(FrozenInstanceError):
        fortune.text = "no"  # type: ignore[misc]


def test_lucky_number_tuple_is_immutable() -> None:
    """Callers cannot append to the number tuple."""
    fortune = _fortune()
    with pytest.raises(TypeError):
        fortune.lucky_numbers[0] = 9  # type: ignore[index]


@pytest.mark.parametrize(
    "overrides",
    [
        {"text": ""},
        {"text": "  padded  "},
        {"text": "has\nbreak"},
        {"text": "has\x1bescape"},
        {"id": ""},
        {"mode": "sideways"},
        {"category": None},
        {"category": "dark"},
        {"mode": "dark", "category": "wisdom"},
        {"mode": "oracle", "category": None},
        {"mode": "oracle", "category": None, "risk_level": "dire", "recommended_action": "Wait."},
        {"risk_level": "low"},
        {"recommended_action": "Wait."},
        {"lucky_numbers": [1, 2]},
        {"lucky_numbers": (2, 1)},
        {"lucky_numbers": (1, 1)},
        {"lucky_numbers": (-1, 2)},
        {"lucky_numbers": (True, 2)},
    ],
)
def test_model_invariants(overrides: dict[str, object]) -> None:
    """Each broken field is rejected with ValueError."""
    with pytest.raises(ValueError, match="."):
        _fortune(**overrides)
