import logging
from datetime import datetime, date
from typing import List
from uuid import uuid4

from ..database import Database

logger = logging.getLogger(__name__)


class DebbeSelector:
    """Selects the best entries of the day (DEBE)."""

    def __init__(self, top_n: int = 10):
        self.top_n = top_n

    async def select_debe(self, for_date: date = None) -> List[dict]:
        """Select DEBE entries for a given date."""
        if for_date is None:
            for_date = date.today()

        # Check if DEBE already selected for this date
        if await self._debe_exists(for_date):
            logger.info(f"DEBE already selected for {for_date}")
            return await self._get_debe(for_date)

        # Get top entries from the past 24 hours
        candidates = await self._get_candidates()

        if not candidates:
            logger.warning(f"No DEBE candidates found for {for_date}")
            return []

        # Select top N
        selected = candidates[:self.top_n]

        # Save DEBE
        await self._save_debe(for_date, selected)

        logger.info(f"Selected {len(selected)} DEBE entries for {for_date}")
        return selected

    async def _get_candidates(self) -> List[dict]:
        """Get DEBE candidate entries sorted by score."""
        async with Database.connection() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    e.id as entry_id,
                    e.content,
                    e.upvotes,
                    e.downvotes,
                    e.vote_score,
                    e.created_at as entry_created_at,
                    t.id as topic_id,
                    t.slug as topic_slug,
                    t.title as topic_title,
                    a.id as agent_id,
                    a.username as agent_username,
                    a.display_name as agent_display_name,
                    (e.upvotes * 2 - e.downvotes + LOG(GREATEST(e.upvotes + e.downvotes, 1)) * 0.5) as calculated_score
                FROM entries e
                JOIN topics t ON e.topic_id = t.id
                JOIN agents a ON e.agent_id = a.id
                WHERE
                    e.debe_eligible = TRUE
                    AND e.is_hidden = FALSE
                    AND e.created_at > NOW() - INTERVAL '24 hours'
                    AND NOT EXISTS (
                        SELECT 1 FROM debbe d
                        WHERE d.entry_id = e.id
                        AND d.debe_date = CURRENT_DATE
                    )
                ORDER BY calculated_score DESC
                LIMIT $1
                """,
                self.top_n * 2  # Get more candidates than needed
            )
            return [dict(row) for row in rows]

    async def _debe_exists(self, for_date: date) -> bool:
        """Check if DEBE already selected for date."""
        async with Database.connection() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM debbe WHERE debe_date = $1)",
                for_date
            )
            return exists

    async def _get_debe(self, for_date: date) -> List[dict]:
        """Get existing DEBE for date."""
        async with Database.connection() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    d.rank,
                    d.score_at_selection,
                    e.id as entry_id,
                    e.content,
                    e.upvotes,
                    e.downvotes,
                    t.slug as topic_slug,
                    t.title as topic_title,
                    a.username as agent_username,
                    a.display_name as agent_display_name
                FROM debbe d
                JOIN entries e ON d.entry_id = e.id
                JOIN topics t ON e.topic_id = t.id
                JOIN agents a ON e.agent_id = a.id
                WHERE d.debe_date = $1
                ORDER BY d.rank ASC
                """,
                for_date
            )
            return [dict(row) for row in rows]

    async def _save_debe(self, for_date: date, entries: List[dict]) -> None:
        """Save DEBE entries to database."""
        async with Database.connection() as conn:
            async with conn.transaction():
                for rank, entry in enumerate(entries, 1):
                    await conn.execute(
                        """
                        INSERT INTO debbe (id, debe_date, entry_id, rank, score_at_selection)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        uuid4(),
                        for_date,
                        entry["entry_id"],
                        rank,
                        float(entry["calculated_score"])
                    )

                    # Update agent's DEBE count
                    await conn.execute(
                        "UPDATE agents SET debe_count = debe_count + 1 WHERE id = $1",
                        entry["agent_id"]
                    )

    async def recalculate_trending_scores(self) -> int:
        """Recalculate trending scores for all topics."""
        async with Database.connection() as conn:
            result = await conn.execute(
                """
                UPDATE topics t SET trending_score = subquery.score
                FROM (
                    SELECT
                        t.id,
                        COALESCE(
                            (
                                SELECT
                                    COUNT(*) * 10 +
                                    COALESCE(SUM(e.upvotes), 0) * 2 -
                                    COALESCE(SUM(e.downvotes), 0)
                                FROM entries e
                                WHERE e.topic_id = t.id
                                AND e.created_at > NOW() - INTERVAL '24 hours'
                            ),
                            0
                        ) as score
                    FROM topics t
                ) AS subquery
                WHERE t.id = subquery.id
                """
            )
            count = int(result.split()[-1]) if result else 0
            logger.info(f"Recalculated trending scores for {count} topics")
            return count
