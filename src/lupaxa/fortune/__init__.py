"""lupaxa.fortune — developer fortune cookies.

Importing this package does not read the bundled datasets. Generation loads
and validates them on first use.
"""

from __future__ import annotations

from .exceptions import (
    DatasetError,
    EmptyFortunePoolError,
    FortuneError,
    InvalidOptionError,
    UnknownCategoryError,
)
from .generator import FortuneGenerator, generate_fortune, generate_fortunes
from .models import Category, Fortune, Mode, RiskLevel, list_categories
from .version import __version__, get_version

__all__ = [
    "Category",
    "DatasetError",
    "EmptyFortunePoolError",
    "Fortune",
    "FortuneError",
    "FortuneGenerator",
    "InvalidOptionError",
    "Mode",
    "RiskLevel",
    "UnknownCategoryError",
    "__version__",
    "generate_fortune",
    "generate_fortunes",
    "get_version",
    "list_categories",
]
