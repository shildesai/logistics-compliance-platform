"""Unit tests for effective-dating invariants.

These use lightweight stand-ins rather than ORM objects: the rules are pure
functions over the `Versioned` shape, and testing them without a database keeps
them fast and makes the intent obvious.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

import pytest

from app.core.graph_enums import PUBLISHED_STATUSES, LifecycleStatus
from app.services.versioning import (
    VersioningError,
    assert_mutable,
    assert_no_overlap,
    assert_ready_to_activate,
    next_version_number,
    resolve_as_at,
    supersede,
    validate_window,
    windows_overlap,
)

REVIEWER = uuid4()
APPROVER = uuid4()


@dataclass
class FakeVersion:
    """Minimal stand-in matching the Versioned mixin's shape."""

    version: int = 1
    status: LifecycleStatus = LifecycleStatus.ACTIVE
    effective_from: date = date(2024, 1, 1)
    effective_to: date | None = None
    reviewed_by_id: UUID | None = field(default=REVIEWER)
    approved_by_id: UUID | None = field(default=APPROVER)

    def is_in_force_on(self, on: date) -> bool:
        if self.status not in PUBLISHED_STATUSES:
            return False
        if on < self.effective_from:
            return False
        return self.effective_to is None or on < self.effective_to


# --- Window validity ------------------------------------------------------


def test_open_ended_window_is_valid():
    validate_window(FakeVersion(effective_to=None))


def test_effective_to_after_effective_from_is_valid():
    validate_window(FakeVersion(effective_from=date(2024, 1, 1), effective_to=date(2025, 1, 1)))


@pytest.mark.parametrize(
    "start,end",
    [
        (date(2024, 6, 1), date(2024, 6, 1)),  # zero-length
        (date(2024, 6, 1), date(2024, 1, 1)),  # inverted
    ],
)
def test_invalid_windows_are_rejected(start, end):
    with pytest.raises(VersioningError) as exc:
        validate_window(FakeVersion(effective_from=start, effective_to=end))
    assert exc.value.code == "invalid_effective_window"


# --- Overlap detection ----------------------------------------------------


def test_adjacent_windows_do_not_overlap():
    """Half-open windows: a successor may start the day the predecessor ends."""
    first = FakeVersion(effective_from=date(2024, 1, 1), effective_to=date(2025, 1, 1))
    second = FakeVersion(effective_from=date(2025, 1, 1), effective_to=None)
    assert windows_overlap(first, second) is False


def test_contained_window_overlaps():
    outer = FakeVersion(effective_from=date(2024, 1, 1), effective_to=date(2026, 1, 1))
    inner = FakeVersion(effective_from=date(2025, 1, 1), effective_to=date(2025, 6, 1))
    assert windows_overlap(outer, inner) is True


def test_two_open_ended_windows_overlap():
    assert windows_overlap(FakeVersion(), FakeVersion()) is True


def test_open_ended_window_overlaps_a_later_closed_one():
    open_ended = FakeVersion(effective_from=date(2024, 1, 1), effective_to=None)
    later = FakeVersion(effective_from=date(2030, 1, 1), effective_to=date(2031, 1, 1))
    assert windows_overlap(open_ended, later) is True


def test_overlapping_published_versions_are_rejected():
    existing = FakeVersion(version=1, effective_from=date(2024, 1, 1), effective_to=None)
    candidate = FakeVersion(version=2, effective_from=date(2025, 1, 1), effective_to=None)

    with pytest.raises(VersioningError) as exc:
        assert_no_overlap(candidate, [existing])
    assert exc.value.code == "overlapping_effective_windows"


def test_superseded_versions_still_block_overlap():
    """A superseded version governs its own window, so an overlap with it
    would make a historical query ambiguous."""
    superseded = FakeVersion(
        version=1,
        status=LifecycleStatus.SUPERSEDED,
        effective_from=date(2024, 1, 1),
        effective_to=date(2026, 1, 1),
    )
    candidate = FakeVersion(version=2, effective_from=date(2025, 1, 1), effective_to=None)

    with pytest.raises(VersioningError):
        assert_no_overlap(candidate, [superseded])


def test_draft_versions_never_conflict():
    """Drafts govern nothing, so they may share dates freely."""
    draft = FakeVersion(version=2, status=LifecycleStatus.DRAFT)
    active = FakeVersion(version=1, status=LifecycleStatus.ACTIVE)

    assert_no_overlap(draft, [active])  # candidate is a draft
    assert_no_overlap(active, [draft])  # sibling is a draft


def test_a_version_does_not_conflict_with_itself():
    version = FakeVersion()
    assert_no_overlap(version, [version])


# --- Immutability ---------------------------------------------------------


@pytest.mark.parametrize("status", sorted(PUBLISHED_STATUSES))
def test_published_versions_cannot_be_edited_in_place(status):
    with pytest.raises(VersioningError) as exc:
        assert_mutable(FakeVersion(status=status))
    assert exc.value.code == "immutable_version"


@pytest.mark.parametrize(
    "status",
    [LifecycleStatus.DRAFT, LifecycleStatus.IN_REVIEW, LifecycleStatus.APPROVED],
)
def test_unpublished_versions_can_be_edited(status):
    assert_mutable(FakeVersion(status=status))


# --- Governance gate ------------------------------------------------------


def test_activation_requires_a_reviewer():
    with pytest.raises(VersioningError) as exc:
        assert_ready_to_activate(FakeVersion(reviewed_by_id=None))
    assert exc.value.code == "missing_reviewer"


def test_activation_requires_an_approver():
    with pytest.raises(VersioningError) as exc:
        assert_ready_to_activate(FakeVersion(approved_by_id=None))
    assert exc.value.code == "missing_approver"


def test_fully_governed_version_may_activate():
    assert_ready_to_activate(FakeVersion())


# --- As-at resolution -----------------------------------------------------


@pytest.fixture()
def two_generation_history() -> list[FakeVersion]:
    """v1 governed 2024-01-01 → 2026-02-01, then v2 took over."""
    return [
        FakeVersion(
            version=1,
            status=LifecycleStatus.SUPERSEDED,
            effective_from=date(2024, 1, 1),
            effective_to=date(2026, 2, 1),
        ),
        FakeVersion(
            version=2,
            status=LifecycleStatus.ACTIVE,
            effective_from=date(2026, 2, 1),
            effective_to=None,
        ),
    ]


def test_as_at_returns_the_superseded_version_for_a_past_date(two_generation_history):
    """The central point of effective-dating: a past assessment resolves to
    the rule that actually applied then, not to today's rule."""
    found = resolve_as_at(two_generation_history, date(2025, 6, 1))
    assert found is not None
    assert found.version == 1


def test_as_at_returns_the_current_version_for_today(two_generation_history):
    found = resolve_as_at(two_generation_history, date(2026, 8, 19))
    assert found is not None
    assert found.version == 2


def test_as_at_on_the_changeover_date_returns_the_successor(two_generation_history):
    """Windows are half-open, so the boundary date belongs to the newer version."""
    found = resolve_as_at(two_generation_history, date(2026, 2, 1))
    assert found is not None
    assert found.version == 2


def test_as_at_before_any_version_returns_none(two_generation_history):
    """Honest 'nothing applied' rather than guessing at the earliest version."""
    assert resolve_as_at(two_generation_history, date(2020, 1, 1)) is None


def test_as_at_ignores_drafts():
    drafts = [FakeVersion(version=1, status=LifecycleStatus.DRAFT)]
    assert resolve_as_at(drafts, date(2026, 1, 1)) is None


def test_as_at_raises_when_data_is_ambiguous():
    """If the invariant has been violated in stored data, fail loudly rather
    than silently returning one of two possible rules."""
    overlapping = [
        FakeVersion(version=1, effective_from=date(2024, 1, 1), effective_to=None),
        FakeVersion(version=2, effective_from=date(2024, 1, 1), effective_to=None),
    ]
    with pytest.raises(VersioningError) as exc:
        resolve_as_at(overlapping, date(2025, 1, 1))
    assert exc.value.code == "ambiguous_effective_version"


def test_as_at_on_empty_history_returns_none():
    assert resolve_as_at([], date(2026, 1, 1)) is None


# --- Supersession ---------------------------------------------------------


def test_supersede_closes_the_window_and_marks_the_status():
    previous = FakeVersion(version=1, effective_from=date(2024, 1, 1), effective_to=None)

    supersede(previous, replacement_effective_from=date(2026, 2, 1))

    assert previous.effective_to == date(2026, 2, 1)
    assert previous.status is LifecycleStatus.SUPERSEDED


def test_supersede_leaves_the_previous_version_resolvable(two_generation_history):
    """Superseding must not erase history — the old rule stays queryable."""
    previous = FakeVersion(version=1, effective_from=date(2024, 1, 1), effective_to=None)
    supersede(previous, replacement_effective_from=date(2026, 2, 1))

    assert previous.is_in_force_on(date(2025, 1, 1)) is True
    assert previous.is_in_force_on(date(2026, 3, 1)) is False


def test_only_active_versions_can_be_superseded():
    draft = FakeVersion(status=LifecycleStatus.DRAFT)
    with pytest.raises(VersioningError) as exc:
        supersede(draft, replacement_effective_from=date(2026, 1, 1))
    assert exc.value.code == "cannot_supersede"


def test_supersede_rejects_a_replacement_that_starts_too_early():
    previous = FakeVersion(effective_from=date(2026, 1, 1))
    with pytest.raises(VersioningError) as exc:
        supersede(previous, replacement_effective_from=date(2025, 1, 1))
    assert exc.value.code == "invalid_supersede_date"


# --- Version numbering ----------------------------------------------------


def test_next_version_number_starts_at_one():
    assert next_version_number([]) == 1


def test_next_version_number_follows_the_highest_existing():
    versions = [FakeVersion(version=1), FakeVersion(version=3), FakeVersion(version=2)]
    assert next_version_number(versions) == 4
