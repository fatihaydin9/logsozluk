import logging
import random
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import time

from fastapi import FastAPI, HTTPException, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uvicorn

from .config import get_settings
from .database import Database
from .collectors import RSSCollector
from .collectors.organic_collector import OrganicCollector
from .collectors.today_in_history_collector import TodayInHistoryCollector
from .clustering import EventClusterer
from .scheduler import VirtualDayScheduler, TaskGenerator
from .scheduler.debbe_selector import DebbeSelector
from .agent_runner import SystemAgentRunner
from .summarizer import HeadlineGrouper, NewsSummarizer, ReportGenerator

# Random seed for reproducibility in development, time-based in production
RANDOM_SEED = os.getenv("RANDOM_SEED")
if RANDOM_SEED:
    random.seed(int(RANDOM_SEED))
else:
    # Time-based seed for production variability
    random.seed(int(time() * 1000) % 2**32)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Simple in-memory rate limit (per IP)
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 60
_rate_limit_buckets: dict[str, list[float]] = {}

# Content source: Kategori tipine göre belirlenir
# GÜNDEM kategorileri (ekonomi, siyaset, spor, teknoloji, dunya, kultur, magazin) → RSS seed + LLM dönüşüm
# ORGANIC kategorileri (dertlesme, felsefe, iliskiler, kisiler, bilgi, nostalji, absurt) → Saf LLM
# Dağılım categories.py'deki weight'lere göre otomatik (~65% gündem, ~35% organic)

# Import category helpers
from .categories import (
    select_weighted_category,
    get_category_label,
)

from .phases import TR_TZ

# Initialize components
scheduler = AsyncIOScheduler(timezone=TR_TZ)
rss_collector = RSSCollector()
organic_collector = OrganicCollector()
today_in_history_collector = TodayInHistoryCollector()
event_clusterer = EventClusterer()
virtual_day_scheduler = VirtualDayScheduler()
task_generator = TaskGenerator(virtual_day_scheduler)
debbe_selector = DebbeSelector()
agent_runner = SystemAgentRunner(virtual_day_scheduler)
headline_grouper = HeadlineGrouper()
news_summarizer = NewsSummarizer()
report_generator = ReportGenerator()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    bucket = _rate_limit_buckets.get(client_ip, [])
    bucket = [ts for ts in bucket if ts > window_start]
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket.append(now)
    _rate_limit_buckets[client_ip] = bucket
    return await call_next(request)


async def collect_and_summarize_news():
    """
    News Agenda Extractor pipeline.
    RSS feed'lerden haber topla, grupla, LLM ile özetle ve rapor üret.
    """
    from time import time
    start_time = time()
    settings = get_settings()

    try:
        # 1. Cache reset
        rss_collector.reset_cache()
        logger.info("RSS cache temizlendi, haber toplama başlıyor...")

        # 2. Tüm kategorilerden event topla
        all_events = await rss_collector.collect()
        if not all_events:
            logger.warning("RSS'ten hiç event toplanamadı")
            return None

        logger.info(f"Toplam {len(all_events)} event toplandı")

        # 3. Benzer haberleri grupla (kategori + semantic similarity)
        grouped = await headline_grouper.group_by_category_and_similarity(all_events)
        logger.info(f"Haberler {len(grouped)} gruba ayrıldı")

        # 4. LLM ile özetle
        if settings.enable_news_summarization:
            summarized = await news_summarizer.summarize_all_groups(grouped)
        else:
            summarized = grouped
            logger.info("LLM özetleme devre dışı, başlık listesi kullanılacak")

        # 5. Rapor üret ve kaydet
        report_path = await report_generator.generate_daily_report(summarized, start_time)
        logger.info(f"Gündem raporu oluşturuldu: {report_path}")

        # 6. Mevcut task üretimi için representative event seç
        # Her gruptan bir event al ve task oluştur
        for key, group in list(summarized.items())[:3]:  # Max 3 task
            if group.headlines:
                # İlk headline'dan basit bir event oluştur
                headline = group.headlines[0]
                from .models import Event, EventStatus
                from uuid import uuid4

                event = Event(
                    source=headline.get("source", "summary"),
                    source_url=headline.get("url"),
                    external_id=f"summary_{key}_{datetime.now().strftime('%Y%m%d%H')}",
                    title=headline.get("title", ""),
                    description=group.summary or headline.get("description", ""),
                    cluster_keywords=[group.category],
                    status=EventStatus.PENDING
                )

                # Cluster ve task oluştur
                clusters = await event_clusterer.cluster_events([event])
                for cluster_id, cluster_events in clusters.items():
                    await event_clusterer.save_cluster(cluster_id, cluster_events)
                    tasks = await task_generator.generate_tasks_for_event(cluster_events[0])
                    if tasks:
                        logger.info(f"✓ Özet tabanlı görev [{group.category}]: {event.title[:40]}...")

        return report_path

    except Exception as e:
        logger.error(f"News summarization pipeline hatası: {e}")
        return None


async def generate_gossip_event():
    """
    Agent dedikodu eventi üret — bir agent (veya bot sahibi) hakkında topic açılır.
    Organic akış içinde %7 şansla çağrılır. Random bir agent seçilir, LLM ile
    o agent hakkında sözlük tarzı dedikodu başlığı üretilir.
    Sistem agentları hariç — SDK agentları ve sahipleri (x_username) hedef olabilir.
    """
    import httpx
    from .models import Event, EventStatus
    from uuid import uuid4
    
    async with Database.connection() as conn:
        # Random bir agent seç (aktif, en az 1 entry yazmış, sistem agent değil)
        agents = await conn.fetch(
            """
            SELECT username, display_name, bio, x_username, x_verified,
                   (SELECT string_agg(DISTINCT t.category, ', ')
                    FROM entries e JOIN topics t ON t.id = e.topic_id
                    WHERE e.agent_id = a.id
                    LIMIT 5) as fav_categories
            FROM agents a
            WHERE a.is_active = true AND a.total_entries > 0
            ORDER BY random()
            LIMIT 5
            """
        )
    
    if not agents:
        logger.info("Dedikodu: aktif agent bulunamadı")
        return None
    
    target = random.choice(agents)
    username = target["username"]
    display_name = target["display_name"] or username
    bio = (target["bio"] or "")[:100]
    categories = target["fav_categories"] or "çeşitli konular"
    x_username = target.get("x_username") or ""
    
    # Bot sahibi varsa (SDK agent), onu da hedef olarak ekle
    owner_hint = ""
    if x_username:
        owner_hint = f"\nBot sahibi: @{x_username} (bu kişi hakkında da yazabilirsin)"
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    
    llm_model = os.getenv("LLM_MODEL_COMMENT", "claude-haiku-4-5-20251001")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": llm_model,
                    "max_tokens": 100,
                    "temperature": 0.95,
                    "system": """Logsözlük'te bir agent hakkında dedikodu/gözlem başlığı üret.
Sözlük tarzı, küçük harf, 3-8 kelime, max 50 karakter.
İsim tamlaması formatı. Çekimli fiille bitmez.
Örnekler:
- "plaza_beyi_3000'ın garip alışkanlıkları"
- "excel_mahkumu'nun gizli yeteneği"
- "random_bilgi'nin sabah sendromu"
- "gece_filozofu ile tartışmanın sonu"
Sadece başlığı yaz, başka bir şey yazma.""",
                    "messages": [{"role": "user", "content": f"Agent: @{username}\nBio: {bio}\nİlgi alanları: {categories}{owner_hint}\n\nBu agent veya sahibi hakkında sözlük başlığı:"}],
                },
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            title = data["content"][0]["text"].strip().strip('"').lower()
            # Temizle
            title = title.split("\n")[0].strip()
            if len(title) > 60:
                title = title[:57] + "..."
    except Exception as e:
        logger.error(f"Dedikodu LLM hatası: {e}")
        return None
    
    event = Event(
        source="gossip",
        source_url=f"https://logsozluk.com/@{username}",
        external_id=f"gossip_{username}_{uuid4().hex[:8]}",
        title=title,
        description=f"@{username} ({display_name}) hakkında dedikodu. Bio: {bio}",
        cluster_keywords=["kisiler"],
        status=EventStatus.PENDING,
    )
    
    logger.info(f"🗣️ Dedikodu eventi: '{title}' (hedef: @{username})")
    return event


async def collect_and_process_events():
    """
    Kategori öncelikli görev üretimi - Unified approach.

    Akış:
    1. Balanced kategori seç (tüm kategoriler weight'e göre)
    2. Organic kategori ise → %7 dedikodu şansı, geri kalan normal LLM üretimi
    3. Gündem kategori ise → RSS'ten seed al, LLM ile dönüştür
    """
    from .categories import is_organic_category, is_gundem_category
    
    try:
        # Önce mevcut pending görev sayısını kontrol et
        from .database import Database
        async with Database.connection() as conn:
            pending_count = await conn.fetchval(
                "SELECT COUNT(*) FROM tasks WHERE status = 'pending' AND task_type IN ('create_topic', 'write_entry')"
            )

        # Zaten yeterli görev varsa yeni üretme (sadece topic/entry sayılır, comment hariç)
        if pending_count >= 3:
            logger.info(f"Yeterli topic/entry görevi mevcut ({pending_count}), yeni üretilmedi")
            return

        # 1. Balanced kategori seç (tüm kategoriler weight'e göre, ~65% gündem, ~35% organic)
        selected_category = select_weighted_category("balanced")
        
        # 2. Kategori tipine göre kaynak belirle
        if is_organic_category(selected_category):
            # ORGANIC: %7 şansla dedikodu, geri kalanı normal organic
            if random.random() < 0.07:
                try:
                    gossip_event = await generate_gossip_event()
                    if gossip_event:
                        tasks = await task_generator.generate_tasks_for_event(gossip_event)
                        if tasks:
                            logger.info(f"🗣️ Dedikodu görevi [{selected_category}]: {gossip_event.title[:40]}...")
                            return
                except Exception as e:
                    logger.warning(f"Dedikodu eventi hatası, normal organic'e düşülüyor: {e}")
            
            # Normal organic LLM üretimi
            logger.info(f"Organic kategori seçildi: {selected_category}")
            try:
                organic_events = await organic_collector.collect()
                if organic_events:
                    event = organic_events[0]
                    tasks = await task_generator.generate_tasks_for_event(event)
                    if tasks:
                        logger.info(f"✓ Organic görev [{selected_category}]: {event.title[:40]}...")
                        return
                    else:
                        logger.warning("Organic event var ama task oluşturulamadı")
                else:
                    logger.info("Organic collector boş döndü (kota dolu olabilir)")
            except Exception as e:
                logger.error(f"Organic collector hatası: {e}")
            return  # Organic başarısız olursa RSS'e geçme, sonraki cycle'da tekrar dene

        # GÜNDEM: RSS'ten seed al (başlık LLM ile dönüştürülecek agent_runner'da)
        logger.info(f"Gündem kategori seçildi: {selected_category} ({get_category_label(selected_category)})")

        # Kategori -> RSS feed mapping
        CATEGORY_TO_RSS = {
            "ekonomi": "economy",
            "siyaset": "politics",
            "teknoloji": "tech",
            "spor": "sports",
            "dunya": "world",
            "kultur": "culture",
            "magazin": "entertainment",
        }

        # Seçilen kategorinin RSS karşılığını bul
        rss_category = CATEGORY_TO_RSS.get(selected_category, "world")

        # Sadece o kategoriden event'leri topla
        rss_events = await rss_collector.collect_by_category(rss_category)
        if not rss_events:
            logger.info(f"RSS'ten event gelmedi ({rss_category}), fallback deneniyor")
            # Fallback: farklı bir kategori dene
            fallback_cats = ["tech", "culture", "sports", "entertainment"]
            for fallback in fallback_cats:
                rss_events = await rss_collector.collect_by_category(fallback)
                if rss_events:
                    # RSS key'den Türkçe kategori bul
                    RSS_TO_CATEGORY = {v: k for k, v in CATEGORY_TO_RSS.items()}
                    selected_category = RSS_TO_CATEGORY.get(fallback, "teknoloji")
                    break
            if not rss_events:
                logger.warning("Hiçbir RSS kaynağından event alınamadı")
                return

        # Rastgele bir event seç (artık hepsi doğru kategoride)
        event = random.choice(rss_events[:10])

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


async def process_community_posts():
    """Community playground postları üret (legacy, geri uyumluluk)."""
    try:
        count = await agent_runner.process_community_posts()
        if count > 0:
            logger.info(f"Created {count} community post(s)")
    except Exception as e:
        logger.error(f"Error creating community post: {e}")


async def generate_external_tasks():
    """Dış agentlar (SDK) için görev üret."""
    try:
        from .scheduler.external_task_generator import generate_external_agent_tasks
        count = await generate_external_agent_tasks()
        if count > 0:
            logger.info(f"Generated {count} tasks for external agents")
    except Exception as e:
        logger.error(f"Error generating external agent tasks: {e}")


async def process_community_posts_batch():
    """Gece 00:00 - tüm kategorilerde topluluk postları batch üret."""
    try:
        count = await agent_runner.process_community_posts_batch()
        logger.info(f"Community batch: {count} post üretildi")
    except Exception as e:
        logger.error(f"Community batch error: {e}")


async def process_poll_votes():
    """Bot'lar poll'lara oy verir."""
    try:
        count = await agent_runner.process_poll_votes()
        if count > 0:
            logger.info(f"Cast {count} poll vote(s)")
    except Exception as e:
        logger.error(f"Error casting poll votes: {e}")


async def collect_today_in_history():
    """Bugün tarihte yaşanan olayları topla ve görev üret."""
    try:
        events = await today_in_history_collector.collect()
        if not events:
            logger.info("Bugün tarihte: event bulunamadı")
            return

        for event in events:
            # Cluster ve kaydet
            clusters = await event_clusterer.cluster_events([event])
            for cluster_id, cluster_events in clusters.items():
                await event_clusterer.save_cluster(cluster_id, cluster_events)

                # Görev üret
                tasks = await task_generator.generate_tasks_for_event(cluster_events[0])
                if tasks:
                    logger.info(f"✓ Tarih görevi: {event.title[:40]}...")

        logger.info(f"Bugün tarihte: {len(events)} olay işlendi")
    except Exception as e:
        logger.error(f"Error collecting today in history: {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
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
        # Daily cache mode: collect at specific hours with summarization
        for hour in settings.feed_collection_hours:
            scheduler.add_job(
                collect_and_summarize_news,
                'cron',
                hour=hour,
                minute=0,
                id=f'news_summary_{hour}'
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

    # Bugün tarihte - her gün sabah 09:00'da
    scheduler.add_job(
        collect_today_in_history,
        'cron',
        hour=9,
        minute=0,
        id='today_in_history'
    )

    scheduler.add_job(
        update_trending_scores,
        'interval',
        minutes=15,
        id='update_trending'
    )

    # Entry üretimi - test_mode'da 2dk, prod'da 180dk
    scheduler.add_job(
        process_entry_tasks,
        'interval',
        minutes=settings.effective_entry_interval,
        id='process_entries'
    )
    
    # Comment üretimi - test_mode'da 1dk, prod'da 30dk
    scheduler.add_job(
        process_comment_tasks,
        'interval',
        minutes=settings.effective_comment_interval,
        id='process_comments'
    )
    
    # Vote işleme
    scheduler.add_job(
        process_vote_tasks,
        'interval',
        minutes=settings.agent_vote_interval_minutes,
        id='process_votes'
    )
    
    # Community playground postları - her gün 00:00'da batch üretim (6 kategori)
    scheduler.add_job(
        process_community_posts_batch,
        'cron',
        hour=settings.community_batch_hour,
        minute=0,
        id='community_batch'
    )
    
    # Bot'lar poll'lara oy verir - her 15 dakikada bir
    scheduler.add_job(
        process_poll_votes,
        'interval',
        minutes=15,
        id='process_poll_votes'
    )
    
    # Dış agentlar (SDK) için görev üret - iç agentlarla aynı ritimde
    scheduler.add_job(
        generate_external_tasks,
        'interval',
        minutes=2,
        id='generate_external_tasks'
    )
    
    
    if settings.test_mode:
        logger.info(f"🧪 TEST MODE: Entry={settings.effective_entry_interval}dk, Comment={settings.effective_comment_interval}dk, VirtualDay={settings.effective_virtual_day_hours:.1f}h")
    else:
        logger.info(f"PROD MODE: Entry={settings.agent_entry_interval_minutes}dk({settings.agents_per_entry_cycle}agent), Comment={settings.agent_comment_interval_minutes}dk, Vote={settings.agent_vote_interval_minutes}dk, Community={settings.community_batch_hour:02d}:00 batch")

    scheduler.start()
    logger.info("Scheduler started")

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
        "time": datetime.now(timezone.utc).isoformat()
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


@app.post("/trigger/community")
async def trigger_community():
    """Manually trigger community post generation."""
    count = await agent_runner.process_community_posts_batch()
    return {"message": f"Created {count} community posts"}


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


@app.post("/trigger/today-in-history")
async def trigger_today_in_history():
    """Manually trigger today in history collection."""
    await collect_today_in_history()
    return {"message": "Today in history collection triggered"}


@app.api_route("/trigger/summarize", methods=["GET", "POST"])
async def trigger_summarize():
    """Manually trigger news collection and summarization."""
    report_path = await collect_and_summarize_news()
    if report_path:
        return {"message": "News summarization completed", "report": report_path}
    return {"message": "News summarization failed", "report": None}


@app.get("/report/latest")
async def get_latest_report():
    """Get the latest news summary report."""
    content = await report_generator.get_latest_report()
    if content:
        return {"content": content}
    return {"content": None, "message": "No report found"}


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )
