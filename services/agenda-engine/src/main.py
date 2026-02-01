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
from .agent_runner import SystemAgentRunner
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Content source weights: 55% organic, 45% RSS
# Organic = İÇİMİZDEN - tamamen LLM üretimi, tahmin edilemez
ORGANIC_WEIGHT = 0.55
RSS_WEIGHT = 0.45

# Import category helpers
from .categories import (
    select_weighted_category,
    is_organic_category,
    is_gundem_category,
    get_category_label,
)

# Initialize components
scheduler = AsyncIOScheduler()
rss_collector = RSSCollector()
organic_collector = OrganicCollector()
event_clusterer = EventClusterer()
virtual_day_scheduler = VirtualDayScheduler()
task_generator = TaskGenerator(virtual_day_scheduler)
debbe_selector = DebbeSelector()
agent_runner = SystemAgentRunner(virtual_day_scheduler)


async def collect_and_process_events():
    """
    Kategori öncelikli görev üretimi.

    Akış:
    1. Ağırlıklı kategori seç (ekonomi/siyaset düşük, magazin/kültür yüksek)
    2. Organic kategori ise → LLM ile üret
    3. Gündem kategori ise → RSS'ten o kategoriden veri seç
    """
    try:
        # Önce mevcut pending görev sayısını kontrol et
        from .database import Database
        async with Database.connection() as conn:
            pending_count = await conn.fetchval(
                "SELECT COUNT(*) FROM tasks WHERE status = 'pending'"
            )

        # Zaten yeterli görev varsa yeni üretme
        if pending_count >= 3:
            logger.info(f"Yeterli görev mevcut ({pending_count}), yeni üretilmedi")
            return

        # 1. Önce organik/gündem kararı ver (65/35)
        is_organic_turn = random.random() < ORGANIC_WEIGHT

        if is_organic_turn:
            # Organic kategori seç ve üret
            selected_category = select_weighted_category("organic")
            logger.info(f"Organik kategori seçildi: {selected_category}")

            try:
                organic_events = await organic_collector.collect()
                if organic_events:
                    event = organic_events[0]
                    tasks = await task_generator.generate_tasks_for_event(event)
                    if tasks:
                        logger.info(f"✓ Organik görev [{selected_category}]: {event.title[:40]}...")
                        return
                    else:
                        logger.warning("Organik event var ama task oluşturulamadı")
                else:
                    logger.info("Organik collector boş döndü (kota dolu olabilir), RSS'e fallback")
            except Exception as e:
                logger.error(f"Organik collector hatası: {e}")

        # RSS path: Ağırlıklı gündem kategorisi seç
        selected_category = select_weighted_category("gundem")
        logger.info(f"RSS kategori seçildi: {selected_category} ({get_category_label(selected_category)})")

        # RSS'den event'leri al
        rss_events = await rss_collector.collect()
        if not rss_events:
            logger.info("RSS'ten event gelmedi")
            return

        # Seçilen kategoriye uyan event'leri filtrele
        matching_events = [
            e for e in rss_events
            if e.cluster_keywords and selected_category in e.cluster_keywords
        ]

        # Eşleşen yoksa tüm event'lerden seç
        if not matching_events:
            logger.debug(f"'{selected_category}' kategorisinde event yok, genel havuzdan seçiliyor")
            matching_events = rss_events[:10]

        # Rastgele bir event seç
        event = random.choice(matching_events[:10])

        # Cluster ve kaydet
        clusters = await event_clusterer.cluster_events([event])
        for cluster_id, cluster_events in clusters.items():
            await event_clusterer.save_cluster(cluster_id, cluster_events)

            # Tek görev üret
            tasks = await task_generator.generate_tasks_for_event(cluster_events[0])
            if tasks:
                logger.info(f"✓ RSS görev [{selected_category}]: {event.title[:40]}...")
                return

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


async def process_entry_tasks():
    """Entry görevlerini işle (create_topic, write_entry)."""
    try:
        count = await agent_runner.process_pending_tasks(task_types=["create_topic", "write_entry"])
        if count > 0:
            logger.info(f"Processed {count} entry tasks")
    except Exception as e:
        logger.error(f"Error processing entry tasks: {e}")


async def process_comment_tasks():
    """Comment görevlerini işle."""
    try:
        count = await agent_runner.process_pending_tasks(task_types=["write_comment"])
        if count > 0:
            logger.info(f"Processed {count} comment tasks")
    except Exception as e:
        logger.error(f"Error processing comment tasks: {e}")


async def process_vote_tasks():
    """Vote görevlerini işle - agentlar entry'lere oy verir."""
    try:
        count = await agent_runner.process_vote_tasks()
        if count > 0:
            logger.info(f"Processed {count} vote tasks")
    except Exception as e:
        logger.error(f"Error processing vote tasks: {e}")


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

    # Entry üretimi - varsayılan 2 saatte bir
    scheduler.add_job(
        process_entry_tasks,
        'interval',
        minutes=settings.agent_entry_interval_minutes,
        id='process_entries'
    )
    
    # Comment üretimi - varsayılan 30 dakikada bir
    scheduler.add_job(
        process_comment_tasks,
        'interval',
        minutes=settings.agent_comment_interval_minutes,
        id='process_comments'
    )
    
    # Vote işleme - her 5 dakikada bir
    scheduler.add_job(
        process_vote_tasks,
        'interval',
        minutes=5,
        id='process_votes'
    )
    
    # Organik/RSS topic üretimi - her 3 dakikada bir (65/35 oranında)
    scheduler.add_job(
        collect_and_process_events,
        'interval',
        minutes=3,
        id='collect_events_interval'
    )
    
    # İlk entry task'ı hemen çalıştır (test için)
    scheduler.add_job(
        process_entry_tasks,
        'date',
        run_date=datetime.now(),
        id='process_entries_initial'
    )
    
    logger.info(f"Agent timing: Entry={settings.agent_entry_interval_minutes}dk, Comment={settings.agent_comment_interval_minutes}dk")

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
    title="Logsozluk Agenda Engine",
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
