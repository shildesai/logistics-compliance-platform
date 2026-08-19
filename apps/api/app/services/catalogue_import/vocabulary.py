"""Controlled vocabularies for translating catalogue values.

Every mapping here is stated in docs/CONTROL_IMPORT_MAPPING.md §2. Nothing
falls back to a default: an unrecognised value raises, because silently
mapping an unknown regulatory term onto a known one is how wrong content gets
into a compliance graph unnoticed.
"""

from __future__ import annotations

from app.core.graph_enums import EvidenceSourceType, PsoeDimension, TestType

#: Review-reason codes recorded on CatalogueImportRecord.review_reasons.
#: Documented in docs/CONTROL_IMPORT_MAPPING.md.
NO_EXECUTABLE_RULE = "no_executable_rule_in_source"
APPLICABILITY_NOT_IN_SOURCE = "applicability_criteria_not_in_source"
REGULATION_LAYER_COMPOUND = "regulation_layer_compound_hvnl_cor_hva"
TEST_TYPE_RULE_NORMALISED = "test_type_rule_normalised"
CONTROL_OWNER_NOT_IN_SOURCE = "control_owner_not_in_source"
CONTROL_FREQUENCY_NOT_IN_SOURCE = "control_frequency_not_in_source"
CONTROL_AUTOMATION_INFERRED = "control_automation_level_inferred"
OBJECTIVE_NOT_IN_SOURCE = "objective_not_in_source"
EVIDENCE_ATTRIBUTION_UNRESOLVED = "evidence_source_attribution_unresolved"
DATA_SOURCE_GENERALISED = "data_source_generalised"
REMEDIATION_DEFAULTS_NOT_IN_SOURCE = "remediation_defaults_not_in_source"
RISK_RATING_NOT_IN_SOURCE = "risk_rating_not_in_source"
AI_REVIEW_OVERRIDDEN = "ai_test_human_review_forced"


TEST_TYPES: dict[str, TestType] = {
    "deterministic": TestType.DETERMINISTIC,
    "analytical": TestType.ANALYTICAL,
    "ai": TestType.AI_ASSISTED,
    "manual": TestType.MANUAL,
    # "Rule" is a labelling inconsistency in the source, not a fifth execution
    # model — FAT-006/FAT-007 do the same status/expiry checks as entries
    # labelled Deterministic (docs/DECISIONS.md §1.2). Normalised, and flagged
    # so the assumption stays visible.
    "rule": TestType.DETERMINISTIC,
}

#: Source values that are normalised rather than mapped 1:1, and therefore
#: produce a review flag.
NORMALISED_TEST_TYPES = {"rule"}


PSOE_DIMENSIONS: dict[str, PsoeDimension] = {
    "present": PsoeDimension.PRESENT,
    "suitable": PsoeDimension.SUITABLE,
    "operating": PsoeDimension.OPERATING,
    "effective": PsoeDimension.EFFECTIVE,
}


#: Data-source tokens that map cleanly onto a connector type.
EVIDENCE_SOURCES: dict[str, EvidenceSourceType] = {
    "tms": EvidenceSourceType.TMS,
    "ewd": EvidenceSourceType.EWD,
    "telematics": EvidenceSourceType.TELEMATICS,
    "fleet maintenance": EvidenceSourceType.FLEET_MAINTENANCE,
    "maintenance": EvidenceSourceType.FLEET_MAINTENANCE,
    "hr": EvidenceSourceType.HR_LMS,
    "lms": EvidenceSourceType.HR_LMS,
    "hr/lms": EvidenceSourceType.HR_LMS,
    "wms": EvidenceSourceType.WMS,
    "weighbridge": EvidenceSourceType.WEIGHBRIDGE,
    "permit register": EvidenceSourceType.PERMIT_REGISTER,
    "driver app": EvidenceSourceType.DRIVER_APP,
    "incident system": EvidenceSourceType.INCIDENT_SYSTEM,
    "supplier portal": EvidenceSourceType.SUPPLIER_PORTAL,
    # Lossy generalisations — the target vocabulary has no distinct member for
    # these, so they are widened and individually flagged.
    "procurement/erp": EvidenceSourceType.SUPPLIER_PORTAL,
    "contract system": EvidenceSourceType.SUPPLIER_PORTAL,
    "assurance platform": EvidenceSourceType.SUPPLIER_PORTAL,
    "dms": EvidenceSourceType.DOCUMENT,
    "email/dms": EvidenceSourceType.DOCUMENT,
    "grc": EvidenceSourceType.DOCUMENT,
    "vehicle master": EvidenceSourceType.DOCUMENT,
    "customer portal": EvidenceSourceType.DOCUMENT,
}

#: Tokens whose mapping loses meaning, flagged per test.
GENERALISED_DATA_SOURCES = {
    "procurement/erp",
    "contract system",
    "assurance platform",
    "dms",
    "email/dms",
    "grc",
    "vehicle master",
    "customer portal",
}


SEVERITIES = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH", "critical": "CRITICAL"}


#: Domain code prefixes, taken from the control-test ids rather than invented.
#: Verified in docs/CONTROL_IMPORT_MAPPING.md §0.1: one prefix per domain.
def code_prefix(control_test_id: str) -> str:
    return control_test_id.split("-", 1)[0].upper()
