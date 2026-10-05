"""Dataset parsing, chaining, and cache behaviour."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from lupaxa.fortune.catalogue import (
    FortuneRecord,
    assemble_catalogue,
    clear_catalogue_cache,
    load_catalogue,
    parse_json,
    parse_numbers,
    parse_oracle,
    parse_ordinary,
    parse_simple,
)
from lupaxa.fortune.exceptions import DatasetError
from lupaxa.fortune.models import CATEGORIES


def _ordinary_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "fortunes": [
            {
                "id": f"{category}-001",
                "category": category,
                "text": f"Fortune about {category} only.",
            }
            for category in CATEGORIES
        ],
    }


def test_bundled_catalogue_loads() -> None:
    """The packaged files cover every mode and category."""
    first = load_catalogue()
    second = load_catalogue()
    assert first is second
    assert {record.category for record in first.ordinary} == set(CATEGORIES)
    assert first.dark
    assert first.corporate
    assert first.oracle
    assert len(first.numbers) >= 4


def test_failed_load_does_not_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """A read failure is raised and the next attempt can succeed."""

    def boom(_name: str) -> str:
        raise DatasetError("missing")

    monkeypatch.setattr("lupaxa.fortune.catalogue._read", boom)
    with pytest.raises(DatasetError, match="missing"):
        load_catalogue()
    monkeypatch.undo()
    clear_catalogue_cache()
    assert load_catalogue().ordinary


def test_import_does_not_load_catalogue() -> None:
    """Importing the public package does not read the datasets."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import lupaxa.fortune; "
                "raise SystemExit('lupaxa.fortune.catalogue' in sys.modules)"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_missing_resource_is_chained() -> None:
    """A missing bundled file keeps the original exception as the cause."""
    from lupaxa.fortune import catalogue

    with pytest.raises(DatasetError, match="could not read") as exc:
        catalogue._read("missing.json")
    assert exc.value.__cause__ is not None


def test_duplicate_json_key() -> None:
    """Duplicate object keys are a dataset error."""
    raw = '{"schema_version": 1, "schema_version": 1, "fortunes": []}'
    with pytest.raises(DatasetError, match="duplicate key"):
        parse_json(raw, resource="fortunes.json")


def test_invalid_json_is_chained() -> None:
    """Malformed JSON points at the resource and keeps the decode error."""
    with pytest.raises(DatasetError, match="invalid JSON") as exc:
        parse_json("{", resource="fortunes.json")
    assert isinstance(exc.value.__cause__, json.JSONDecodeError)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ([], "JSON object"),
        ({"fortunes": []}, "missing field"),
        ({"schema_version": 1, "fortunes": [], "extra": 1}, "unknown field"),
        ({"schema_version": True, "fortunes": [1]}, "schema_version"),
        ({"schema_version": 2, "fortunes": [1]}, "unsupported schema_version"),
        ({"schema_version": 1, "fortunes": "nope"}, "must be a list"),
        ({"schema_version": 1, "fortunes": []}, "must not be empty"),
        ({"schema_version": 1, "fortunes": ["nope"]}, "JSON object"),
    ],
)
def test_ordinary_shape_errors(payload: object, match: str) -> None:
    """The ordinary file rejects broken envelopes."""
    with pytest.raises(DatasetError, match=match):
        parse_ordinary(payload)


def test_record_field_errors() -> None:
    """Record-level problems name the resource, index, and field."""
    payload = _ordinary_payload()
    fortunes = payload["fortunes"]
    assert isinstance(fortunes, list)
    fortunes[0] = {"id": "wisdom-001", "category": "wisdom", "text": "  padded  "}
    with pytest.raises(DatasetError, match="record 0") as exc:
        parse_ordinary(payload)
    assert exc.value.__cause__ is not None
    fortunes[0] = {"id": "nope", "category": "wisdom", "text": "Fine text."}
    with pytest.raises(DatasetError, match="wrong shape"):
        parse_ordinary(payload)
    fortunes[0] = {"id": "warning-001", "category": "wisdom", "text": "Fine text."}
    with pytest.raises(DatasetError, match="begin with the category"):
        parse_ordinary(payload)
    fortunes[0] = {"id": "wisdom-001", "category": "sideways", "text": "Fine text."}
    with pytest.raises(DatasetError, match="not an ordinary category"):
        parse_ordinary(payload)
    fortunes[0] = {"category": "wisdom", "text": "Fine text."}
    with pytest.raises(DatasetError, match="missing field 'id'"):
        parse_ordinary(payload)


def test_missing_category() -> None:
    """Every ordinary category must be present."""
    payload = _ordinary_payload()
    fortunes = payload["fortunes"]
    assert isinstance(fortunes, list)
    del fortunes[-1]
    with pytest.raises(DatasetError, match="missing categories"):
        parse_ordinary(payload)


def test_simple_and_oracle_rules() -> None:
    """Special files reject the wrong fields and bad risk levels."""
    with pytest.raises(DatasetError, match="unknown field"):
        parse_simple(
            {
                "schema_version": 1,
                "fortunes": [{"id": "dark-001", "text": "Bleak humour.", "category": "devops"}],
            },
            resource="dark.json",
            mode="dark",
        )
    with pytest.raises(DatasetError, match="risk_level"):
        parse_oracle(
            {
                "schema_version": 1,
                "fortunes": [
                    {
                        "id": "oracle-001",
                        "text": "An omen.",
                        "risk_level": "dire",
                        "recommended_action": "Wait.",
                    }
                ],
            }
        )
    with pytest.raises(DatasetError, match="missing field 'recommended_action'"):
        parse_oracle(
            {
                "schema_version": 1,
                "fortunes": [{"id": "oracle-001", "text": "An omen.", "risk_level": "low"}],
            }
        )


def test_lucky_number_rules() -> None:
    """The number pool rejects bools, duplicates, negatives, and short lists."""
    base = {"schema_version": 1, "numbers": [1, 2, 3, 4]}
    assert parse_numbers(base) == (1, 2, 3, 4)
    for numbers, match in (
        ([1, 2, 3], "at least four"),
        ([1, 2, 3, True], "integer"),
        ([1, 2, 3, -1], "non-negative"),
        ([1, 2, 3, 3], "duplicate"),
        ([1, 2, 3, 1.5], "integer"),
    ):
        with pytest.raises(DatasetError, match=match):
            parse_numbers({"schema_version": 1, "numbers": numbers})


def test_duplicate_id_and_text_across_files() -> None:
    """IDs and fortune text are unique across the whole catalogue."""
    ordinary = parse_ordinary(_ordinary_payload())
    dark = (FortuneRecord(id="wisdom-001", text="Different dark text.", mode="dark"),)
    with pytest.raises(DatasetError, match="duplicate id"):
        assemble_catalogue(
            ordinary=ordinary, dark=dark, corporate=(), oracle=(), numbers=(1, 2, 3, 4)
        )
    dark = (FortuneRecord(id="dark-001", text="Fortune about wisdom only.", mode="dark"),)
    with pytest.raises(DatasetError, match="duplicate fortune text"):
        assemble_catalogue(
            ordinary=ordinary, dark=dark, corporate=(), oracle=(), numbers=(1, 2, 3, 4)
        )


def test_more_dataset_rejections() -> None:
    """Numbers, identifiers, and decode errors name the failing field."""
    with pytest.raises(DatasetError, match="must be a list"):
        parse_numbers({"schema_version": 1, "numbers": "1234"})
    payload = _ordinary_payload()
    fortunes = payload["fortunes"]
    assert isinstance(fortunes, list)
    fortunes[0] = {"id": "", "category": "wisdom", "text": "Fine text."}
    with pytest.raises(DatasetError, match="field 'id' is invalid") as exc:
        parse_ordinary(payload)
    assert isinstance(exc.value.__cause__, ValueError)

    def boom(*_args: object, **_kwargs: object) -> object:
        raise UnicodeError("bad bytes")

    monkey_json = pytest.MonkeyPatch()
    monkey_json.setattr(json, "loads", boom)
    try:
        with pytest.raises(DatasetError, match="invalid UTF-8") as unicode_exc:
            parse_json("{}", resource="fortunes.json")
    finally:
        monkey_json.undo()
    assert isinstance(unicode_exc.value.__cause__, UnicodeError)
