from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint

from hmde.db.base import Base
from hmde.models import (
    QualityException,
    QualityFinding,
    QualityMetric,
    QualityRule,
    QualityRuleCatalogue,
    QualityRun,
)


def test_quality_tables_are_registered() -> None:
    for model, name in (
        (QualityRuleCatalogue, "quality_rule_catalogue"),
        (QualityRule, "quality_rule"),
        (QualityRun, "quality_run"),
        (QualityFinding, "quality_finding"),
        (QualityException, "quality_exception"),
        (QualityMetric, "quality_metric"),
    ):
        assert model.__table__ is Base.metadata.tables[name]


def test_quality_rule_constraints() -> None:
    table = QualityRule.__table__
    checks = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    uniques = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert {"ck_quality_rule_dimension", "ck_quality_rule_severity"} <= checks
    assert "uq_quality_rule_catalogue_code" in uniques


def test_quality_run_has_lifecycle_and_versions() -> None:
    table = QualityRun.__table__
    checks = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "normalization_run_id",
        "dataset_version",
        "taxonomy_version",
        "catalogue_version",
        "code_version",
        "status",
        "report_path",
    } <= set(table.c.keys())
    assert {"ck_quality_run_status", "ck_quality_run_finished_at"} <= checks


def test_quality_finding_and_exception_constraints() -> None:
    finding = QualityFinding.__table__
    exception = QualityException.__table__
    finding_checks = {
        constraint.name
        for constraint in finding.constraints
        if isinstance(constraint, CheckConstraint)
    }
    finding_uniques = {
        constraint.name
        for constraint in finding.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    exception_uniques = {
        constraint.name
        for constraint in exception.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert {"ck_quality_finding_severity", "ck_quality_finding_status"} <= finding_checks
    assert "uq_quality_finding_run_key" in finding_uniques
    assert "uq_quality_exception_key" in exception_uniques


def test_quality_metric_has_denominator_and_scope() -> None:
    table = QualityMetric.__table__

    assert {
        "metric_code",
        "dimension",
        "scope_type",
        "scope_key",
        "numerator",
        "denominator",
        "value",
        "unit",
        "missing_count",
    } <= set(table.c.keys())
