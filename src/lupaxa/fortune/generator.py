"""Select fortunes. Randomness is always an explicit Random instance."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from lupaxa.fortune.exceptions import (
    EmptyFortunePoolError,
    InvalidOptionError,
    UnknownCategoryError,
)
from lupaxa.fortune.models import CATEGORIES, MODES, Category, Fortune, Mode

if TYPE_CHECKING:
    from lupaxa.fortune.catalogue import Catalogue, FortuneRecord


class FortuneGenerator:
    """Draw fortunes from a catalogue with one RNG stream.

    Disabling lucky numbers skips ``rng.sample``. Later draws in the same
    batch therefore see different RNG state than a batch that sampled numbers.
    Seeds are reproducible for a given dataset and Python random implementation.
    They are not a stable cross-release contract.
    """

    def __init__(
        self,
        *,
        rng: random.Random | None = None,
        catalogue: Catalogue | None = None,
    ) -> None:
        """Store an RNG and an optional in-memory catalogue.

        ``catalogue`` is for tests. It does not read a caller-supplied path.
        """
        self._rng = random.Random() if rng is None else rng
        self._catalogue_override = catalogue

    def generate(
        self,
        *,
        category: Category | None = None,
        mode: Mode = "standard",
        include_numbers: bool = True,
        number_count: int = 4,
    ) -> Fortune:
        """Return one fortune."""
        self._validate(
            category=category,
            mode=mode,
            include_numbers=include_numbers,
            number_count=number_count,
        )
        catalogue = self._catalogue()
        pool = self._prepare_pool(
            catalogue,
            category=category,
            mode=mode,
            include_numbers=include_numbers,
            number_count=number_count,
        )
        return self._draw(
            catalogue, pool, include_numbers=include_numbers, number_count=number_count
        )

    def generate_many(
        self,
        count: int = 1,
        *,
        category: Category | None = None,
        mode: Mode = "standard",
        include_numbers: bool = True,
        number_count: int = 4,
    ) -> tuple[Fortune, ...]:
        """Return ``count`` fortunes from one validation and one RNG stream."""
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise InvalidOptionError("count must be a positive integer")
        self._validate(
            category=category,
            mode=mode,
            include_numbers=include_numbers,
            number_count=number_count,
        )
        catalogue = self._catalogue()
        pool = self._prepare_pool(
            catalogue,
            category=category,
            mode=mode,
            include_numbers=include_numbers,
            number_count=number_count,
        )
        return tuple(
            self._draw(catalogue, pool, include_numbers=include_numbers, number_count=number_count)
            for _ in range(count)
        )

    def _catalogue(self) -> Catalogue:
        if self._catalogue_override is not None:
            return self._catalogue_override
        from lupaxa.fortune.catalogue import load_catalogue

        return load_catalogue()

    def _validate(
        self,
        *,
        category: Category | None,
        mode: Mode,
        include_numbers: bool,
        number_count: int,
    ) -> None:
        if not isinstance(mode, str) or mode not in MODES:
            raise InvalidOptionError(f"unknown mode: {mode!r}")
        if category is not None:
            if not isinstance(category, str):
                raise UnknownCategoryError(f"unknown category: {category!r}")
            if category not in CATEGORIES:
                raise UnknownCategoryError(f"unknown category: {category}")
        if mode != "standard" and category is not None:
            raise InvalidOptionError("a category cannot be combined with a special mode")
        if not isinstance(include_numbers, bool):
            raise InvalidOptionError("include_numbers must be a boolean")
        if isinstance(number_count, bool) or not isinstance(number_count, int) or number_count < 1:
            raise InvalidOptionError("number_count must be a positive integer")

    def _prepare_pool(
        self,
        catalogue: Catalogue,
        *,
        category: Category | None,
        mode: Mode,
        include_numbers: bool,
        number_count: int,
    ) -> tuple[FortuneRecord, ...]:
        pool = catalogue.pool(mode, category)
        if not pool:
            raise EmptyFortunePoolError(f"no fortunes are available for mode {mode!r}")
        if include_numbers and number_count > len(catalogue.numbers):
            raise InvalidOptionError("number_count exceeds the lucky-number pool")
        return pool

    def _draw(
        self,
        catalogue: Catalogue,
        pool: tuple[FortuneRecord, ...],
        *,
        include_numbers: bool,
        number_count: int,
    ) -> Fortune:
        record = self._rng.choice(pool)
        numbers: tuple[int, ...] = ()
        if include_numbers:
            picked = self._rng.sample(catalogue.numbers, number_count)
            numbers = tuple(sorted(picked))
        return Fortune(
            id=record.id,
            text=record.text,
            mode=record.mode,
            category=record.category,
            risk_level=record.risk_level,
            recommended_action=record.recommended_action,
            lucky_numbers=numbers,
        )


def generate_fortune(
    *,
    category: Category | None = None,
    mode: Mode = "standard",
    include_numbers: bool = True,
    number_count: int = 4,
    rng: random.Random | None = None,
) -> Fortune:
    """Return one fortune, reusing ``rng`` when the caller supplied one."""
    return FortuneGenerator(rng=rng).generate(
        category=category,
        mode=mode,
        include_numbers=include_numbers,
        number_count=number_count,
    )


def generate_fortunes(
    count: int = 1,
    *,
    category: Category | None = None,
    mode: Mode = "standard",
    include_numbers: bool = True,
    number_count: int = 4,
    rng: random.Random | None = None,
) -> tuple[Fortune, ...]:
    """Return several fortunes from one generator and the supplied RNG."""
    return FortuneGenerator(rng=rng).generate_many(
        count,
        category=category,
        mode=mode,
        include_numbers=include_numbers,
        number_count=number_count,
    )
