"""Public exceptions for the fortune cookie package."""

from __future__ import annotations


class FortuneError(Exception):
    """Base application error."""


class InvalidOptionError(FortuneError, ValueError):
    """Invalid API options or incompatible combinations."""


class UnknownCategoryError(InvalidOptionError):
    """Category is not supported."""


class DatasetError(FortuneError):
    """Dataset could not be loaded or validated."""


class EmptyFortunePoolError(DatasetError):
    """No records are available for the selected pool."""
