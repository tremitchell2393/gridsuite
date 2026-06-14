# GridSuite Frontend

React + TypeScript + Vite dashboard, built against the FastAPI backend in `../backend`.

## Getting Started

```bash
npm install
npm run dev
```

Runs on `http://localhost:5173`. API requests to `/v1/...` are proxied to the backend at `http://localhost:8000` (see `vite.config.ts`) — make sure the backend is running too (`make backend-dev` from the project root).

## Structure

```
src/
├── api/
│   ├── client.ts       # axios instance, auth header injection
│   └── endpoints.ts     # typed request functions, one per backend route
├── components/
│   ├── AppLayout.tsx    # sidebar + topbar shell
│   └── Dashboard.tsx    # shared presentational components (KPI cards, panels, tables)
├── hooks/
│   ├── useApi.ts        # React Query hooks wrapping api/endpoints.ts
│   └── useAuth.tsx      # auth context (JWT in localStorage)
├── pages/
│   ├── DashboardPage.tsx     # Overview — KPI row + lane forecast table
│   ├── LaneDetailPage.tsx     # Forecast chart + signal attribution for one lane
│   ├── SignalLibraryPage.tsx  # Browsable list of active signals
│   ├── AlertsPage.tsx         # Configure alert rules
│   ├── SettingsPage.tsx       # Lane watchlist management
│   └── LoginPage.tsx           # Login / registration
├── styles/
│   └── global.css       # design tokens (colors, fonts) — mirrors brand identity
└── types/
    └── api.ts            # TypeScript types mirroring backend Pydantic schemas
```

## Design System

Colors and typography in `src/styles/global.css` are lifted directly from the
brand identity guidelines and the landing page v3 mock (deep navy-slate shell,
Signal Teal `#00D4AA` accent, Inter + JetBrains Mono). The landing page's
dashboard preview was an intentional visual prototype for this real
dashboard — the transition should feel seamless.

## Notes on Types

`src/types/api.ts` is currently hand-written to mirror
`backend/app/schemas/`. Once the API stabilizes, consider generating these
automatically from the OpenAPI spec (available at `/v1/openapi.json` when the
backend is running) using `openapi-typescript`.
