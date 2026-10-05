"""Selection rules, RNG identity, and option validation."""

from __future__ import annotations

import random

import pytest

from lupaxa.fortune import (
    EmptyFortunePoolError,
    FortuneGenerator,
    InvalidOptionError,
    UnknownCategoryError,
    generate_fortune,
    generate_fortunes,
)
from lupaxa.fortune.catalogue import Catalogue, FortuneRecord
from lupaxa.fortune.models import CATEGORIES


class Spy:
    """Records choice and sample without being a random.Random."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.choice_seq: list[FortuneRecord] | None = None

    def choice(self, seq: tuple[FortuneRecord, ...]) -> FortuneRecord:
        """Record a pool draw and return the first record."""
        self.calls.append("choice")
        self.choice_seq = list(seq)
        return seq[0]

    def sample(self, population: tuple[int, ...], count: int) -> list[int]:
        """Record a sample and return the first ``count`` values."""
        self.calls.append("sample")
        return list(population)[:count]


def _catalogue() -> Catalogue:
    ordinary = tuple(
        FortuneRecord(
            id=f"{category}-001",
            text=f"Standard fortune for {category}.",
            mode="standard",
            category=category,
        )
        for category in CATEGORIES
    )
    ordinary = (
        *ordinary,
        FortuneRecord(
            id="wisdom-002",
            text="A second wisdom fortune.",
            mode="standard",
            category="wisdom",
        ),
    )
    return Catalogue(
        ordinary=ordinary,
        dark=(FortuneRecord(id="dark-001", text="A bleak fortune.", mode="dark"),),
        corporate=(FortuneRecord(id="corporate-001", text="Please align.", mode="corporate"),),
        oracle=(
            FortuneRecord(
                id="oracle-001",
                text="The omens are mixed.",
                mode="oracle",
                risk_level="high",
                recommended_action="Review the rollback plan.",
            ),
        ),
        numbers=(8, 16, 32, 64, 128),
    )


def test_same_seed_matches() -> None:
    """The same seed and options rebuild the same fortunes."""
    first = generate_fortunes(3, category="code", rng=random.Random(42))
    second = generate_fortunes(3, category="code", rng=random.Random(42))
    assert first == second
    assert all(item.category == "code" for item in first)


def test_unfiltered_choice_uses_flattened_order() -> None:
    """Standard mode draws from the ordinary records in source order."""
    spy = Spy()
    catalogue = _catalogue()
    fortune = FortuneGenerator(rng=spy, catalogue=catalogue).generate()  # type: ignore[arg-type]
    assert spy.calls == ["choice", "sample"]
    assert spy.choice_seq is not None
    assert [record.id for record in spy.choice_seq] == [record.id for record in catalogue.ordinary]
    assert fortune.id == catalogue.ordinary[0].id
    assert fortune.lucky_numbers == (8, 16, 32, 64)


def test_category_pool_preserves_order() -> None:
    """A category filter is that category's records, in source order."""
    spy = Spy()
    catalogue = _catalogue()
    FortuneGenerator(rng=spy, catalogue=catalogue).generate(category="wisdom")  # type: ignore[arg-type]
    assert [record.id for record in spy.choice_seq or []] == ["wisdom-001", "wisdom-002"]


def test_disabled_numbers_do_not_sample() -> None:
    """Skipping numbers skips sample and changes later RNG state."""
    spy = Spy()
    FortuneGenerator(rng=spy, catalogue=_catalogue()).generate(include_numbers=False)  # type: ignore[arg-type]
    assert spy.calls == ["choice"]
    with_numbers = random.Random(1)
    without_numbers = random.Random(1)
    generate_fortune(rng=with_numbers)
    generate_fortune(rng=without_numbers, include_numbers=False)
    assert with_numbers.getstate() != without_numbers.getstate()


def test_large_number_count_is_ignored_when_numbers_are_off() -> None:
    """Pool size is checked only when numbers are enabled."""
    fortune = FortuneGenerator(catalogue=_catalogue()).generate(
        include_numbers=False,
        number_count=100,
    )
    assert fortune.lucky_numbers == ()


def test_oracle_metadata_comes_from_the_record() -> None:
    """Risk and action are copied from the chosen oracle entry."""
    spy = Spy()
    fortune = FortuneGenerator(rng=spy, catalogue=_catalogue()).generate(mode="oracle")  # type: ignore[arg-type]
    assert fortune.risk_level == "high"
    assert fortune.recommended_action == "Review the rollback plan."
    assert fortune.category is None


def test_many_allows_duplicates_in_order() -> None:
    """A one-record pool can repeat, in call order."""
    catalogue = _catalogue()
    only_dark = Catalogue(
        ordinary=catalogue.ordinary,
        dark=catalogue.dark,
        corporate=catalogue.corporate,
        oracle=catalogue.oracle,
        numbers=catalogue.numbers,
    )
    results = FortuneGenerator(rng=random.Random(1), catalogue=only_dark).generate_many(
        3, mode="dark"
    )
    assert [item.id for item in results] == ["dark-001", "dark-001", "dark-001"]


def test_invalid_input_consumes_no_rng() -> None:
    """Bad options fail before the generator touches the RNG."""
    spy = Spy()
    generator = FortuneGenerator(rng=spy, catalogue=_catalogue())  # type: ignore[arg-type]
    with pytest.raises(UnknownCategoryError):
        generator.generate(category="nope")  # type: ignore[arg-type]
    assert spy.calls == []


def test_global_random_is_unchanged() -> None:
    """Generation does not seed or draw from the global generator."""
    random.seed(123)
    before = random.getstate()
    generate_fortune()
    generate_fortunes(2)
    assert random.getstate() == before


def test_empty_pool() -> None:
    """An empty selected pool is reported before a draw."""
    catalogue = _catalogue()
    empty = Catalogue(
        ordinary=catalogue.ordinary,
        dark=(),
        corporate=catalogue.corporate,
        oracle=catalogue.oracle,
        numbers=catalogue.numbers,
    )
    with pytest.raises(EmptyFortunePoolError):
        FortuneGenerator(catalogue=empty).generate(mode="dark")


def _invoke(generator: FortuneGenerator, kwargs: dict[str, object]) -> object:
    if "count" in kwargs:
        return generator.generate_many(**kwargs)  # type: ignore[arg-type]
    return generator.generate(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kwargs", "exc"),
    [
        ({"count": 0}, InvalidOptionError),
        ({"count": True}, InvalidOptionError),
        ({"mode": "sideways"}, InvalidOptionError),
        ({"category": 3}, UnknownCategoryError),
        ({"category": "wisdom", "mode": "dark"}, InvalidOptionError),
        ({"include_numbers": 1}, InvalidOptionError),
        ({"number_count": True}, InvalidOptionError),
        ({"number_count": 0}, InvalidOptionError),
        ({"number_count": 99}, InvalidOptionError),
    ],
)
def test_invalid_options(kwargs: dict[str, object], exc: type[Exception]) -> None:
    """Bad counts, modes, and combinations raise the public option errors."""
    generator = FortuneGenerator(catalogue=_catalogue())
    with pytest.raises(exc):
        _invoke(generator, kwargs)


def test_supplied_rng_object_is_used() -> None:
    """Convenience functions keep the caller's RNG object."""
    spy = Spy()
    generate_fortunes(2, rng=spy, category="code")  # type: ignore[arg-type]
    assert spy.calls == ["choice", "sample", "choice", "sample"]
