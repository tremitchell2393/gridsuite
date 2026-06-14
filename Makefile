# GridSuite — common development commands.
#
# Usage: make <target>
# Run from the project root.

.PHONY: help backend-install backend-dev backend-test backend-migrate \
        backend-scheduler frontend-install frontend-dev frontend-build test

help:
	@echo "GridSuite development commands"
	@echo ""
	@echo "  make backend-install    Install backend Python dependencies"
	@echo "  make backend-dev        Run the FastAPI dev server (localhost:8000)"
	@echo "  make backend-test       Run backend test suite"
	@echo "  make backend-migrate    Run database migrations (alembic upgrade head)"
	@echo "  make backend-scheduler  Run the daily job scheduler"
	@echo ""
	@echo "  make frontend-install   Install frontend dependencies"
	@echo "  make frontend-dev       Run the Vite dev server (localhost:5173)"
	@echo "  make frontend-build     Build frontend for production"
	@echo ""
	@echo "  make test               Run all tests (backend)"

# ── Backend ──
backend-install:
	cd backend && python -m venv venv && venv/bin/pip install -r requirements.txt

backend-dev:
	cd backend && uvicorn app.main:app --reload

backend-test:
	cd backend && python -m pytest tests/ -v

backend-migrate:
	cd backend && alembic upgrade head

backend-scheduler:
	cd backend && python -m app.services.scheduler

# ── Frontend ──
frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

# ── Combined ──
test: backend-test
