"""Provenance for content imported from an external control catalogue.

Every graph record created or updated by an import gets a row here recording
where it came from and what could not be resolved. Two things depend on it:

  * **Traceability.** An assurance claim has to be able to answer "where did
    this control come from, and from which revision of which file?" The
    checksum makes that answerable even after the source file changes on disk.
  * **Review triage.** The catalogue supplies no thresholds and no
    applicability criteria (docs/CONTROL_IMPORT_MAPPING.md §0.2, §0.3), so
    imported content is not usable until a specialist completes it. This table
    is the work queue: `SELECT ... WHERE needs_review`.

Kept separate from `source_reference` on the versioned records because that
field is a human-readable citation, while this is structured, queryable, and
holds the original payload for comparison.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


class CatalogueImportRecord(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "catalogue_import_records"
    __table_args__ = (
        # Upsert key: re-importing the same file updates these rows rather than
        # appending, which is what keeps repeated imports idempotent.
        UniqueConstraint(
            "source_file",
            "source_entity_id",
            "target_table",
            name="uq_catalogue_import_record",
        ),
    )

    source_file: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_version: Mapped[str] = mapped_column(String(50), nullable=False)
    #: SHA-256 of the file as read. If the file later changes, this no longer
    #: matches and a reviewer can see the imported content is from an older
    #: revision than the one on disk.
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    #: Identifier of the thing in the source that produced this record — a
    #: control-test id such as "FAT-001", or "DOMAIN:<domain>" for records
    #: derived from a whole domain rather than one entry.
    source_entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    target_table: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    #: True when something could not be resolved from the source and a
    #: specialist must complete it. Expected to be true for most imported rows.
    needs_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    #: Machine-readable reasons, e.g. ["no_executable_rule_in_source"]. Named
    #: in docs/CONTROL_IMPORT_MAPPING.md.
    review_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), nullable=False, default=list
    )

    #: The original JSON entry, so a reviewer can compare the imported record
    #: against exactly what was read rather than trusting the transformation.
    source_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
