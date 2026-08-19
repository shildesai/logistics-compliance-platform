# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project Layout

- `apps/web` — frontend web application
- `apps/api` — backend API service
- `packages/shared` — code/types shared between apps
- `compliance/regulations` — source regulation texts and metadata
- `compliance/control_catalogue` — catalogue of compliance controls
- `compliance/rules` — machine-readable compliance rules
- `compliance/fixtures` — sample/test data for the compliance domain
- `docs` — product, architecture, and security documentation
- `tests` — cross-cutting/integration tests
- `scripts` — development, build, and operations scripts

## Working Conventions

- Keep compliance content (`compliance/`) separate from application code
  (`apps/`) — regulations, controls, and rules should be reviewable on their own.
- Document architecture and data model decisions in `docs/` as they are made.
- Prefer adding tests under the relevant app/package first; use top-level
  `tests/` for integration or cross-app tests.
- Do not commit real secrets — use `.env.example` to document required
  environment variables.
