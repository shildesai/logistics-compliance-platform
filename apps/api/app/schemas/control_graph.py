import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.core.graph_enums import (
    AutomationLevel,
    ControlFrequency,
    ControlOwnerType,
    EvidenceSourceType,
    LifecycleStatus,
    PsoeDimension,
    RiskConsequence,
    RiskLikelihood,
    TestType,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class VersionMeta(ORMModel):
    """The governance envelope every versioned record carries."""

    version: int
    status: LifecycleStatus
    effective_from: date
    effective_to: date | None
    source_reference: str | None
    reviewed_by_id: uuid.UUID | None
    approved_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


# --- Regulation -----------------------------------------------------------


class RegulatorySourceOut(ORMModel):
    id: uuid.UUID
    source_code: str
    name: str
    publisher: str
    url: str | None
    document_type: str | None
    retrieved_on: date | None


class RegulationVersionOut(VersionMeta):
    id: uuid.UUID
    title: str
    summary: str | None
    jurisdiction_codes: list[str]
    requires_control_review: bool
    change_note: str | None
    regulatory_source: RegulatorySourceOut | None = None


class RegulationOut(ORMModel):
    id: uuid.UUID
    regulation_code: str
    name: str
    short_name: str | None
    regulator: str | None


class RegulationListItem(BaseModel):
    regulation: RegulationOut
    #: None when no version is in force on the requested date. Surfaced rather
    #: than hidden — a lapsed regulation is a governance gap worth seeing.
    current_version: RegulationVersionOut | None


# --- Obligation / Risk ----------------------------------------------------


class ApplicabilityRuleOut(VersionMeta):
    id: uuid.UUID
    rule_code: str
    name: str
    description: str | None
    #: Opaque criteria for display only. Evaluation happens server-side; the
    #: frontend must never branch on the contents.
    criteria: dict


class RiskOut(VersionMeta):
    id: uuid.UUID
    risk_code: str
    name: str
    description: str
    inherent_likelihood: RiskLikelihood | None
    inherent_consequence: RiskConsequence | None


class ObligationOut(VersionMeta):
    id: uuid.UUID
    obligation_code: str
    regulation_id: uuid.UUID
    name: str
    description: str
    cor_role_codes: list[str]


class ObligationDetailOut(ObligationOut):
    regulation: RegulationOut
    risks: list[RiskOut]
    applicability_rules: list[ApplicabilityRuleOut]


# --- Control --------------------------------------------------------------


class ControlVersionOut(VersionMeta):
    id: uuid.UUID
    name: str
    objective: str
    owner_type: ControlOwnerType
    frequency: ControlFrequency
    automation_level: AutomationLevel
    psoe_relevance: list[PsoeDimension]
    procedure_reference: str | None
    change_note: str | None


class ControlOut(ORMModel):
    id: uuid.UUID
    control_code: str
    domain: str


class ControlListItem(BaseModel):
    control: ControlOut
    current_version: ControlVersionOut | None


# --- Control test ---------------------------------------------------------


class EvidenceRequirementOut(VersionMeta):
    id: uuid.UUID
    requirement_code: str
    name: str
    description: str | None
    source_type: EvidenceSourceType
    required_fields: list[str]
    is_mandatory: bool
    max_age_days: int | None


class RemediationTemplateOut(VersionMeta):
    id: uuid.UUID
    template_code: str
    title: str
    description: str
    suggested_steps: list[str]
    default_owner_type: ControlOwnerType
    default_due_days: int
    requires_closure_evidence: bool
    requires_effectiveness_check: bool


class ControlTestVersionOut(VersionMeta):
    id: uuid.UUID
    name: str
    test_logic_description: str
    test_type: TestType
    #: Versioned rule definition, returned as data for display and review.
    #: The evaluation engine is server-side; clients must not interpret this.
    rule_configuration: dict
    severity_configuration: dict
    human_review_required: bool
    psoe_impact: list[PsoeDimension]
    change_note: str | None


class ControlTestOut(ORMModel):
    id: uuid.UUID
    test_code: str


class ControlTestDetailOut(BaseModel):
    control_test: ControlTestOut
    current_version: ControlTestVersionOut | None
    evidence_requirements: list[EvidenceRequirementOut]
    remediation_templates: list[RemediationTemplateOut]


class ControlDetailOut(BaseModel):
    control: ControlOut
    current_version: ControlVersionOut | None
    risks: list[RiskOut]
    tests: list[ControlTestDetailOut]


# --- Lineage --------------------------------------------------------------


class LineagePathOut(BaseModel):
    regulation: RegulationOut
    regulation_version: RegulationVersionOut | None
    obligation: ObligationOut
    applicability_rules: list[ApplicabilityRuleOut]
    risk: RiskOut
    is_primary_control: bool


class ControlLineageOut(BaseModel):
    control: ControlOut
    current_version: ControlVersionOut | None
    #: More than one path is normal: a shared control satisfies several
    #: obligations, which is the architecture the product is built on.
    paths: list[LineagePathOut]
    control_version_history: list[ControlVersionOut]
    test_version_history: dict[str, list[ControlTestVersionOut]]


class GraphStatisticsOut(BaseModel):
    regulations: int
    obligations: int
    controls: int
    control_tests: int
    active_control_versions: int
