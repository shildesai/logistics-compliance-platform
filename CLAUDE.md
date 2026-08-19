# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Overview

Logistics Compliance Platform: manages regulatory compliance for logistics
operations, including regulation tracking, control catalogues, and rule
evaluation, surfaced through a web app and API.

## Repository Structure

See `README.md` for the full directory layout. Key points:

- `apps/web` and `apps/api` hold application code.
- `packages/shared` holds code shared between apps.
- `compliance/` holds the domain content: regulations, control catalogue,
  rules, and fixtures. Treat this as the source of truth for compliance
  logic — keep it well-organized and reviewable independent of app code.
- `docs/` holds PRD, architecture, control model, data model, and security
  documentation — update these alongside relevant code changes.

## Conventions

- Follow the structure in `AGENTS.md` for where new code/content belongs.
- Keep documentation in `docs/` up to date when architecture or data models
  change.
- Do not commit secrets; add new required environment variables to
  `.env.example`.
