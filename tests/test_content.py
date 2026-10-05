"""Production dataset size and editorial limits."""

from __future__ import annotations

from lupaxa.fortune.catalogue import load_catalogue
from lupaxa.fortune.models import CATEGORIES, RISK_LEVELS

EXPECTED_NUMBERS = (
    0,
    1,
    2,
    8,
    16,
    22,
    32,
    42,
    64,
    80,
    128,
    256,
    404,
    418,
    443,
    500,
    512,
    1024,
    1337,
    2048,
    4096,
    5432,
    6379,
    8000,
    8080,
    8443,
    9000,
)


def test_production_content_targets() -> None:
    """The bundled copy meets the release counts and length limits."""
    catalogue = load_catalogue()
    counts = dict.fromkeys(CATEGORIES, 0)
    texts: list[str] = []
    for record in catalogue.ordinary:
        assert record.category is not None
        counts[record.category] += 1
        texts.append(record.text)
    assert all(count >= 25 for count in counts.values())
    assert len(catalogue.dark) >= 40
    assert len(catalogue.corporate) >= 40
    assert len(catalogue.oracle) >= 40
    risks = dict.fromkeys(RISK_LEVELS, 0)
    for record in catalogue.oracle:
        assert record.risk_level is not None
        assert record.recommended_action is not None
        assert len(record.recommended_action) < 160
        risks[record.risk_level] += 1
        texts.append(record.text)
    assert all(count >= 10 for count in risks.values())
    texts.extend(record.text for record in catalogue.dark)
    texts.extend(record.text for record in catalogue.corporate)
    assert all(len(text) < 240 for text in texts)
    assert sum(len(text) < 160 for text in texts) >= int(len(texts) * 0.9)
    folded = "\n".join(texts).casefold()
    for banned in ("todo", "fixme", "lorem ipsum", "placeholder"):
        assert banned not in folded
    assert catalogue.numbers == EXPECTED_NUMBERS
