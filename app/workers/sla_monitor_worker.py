import asyncio
import logging
from app.core.database import SessionLocal
from app.services.sla_monitor import check_sla_breaches_and_warnings

logger = logging.getLogger("sla_worker")

_worker_task = None
_stop_event = asyncio.Event()

async def sla_monitor_worker_loop(interval_seconds: int = 60):
    """
    Background worker loop periodically checking for approaching deadlines and breaches (FEAT-27).
    """
    logger.info("Starting Background SLA Monitor Worker...")
    # Allow FastAPI startup to complete before initial database scan
    try:
        await asyncio.wait_for(_stop_event.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        pass

    while not _stop_event.is_set():
        db = SessionLocal()
        try:
            results = check_sla_breaches_and_warnings(db)
            if results.get("new_breaches", 0) > 0 or results.get("new_warnings", 0) > 0:
                logger.info(f"SLA Check: {results}")
        except Exception as e:
            logger.error(f"Error in SLA monitor worker: {e}")
        finally:
            db.close()

        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass

    logger.info("Background SLA Monitor Worker stopped.")

def start_sla_worker(interval_seconds: int = 60):
    global _worker_task, _stop_event
    _stop_event.clear()
    _worker_task = asyncio.create_task(sla_monitor_worker_loop(interval_seconds))

def stop_sla_worker():
    global _stop_event, _worker_task
    _stop_event.set()
    if _worker_task:
        _worker_task.cancel()
