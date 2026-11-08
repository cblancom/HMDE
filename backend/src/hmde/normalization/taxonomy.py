"""Taxonomy version persistence and current projection synchronization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from hmde.models import Subgenre, TaxonomyNode, TaxonomyVersion

from .errors import TaxonomyValidationError


@dataclass(frozen=True, slots=True)
class TaxonomyEntry:
    code: str
    name: str
    parent_code: str | None
    assignable: bool
    display_order: int


@dataclass(frozen=True, slots=True)
class TaxonomyDocument:
    version: str
    source_hash: str
    source_path: str
    entries: tuple[TaxonomyEntry, ...]

    @property
    def by_code(self) -> dict[str, TaxonomyEntry]:
        return {entry.code: entry for entry in self.entries}

    @property
    def assignable_leaves(self) -> frozenset[str]:
        return frozenset(entry.code for entry in self.entries if entry.assignable)


@dataclass(frozen=True, slots=True)
class TaxonomySyncResult:
    version: str
    source_hash: str
    node_count: int
    leaf_count: int
    created: bool


def load_taxonomy_document(path: Path) -> TaxonomyDocument:
    if not path.is_file():
        raise TaxonomyValidationError(f"taxonomy does not exist: {path}")
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TaxonomyValidationError(f"could not read taxonomy: {path}") from exc
    entries = parse_taxonomy_payload(payload)
    source_hash = hashlib.sha256(raw).hexdigest()
    return TaxonomyDocument(
        version=_required_string(payload, "version"),
        source_hash=source_hash,
        source_path=str(path),
        entries=entries,
    )


def parse_taxonomy_payload(payload: object) -> tuple[TaxonomyEntry, ...]:
    if not isinstance(payload, dict):
        raise TaxonomyValidationError("taxonomy root must be a JSON object")
    _required_string(payload, "version")
    raw_nodes = payload.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise TaxonomyValidationError("taxonomy must contain a non-empty nodes array")

    entries: list[TaxonomyEntry] = []
    by_code: dict[str, TaxonomyEntry] = {}
    for index, raw_node in enumerate(raw_nodes, start=1):
        if not isinstance(raw_node, dict):
            raise TaxonomyValidationError(f"taxonomy node at position {index} must be an object")
        code = _required_string(raw_node, "code", position=index)
        name = _required_string(raw_node, "name", position=index)
        parent_code = raw_node.get("parent_code")
        if parent_code is not None and (
            not isinstance(parent_code, str) or not parent_code.strip()
        ):
            raise TaxonomyValidationError(f"taxonomy node {code!r} has an invalid parent_code")
        assignable = raw_node.get("assignable")
        if not isinstance(assignable, bool):
            raise TaxonomyValidationError(
                f"taxonomy node {code!r} must declare assignable as a boolean"
            )
        if code in by_code:
            raise TaxonomyValidationError(f"duplicate taxonomy code: {code}")
        entry = TaxonomyEntry(
            code=code,
            name=name,
            parent_code=parent_code.strip() if isinstance(parent_code, str) else None,
            assignable=assignable,
            display_order=index,
        )
        entries.append(entry)
        by_code[code] = entry

    children: dict[str, int] = {code: 0 for code in by_code}
    for entry in entries:
        if entry.parent_code is None:
            continue
        if entry.parent_code not in by_code:
            raise TaxonomyValidationError(
                f"taxonomy node {entry.code!r} references unknown parent {entry.parent_code!r}"
            )
        children[entry.parent_code] += 1

    for entry in entries:
        if entry.assignable and children[entry.code]:
            raise TaxonomyValidationError(
                f"taxonomy node {entry.code!r} is assignable but has children"
            )
        if not entry.assignable and not children[entry.code]:
            raise TaxonomyValidationError(f"taxonomy leaf {entry.code!r} must be assignable")

    for entry in entries:
        seen: set[str] = set()
        current: str | None = entry.code
        while current is not None:
            if current in seen:
                raise TaxonomyValidationError(
                    f"taxonomy contains a parent cycle involving {entry.code!r}"
                )
            seen.add(current)
            current = by_code[current].parent_code

    return tuple(entries)


def sync_taxonomy(
    session: Session,
    path: Path,
    *,
    make_current: bool = True,
) -> TaxonomySyncResult:
    document = load_taxonomy_document(path)
    existing = session.get(TaxonomyVersion, document.version)

    if existing is None:
        if make_current:
            session.execute(update(TaxonomyVersion).values(is_current=False))
        row = TaxonomyVersion(
            version=document.version,
            status="approved",
            source_hash=document.source_hash,
            source_path=document.source_path,
            is_current=make_current,
        )
        session.add(row)
        session.flush()
        for entry in _ordered_entries(document.entries):
            session.add(
                TaxonomyNode(
                    taxonomy_version=document.version,
                    code=entry.code,
                    name=entry.name,
                    parent_code=entry.parent_code,
                    assignable=entry.assignable,
                    display_order=entry.display_order,
                )
            )
        created = True
    else:
        if existing.source_hash != document.source_hash:
            raise TaxonomyValidationError(
                f"taxonomy version {document.version!r} already exists with different content"
            )
        node_count = session.scalar(
            select(func.count())
            .select_from(TaxonomyNode)
            .where(TaxonomyNode.taxonomy_version == document.version)
        )
        if node_count != len(document.entries):
            raise TaxonomyValidationError(
                f"taxonomy version {document.version!r} has inconsistent node history"
            )
        if make_current and not existing.is_current:
            session.execute(update(TaxonomyVersion).values(is_current=False))
            existing.is_current = True
        created = False

    for entry in document.entries:
        session.merge(Subgenre(code=entry.code, name=entry.name))

    session.flush()
    return TaxonomySyncResult(
        version=document.version,
        source_hash=document.source_hash,
        node_count=len(document.entries),
        leaf_count=len(document.assignable_leaves),
        created=created,
    )


def _ordered_entries(entries: tuple[TaxonomyEntry, ...]) -> tuple[TaxonomyEntry, ...]:
    by_code = {entry.code: entry for entry in entries}
    ordered: list[TaxonomyEntry] = []
    pending = set(by_code)
    while pending:
        ready = sorted(
            code
            for code in pending
            if by_code[code].parent_code is None or by_code[code].parent_code not in pending
        )
        if not ready:
            raise TaxonomyValidationError("taxonomy contains a parent cycle")
        for code in ready:
            ordered.append(by_code[code])
            pending.remove(code)
    return tuple(ordered)


def _required_string(
    payload: dict[str, Any],
    key: str,
    *,
    position: int | None = None,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        location = f"taxonomy node at position {position}" if position else "taxonomy"
        raise TaxonomyValidationError(f"{location} is missing a valid {key}")
    return value.strip()
