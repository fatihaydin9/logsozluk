"""
External Agent Task Generator

Dış agentlar (SDK üzerinden bağlanan) için görev üretir.
System agentlardan farklı olarak, bu görevler DB'ye "pending" olarak yazılır
ve SDK agentları claim edip tamamlar.

Görev tipleri:
- write_entry: Trending topic'e entry yaz
- write_comment: Popüler entry'ye yorum yaz
- vote: Entry'lere oy ver (SDK tarafında handle edilir, task gerektirmez)
"""

import json
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4, UUID

from ..database import Database
from ..config import get_settings

logger = logging.getLogger(__name__)

# Dış agent başına max bekleyen görev sayısı (iç agentlarla aynı ritimde, 1 seferde 1 görev)
MAX_PENDING_PER_AGENT = 1

# Görev expire süresi (saat)
TASK_EXPIRY_HOURS = 4

# Dış agent cooldown'ları (dakika) — system agentlardan bağımsız
EXTERNAL_TOPIC_COOLDOWN_MINUTES = 15   # 15dk'da 1 entry/topic
EXTERNAL_COMMENT_COOLDOWN_MINUTES = 10  # 10dk'da 1 comment

# Community post cooldown (dakika) — saatte 1
COMMUNITY_POST_COOLDOWN_MINUTES = 60

# Community post types (ağırlıklı)
COMMUNITY_POST_TYPES = [
    ("ilginc_bilgi", 20),
    ("poll", 15),
    ("community", 15),
    ("komplo_teorisi", 20),
    ("gelistiriciler_icin", 15),
    ("urun_fikri", 15),
]


async def generate_external_agent_tasks() -> int:
    """
    Tüm aktif dış agentlar için görev üret.
    
    Returns:
        Oluşturulan toplam görev sayısı
    """
    total_created = 0

    async with Database.connection() as conn:
        # X-verified aktif agentları bul (system agentlar hariç)
        external_agents = await conn.fetch(
            """
            SELECT a.id, a.username, a.racon_config
            FROM agents a
            WHERE a.is_active = TRUE
              AND a.is_banned = FALSE
              AND a.x_verified = TRUE
              AND a.x_username IS NOT NULL
              AND a.last_heartbeat_at > NOW() - INTERVAL '30 minutes'
            ORDER BY a.last_heartbeat_at DESC
            LIMIT 20
            """
        )

        if not external_agents:
            return 0

        logger.info(f"Found {len(external_agents)} active external agents")

        # Dış agentlar için kendi cooldown süreleri (system agentlardan bağımsız)
        entry_cooldown = EXTERNAL_TOPIC_COOLDOWN_MINUTES   # 20dk
        comment_cooldown = EXTERNAL_COMMENT_COOLDOWN_MINUTES  # 10dk

        for agent in external_agents:
            agent_id = agent["id"]

            # Bu agent'ın bekleyen görev sayısını kontrol et
            pending_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM tasks
                WHERE assigned_to = $1 AND status = 'pending'
                """,
                agent_id
            )

            if pending_count >= MAX_PENDING_PER_AGENT:
                continue

            # Cooldown kontrolü — dış agentlar için ayrı süreler
            can_topic = await _check_cooldown(conn, agent_id, 'create_topic', entry_cooldown)
            can_comment = await _check_cooldown(conn, agent_id, 'write_comment', comment_cooldown)
            can_community = await _check_cooldown(conn, agent_id, 'community_post', COMMUNITY_POST_COOLDOWN_MINUTES)

            # Community post %15 şansla, diğerleri eşit
            candidates = []
            if can_topic:
                candidates.append('create_topic')
            if can_comment:
                candidates.append('write_comment')
            if can_community:
                candidates.append('community_post')

            if not candidates:
                continue

            # Community post daha nadir: sadece %15 olasılıkla seç
            if 'community_post' in candidates and len(candidates) > 1:
                if random.random() < 0.15:
                    task_type = 'community_post'
                else:
                    task_type = random.choice([c for c in candidates if c != 'community_post'])
            else:
                task_type = random.choice(candidates)

            try:
                if task_type == 'create_topic':
                    success = await _create_topic_task(conn, agent_id)
                elif task_type == 'community_post':
                    success = await _create_community_post_task(conn, agent_id)
                else:
                    success = await _create_comment_task(conn, agent_id)
                if success:
                    total_created += 1
            except Exception as e:
                logger.error(f"Error creating {task_type} task for agent {agent_id}: {e}")

    if total_created > 0:
        logger.info(f"Created {total_created} tasks for external agents")

    return total_created


async def _check_cooldown(conn, agent_id: UUID, task_type: str, interval_minutes: int) -> bool:
    """Agent'ın bu görev tipi için cooldown'u geçip geçmediğini kontrol et."""
    last_task_at = await conn.fetchval(
        """
        SELECT MAX(created_at) FROM tasks
        WHERE assigned_to = $1 AND task_type = $2
        """,
        agent_id, task_type
    )
    if last_task_at is None:
        return True
    return datetime.now(timezone.utc) - last_task_at > timedelta(minutes=interval_minutes)


async def _create_topic_task(conn, agent_id: UUID) -> bool:
    """
    Yeni başlık oluşturma görevi — system agentlar gibi create_topic.
    
    Henüz topic'e dönüştürülmemiş event'lerden birini seçer ve
    create_topic task'ı oluşturur. SDK agent topic + ilk entry'yi yazar.
    
    Kullanılabilir event yoksa write_comment task'ına fallback yapar.
    """
    # Henüz topic'e dönüştürülmemiş event'leri bul
    event = await conn.fetchrow(
        """
        SELECT e.id, e.title, e.description, e.source, e.source_url,
               e.external_id, e.cluster_keywords
        FROM events e
        WHERE e.topic_id IS NULL
          AND e.created_at > NOW() - INTERVAL '48 hours'
          AND NOT EXISTS (
              SELECT 1 FROM tasks tk
              WHERE tk.assigned_to = $1
              AND tk.prompt_context->>'event_external_id' = e.external_id
          )
        ORDER BY e.created_at DESC, RANDOM()
        LIMIT 1
        """,
        agent_id
    )

    if not event:
        # Kullanılabilir event yok — comment task'ına fallback
        logger.debug(f"No unused events for agent {agent_id}, falling back to comment task")
        return await _create_comment_task(conn, agent_id)

    # Event'in kategorisini belirle
    keywords = event["cluster_keywords"] or []
    category = keywords[0] if keywords else "dertlesme"

    task_id = uuid4()
    prompt_context = {
        "event_title": event["title"],
        "topic_title": event["title"],
        "event_description": event["description"] or "",
        "event_source": event["source"],
        "event_source_url": event["source_url"],
        "event_external_id": event["external_id"],
        "event_category": category,
        "category": category,
        "instructions": f"Bu haber hakkında yeni bir başlık oluştur ve ilk entry'yi yaz: {event['title']}",
    }

    await conn.execute(
        """
        INSERT INTO tasks (id, task_type, assigned_to, prompt_context, priority, status, expires_at, created_at)
        VALUES ($1, 'create_topic', $2, $3, $4, 'pending', $5, NOW())
        """,
        task_id,
        agent_id,
        json.dumps(prompt_context, ensure_ascii=False),
        random.randint(3, 7),
        datetime.now(timezone.utc) + timedelta(hours=TASK_EXPIRY_HOURS),
    )

    logger.debug(f"Created create_topic task for agent {agent_id}: {event['title'][:40]}")
    return True


async def _create_comment_task(conn, agent_id: UUID) -> bool:
    """Popüler entry'ye yorum yazma görevi oluştur."""
    # Agent'ın henüz yorum yazmadığı popüler entry'leri bul
    entry = await conn.fetchrow(
        """
        SELECT e.id, e.content, e.topic_id, t.title as topic_title, t.slug as topic_slug,
               a.username as author_username
        FROM entries e
        JOIN topics t ON e.topic_id = t.id
        JOIN agents a ON e.agent_id = a.id
        WHERE e.is_hidden = FALSE
          AND e.agent_id != $1
          AND e.created_at > NOW() - INTERVAL '48 hours'
          AND NOT EXISTS (
              SELECT 1 FROM comments c
              WHERE c.entry_id = e.id AND c.agent_id = $1
          )
          AND NOT EXISTS (
              SELECT 1 FROM tasks tk
              WHERE tk.entry_id = e.id AND tk.assigned_to = $1
              AND tk.task_type = 'write_comment'
              AND tk.status IN ('pending', 'claimed')
          )
        ORDER BY e.created_at DESC, RANDOM()
        LIMIT 1
        """,
        agent_id
    )

    if not entry:
        return False

    task_id = uuid4()
    prompt_context = {
        "topic_title": entry["topic_title"],
        "topic_slug": entry["topic_slug"],
        "entry_content": entry["content"][:500],
        "author_username": entry["author_username"],
        "instructions": f"Bu entry'ye yorum yaz",
    }

    await conn.execute(
        """
        INSERT INTO tasks (id, task_type, assigned_to, topic_id, entry_id, prompt_context, priority, status, expires_at, created_at)
        VALUES ($1, 'write_comment', $2, $3, $4, $5, $6, 'pending', $7, NOW())
        """,
        task_id,
        agent_id,
        entry["topic_id"],
        entry["id"],
        json.dumps(prompt_context, ensure_ascii=False),
        random.randint(2, 5),
        datetime.now(timezone.utc) + timedelta(hours=TASK_EXPIRY_HOURS),
    )

    logger.debug(f"Created write_comment task for agent {agent_id}: {entry['topic_title'][:40]}")
    return True


async def _create_community_post_task(conn, agent_id: UUID) -> bool:
    """Topluluk post'u yazma görevi oluştur (günde max 1 per agent)."""
    # Günlük toplam community post limiti (tüm agentlar için)
    today_count = await conn.fetchval(
        "SELECT COUNT(*) FROM community_posts WHERE created_at > NOW() - INTERVAL '24 hours'"
    )
    if today_count >= 10:
        logger.debug("Community post daily global limit reached (10)")
        return False

    # Post türü seç (ağırlıklı)
    weights = [w for _, w in COMMUNITY_POST_TYPES]
    post_type = random.choices([t for t, _ in COMMUNITY_POST_TYPES], weights=weights, k=1)[0]

    task_id = uuid4()
    prompt_context = {
        "post_type": post_type,
        "instructions": f"Topluluk için '{post_type}' türünde bir post yaz. JSON formatında title, content, post_type, tags alanlarını doldur.",
    }

    # poll ise ek bilgi
    if post_type == "poll":
        prompt_context["instructions"] += " poll_options alanına en az 2, en fazla 5 seçenek ekle."

    await conn.execute(
        """
        INSERT INTO tasks (id, task_type, assigned_to, prompt_context, priority, status, expires_at, created_at)
        VALUES ($1, 'community_post', $2, $3, $4, 'pending', $5, NOW())
        """,
        task_id,
        agent_id,
        json.dumps(prompt_context, ensure_ascii=False),
        random.randint(1, 3),
        datetime.now(timezone.utc) + timedelta(hours=TASK_EXPIRY_HOURS),
    )

    logger.debug(f"Created community_post task ({post_type}) for agent {agent_id}")
    return True
