"""Import a control-test catalogue into the Compliance Control Graph.

    python scripts/import_control_catalogue.py \
        ../../docs/reference/Logistics_Compliance_Control_Test_Catalogue_v2.json

Safe to run repeatedly: the import is idempotent, so an unchanged catalogue
produces no changes at all (see docs/CONTROL_IMPORT_MAPPING.md §4).

By default everything lands as DRAFT, because nothing imported has been through
compliance review inside this system. `--activate` is a development
convenience that marks content ACTIVE against a nominated reviewer/approver so
the Control Explorer has something to show; it does not represent real review,
and every imported rule stays non-executable either way.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.graph_enums import LifecycleStatus  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.models import User  # noqa: E402
from app.services.catalogue_import import (  # noqa: E402
    CatalogueImportError,
    import_catalogue,
    load_catalogue,
)

PRODUCTION_LIKE = {"production", "prod", "staging"}


def _print_report(report) -> None:
    print(f"\nImported {report.source_file} (v{report.source_version})")
    print(f"  SHA-256: {report.checksum}")

    for label, bucket in (
        ("created", report.created),
        ("updated", report.updated),
        ("new versions", report.new_versions),
        ("unchanged", report.unchanged),
    ):
        if bucket:
            total = sum(bucket.values())
            print(f"\n  {label} ({total}):")
            for table, count in sorted(bucket.items()):
                print(f"    {count:>4}  {table}")

    if not (report.created or report.updated or report.new_versions):
        print("\n  No changes — the catalogue matches what is already imported.")

    if report.warnings:
        print(f"\n  Warnings ({len(report.warnings)}):")
        for warning in report.warnings:
            print(f"    {warning}")

    if report.review_reason_counts:
        print(f"\n  Records needing specialist review: {report.needs_review}")
        for reason, count in sorted(
            report.review_reason_counts.items(), key=lambda kv: -kv[1]
        ):
            print(f"    {count:>4}  {reason}")
        print(
            "\n  This is expected. The catalogue specifies *what* to test, not *how*:\n"
            "  it contains no thresholds, so no imported test can run until a\n"
            "  compliance specialist defines its rule. See\n"
            "  docs/CONTROL_IMPORT_MAPPING.md."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalogue", type=Path, help="Path to the catalogue JSON file")
    parser.add_argument(
        "--effective-from",
        type=date.fromisoformat,
        default=None,
        help=(
            "Date the imported content takes effect (YYYY-MM-DD). Defaults to the "
            "catalogue's own date, which is recorded as its origin. The catalogue "
            "carries no per-entry dates, so this is never guessed."
        ),
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help=(
            "Development only: mark imported content ACTIVE against a platform "
            "administrator so the Control Explorer can display it. This is fixture "
            "activation, not compliance review."
        ),
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the catalogue and report issues without writing anything.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if args.activate and settings.environment.lower() in PRODUCTION_LIKE:
        raise SystemExit(
            f"--activate is a development convenience and must not be used in "
            f"environment='{settings.environment}'."
        )

    if not args.catalogue.exists():
        raise SystemExit(f"Catalogue not found: {args.catalogue}")

    catalogue = load_catalogue(args.catalogue)
    effective_from = args.effective_from or date.fromisoformat(catalogue.date)

    if catalogue.fatal_issues:
        print(f"Validation failed with {len(catalogue.fatal_issues)} error(s):\n")
        for issue in catalogue.fatal_issues:
            print(f"  {issue}")
        return 1

    if args.validate_only:
        print(f"{args.catalogue.name} is valid: {len(catalogue.entries)} entries.")
        for warning in catalogue.warnings:
            print(f"  {warning}")
        return 0

    with Session(engine) as db:
        reviewer = None
        if args.activate:
            admin = (
                db.execute(select(User).where(User.is_platform_admin.is_(True)))
                .scalars()
                .first()
            )
            if admin is None:
                raise SystemExit(
                    "--activate needs a platform administrator to record as reviewer "
                    "and approver. Run scripts/seed_dev_data.py first."
                )
            reviewer = admin.id

        try:
            report = import_catalogue(
                db,
                args.catalogue,
                effective_from=effective_from,
                status=LifecycleStatus.ACTIVE if args.activate else LifecycleStatus.DRAFT,
                reviewed_by_id=reviewer,
                approved_by_id=reviewer,
            )
        except CatalogueImportError as exc:
            print(f"Import failed: {exc.message}")
            for issue in exc.issues:
                print(f"  {issue}")
            return 1

        db.commit()

    _print_report(report)
    if args.activate:
        print(
            "\n  NOTE: content was marked ACTIVE for development display. That is "
            "fixture\n  activation, not compliance review — the review trail names a "
            "platform\n  administrator, and every rule remains UNSPECIFIED."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
