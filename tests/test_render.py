"""Exact rendering for every mode and style."""

from __future__ import annotations

import pytest

from lupaxa.fortune import Fortune
from lupaxa.fortune.render import render_fortune


def _standard() -> Fortune:
    return Fortune(
        id="wisdom-001",
        text="The code you are afraid to touch will soon require modification.",
        mode="standard",
        category="wisdom",
        lucky_numbers=(22, 80, 443, 8080),
    )


def _oracle() -> Fortune:
    return Fortune(
        id="oracle-021",
        text="The pipeline is green, but the omens remain ambiguous.",
        mode="oracle",
        risk_level="high",
        recommended_action="Inspect the rollback plan before celebrating.",
        lucky_numbers=(42, 404, 443, 8080),
    )


def test_decorative_standard() -> None:
    """Standard output matches the documented block."""
    assert render_fortune(_standard()) == (
        "🥠 Your fortune:\n"
        "\n"
        "The code you are afraid to touch will soon require modification.\n"
        "\n"
        "Lucky numbers: 22, 80, 443, 8080"
    )


def test_decorative_modes() -> None:
    """Dark and corporate headings stay specific."""
    dark = Fortune(id="dark-001", text="Bleak, but playful.", mode="dark", lucky_numbers=(8, 16))
    corporate = Fortune(
        id="corporate-001",
        text="Please align the alignment.",
        mode="corporate",
        lucky_numbers=(404,),
    )
    assert render_fortune(dark).startswith("🌑 Your dark fortune:")
    assert render_fortune(corporate).startswith("💼 Your corporate fortune:")


def test_decorative_oracle() -> None:
    """Oracle output uppercases the risk and keeps the action."""
    assert render_fortune(_oracle()) == (
        "🔮 The Developer Oracle speaks:\n"
        "\n"
        "The pipeline is green, but the omens remain ambiguous.\n"
        "\n"
        "Risk level: HIGH\n"
        "Recommended action: Inspect the rollback plan before celebrating.\n"
        "\n"
        "Lucky numbers: 42, 404, 443, 8080"
    )


def test_plain_oracle() -> None:
    """Plain oracle output keeps the facts and drops the decoration."""
    assert render_fortune(_oracle(), plain=True) == (
        "The pipeline is green, but the omens remain ambiguous.\n"
        "Risk level: high\n"
        "Recommended action: Inspect the rollback plan before celebrating.\n"
        "Lucky numbers: 42, 404, 443, 8080"
    )


def test_omits_empty_numbers() -> None:
    """An empty number tuple drops the lucky line and its blank line."""
    fortune = Fortune(
        id="wisdom-001",
        text="A short fortune.",
        mode="standard",
        category="wisdom",
    )
    assert render_fortune(fortune) == "🥠 Your fortune:\n\nA short fortune."
    assert render_fortune(fortune, plain=True) == "A short fortune."
    oracle = Fortune(
        id="oracle-001",
        text="A calm omen.",
        mode="oracle",
        risk_level="low",
        recommended_action="Commit your work and enjoy the quiet.",
    )
    rendered = render_fortune(oracle, plain=True)
    assert "Lucky numbers" not in rendered
    assert "Risk level: low" in rendered


def test_plain_must_be_boolean() -> None:
    """The renderer rejects a non-boolean style flag."""
    with pytest.raises(ValueError, match="boolean"):
        render_fortune(_standard(), plain=1)  # type: ignore[arg-type]
