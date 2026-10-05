"""Pure fortune rendering. No randomness and no dataset access."""

from __future__ import annotations

from lupaxa.fortune.models import Fortune, Mode

_HEADINGS: dict[Mode, str] = {
    "standard": "🥠 Your fortune:",
    "dark": "🌑 Your dark fortune:",
    "corporate": "💼 Your corporate fortune:",
    "oracle": "🔮 The Developer Oracle speaks:",
}


def render_fortune(fortune: Fortune, *, plain: bool = False) -> str:
    """Return one fortune block with no trailing newline.

    Decorative output includes a mode heading. Plain output keeps the same
    facts without emoji, headings, or uppercase risk labels. An empty lucky
    number tuple omits that line and the blank line that would precede it.
    """
    if not isinstance(plain, bool):
        raise ValueError("plain must be a boolean")
    lines: list[str] = []
    if not plain:
        lines.append(_HEADINGS[fortune.mode])
        lines.append("")
    lines.append(fortune.text)
    if fortune.mode == "oracle":
        if not plain:
            lines.append("")
        risk = fortune.risk_level or ""
        lines.append(f"Risk level: {risk if plain else risk.upper()}")
        lines.append(f"Recommended action: {fortune.recommended_action}")
    if fortune.lucky_numbers:
        if not plain:
            lines.append("")
        rendered = ", ".join(str(number) for number in fortune.lucky_numbers)
        lines.append(f"Lucky numbers: {rendered}")
    return "\n".join(lines)
