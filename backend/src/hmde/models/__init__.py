"""SQLAlchemy models."""

from hmde.models.analytics import (
    AnalysisRun,
    Community,
    CommunityMembership,
    GraphEdge,
    GraphNode,
    NodeMetric,
    ProducerMetric,
    TemporalMetric,
)
from hmde.models.artist import Artist, ExternalId
from hmde.models.catalog import Recording, RecordingRelease, Release, ReleaseGroup
from hmde.models.credit import Credit, Role, SourceRecord
from hmde.models.fixture import FixtureLoad
from hmde.models.ingestion import IngestError, IngestRun, RawResponse
from hmde.models.normalization import (
    ArtistSubgenreClassification,
    DatasetMembership,
    NormalizationIssue,
    NormalizationIssueAction,
    NormalizationRun,
    ReleaseGroupSubgenre,
    TaxonomyNode,
    TaxonomyVersion,
)
from hmde.models.quality import (
    QualityException,
    QualityFinding,
    QualityMetric,
    QualityRule,
    QualityRuleCatalogue,
    QualityRun,
)
from hmde.models.subgenre import ArtistSubgenre, Subgenre

__all__ = [
    "AnalysisRun",
    "Artist",
    "ArtistSubgenre",
    "ArtistSubgenreClassification",
    "Community",
    "CommunityMembership",
    "Credit",
    "DatasetMembership",
    "ExternalId",
    "FixtureLoad",
    "GraphEdge",
    "GraphNode",
    "IngestError",
    "IngestRun",
    "NormalizationIssue",
    "NormalizationIssueAction",
    "NodeMetric",
    "NormalizationRun",
    "ProducerMetric",
    "QualityException",
    "QualityFinding",
    "QualityMetric",
    "QualityRule",
    "QualityRuleCatalogue",
    "QualityRun",
    "RawResponse",
    "ReleaseGroupSubgenre",
    "Recording",
    "RecordingRelease",
    "Release",
    "ReleaseGroup",
    "Role",
    "SourceRecord",
    "Subgenre",
    "TaxonomyNode",
    "TaxonomyVersion",
    "TemporalMetric",
]
