"""Band graph API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    label: str
    type: Literal["band", "producer"]


class GraphEdge(BaseModel):
    source: str
    target: str
    type: Literal["produced"]
    role: Literal["producer", "co-producer"]
    album_count: int
    albums: list[str]


class GraphMeta(BaseModel):
    fixture_version: str


class BandGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    meta: GraphMeta
