# apps/web

Next.js (App Router) + TypeScript frontend for the Logistics Compliance Intelligence
Platform. See the repo-level `README.md` for how to run the full stack.

## Structure

- `src/app/(dashboard)/*` — the 8 navigation sections (Assurance Overview, Controls,
  Evidence, Findings, Corrective Actions, Audit Readiness, Compliance Assistant,
  Administration), each fetching synthetic data from the API.
- `src/components/layout/` — Sidebar, TopBar, OrgSelector, UserMenu, AppShell.
- `src/contexts/org-context.tsx` — client-side organisation selection, shared across
  the app via `useOrg()`.
- `src/lib/api.ts` — typed fetch client for `apps/api`'s `/api/v1` endpoints.
- `e2e/` — Playwright smoke tests.

## Commands

```bash
npm run dev         # dev server
npm run build        # production build
npm run start        # run the production build
npm run lint          # eslint
npm run typecheck     # tsc --noEmit
npm run test:e2e       # Playwright smoke tests (API + web must be running)
```

`NEXT_PUBLIC_API_URL` (see `.env.example`) points the app at the FastAPI backend;
defaults to `http://localhost:8000`.
