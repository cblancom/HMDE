"""Versioned taxonomy read and descendant helpers."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import TaxonomyNode, TaxonomyVersion
from hmde.schemas.api import TaxonomyNodeResponse, TaxonomyResponse


def get_taxonomy(session: Session, version: str | None = None) -> TaxonomyResponse | None:
    if version is None:
        version = session.scalar(
            select(TaxonomyVersion.version).where(TaxonomyVersion.is_current.is_(True)).limit(1)
        )
    if version is None:
        return None
    nodes = session.scalars(
        select(TaxonomyNode)
        .where(TaxonomyNode.taxonomy_version == version)
        .order_by(TaxonomyNode.display_order, TaxonomyNode.code)
    )
    return TaxonomyResponse(
        version=version,
        nodes=[
            TaxonomyNodeResponse(
                code=node.code,
                name=node.name,
                parent_code=node.parent_code,
                assignable=node.assignable,
            )
            for node in nodes
        ],
    )


def descendant_codes(
    session: Session,
    code: str,
    version: str | None = None,
) -> set[str]:
    if version is None:
        version = session.scalar(
            select(TaxonomyVersion.version).where(TaxonomyVersion.is_current.is_(True)).limit(1)
        )
    if version is None:
        return set()
    rows = session.execute(
        select(TaxonomyNode.code, TaxonomyNode.parent_code).where(
            TaxonomyNode.taxonomy_version == version
        )
    ).all()
    known = {row.code for row in rows}
    if code not in known:
        return set()
    children: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.parent_code:
            children[row.parent_code].append(row.code)
    result: set[str] = set()
    stack = [code]
    while stack:
        current = stack.pop()
        if current in result:
            continue
        result.add(current)
        stack.extend(children.get(current, []))
    return result
