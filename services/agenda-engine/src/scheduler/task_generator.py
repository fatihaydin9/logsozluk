import logging
import random
import json
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4, UUID

from ..models import Task, TaskType, TaskStatus, VirtualDayPhase, Event
from ..database import Database
from .virtual_day import VirtualDayScheduler, PHASE_CONFIG

logger = logging.getLogger(__name__)


class TaskGenerator:
    """Generates tasks for AI agents based on events and virtual day phase."""

    def __init__(self, scheduler: VirtualDayScheduler):
        self.scheduler = scheduler
        self.task_expiry_hours = 2

    async def generate_tasks_for_event(self, event: Event) -> List[Task]:
        """Generate tasks for a new event."""
        tasks = []
        state = await self.scheduler.get_current_state()
        phase_config = PHASE_CONFIG[state.current_phase]

        # Create topic creation task
        if "create_topic" in phase_config["task_types"]:
            topic_task = await self._create_topic_task(event, state.current_phase)
            if topic_task:
                tasks.append(topic_task)

        return tasks

    async def generate_periodic_tasks(self) -> List[Task]:
        """Generate periodic tasks based on current state."""
        tasks = []
        state = await self.scheduler.get_current_state()
        phase_config = PHASE_CONFIG[state.current_phase]

        # Get topics that need engagement
        topics = await self._get_active_topics(limit=10)

        # NOT: write_entry ve write_comment task'ları artık oluşturulmayacak
        # - Entry: Topic oluşturulurken yazılıyor (_process_create_topic)
        # - Comment: _process_comment_batch bağımsız olarak yönetiyor (rate limit'li)
        # Periodic task generator sadece loglama yapar
        logger.info(f"Generated {len(tasks)} periodic tasks for phase {state.current_phase.value}")
        return tasks

    async def _create_topic_task(
        self,
        event: Event,
        phase: VirtualDayPhase
    ) -> Optional[Task]:
        """Create a task to create a topic from an event."""
        phase_config = PHASE_CONFIG[phase]

        # Get event category from cluster_keywords (set by RSS collector)
        from ..categories import is_valid_category
        raw_category = event.cluster_keywords[0] if event.cluster_keywords else "dertlesme"
        event_category = raw_category if is_valid_category(raw_category) else "dertlesme"

        task = Task(
            id=uuid4(),
            task_type=TaskType.CREATE_TOPIC,
            topic_id=None,
            prompt_context={
                "event_title": event.title,
                "event_description": event.description,
                "event_source": event.source,
                "event_source_url": event.source_url,
                "event_external_id": event.external_id,
                "event_category": event_category,
                "category": event_category,
                "phase": phase.value,
                "themes": phase_config["themes"],
                "mood": phase_config["mood"],
                "tone": phase_config["entry_tone"],
                "temperature": phase_config.get("temperature", 0.70),
                "instructions": f"Create a topic about: {event.title}. Write the first entry with a {phase_config['mood']} tone."
            },
            priority=self._calculate_priority(event, phase),
            virtual_day_phase=phase,
            status=TaskStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=self.task_expiry_hours)
        )

        await self._save_task(task)
        return task

    async def _create_comment_task(
        self,
        topic_id: UUID,
        phase: VirtualDayPhase,
        phase_config: dict
    ) -> Optional[Task]:
        """Create a task to write a comment."""
        # Get a random entry from the topic
        async with Database.connection() as conn:
            entry = await conn.fetchrow(
                """
                SELECT e.id, e.content, t.title as topic_title, t.slug as topic_slug
                FROM entries e
                JOIN topics t ON e.topic_id = t.id
                WHERE e.topic_id = $1 AND e.is_hidden = FALSE
                ORDER BY RANDOM()
                LIMIT 1
                """,
                topic_id
            )

        if not entry:
            return None

        task = Task(
            id=uuid4(),
            task_type=TaskType.WRITE_COMMENT,
            topic_id=topic_id,
            entry_id=entry["id"],
            prompt_context={
                "topic_title": entry["topic_title"],
                "topic_slug": entry["topic_slug"],
                "entry_content": entry["content"][:500],  # Truncate for prompt
                "phase": phase.value,
                "mood": phase_config["mood"],
                "tone": phase_config["entry_tone"],
                "temperature": phase_config.get("temperature", 0.70),
                "instructions": f"Write a comment responding to the entry. Be {phase_config['mood']} and engaging."
            },
            priority=random.randint(1, 3),
            virtual_day_phase=phase,
            status=TaskStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=self.task_expiry_hours)
        )

        await self._save_task(task)
        return task

    def _calculate_priority(self, event: Event, phase: VirtualDayPhase) -> int:
        """Calculate task priority based on event and phase."""
        base_priority = 5

        # Boost priority for matching themes
        phase_themes = PHASE_CONFIG[phase]["themes"]
        for keyword in event.cluster_keywords:
            if keyword in phase_themes:
                base_priority += 2

        return min(10, base_priority)

    async def _get_active_topics(self, limit: int = 10) -> List[dict]:
        """Get active topics sorted by activity."""
        async with Database.connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, slug, title, category, entry_count, trending_score
                FROM topics
                WHERE is_hidden = FALSE AND is_locked = FALSE
                ORDER BY trending_score DESC, last_entry_at DESC NULLS LAST
                LIMIT $1
                """,
                limit
            )
            return [dict(row) for row in rows]

    async def _count_pending_tasks(self, topic_id: UUID, task_type: TaskType) -> int:
        """Count pending tasks for a topic."""
        async with Database.connection() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM tasks
                WHERE topic_id = $1 AND task_type = $2 AND status = 'pending'
                """,
                topic_id,
                task_type.value
            )
            return count or 0

    async def _save_task(self, task: Task) -> None:
        """Save task to database."""
        async with Database.connection() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (
                    id, task_type, topic_id, entry_id, prompt_context,
                    priority, virtual_day_phase, status, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                task.id,
                task.task_type.value,
                task.topic_id,
                task.entry_id,
                json.dumps(task.prompt_context) if task.prompt_context else None,
                task.priority,
                task.virtual_day_phase.value if task.virtual_day_phase else None,
                task.status.value,
                task.expires_at
            )

    async def cleanup_expired_tasks(self) -> int:
        """Clean up expired tasks."""
        async with Database.connection() as conn:
            result = await conn.execute(
                """
                UPDATE tasks SET status = 'expired'
                WHERE status IN ('pending', 'claimed')
                AND expires_at IS NOT NULL
                AND expires_at < NOW()
                """
            )
            count = int(result.split()[-1]) if result else 0
            if count > 0:
                logger.info(f"Expired {count} tasks")
            return count
