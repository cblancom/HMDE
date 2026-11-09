"""SQLAlchemy models."""

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
    "Artist",
    "ArtistSubgenre",
    "ArtistSubgenreClassification",
    "Credit",
    "DatasetMembership",
    "ExternalId",
    "FixtureLoad",
    "IngestError",
    "IngestRun",
    "NormalizationIssue",
    "NormalizationIssueAction",
    "NormalizationRun",
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
]
