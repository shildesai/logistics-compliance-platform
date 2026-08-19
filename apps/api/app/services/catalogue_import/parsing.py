"""Parse and validate the source catalogue before anything touches the database.

Validation runs as a separate pass so a malformed catalogue is rejected whole
rather than half-imported. Errors are collected rather than raised one at a
time, so a reviewer sees every problem in one report instead of fixing them
one re-run at a time.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from app.core.graph_enums import PsoeDimension, TestType
from app.services.catalogue_import import vocabulary as vocab

TEST_ID_PATTERN = re.compile(r"^[A-Z]{3}-\d{3}$")

REQUIRED_FIELDS = (
    "domain",
    "control_test_id",
    "name",
    "obligation",
    "risk",
    "control",
    "evidence",
    "data_sources",
    "required_data_fields",
    "test_type",
    "test_logic",
    "psoe_dimension",
    "default_severity",
    "remediation_template",
    "human_review_required",
)


@dataclass(frozen=True)
class ValidationIssue:
    """A problem with the source. `fatal` issues abort the import."""

    entity_id: str
    field: str
    message: str
    fatal: bool = True

    def __str__(self) -> str:
        severity = "ERROR" if self.fatal else "WARN "
        return f"{severity} {self.entity_id} [{self.field}] {self.message}"


@dataclass
class SourceCatalogue:
    """A parsed, validated catalogue."""

    path: Path
    version: str
    date: str
    checksum: str
    entries: list[dict]
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def file_name(self) -> str:
        return self.path.name

    @property
    def fatal_issues(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.fatal]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if not i.fatal]

    def citation(self, entity_id: str) -> str:
        return f"{self.file_name}#{entity_id} (catalogue v{self.version}, {self.date})"

    def entries_by_domain(self) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = defaultdict(list)
        for entry in self.entries:
            grouped[entry["domain"]].append(entry)
        return dict(grouped)


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_catalogue(path: Path) -> SourceCatalogue:
    """Read, parse and validate. Never touches the database."""
    payload = json.loads(path.read_text())

    catalogue = SourceCatalogue(
        path=path,
        version=str(payload.get("version", "unknown")),
        date=str(payload.get("date", "unknown")),
        checksum=_checksum(path),
        entries=list(payload.get("controls", [])),
    )
    catalogue.issues.extend(_validate(catalogue))
    return catalogue


def _validate(catalogue: SourceCatalogue) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    entries = catalogue.entries

    if not entries:
        return [ValidationIssue("<file>", "controls", "Catalogue contains no entries")]

    seen_ids: set[str] = set()

    for entry in entries:
        entity_id = str(entry.get("control_test_id", "<missing id>"))

        for name in REQUIRED_FIELDS:
            if name not in entry or entry[name] in (None, "", []):
                issues.append(ValidationIssue(entity_id, name, "Required field missing or empty"))

        if "control_test_id" in entry:
            if not TEST_ID_PATTERN.match(entity_id):
                issues.append(
                    ValidationIssue(
                        entity_id,
                        "control_test_id",
                        f"Does not match expected format AAA-999: {entity_id!r}",
                    )
                )
            if entity_id in seen_ids:
                # Duplicates would make the idempotency key ambiguous.
                issues.append(
                    ValidationIssue(entity_id, "control_test_id", "Duplicate control_test_id")
                )
            seen_ids.add(entity_id)

        issues.extend(_validate_vocabulary(entity_id, entry))

    issues.extend(_validate_domain_consistency(catalogue))
    return issues


def _validate_vocabulary(entity_id: str, entry: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    raw_type = str(entry.get("test_type", "")).strip().lower()
    if raw_type and raw_type not in vocab.TEST_TYPES:
        issues.append(
            ValidationIssue(
                entity_id,
                "test_type",
                f"Unknown test type {entry.get('test_type')!r}; refusing to guess a default",
            )
        )

    for token in str(entry.get("psoe_dimension", "")).split("/"):
        token = token.strip().lower()
        if token and token not in vocab.PSOE_DIMENSIONS:
            issues.append(
                ValidationIssue(entity_id, "psoe_dimension", f"Unknown PSOE dimension {token!r}")
            )

    severity = str(entry.get("default_severity", "")).strip().lower()
    if severity and severity not in vocab.SEVERITIES:
        issues.append(
            ValidationIssue(entity_id, "default_severity", f"Unknown severity {severity!r}")
        )

    for source in entry.get("data_sources", []) or []:
        if str(source).strip().lower() not in vocab.EVIDENCE_SOURCES:
            issues.append(
                ValidationIssue(
                    entity_id,
                    "data_sources",
                    f"Unmapped data source {source!r}; add it to the vocabulary rather "
                    f"than letting it fall through to a default",
                )
            )

    # A safety invariant, not a source problem: AI output can never be a final
    # determination, so this is corrected on import and reported as a warning.
    if raw_type == "ai" and entry.get("human_review_required") is False:
        issues.append(
            ValidationIssue(
                entity_id,
                "human_review_required",
                "AI-assisted test declares human_review_required=false; overridden to true",
                fatal=False,
            )
        )

    return issues


def _validate_domain_consistency(catalogue: SourceCatalogue) -> list[ValidationIssue]:
    """The import collapses each domain into one obligation/risk/control.

    That is only sound if every entry in the domain agrees on them. Disagreement
    is reported rather than resolved by arbitrarily taking the first value.
    """
    issues: list[ValidationIssue] = []

    for domain, entries in catalogue.entries_by_domain().items():
        for field_name in ("obligation", "risk", "control"):
            distinct = {str(e.get(field_name, "")).strip() for e in entries}
            if len(distinct) > 1:
                issues.append(
                    ValidationIssue(
                        f"DOMAIN:{domain}",
                        field_name,
                        f"Domain has {len(distinct)} distinct {field_name} values; the import "
                        f"collapses a domain into one, so this is ambiguous: {sorted(distinct)}",
                    )
                )

        prefixes = {vocab.code_prefix(str(e.get("control_test_id", ""))) for e in entries}
        if len(prefixes) > 1:
            issues.append(
                ValidationIssue(
                    f"DOMAIN:{domain}",
                    "control_test_id",
                    f"Domain spans multiple code prefixes {sorted(prefixes)}; derived codes "
                    f"would not be stable",
                )
            )

    # A prefix shared by two domains would make derived codes collide.
    prefix_to_domains: dict[str, set[str]] = defaultdict(set)
    for domain, entries in catalogue.entries_by_domain().items():
        for entry in entries:
            prefix_to_domains[vocab.code_prefix(str(entry.get("control_test_id", "")))].add(domain)
    for prefix, domains in prefix_to_domains.items():
        if len(domains) > 1:
            issues.append(
                ValidationIssue(
                    f"PREFIX:{prefix}",
                    "control_test_id",
                    f"Prefix used by multiple domains {sorted(domains)}; derived codes collide",
                )
            )

    return issues


# --- Value transformations ------------------------------------------------


def parse_test_type(raw: str) -> tuple[TestType, bool]:
    """Return the mapped type and whether the mapping was a normalisation."""
    key = raw.strip().lower()
    return vocab.TEST_TYPES[key], key in vocab.NORMALISED_TEST_TYPES


def parse_psoe(raw: str) -> list[PsoeDimension]:
    """Split "Operating/Effective" into its dimensions, preserving order."""
    dimensions: list[PsoeDimension] = []
    for token in raw.split("/"):
        token = token.strip().lower()
        if not token:
            continue
        dimension = vocab.PSOE_DIMENSIONS[token]
        if dimension not in dimensions:
            dimensions.append(dimension)
    return dimensions


def parse_remediation_steps(raw: str) -> list[str]:
    """The source joins discrete actions with semicolons."""
    return [step.strip() for step in raw.split(";") if step.strip()]


def parse_severity(raw: str) -> str:
    return vocab.SEVERITIES[raw.strip().lower()]
