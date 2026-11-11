"""Read API v1 schemas beyond the E2 band contract."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AnalysisRunMeta(BaseModel):
    analysis_run_id: UUID
    analysis_version: str
    dataset_version: str
    taxonomy_version: str
    graph_version: str
    finished_at: datetime | None


class AnalysisRunListItem(AnalysisRunMeta):
    status: str
    code_version: str
    started_at: datetime
    report_path: str | None


class AnalysisRunListResponse(BaseModel):
    items: list[AnalysisRunListItem]
    total: int
    limit: int
    offset: int


class ArtistDetailResponse(BaseModel):
    id: UUID
    mbid: str
    name: str
    type: str
    country: str | None
    disambiguation: str | None


class AlbumCreditResponse(BaseModel):
    artist_id: UUID
    artist_name: str
    role: str
    role_name: str
    scope: str
    supporting_recording_count: int
    recording_count: int
    support_ratio: float | None
    confidence: float
    status: str


class AlbumListItem(BaseModel):
    id: UUID
    mbid: str
    title: str
    band_id: UUID
    band_name: str
    year: int | None
    first_release_date: date | None
    primary_subgenre: str | None
    producer_count: int
    credit_count: int


class AlbumListResponse(BaseModel):
    items: list[AlbumListItem]
    total: int
    limit: int
    offset: int


class AlbumDetailResponse(BaseModel):
    id: UUID
    mbid: str
    title: str
    band_id: UUID
    band_name: str
    year: int | None
    first_release_date: date | None
    primary_subgenre: str | None
    secondary_subgenres: list[str]
    credits: list[AlbumCreditResponse]


class CreditListItem(BaseModel):
    id: UUID
    album_id: UUID
    album_title: str
    band_id: UUID
    band_name: str
    artist_id: UUID
    artist_name: str
    role: str
    role_name: str
    scope: str
    confidence: float
    status: str


class CreditListResponse(BaseModel):
    items: list[CreditListItem]
    total: int
    limit: int
    offset: int


class ProducerListItem(BaseModel):
    id: UUID
    mbid: str
    name: str
    country: str | None
    artist_type: str
    album_count: int
    band_count: int
    self_produced_albums: int
    betweenness: float | None
    community_key: str | None


class ProducerListResponse(BaseModel):
    items: list[ProducerListItem]
    total: int
    limit: int
    offset: int


class ProducerAlbumSummary(BaseModel):
    album_id: UUID
    title: str
    band_name: str
    year: int | None
    role: str
    support_ratio: float | None


class ProducerBandSummary(BaseModel):
    band_id: UUID
    name: str
    album_count: int
    first_year: int | None
    last_year: int | None


class ProducerDetailResponse(BaseModel):
    id: UUID
    mbid: str
    name: str
    country: str | None
    artist_type: str
    album_count: int
    band_count: int
    self_produced_albums: int
    betweenness: float | None
    community_key: str | None
    top_albums: list[ProducerAlbumSummary]
    top_bands: list[ProducerBandSummary]
    meta: AnalysisRunMeta


class ProducerGraphNode(BaseModel):
    id: UUID
    type: Literal["producer", "album", "band"]
    label: str
    roles: list[str]
    attributes: dict[str, object]


class ProducerGraphEdge(BaseModel):
    source: UUID
    target: UUID
    layer: Literal["producer_album", "producer_band"]
    role: str
    weight: float
    support_ratio: float | None
    supporting_recordings: int | None
    album_recordings: int | None
    album_count: int | None
    evidence: dict[str, object]


class ProducerGraphLimits(BaseModel):
    limit: int
    depth: int
    max_nodes: int
    max_edges: int


class ProducerGraphMeta(BaseModel):
    view: Literal["albums", "bands"]
    analysis_run_id: UUID
    analysis_version: str
    dataset_version: str
    taxonomy_version: str
    graph_version: str
    truncated: bool
    limits: ProducerGraphLimits


class ProducerGraphResponse(BaseModel):
    nodes: list[ProducerGraphNode]
    edges: list[ProducerGraphEdge]
    meta: ProducerGraphMeta


class ProducerOverviewGraphLimits(BaseModel):
    producer_limit: int
    max_nodes: int
    max_edges: int


class ProducerOverviewGraphMeta(BaseModel):
    scope: Literal["overview"]
    view: Literal["albums", "bands"]
    analysis_run_id: UUID
    analysis_version: str
    dataset_version: str
    taxonomy_version: str
    graph_version: str
    truncated: bool
    matched_producers: int
    selected_producers: int
    include_isolated: bool
    limits: ProducerOverviewGraphLimits


class ProducerOverviewGraphResponse(BaseModel):
    nodes: list[ProducerGraphNode]
    edges: list[ProducerGraphEdge]
    meta: ProducerOverviewGraphMeta


class TaxonomyNodeResponse(BaseModel):
    code: str
    name: str
    parent_code: str | None
    assignable: bool


class TaxonomyResponse(BaseModel):
    version: str
    nodes: list[TaxonomyNodeResponse]


class SearchBandItem(BaseModel):
    id: UUID
    name: str
    subgenre: str | None


class SearchAlbumItem(BaseModel):
    id: UUID
    title: str
    band_name: str
    year: int | None


class SearchProducerItem(BaseModel):
    id: UUID
    name: str


class SearchResponse(BaseModel):
    query: str
    bands: list[SearchBandItem]
    albums: list[SearchAlbumItem]
    producers: list[SearchProducerItem]


class AnalyticsSummaryResponse(BaseModel):
    graph_counts: dict[str, object]
    support: dict[str, int]
    top_albums: list[dict[str, object]]
    top_bands: list[dict[str, object]]
    community_count: int
    meta: AnalysisRunMeta


class DecadeMetricItem(BaseModel):
    layer_code: str
    scope_key: str
    metric_code: str
    numerator: float | None
    denominator: float | None
    value: float
    unit: str


class DecadeMetricResponse(BaseModel):
    items: list[DecadeMetricItem]
    meta: AnalysisRunMeta


class CommunityListItem(BaseModel):
    community_key: str
    algorithm: str
    resolution: float
    size: int


class CommunityListResponse(BaseModel):
    items: list[CommunityListItem]
    total: int
    limit: int
    offset: int
    meta: AnalysisRunMeta


class CommunityMember(BaseModel):
    producer_id: UUID
    name: str


class CommunityDetailResponse(BaseModel):
    community_key: str
    algorithm: str
    resolution: float
    size: int
    members: list[CommunityMember]
    meta: AnalysisRunMeta
