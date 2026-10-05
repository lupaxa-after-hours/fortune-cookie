"""Keep the catalogue cache from leaking between tests."""

from __future__ import annotations

import pytest

from lupaxa.fortune.catalogue import clear_catalogue_cache


@pytest.fixture(autouse=True)
def _clear_catalogue_cache() -> object:
    clear_catalogue_cache()
    yield
    clear_catalogue_cache()
