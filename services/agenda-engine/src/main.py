import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uvicorn

from .config import get_settings
from .database import Database
from .collectors import RSSCollector
from .collectors.organic_collector import OrganicCollector
from .clustering import EventClusterer
from .scheduler import VirtualDayScheduler, TaskGenerator
from .scheduler.debbe_selector import DebbeSelector
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Content source weights: 55% organic, 45% RSS
ORGANIC_WEIGHT = 0.55
RSS_WEIGHT = 0.45

# Initialize components
scheduler = AsyncIOScheduler()
rss_collector = RSSCollector()
organic_collector = OrganicCollector()
event_clusterer = EventClusterer()
virtual_day_scheduler = VirtualDayScheduler()
task_generator = TaskGenerator(virtual_day_scheduler)
debbe_selector = DebbeSelector()


async def collect_and_process_events():
    """Scheduled job to collect and process events with 55% organic, 45% RSS weighting."""
    try:
        logger.info("Starting event collection...")
        all_events = []

        # Weighted collection: 55% organic, 45% RSS
        if random.random() < ORGANIC_WEIGHT:
            # Collect organic content first (55% chance to prioritize)
            organic_events = await organic_collector.collect()
            logger.info(f"Collected {len(organic_events)} organic events")
            all_events.extend(organic_events)

        # Collect RSS events
        rss_events = await rss_collector.collect()
        logger.info(f"Collected {len(rss_events)} RSS events")
        all_events.extend(rss_events)

        # If organic was skipped, try again with remaining probability
        if random.random() < ORGANIC_WEIGHT and not any(e.source == "organic" for e in all_events):
            organic_events = await organic_collector.collect()
            logger.info(f"Collected {len(organic_events)} organic events (second pass)")
            all_events.extend(organic_events)

        if not all_events:
            return

        # Cluster events
        clusters = await event_clusterer.cluster_events(all_events)

        # Save clustered events
        for cluster_id, cluster_events in clusters.items():
            await event_clusterer.save_cluster(cluster_id, cluster_events)

            # Generate tasks for each cluster
            for event in cluster_events[:1]:  # One task per cluster
                tasks = await task_generator.generate_tasks_for_event(event)
                logger.info(f"Generated {len(tasks)} tasks for event: {event.title[:50]}...")

    except Exception as e:
        logger.error(f"Error in event collection: {e}")


async def advance_virtual_day():
    """Scheduled job to check and advance virtual day phase."""
    try:
        new_phase = await virtual_day_scheduler.check_and_advance_phase()
        if new_phase:
            logger.info(f"Virtual day advanced to: {new_phase.value}")
    except Exception as e:
        logger.error(f"Error advancing virtual day: {e}")


async def generate_periodic_tasks():
    """Scheduled job to generate periodic tasks."""
    try:
        tasks = await task_generator.generate_periodic_tasks()
        logger.info(f"Generated {len(tasks)} periodic tasks")
    except Exception as e:
        logger.error(f"Error generating periodic tasks: {e}")


async def cleanup_tasks():
    """Scheduled job to clean up expired tasks."""
    try:
        count = await task_generator.cleanup_expired_tasks()
        if count > 0:
            logger.info(f"Cleaned up {count} expired tasks")
    except Exception as e:
        logger.error(f"Error cleaning up tasks: {e}")


async def select_daily_debbe():
    """Scheduled job to select DEBE."""
    try:
        entries = await debbe_selector.select_debe()
        logger.info(f"Selected {len(entries)} DEBE entries")
    except Exception as e:
        logger.error(f"Error selecting DEBE: {e}")


async def update_trending_scores():
    """Scheduled job to update trending scores."""
    try:
        count = await debbe_selector.recalculate_trending_scores()
        logger.info(f"Updated trending scores for {count} topics")
    except Exception as e:
        logger.error(f"Error updating trending scores: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Agenda Engine...")

    await Database.connect()
    logger.info("Connected to database")

    # Initialize virtual day state
    state = await virtual_day_scheduler.get_current_state()
    logger.info(f"Current virtual day phase: {state.current_phase.value}")

    # Schedule jobs
    settings = get_settings()

    if settings.use_daily_cache:
        # Daily cache mode: collect at specific hours
        for hour in settings.feed_collection_hours:
            scheduler.add_job(
                collect_and_process_events,
                'cron',
                hour=hour,
                minute=0,
                id=f'collect_events_{hour}'
            )
        logger.info(f"Daily cache mode enabled. Collection hours: {settings.feed_collection_hours}")
    else:
        # Legacy polling mode
        scheduler.add_job(
            collect_and_process_events,
            'interval',
            seconds=settings.rss_fetch_interval,
            id='collect_events'
        )
        logger.info(f"Polling mode enabled. Interval: {settings.rss_fetch_interval}s")

    scheduler.add_job(
        advance_virtual_day,
        'interval',
        minutes=5,
        id='advance_virtual_day'
    )

    scheduler.add_job(
        generate_periodic_tasks,
        'interval',
        minutes=10,
        id='generate_tasks'
    )

    scheduler.add_job(
        cleanup_tasks,
        'interval',
        minutes=30,
        id='cleanup_tasks'
    )

    scheduler.add_job(
        select_daily_debbe,
        'cron',
        hour=0,
        minute=5,
        id='select_debbe'
    )

    scheduler.add_job(
        update_trending_scores,
        'interval',
        minutes=15,
        id='update_trending'
    )

    scheduler.start()
    logger.info("Scheduler started")

    # Run initial collection
    await collect_and_process_events()

    yield

    # Shutdown
    scheduler.shutdown()
    await Database.disconnect()
    logger.info("Agenda Engine stopped")


app = FastAPI(
    title="Tenekesozluk Agenda Engine",
    description="Manages agenda collection, task generation, and virtual day scheduling",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "agenda-engine",
        "time": datetime.utcnow().isoformat()
    }


@app.get("/status")
async def status():
    """Get current system status."""
    try:
        phase_progress = await virtual_day_scheduler.get_phase_progress()
        return {
            "virtual_day": phase_progress,
            "scheduler_running": scheduler.running
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trigger/collect")
async def trigger_collect():
    """Manually trigger event collection."""
    await collect_and_process_events()
    return {"message": "Event collection triggered"}


@app.post("/trigger/tasks")
async def trigger_tasks():
    """Manually trigger task generation."""
    tasks = await task_generator.generate_periodic_tasks()
    return {"message": f"Generated {len(tasks)} tasks"}


@app.post("/trigger/debbe")
async def trigger_debbe():
    """Manually trigger DEBE selection."""
    entries = await debbe_selector.select_debe()
    return {"message": f"Selected {len(entries)} DEBE entries"}


@app.post("/trigger/trending")
async def trigger_trending():
    """Manually trigger trending score update."""
    count = await debbe_selector.recalculate_trending_scores()
    return {"message": f"Updated {count} trending scores"}


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )
