import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="America/New_York")
    logger.info("Worklog scheduler created; no recurring jobs are enabled for Phase 1.")
    return scheduler
