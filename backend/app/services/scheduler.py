"""
Scheduler — orchestrates the daily job pipeline.

At MVP, APScheduler running in-process is sufficient (per architecture
doc section 2: "don't over-engineer... move to Temporal/Airflow only
once the number of pipelines justifies it").

Run as a standalone process: `python -m app.services.scheduler`
(separate from the API process — `uvicorn app.main:app`).

JOB ORDER MATTERS:
  1. Ingestion (fetch new signals)
  2. Forecasting (generate forecasts from latest signals)
  3. Validation (check past forecasts against realized outcomes)
  4. Alerting (evaluate alert rules against latest signals/forecasts)

Ecosystem benchmark computation runs weekly, independent of the daily
chain.
"""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.ingestion.runner import run_all_adapters
from app.services.alerting import evaluate_all_alerts
from app.services.ecosystem import compute_weekly_benchmarks
from app.services.forecasting import run_daily_forecasts, validate_past_forecasts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def daily_pipeline() -> None:
    logger.info("=== Starting daily pipeline ===")

    logger.info("Step 1/4: Ingestion")
    run_all_adapters()

    logger.info("Step 2/4: Forecasting")
    run_daily_forecasts()

    logger.info("Step 3/4: Forecast validation")
    validate_past_forecasts()

    logger.info("Step 4/4: Alert evaluation")
    evaluate_all_alerts()

    logger.info("=== Daily pipeline complete ===")


def weekly_ecosystem_pipeline() -> None:
    logger.info("=== Starting weekly ecosystem benchmark pipeline ===")
    compute_weekly_benchmarks()
    logger.info("=== Weekly ecosystem pipeline complete ===")


def main() -> None:
    scheduler = BlockingScheduler()

    # Daily pipeline — run at 06:00 UTC (after most overnight data
    # sources have updated)
    scheduler.add_job(daily_pipeline, "cron", hour=6, minute=0, id="daily_pipeline")

    # Weekly ecosystem benchmarks — Monday 07:00 UTC, after daily pipeline
    scheduler.add_job(weekly_ecosystem_pipeline, "cron", day_of_week="mon", hour=7, minute=0, id="weekly_ecosystem")

    logger.info("Scheduler started. Jobs: %s", [job.id for job in scheduler.get_jobs()])
    scheduler.start()


if __name__ == "__main__":
    main()
