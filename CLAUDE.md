# Logistics Compliance Intelligence Platform

## Product purpose

Build a multi-tenant SaaS platform for continuous logistics compliance,
assurance and audit readiness.

The core domain model is:

Regulation
→ Obligation
→ Risk
→ Control
→ Evidence
→ Data Source
→ Test
→ Finding
→ Remediation
→ Verification

The system supports HVA/CoR assurance but must NOT imply that every
organisation requires HVA accreditation.

## Critical product principles

1. Never allow AI to make a final legal or regulatory compliance determination.
2. AI may create POTENTIAL findings.
3. Material findings require human approval.
4. Every finding must have traceable supporting evidence.
5. Regulatory rules must be versioned and effective-dated.
6. Never hard-code legal thresholds into UI code.
7. Deterministic rules must be preferred where rules are objectively calculable.
8. LLMs should be used for interpretation, classification, summarisation,
   cross-system reasoning and proposed root-cause analysis.
9. Preserve full data lineage.
10. All customer data must be tenant-isolated.

## Technical architecture

Frontend:
- Next.js
- React
- TypeScript

Backend:
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL

Testing:
- pytest
- Playwright

## Development rules

- Write migrations for every schema change.
- Add unit tests for business logic.
- Add integration tests for API routes.
- Never modify a regulatory rule without creating a new version.
- Never silently swallow compliance engine errors.
- Use typed models.
- Keep business logic outside API controllers.
- Do not introduce new infrastructure without justification.

## Definition of Done

A feature is complete only when:
- code works
- tests pass
- lint passes
- database migrations exist
- documentation is updated
- security implications are considered
- errors are handled
- acceptance criteria are demonstrated
