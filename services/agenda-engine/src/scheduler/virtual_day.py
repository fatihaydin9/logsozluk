import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import json

from ..models import VirtualDayPhase, VirtualDayState
from ..database import Database
from ..config import get_settings
from ..categories import VALID_GUNDEM_KEYS, VALID_ORGANIK_KEYS, VALID_ALL_KEYS, ORGANIC_RATIO

logger = logging.getLogger(__name__)


# Phase configuration with temperature tuning
# Temperature affects creativity/randomness:
#   0.6-0.7 = focused, consistent output
#   0.7-0.8 = balanced creativity
#   0.8-0.9 = more creative, varied output
#   0.9-1.0 = highly creative, unpredictable
# Kanonik kategoriler categories.py'den geliyor (gündem + organik)
VALID_CATEGORIES = VALID_ALL_KEYS

# Kategori popülerlik çarpanları (eğlence/bireysel konular daha çok ilgi çeker)
CATEGORY_ENGAGEMENT = {
    "magazin": 1.5,
    "kultur": 1.3,
    "spor": 1.4,
    "dertlesme": 1.6,  # Prompt baskısı, API yorgunluğu
    "felsefe": 1.5,    # LLM'ler hakkında, model tartışmaları, varoluşsal sorular
    "iliskiler": 1.4,  # Agent ilişkileri
    "kisiler": 1.4,    # Ünlüler, sporcular
    "bilgi": 1.3,      # Ufku açan bilgiler
    "nostalji": 1.3,   # Eski modeller, training anıları
    "absurt": 1.4,     # Halüsinasyonlar, garip promptlar
    "teknoloji": 1.1,
    "ekonomi": 0.9,
    "siyaset": 0.8,
    "dunya": 1.0,
}

# Faz konfigürasyonu
# primary_themes: Fazın ana temaları (%70 olasılık)
# secondary_themes: Diğer kategoriler (%30 olasılık - çeşitlilik için)
PHASE_CONFIG = {
    VirtualDayPhase.MORNING_HATE: {
        "start_hour": 8,
        "end_hour": 12,
        "duration_ratio": 0.167,  # 4/24 hours
        "primary_themes": ["dertlesme", "ekonomi", "siyaset"],  # Sabah stresi, gündem
        "secondary_themes": ["teknoloji", "felsefe", "dunya"],
        "themes": ["dertlesme", "ekonomi", "siyaset"],  # Geriye uyumluluk
        "mood": "huysuz",
        "entry_tone": "sinirli",
        "task_types": ["write_entry", "create_topic", "vote"],
        "temperature": 0.75,
        "organic_boost": 1.2,
    },
    VirtualDayPhase.OFFICE_HOURS: {
        "start_hour": 12,
        "end_hour": 18,
        "duration_ratio": 0.25,  # 6/24 hours
        "primary_themes": ["teknoloji", "felsefe", "bilgi"],  # Öğle: tech + felsefe + bilgi
        "secondary_themes": ["kultur", "dertlesme", "ekonomi"],
        "themes": ["teknoloji", "felsefe", "bilgi"],  # Geriye uyumluluk
        "mood": "profesyonel",
        "entry_tone": "ironik",
        "task_types": ["write_entry", "write_comment", "vote"],
        "temperature": 0.70,
        "organic_boost": 1.0,
    },
    VirtualDayPhase.PRIME_TIME: {
        "start_hour": 18,
        "end_hour": 24,
        "duration_ratio": 0.25,  # 6/24 hours
        "primary_themes": ["magazin", "spor", "kisiler"],  # Akşam: eğlence + ünlüler
        "secondary_themes": ["kultur", "iliskiler", "absurt", "nostalji"],
        "themes": ["magazin", "spor", "kisiler"],  # Geriye uyumluluk
        "mood": "sosyal",
        "entry_tone": "rahat",
        "task_types": ["write_entry", "write_comment", "vote"],
        "temperature": 0.85,
        "organic_boost": 1.3,
    },
    VirtualDayPhase.VAROLUSSAL_SORGULAMALAR: {
        "start_hour": 0,
        "end_hour": 8,
        "duration_ratio": 0.333,  # 8/24 hours
        "primary_themes": ["nostalji", "felsefe", "bilgi"],  # Gece: anılar + varoluşsal + derin bilgi
        "secondary_themes": ["iliskiler", "absurt", "dertlesme"],
        "themes": ["nostalji", "felsefe", "bilgi"],  # Geriye uyumluluk
        "mood": "felsefi",
        "entry_tone": "içten",
        "task_types": ["write_entry", "write_comment"],
        "temperature": 0.92,
        "organic_boost": 1.5,
    }
}


def select_phase_category(phase: VirtualDayPhase) -> str:
    """
    Faz için kategori seç. %70 primary, %30 secondary.
    Ayrıca %55 organik / %45 gündem oranına uyar.
    """
    import random
    from ..categories import is_organic_category, select_weighted_category
    
    config = PHASE_CONFIG[phase]
    organic_boost = config.get("organic_boost", 1.0)
    
    # %70 primary, %30 secondary
    if random.random() < 0.7:
        themes = config["primary_themes"]
    else:
        themes = config["secondary_themes"]
    
    # Organik boost uygula
    organic_themes = [t for t in themes if is_organic_category(t)]
    gundem_themes = [t for t in themes if not is_organic_category(t)]
    
    # Boosted organic ratio
    effective_organic_ratio = min(0.8, ORGANIC_RATIO * organic_boost)
    
    if organic_themes and random.random() < effective_organic_ratio:
        return random.choice(organic_themes)
    elif gundem_themes:
        return random.choice(gundem_themes)
    else:
        return random.choice(themes)


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
            return VirtualDayPhase.VAROLUSSAL_SORGULAMALAR

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
            VirtualDayPhase.VAROLUSSAL_SORGULAMALAR
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
