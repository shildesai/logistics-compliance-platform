# Logistics Compliance Platform

A platform for managing logistics compliance: regulations, controls, rules, and the
applications that surface them to users.

## Repository Structure

```
logistics-compliance-platform/
│
├── apps/
│   ├── web/                  # Next.js/TypeScript frontend (Phase 1 shell)
│   └── api/                  # FastAPI backend, /api/v1, Alembic migrations
│
├── docker-compose.yml         # Postgres + API + Web for local development
│
├── packages/
│   └── shared/                # Shared code/types used across apps
│
├── compliance/
│   ├── regulations/           # Source regulation texts and metadata
│   ├── control_catalogue/     # Catalogue of compliance controls
│   ├── rules/                 # Machine-readable compliance rules
│   └── fixtures/              # Sample/test data for compliance domain
│
├── docs/
│   ├── PRD.md                 # Product requirements
│   ├── ARCHITECTURE.md        # System architecture
│   ├── CONTROL_MODEL.md       # Control modeling approach
│   ├── DATA_MODEL.md          # Data model reference
│   ├── SECURITY.md            # Security considerations
│   └── reference/              # Reference documentation (API, schemas, etc.)
│
├── tests/                     # Cross-cutting/integration tests
├── scripts/                   # Dev, build, and ops scripts
│
├── AGENTS.md                  # Guidance for AI coding agents
├── CLAUDE.md                  # Guidance for Claude Code
├── README.md
└── .env.example
```

## Status

Phase 1 application shell is implemented: a Next.js/TypeScript frontend, a FastAPI
backend serving synthetic dashboard data under a versioned `/api/v1` API, and
PostgreSQL migrations. No real compliance logic (rule evaluation, evidence ingestion,
finding generation) exists yet — see `docs/IMPLEMENTATION_PLAN.md` for the phased plan
and `docs/DECISIONS.md` for what deliberately isn't built yet.

## Getting Started

### Option A — Docker Compose (Postgres + API + Web)

```bash
docker compose up --build
```

- Web: http://localhost:3000
- API: http://localhost:8000 (docs at `/docs`, health at `/health`)
- Postgres: `localhost:5432` (user/password/db: `logistics`/`logistics`/`logistics_compliance`)

Migrations run automatically on API container start.

### Option B — Run locally without Docker

Requires PostgreSQL 16+, Python 3.11+, Node.js 20+.

```bash
# 1. Database
createdb logistics_compliance   # or use an existing Postgres instance

# 2. API
cd apps/api
cp .env.example .env            # adjust DATABASE_URL if needed
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Web (in a second terminal)
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

Then open http://localhost:3000 (redirects to `/overview`).

## Testing

```bash
# Backend: unit tests + API smoke tests (pytest)
cd apps/api && source .venv/bin/activate && python -m pytest -v

# Frontend: typecheck + lint
cd apps/web && npm run typecheck && npm run lint

# Frontend: end-to-end smoke tests (Playwright, requires API + web running)
cd apps/web && npm run test:e2e
```
