"""Load and validate the bundled fortune datasets.

The validated catalogue is cached only after a successful load. Call
``clear_catalogue_cache`` from tests so a failure cannot leak into the next
case. There is no public API for reading an arbitrary file path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from typing import NoReturn, cast

from lupaxa.fortune.exceptions import DatasetError
from lupaxa.fortune.models import (
    CATEGORIES,
    RISK_LEVELS,
    Category,
    Mode,
    RiskLevel,
    display_text,
)

SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"[a-z][a-z0-9]*-[0-9]{3,}\Z")

_CACHE: Catalogue | None = None


@dataclass(frozen=True, slots=True)
class FortuneRecord:
    """One curated fortune before lucky numbers are attached."""

    id: str
    text: str
    mode: Mode
    category: Category | None = None
    risk_level: RiskLevel | None = None
    recommended_action: str | None = None


@dataclass(frozen=True, slots=True)
class Catalogue:
    """Immutable validated content used by the generator."""

    ordinary: tuple[FortuneRecord, ...]
    dark: tuple[FortuneRecord, ...]
    corporate: tuple[FortuneRecord, ...]
    oracle: tuple[FortuneRecord, ...]
    numbers: tuple[int, ...]

    def pool(self, mode: Mode, category: Category | None) -> tuple[FortuneRecord, ...]:
        """Return the source records for a mode, preserving dataset order."""
        if mode == "standard":
            if category is None:
                return self.ordinary
            return tuple(record for record in self.ordinary if record.category == category)
        if mode == "dark":
            return self.dark
        if mode == "corporate":
            return self.corporate
        return self.oracle


def clear_catalogue_cache() -> None:
    """Drop a successful catalogue cache. Failed loads are never stored."""
    global _CACHE
    _CACHE = None


def load_catalogue() -> Catalogue:
    """Load, validate, and cache the bundled datasets."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    catalogue = _load_bundled()
    _CACHE = catalogue
    return catalogue


def parse_json(text: str, *, resource: str) -> object:
    """Parse JSON and reject duplicate object keys."""

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        payload: dict[str, object] = {}
        for key, value in items:
            if key in payload:
                raise DatasetError(f"{resource}: duplicate key {key!r}")
            payload[key] = value
        return payload

    try:
        return json.loads(text, object_pairs_hook=pairs)
    except DatasetError:
        raise
    except json.JSONDecodeError as exc:
        raise DatasetError(f"{resource}: invalid JSON") from exc
    except UnicodeError as exc:
        raise DatasetError(f"{resource}: invalid UTF-8") from exc


def parse_ordinary(
    payload: object, *, resource: str = "fortunes.json"
) -> tuple[FortuneRecord, ...]:
    """Validate the ordinary fortune file."""
    fortunes = _fortune_list(payload, resource=resource, allowed=("schema_version", "fortunes"))
    records: list[FortuneRecord] = []
    seen_categories: set[str] = set()
    for index, item in enumerate(fortunes):
        record = _ordinary_record(item, resource=resource, index=index)
        seen_categories.add(record.category or "")
        records.append(record)
    missing = [category for category in CATEGORIES if category not in seen_categories]
    if missing:
        raise DatasetError(f"{resource}: missing categories {missing}")
    return tuple(records)


def parse_simple(payload: object, *, resource: str, mode: Mode) -> tuple[FortuneRecord, ...]:
    """Validate a dark or corporate fortune file."""
    fortunes = _fortune_list(payload, resource=resource, allowed=("schema_version", "fortunes"))
    return tuple(
        _simple_record(item, resource=resource, index=index, mode=mode)
        for index, item in enumerate(fortunes)
    )


def parse_oracle(payload: object, *, resource: str = "oracle.json") -> tuple[FortuneRecord, ...]:
    """Validate the oracle file."""
    fortunes = _fortune_list(payload, resource=resource, allowed=("schema_version", "fortunes"))
    return tuple(
        _oracle_record(item, resource=resource, index=index) for index, item in enumerate(fortunes)
    )


def parse_numbers(payload: object, *, resource: str = "lucky_numbers.json") -> tuple[int, ...]:
    """Validate the lucky-number pool."""
    body = _object(payload, resource=resource)
    _exact_keys(
        body,
        required=("schema_version", "numbers"),
        allowed=("schema_version", "numbers"),
        resource=resource,
    )
    _schema_version(body, resource=resource)
    raw_numbers = body["numbers"]
    if not isinstance(raw_numbers, list):
        raise DatasetError(f"{resource}: field 'numbers' must be a list")
    if len(raw_numbers) < 4:
        raise DatasetError(f"{resource}: field 'numbers' must contain at least four values")
    numbers: list[int] = []
    seen: set[int] = set()
    for index, raw in enumerate(raw_numbers):
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise DatasetError(f"{resource}: record {index}: field 'numbers' must be an integer")
        if raw < 0:
            raise DatasetError(f"{resource}: record {index}: field 'numbers' must be non-negative")
        if raw in seen:
            raise DatasetError(f"{resource}: record {index}: duplicate lucky number {raw}")
        seen.add(raw)
        numbers.append(raw)
    return tuple(numbers)


def assemble_catalogue(
    *,
    ordinary: tuple[FortuneRecord, ...],
    dark: tuple[FortuneRecord, ...],
    corporate: tuple[FortuneRecord, ...],
    oracle: tuple[FortuneRecord, ...],
    numbers: tuple[int, ...],
) -> Catalogue:
    """Reject duplicate IDs and fortune text across an already parsed catalogue."""
    seen_ids: set[str] = set()
    seen_text: set[str] = set()
    for record in (*ordinary, *dark, *corporate, *oracle):
        if record.id in seen_ids:
            raise DatasetError(f"duplicate id {record.id!r}")
        folded = record.text.casefold()
        if folded in seen_text:
            raise DatasetError(f"{record.id}: duplicate fortune text")
        seen_ids.add(record.id)
        seen_text.add(folded)
    return Catalogue(
        ordinary=ordinary,
        dark=dark,
        corporate=corporate,
        oracle=oracle,
        numbers=numbers,
    )


def _load_bundled() -> Catalogue:
    ordinary = parse_ordinary(parse_json(_read("fortunes.json"), resource="fortunes.json"))
    dark = parse_simple(
        parse_json(_read("dark.json"), resource="dark.json"),
        resource="dark.json",
        mode="dark",
    )
    corporate = parse_simple(
        parse_json(_read("corporate.json"), resource="corporate.json"),
        resource="corporate.json",
        mode="corporate",
    )
    oracle = parse_oracle(parse_json(_read("oracle.json"), resource="oracle.json"))
    numbers = parse_numbers(parse_json(_read("lucky_numbers.json"), resource="lucky_numbers.json"))
    return assemble_catalogue(
        ordinary=ordinary,
        dark=dark,
        corporate=corporate,
        oracle=oracle,
        numbers=numbers,
    )


def _read(name: str) -> str:
    try:
        return files("lupaxa.fortune").joinpath("data").joinpath(name).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise DatasetError(f"{name}: could not read bundled data") from exc


def _fortune_list(payload: object, *, resource: str, allowed: tuple[str, ...]) -> list[object]:
    body = _object(payload, resource=resource)
    _exact_keys(body, required=("schema_version", "fortunes"), allowed=allowed, resource=resource)
    _schema_version(body, resource=resource)
    fortunes = body["fortunes"]
    if not isinstance(fortunes, list):
        raise DatasetError(f"{resource}: field 'fortunes' must be a list")
    if not fortunes:
        raise DatasetError(f"{resource}: field 'fortunes' must not be empty")
    return fortunes


def _ordinary_record(item: object, *, resource: str, index: int) -> FortuneRecord:
    body = _record_object(item, resource=resource, index=index)
    _exact_keys(
        body,
        required=("id", "category", "text"),
        allowed=("id", "category", "text"),
        resource=resource,
        index=index,
    )
    category = body["category"]
    record_id = _identifier(body["id"], resource=resource, index=index, prefix=None)
    if not isinstance(category, str) or category not in CATEGORIES:
        _field_error(resource, index, record_id, "category", "is not an ordinary category")
    if not record_id.startswith(f"{category}-"):
        _field_error(resource, index, record_id, "id", "must begin with the category name")
    text = _entry_text(
        body["text"], resource=resource, index=index, record_id=record_id, field="text"
    )
    return FortuneRecord(
        id=record_id,
        text=text,
        mode="standard",
        category=cast(Category, category),
    )


def _simple_record(item: object, *, resource: str, index: int, mode: Mode) -> FortuneRecord:
    body = _record_object(item, resource=resource, index=index)
    _exact_keys(
        body, required=("id", "text"), allowed=("id", "text"), resource=resource, index=index
    )
    record_id = _identifier(body["id"], resource=resource, index=index, prefix=mode)
    text = _entry_text(
        body["text"], resource=resource, index=index, record_id=record_id, field="text"
    )
    return FortuneRecord(id=record_id, text=text, mode=mode, category=None)


def _oracle_record(item: object, *, resource: str, index: int) -> FortuneRecord:
    body = _record_object(item, resource=resource, index=index)
    _exact_keys(
        body,
        required=("id", "text", "risk_level", "recommended_action"),
        allowed=("id", "text", "risk_level", "recommended_action"),
        resource=resource,
        index=index,
    )
    record_id = _identifier(body["id"], resource=resource, index=index, prefix="oracle")
    text = _entry_text(
        body["text"], resource=resource, index=index, record_id=record_id, field="text"
    )
    risk = body["risk_level"]
    if not isinstance(risk, str) or risk not in RISK_LEVELS:
        _field_error(resource, index, record_id, "risk_level", "is not a known risk level")
    action = _entry_text(
        body["recommended_action"],
        resource=resource,
        index=index,
        record_id=record_id,
        field="recommended_action",
    )
    return FortuneRecord(
        id=record_id,
        text=text,
        mode="oracle",
        category=None,
        risk_level=cast(RiskLevel, risk),
        recommended_action=action,
    )


def _object(payload: object, *, resource: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise DatasetError(f"{resource}: top-level value must be a JSON object")
    return payload


def _record_object(item: object, *, resource: str, index: int) -> dict[str, object]:
    if not isinstance(item, dict):
        raise DatasetError(f"{resource}: record {index}: value must be a JSON object")
    return item


def _exact_keys(
    body: dict[str, object],
    *,
    required: tuple[str, ...],
    allowed: tuple[str, ...],
    resource: str,
    index: int | None = None,
) -> None:
    where = resource if index is None else f"{resource}: record {index}"
    missing = [key for key in required if key not in body]
    unknown = [key for key in body if key not in allowed]
    if missing:
        raise DatasetError(f"{where}: missing field {missing[0]!r}")
    if unknown:
        raise DatasetError(f"{where}: unknown field {unknown[0]!r}")


def _schema_version(body: dict[str, object], *, resource: str) -> None:
    version = body["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise DatasetError(f"{resource}: field 'schema_version' must be an integer")
    if version != SCHEMA_VERSION:
        raise DatasetError(f"{resource}: unsupported schema_version {version}")


def _identifier(value: object, *, resource: str, index: int, prefix: str | None) -> str:
    try:
        text = display_text(value, field="id")
    except ValueError as exc:
        raise DatasetError(f"{resource}: record {index}: field 'id' is invalid") from exc
    if ID_PATTERN.fullmatch(text) is None:
        raise DatasetError(f"{resource}: record {index}: field 'id' has the wrong shape")
    if prefix is not None and not text.startswith(f"{prefix}-"):
        raise DatasetError(
            f"{resource}: record {index} ({text}): field 'id' must begin with {prefix!r}"
        )
    return text


def _entry_text(value: object, *, resource: str, index: int, record_id: str, field: str) -> str:
    try:
        return display_text(value, field=field)
    except ValueError as exc:
        raise DatasetError(
            f"{resource}: record {index} ({record_id}): field {field!r} is invalid"
        ) from exc


def _field_error(resource: str, index: int, record_id: str, field: str, message: str) -> NoReturn:
    raise DatasetError(f"{resource}: record {index} ({record_id}): field {field!r} {message}")
