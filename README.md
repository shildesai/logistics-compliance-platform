# Logistics Compliance Platform

A platform for managing logistics compliance: regulations, controls, rules, and the
applications that surface them to users.

## Repository Structure

```
logistics-compliance-platform/
│
├── apps/
│   ├── web/                  # Frontend web application
│   └── api/                  # Backend API service
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

## Getting Started

Setup instructions will be added as `apps/web` and `apps/api` are implemented.
