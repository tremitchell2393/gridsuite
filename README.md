# GridSuite

Supply chain intelligence platform — signal ingestion, predictive modeling, and ecosystem data network.

## Structure

```
gridsuite/
├── backend/          FastAPI application (API, ingestion, modeling)
│   ├── app/
│   │   ├── api/v1/        # API route handlers
│   │   ├── core/          # config, security, settings
│   │   ├── db/             # database session, base models
│   │   ├── ingestion/      # signal ingestion pipelines + adapters
│   │   ├── modeling/       # forecasting models
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic schemas (request/response)
│   │   └── services/       # business logic
│   └── tests/
└── frontend/          React dashboard (Vite + TypeScript)
```

## Getting Started — Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in your local config
alembic upgrade head         # run migrations
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs` once running.

## Getting Started — Frontend

```bash
cd frontend
npm install
npm run dev
```

## Core Concept: The Signal Schema

Every data signal in GridSuite — regardless of source — conforms to one schema
(see `app/models/signal.py`). This is the architectural foundation that lets us
continuously add new signal sources without touching downstream code. See
`/docs/architecture.md` (or the project's Technical Architecture doc) for the
full rationale.

## Environment

Copy `.env.example` to `.env` and fill in:

- `DATABASE_URL` — Postgres connection string (Timescale-enabled recommended)
- `SECRET_KEY` — app secret for auth/session signing
- `STRIPE_SECRET_KEY` — for billing (optional in early dev)
- Source-specific API keys for ingestion adapters (see `app/ingestion/adapters/`)
