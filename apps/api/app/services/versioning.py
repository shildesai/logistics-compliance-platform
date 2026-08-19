"""Rules governing effective-dated regulatory content.

These invariants are what make an assurance claim defensible a year later:

  1. **Immutability once in force.** An ACTIVE, SUPERSEDED or RETIRED version
     cannot be edited. A change produces a new version. Without this, a finding
     raised last quarter could silently start referring to a rule that did not
     exist when it was raised.
  2. **No overlapping effective windows.** For one logical record, at most one
     version is in force on any given date, so "which rule applied on 3 March?"
     always has exactly one answer.
  3. **Governance before force.** A version cannot become ACTIVE without a
     reviewer and an approver recorded.
  4. **Coherent windows.** `effective_to` (exclusive) must be after
     `effective_from`.

They live here rather than in the database because they span the
container/version split and the lifecycle enum — a CHECK constraint cannot see
sibling rows, and an EXCLUDE constraint could not express "only among ACTIVE
versions of the same logical record".

Errors are raised, never swallowed (CLAUDE.md: "Never silently swallow
compliance engine errors").
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Protocol, TypeVar

from app.core.errors import AppError
from app.core.graph_enums import IMMUTABLE_STATUSES, PUBLISHED_STATUSES, LifecycleStatus


class VersioningError(AppError):
    """A change would violate an effective-dating invariant."""

    def __init__(self, message: str, code: str = "versioning_violation"):
        super().__init__(code=code, message=message, status_code=409)


class VersionedRecord(Protocol):
    """Structural type matching anything using the `Versioned` mixin."""

    version: int
    status: LifecycleStatus
    effective_from: date
    effective_to: date | None
    reviewed_by_id: object | None
    approved_by_id: object | None


V = TypeVar("V", bound=VersionedRecord)


def validate_window(record: VersionedRecord) -> None:
    """`effective_to` is exclusive, so it must be strictly after the start."""
    if record.effective_to is not None and record.effective_to <= record.effective_from:
        raise VersioningError(
            f"effective_to ({record.effective_to}) must be after effective_from "
            f"({record.effective_from})",
            code="invalid_effective_window",
        )


def windows_overlap(a: VersionedRecord, b: VersionedRecord) -> bool:
    """Whether two half-open [from, to) windows intersect.

    A NULL `effective_to` is treated as open-ended.
    """
    a_end = a.effective_to
    b_end = b.effective_to
    if a_end is not None and a_end <= b.effective_from:
        return False
    if b_end is not None and b_end <= a.effective_from:
        return False
    return True


def assert_no_overlap(candidate: VersionedRecord, siblings: Iterable[VersionedRecord]) -> None:
    """Refuse a candidate that would govern the same date as a sibling.

    Considers every *published* version, not just ACTIVE ones: a superseded
    version still governs its own window, so an overlap with it would make an
    as-at query ambiguous. Drafts are ignored — they govern nothing.
    """
    if candidate.status not in PUBLISHED_STATUSES:
        return

    for sibling in siblings:
        if sibling is candidate:
            continue
        if sibling.status not in PUBLISHED_STATUSES:
            continue
        if windows_overlap(candidate, sibling):
            raise VersioningError(
                f"Effective window [{candidate.effective_from}, {candidate.effective_to}) "
                f"overlaps published version {sibling.version} "
                f"[{sibling.effective_from}, {sibling.effective_to})",
                code="overlapping_effective_windows",
            )


def assert_mutable(record: VersionedRecord) -> None:
    """Refuse an in-place edit of content that is or has been in force."""
    if record.status in IMMUTABLE_STATUSES:
        raise VersioningError(
            f"Version {record.version} is {record.status.value} and cannot be modified "
            f"in place. Create a new version instead.",
            code="immutable_version",
        )


def assert_ready_to_activate(record: VersionedRecord) -> None:
    """Governance gate: nothing becomes binding without a review trail."""
    if record.reviewed_by_id is None:
        raise VersioningError(
            "A version cannot become ACTIVE without a recorded reviewer",
            code="missing_reviewer",
        )
    if record.approved_by_id is None:
        raise VersioningError(
            "A version cannot become ACTIVE without a recorded approver",
            code="missing_approver",
        )


def resolve_as_at(versions: Sequence[V], on: date) -> V | None:
    """The single version in force on `on`, or None.

    Returns None rather than falling back to the newest draft: if no rule was
    in force, the honest answer is "nothing applied", not a guess.
    """
    in_force = [v for v in versions if v.is_in_force_on(on)]  # type: ignore[attr-defined]
    if not in_force:
        return None
    if len(in_force) > 1:
        # assert_no_overlap should make this unreachable; if data has drifted,
        # fail loudly rather than silently picking one.
        raise VersioningError(
            f"{len(in_force)} versions are simultaneously in force on {on}: "
            f"{sorted(v.version for v in in_force)}",
            code="ambiguous_effective_version",
        )
    return in_force[0]


def current_version(versions: Sequence[V]) -> V | None:
    """The version in force today."""
    return resolve_as_at(versions, date.today())


def next_version_number(versions: Iterable[VersionedRecord]) -> int:
    return max((v.version for v in versions), default=0) + 1


def supersede(previous: V, *, replacement_effective_from: date) -> None:
    """Close a version's window so a successor can take over.

    Called as part of publishing the successor. The previous version becomes
    SUPERSEDED rather than being deleted — the history is the point.
    """
    if previous.status is not LifecycleStatus.ACTIVE:
        raise VersioningError(
            f"Only an ACTIVE version can be superseded; version {previous.version} "
            f"is {previous.status.value}",
            code="cannot_supersede",
        )
    if replacement_effective_from <= previous.effective_from:
        raise VersioningError(
            f"Replacement starts {replacement_effective_from}, which is not after the "
            f"version it supersedes ({previous.effective_from})",
            code="invalid_supersede_date",
        )
    previous.effective_to = replacement_effective_from
    previous.status = LifecycleStatus.SUPERSEDED
