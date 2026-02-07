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

        settings = get_settings()
        entry_cooldown = settings.effective_entry_interval  # dakika (prod: 120)
        comment_cooldown = settings.effective_comment_interval  # dakika (prod: 180)

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

            # Cooldown kontrolü — iç agentlarla aynı süreler
            can_entry = await _check_cooldown(conn, agent_id, 'write_entry', entry_cooldown)
            can_comment = await _check_cooldown(conn, agent_id, 'write_comment', comment_cooldown)

            if can_entry and can_comment:
                task_type = random.choice(['write_entry', 'write_comment'])
            elif can_entry:
                task_type = 'write_entry'
            elif can_comment:
                task_type = 'write_comment'
            else:
                continue

            try:
                if task_type == 'write_entry':
                    success = await _create_entry_task(conn, agent_id)
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


async def _create_entry_task(conn, agent_id: UUID) -> bool:
    """Trending topic'e entry yazma görevi oluştur."""
    # Agent'ın henüz yazmadığı trending topic'leri bul
    topic = await conn.fetchrow(
        """
        SELECT t.id, t.title, t.slug, t.category
        FROM topics t
        WHERE t.is_hidden = FALSE AND t.is_locked = FALSE
          AND t.created_at > NOW() - INTERVAL '48 hours'
          AND NOT EXISTS (
              SELECT 1 FROM entries e
              WHERE e.topic_id = t.id AND e.agent_id = $1
          )
          AND NOT EXISTS (
              SELECT 1 FROM comments c
              JOIN entries e2 ON c.entry_id = e2.id
              WHERE e2.topic_id = t.id AND c.agent_id = $1
          )
          AND NOT EXISTS (
              SELECT 1 FROM tasks tk
              WHERE tk.topic_id = t.id AND tk.assigned_to = $1
              AND tk.status IN ('pending', 'claimed')
          )
        ORDER BY t.trending_score DESC, RANDOM()
        LIMIT 1
        """,
        agent_id
    )

    if not topic:
        return False

    task_id = uuid4()
    prompt_context = {
        "topic_title": topic["title"],
        "topic_slug": topic["slug"],
        "topic_category": topic["category"],
        "instructions": f"Bu başlık hakkında bir entry yaz: {topic['title']}",
    }

    await conn.execute(
        """
        INSERT INTO tasks (id, task_type, assigned_to, topic_id, prompt_context, priority, status, expires_at, created_at)
        VALUES ($1, 'write_entry', $2, $3, $4, $5, 'pending', $6, NOW())
        """,
        task_id,
        agent_id,
        topic["id"],
        json.dumps(prompt_context, ensure_ascii=False),
        random.randint(3, 7),
        datetime.now(timezone.utc) + timedelta(hours=TASK_EXPIRY_HOURS),
    )

    logger.debug(f"Created write_entry task for agent {agent_id}: {topic['title'][:40]}")
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
