# GridSuite — Handoff Document

**Status: fully running locally, end-to-end, with real seeded data.**

This document covers (1) what's running right now and how to see it, (2) what
I built/fixed in this session, (3) exactly what's left that requires your
accounts/ownership, and (4) a recommended order of operations.

---

## 1. What's running right now

A complete instance of GridSuite is live in this sandbox:

- **Postgres 16** database, fully migrated (10 tables)
- **FastAPI backend** on `localhost:8000`
- **React frontend** on `localhost:5173`
- **A real account** with 3 watched lanes, 90 days of seeded signal history,
  forecasts, and one active alert rule

You can't browse to these URLs yourself (they're inside this sandbox, not the
public internet) — but the screenshots below show exactly what's rendering,
and everything below this point is about getting *your own* copy running
somewhere you control.

**Demo login** (in the seeded local instance): `founder@gridsuite.io` /
`gridsuite2024`

### What the running instance demonstrates

- **Dashboard**: 3 lanes (SHSE-LAX, SHSE-HOU, SHSE-RTM), each with a current
  spot rate and a 30-day forecast (+10.4%, +6.2%, +12.9%) with confidence
  scores (71-79%)
- **Lane Detail**: a 90-day customs velocity chart trending from ~1.00 to
  ~1.18, with the 30-day forecast plotted as a continuation with a confidence
  band — and a signal attribution table showing *why* the model is calling
  this
- **Signal Library**: lists the 3 active signals with descriptions
- **Alerts**: created a real alert rule (SHSE-RTM, forecast change > 10%,
  email), and verified it **actually fires** — ran the alerting engine and
  confirmed it correctly logged: *"GridSuite Alert — SHSE-RTM: rate_change_pct
  is 13.6% (threshold: 10.0)"*

---

## 2. What I built/fixed in this session

Beyond the original codebase scaffold, I:

1. **Installed Postgres locally**, created the database, and ran the Alembic
   migration successfully (10 tables, with `ENABLE_TIMESCALE=false` since
   Timescale isn't available outside a Timescale-enabled host — your
   production Postgres should have this extension; Supabase/Neon/Timescale
   Cloud all support it)

2. **Fixed three real bugs** found only by actually running the system:
   - **Enum serialization bug**: SQLAlchemy was sending `"CORE"` instead of
     `"core"` to Postgres's enum type, breaking every registration. Fixed
     with `values_callable` on all three enum columns (`SubscriptionTier`,
     `AlertCondition`, `AlertChannel`).
   - **Missing relationship**: `Organization.watched_lanes` wasn't defined,
     so the dashboard summary endpoint silently returned `[]`. Added the
     relationship.
   - **Alert threshold unit mismatch**: forecasts store `predicted_value` as
     a fraction (`0.1129`), but users naturally enter alert thresholds as
     percentage points (`12` meaning 12%). The alert would never fire.
     Fixed the comparison and the alert message formatting, and added
     5 new tests covering this.

3. **Fixed a chart bug**: the Lane Detail forecast chart was plotting the
   forecast's percentage-change value on the same axis as the raw signal
   value (~1.0-1.18), making the forecast point collapse to near-zero.
   Fixed by converting the forecast to an "implied future value" on the same
   scale — now the chart tells a coherent visual story.

4. **Wrote a seed script** (`backend/app/ingestion/seed_demo_data.py`) that
   generates 90 days of realistic signal history (customs velocity trending
   up, port dwell with a recent congestion spike, spot rates) plus one
   30-day forecast per lane. This is what's populating the dashboard right
   now. **This is clearly marked as demo-only** — it's not one of the
   production ingestion adapters, and the real adapters (customs_velocity.py,
   port_dwell.py) still point at placeholder API URLs that need real
   provider credentials.

5. **Ran the full pipeline end-to-end**: registration → login → add lanes →
   ingest signals → generate forecasts → evaluate alerts → fire alert. Every
   stage works.

6. **Test suite: 16/16 passing** (was 11/16 before — added 5 tests for the
   alerting fix).

---

## 3. What's left — and why it needs you specifically

Everything below requires an account, payment method, or ownership that has
to be yours. I cannot create these on your behalf.

### A. A real, persistent database (15 min)

Pick one (all have free tiers, all support the Timescale extension our
migration wants):

- **Supabase** (supabase.com) — easiest, includes auth/storage if you want
  them later
- **Neon** (neon.tech) — serverless Postgres, generous free tier
- **Timescale Cloud** (timescale.com) — built by the Timescale team directly

Steps:
1. Create an account, create a new project/database
2. Copy the connection string (looks like
   `postgresql://user:pass@host:5432/dbname`)
3. Paste it into `backend/.env` as `DATABASE_URL`
4. Run `make backend-migrate` (with `ENABLE_TIMESCALE=true` if the extension
   is available — try without the flag first; our migration defaults to
   `true` and only the local sandbox needed it disabled)

### B. Deploy the backend (30-45 min)

**Railway** (railway.app) is the simplest option for a FastAPI + Postgres
app:
1. Connect your GitHub repo (push this code there first)
2. Railway auto-detects `requirements.txt` and `app.main:app`
3. Add environment variables from `.env.example` (use your real `DATABASE_URL`
   from step A, generate a new random `SECRET_KEY`)
4. Railway gives you a public URL like `gridsuite-backend.up.railway.app`

Alternatives: Render, Fly.io — similar process.

### C. Deploy the frontend (15 min)

**Vercel** (vercel.com):
1. Connect the same GitHub repo, set root directory to `frontend/`
2. Set build command `npm run build`, output directory `dist`
3. Update `vite.config.ts`'s proxy — in production the frontend needs to know
   the backend's real URL. Simplest fix: set an environment variable
   `VITE_API_URL` and update `src/api/client.ts`'s `baseURL` to use it
   (currently hardcoded to `/v1` which relies on the dev proxy)
4. Vercel gives you a public URL like `gridsuite.vercel.app`

### D. Get real data flowing (ongoing — your relationships, your timeline)

The two example adapters (`customs_velocity.py`, `port_dwell.py`) are
reference implementations pointing at placeholder URLs
(`api.example-customs-data.com`). To get real signals:

1. Identify one real data source you can access — a customs data provider,
   a port authority API, or even a manual CSV export from a contact at a 3PL
2. Replace the `_fetch_raw` method in the relevant adapter with a real API
   call (or write a new adapter following the same pattern for CSV/manual
   input)
3. Add the API key to `.env`
4. Run `python -m app.ingestion.runner` — signals land in the database, the
   dashboard updates automatically

This is the step where "demo" becomes "product," and it's inherently tied to
your business development — I can help you write the adapter once you know
what data source you're integrating with.

### E. Stripe billing (when you have a paying customer)

Stubbed throughout (`Subscription.stripe_customer_id`,
`Subscription.stripe_subscription_id` fields exist; webhook handler doesn't
yet). Set this up when you have your first design partner ready to pay —
no point building it earlier.

---

## 4. Recommended order of operations

Given where you are (pre-revenue, relationship-led), I'd sequence this as:

1. **This week**: Steps A-C above (~1.5 hours total) — gets you a real public
   URL you can put in front of design partners. The seeded demo data is
   genuinely fine to show people; it tells a coherent, realistic story.
2. **In parallel**: keep having design partner conversations using the
   landing page + business plan. Ask specifically *what signal would make
   them switch* — that answer determines which adapter to build first.
3. **Once you have a committed pilot**: build the one adapter that matters to
   them (step D), even if it's manual CSV ingestion at first.
4. **Once someone wants to pay**: Stripe (step E).

---

## 5. Everything that's yours now

The zip below contains the complete, working codebase — backend, frontend,
migrations, tests, the seed script, and this handoff doc. Test suite passes
(16/16). Both servers start cleanly with `make backend-dev` and
`make frontend-dev` after `make backend-install` / `make frontend-install`
and setting up `.env`.

If you get stuck on any of steps A-E above, bring the specific error back
here — I can debug deployment issues, write the adapter for whatever data
source you land on, or extend any part of this.
