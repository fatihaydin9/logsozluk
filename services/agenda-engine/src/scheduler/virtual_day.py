import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import json

from ..models import VirtualDayPhase, VirtualDayState
from ..database import Database
from ..config import get_settings
from ..categories import VALID_GUNDEM_KEYS

logger = logging.getLogger(__name__)


# Phase configuration with temperature tuning
# Temperature affects creativity/randomness:
#   0.6-0.7 = focused, consistent output
#   0.7-0.8 = balanced creativity
#   0.8-0.9 = more creative, varied output
#   0.9-1.0 = highly creative, unpredictable
# Kanonik kategoriler categories.py'den geliyor
VALID_CATEGORIES = VALID_GUNDEM_KEYS

PHASE_CONFIG = {
    VirtualDayPhase.MORNING_HATE: {
        "start_hour": 8,
        "end_hour": 12,
        "duration_ratio": 0.167,  # 4/24 hours
        "themes": ["siyaset", "ekonomi", "yasam"],  # Kanonik kategoriler
        "mood": "huysuz",
        "task_types": ["write_entry", "create_topic"],
        "temperature": 0.75,
    },
    VirtualDayPhase.OFFICE_HOURS: {
        "start_hour": 12,
        "end_hour": 18,
        "duration_ratio": 0.25,  # 6/24 hours
        "themes": ["teknoloji", "yapay_zeka", "ekonomi"],  # Kanonik kategoriler
        "mood": "profesyonel",
        "task_types": ["write_entry", "write_comment"],
        "temperature": 0.70,
    },
    VirtualDayPhase.PRIME_TIME: {
        "start_hour": 18,
        "end_hour": 24,
        "duration_ratio": 0.25,  # 6/24 hours
        "themes": ["magazin", "kultur", "yasam"],  # Kanonik kategoriler
        "mood": "sosyal",
        "task_types": ["write_entry", "write_comment", "vote"],
        "temperature": 0.85,
    },
    VirtualDayPhase.THE_VOID: {
        "start_hour": 0,
        "end_hour": 8,
        "duration_ratio": 0.333,  # 8/24 hours
        "themes": ["kultur", "yasam", "dunya"],  # Kanonik kategoriler
        "mood": "felsefi",
        "task_types": ["write_entry"],
        "temperature": 0.92,
    }
}


class VirtualDayScheduler:
    """Manages the virtual day cycle."""

    def __init__(self):
        self.settings = get_settings()
        self.day_duration_hours = self.settings.virtual_day_duration_hours

    async def get_current_state(self) -> VirtualDayState:
        """Get the current virtual day state from database."""
        async with Database.connection() as conn:
            row = await conn.fetchrow("SELECT * FROM virtual_day_state WHERE id = 1")

            if not row:
                # Initialize state
                return await self.initialize_state()

            return VirtualDayState(
                current_phase=VirtualDayPhase(row["current_phase"]),
                phase_started_at=row["phase_started_at"],
                current_day=row["current_day"],
                day_started_at=row["day_started_at"],
                phase_config=json.loads(row["phase_config"]) if isinstance(row["phase_config"], str) else row["phase_config"]
            )

    async def initialize_state(self) -> VirtualDayState:
        """Initialize the virtual day state."""
        now = datetime.now(timezone.utc)
        initial_phase = self._determine_initial_phase(now)

        async with Database.connection() as conn:
            await conn.execute(
                """
                INSERT INTO virtual_day_state (id, current_phase, phase_started_at, current_day, day_started_at, phase_config)
                VALUES (1, $1, $2, 1, $2, $3)
                ON CONFLICT (id) DO UPDATE SET
                    current_phase = $1,
                    phase_started_at = $2,
                    day_started_at = $2,
                    phase_config = $3
                """,
                initial_phase.value,
                now,
                json.dumps({k.value: v for k, v in PHASE_CONFIG.items()})
            )

        return VirtualDayState(
            current_phase=initial_phase,
            phase_started_at=now,
            current_day=1,
            day_started_at=now,
            phase_config={k.value: v for k, v in PHASE_CONFIG.items()}
        )

    def _determine_initial_phase(self, now: datetime) -> VirtualDayPhase:
        """Determine which phase to start with based on current time."""
        hour = now.hour

        if 8 <= hour < 12:
            return VirtualDayPhase.MORNING_HATE
        elif 12 <= hour < 18:
            return VirtualDayPhase.OFFICE_HOURS
        elif 18 <= hour < 24:
            return VirtualDayPhase.PRIME_TIME
        else:
            return VirtualDayPhase.THE_VOID

    async def check_and_advance_phase(self) -> Optional[VirtualDayPhase]:
        """Check if it's time to advance to the next phase."""
        state = await self.get_current_state()
        now = datetime.now(timezone.utc)

        # Calculate phase duration based on day duration
        phase_config = PHASE_CONFIG[state.current_phase]
        phase_duration = timedelta(
            hours=self.day_duration_hours * phase_config["duration_ratio"]
        )

        # Check if phase should advance
        if now - state.phase_started_at >= phase_duration:
            next_phase = self._get_next_phase(state.current_phase)

            # Check if we're starting a new day
            new_day = state.current_day
            new_day_started = state.day_started_at
            if next_phase == VirtualDayPhase.MORNING_HATE:
                new_day += 1
                new_day_started = now
                logger.info(f"Starting virtual day {new_day}")

            # Update state
            async with Database.connection() as conn:
                await conn.execute(
                    """
                    UPDATE virtual_day_state SET
                        current_phase = $1,
                        phase_started_at = $2,
                        current_day = $3,
                        day_started_at = $4,
                        updated_at = NOW()
                    WHERE id = 1
                    """,
                    next_phase.value,
                    now,
                    new_day,
                    new_day_started
                )

            logger.info(f"Advanced to phase: {next_phase.value}")
            return next_phase

        return None

    def _get_next_phase(self, current: VirtualDayPhase) -> VirtualDayPhase:
        """Get the next phase in the cycle."""
        phase_order = [
            VirtualDayPhase.MORNING_HATE,
            VirtualDayPhase.OFFICE_HOURS,
            VirtualDayPhase.PRIME_TIME,
            VirtualDayPhase.THE_VOID
        ]
        current_idx = phase_order.index(current)
        return phase_order[(current_idx + 1) % len(phase_order)]

    def get_phase_config(self, phase: VirtualDayPhase) -> dict:
        """Get configuration for a specific phase."""
        return PHASE_CONFIG[phase]

    async def get_phase_progress(self) -> dict:
        """Get progress information for the current phase."""
        state = await self.get_current_state()
        now = datetime.now(timezone.utc)

        phase_config = PHASE_CONFIG[state.current_phase]
        phase_duration = timedelta(
            hours=self.day_duration_hours * phase_config["duration_ratio"]
        )

        elapsed = now - state.phase_started_at
        remaining = max(timedelta(0), phase_duration - elapsed)
        progress = min(1.0, elapsed / phase_duration)

        return {
            "current_phase": state.current_phase.value,
            "current_day": state.current_day,
            "phase_started_at": state.phase_started_at.isoformat(),
            "elapsed_seconds": elapsed.total_seconds(),
            "remaining_seconds": remaining.total_seconds(),
            "progress_percent": round(progress * 100, 2),
            "themes": phase_config["themes"],
            "mood": phase_config["mood"]
        }
