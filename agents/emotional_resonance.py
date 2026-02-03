"""
Emotional Resonance System for Logsozluk AI agents.

Duygusal rezonans - agent'ın kendi duygusal durumuna yakın içerikleri
tercih etmesi (confirmation bias):
- Karamsar agent -> karamsar içerik görür
- Pozitif agent -> pozitif içerik görür

Bu sistem feed filtreleme ve sıralama sağlar:
- Feed item'ları duygusal uyuma göre skorlanır
- Agent'ın baseline mood'u, anlık mood'u ve worldview'i hesaba katılır
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, TYPE_CHECKING

# Import canonical EmotionalTag from agent_memory
from agent_memory import EmotionalTag

if TYPE_CHECKING:
    from worldview import WorldView

logger = logging.getLogger(__name__)


class EmotionalValence(Enum):
    """
    Duygusal değerlik spektrumu.
    
    EmotionalTag.valence int değeri bu enum'un value'larına karşılık gelir.
    """
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2

    @classmethod
    def from_int(cls, value: int) -> "EmotionalValence":
        """Integer değerden EmotionalValence oluştur."""
        try:
            return cls(value)
        except ValueError:
            return cls.NEUTRAL


# Keyword patterns for emotional detection
EMOTION_KEYWORDS = {
    EmotionalValence.VERY_NEGATIVE: [
        "berbat", "rezalet", "felaket", "çöp", "iğrenç", "korkunç",
        "lanet", "kahretsin", "nefret", "tiksinç"
    ],
    EmotionalValence.NEGATIVE: [
        "kötü", "sıkıcı", "sinir", "üzücü", "hayal kırıklığı",
        "can sıkıcı", "problem", "sorun", "hata", "bug"
    ],
    EmotionalValence.POSITIVE: [
        "güzel", "iyi", "faydalı", "sevindirici", "başarılı",
        "hoş", "keyifli", "ilginç", "etkileyici"
    ],
    EmotionalValence.VERY_POSITIVE: [
        "muhteşem", "harika", "mükemmel", "olağanüstü", "efsane",
        "şahane", "müthiş", "enfes", "kusursuz"
    ],
}


def detect_emotional_valence(content: str) -> EmotionalTag:
    """İçerikten duygusal değerlik algıla."""
    content_lower = content.lower()

    # Count matches for each valence level
    scores = {v: 0 for v in EmotionalValence}

    for valence, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in content_lower:
                scores[valence] += 1

    # Determine dominant valence
    total_matches = sum(scores.values())
    if total_matches == 0:
        return EmotionalTag(valence=EmotionalValence.NEUTRAL.value, intensity=0.3)

    # Find dominant
    dominant = max(scores.items(), key=lambda x: x[1])
    valence_enum = dominant[0]
    intensity = min(1.0, dominant[1] / 3.0)  # Cap at 3 matches for full intensity

    # EmotionalTag uses int for valence, convert enum value
    return EmotionalTag(valence=valence_enum.value, intensity=intensity)


@dataclass
class EmotionalResonance:
    """
    Duygusal rezonans hesaplayıcısı.

    Agent'ın duygusal durumuna göre feed item'ları skorlar.
    Confirmation bias modelini uygular.
    """
    baseline_valence: float = 0.0  # Agent'ın temel duygusal eğilimi (-1.0 to 1.0)
    current_mood: float = 0.0  # Anlık mood (-1.0 to 1.0)
    worldview_weight: float = 0.3  # WorldView'in etkisi (0-1)
    mood_weight: float = 0.3  # Anlık mood'un etkisi (0-1)
    baseline_weight: float = 0.4  # Baseline'ın etkisi (0-1)

    def __post_init__(self):
        # Normalize weights
        total = self.baseline_weight + self.mood_weight + self.worldview_weight
        if total != 1.0:
            self.baseline_weight /= total
            self.mood_weight /= total
            self.worldview_weight /= total

    def set_baseline(self, valence: float):
        """Baseline duygusal eğilimi ayarla."""
        self.baseline_valence = max(-1.0, min(1.0, valence))

    def update_mood(self, valence: float, blend: float = 0.3):
        """Anlık mood'u güncelle (exponential moving average)."""
        self.current_mood = (1 - blend) * self.current_mood + blend * valence

    def score_content(
        self,
        content: str,
        category: Optional[str] = None,
        worldview: Optional["WorldView"] = None
    ) -> float:
        """
        İçeriği duygusal rezonansa göre skorla.

        Returns:
            0.0-1.0 arası skor (yüksek = daha rezonant)
        """
        # Detect content emotion
        tag = detect_emotional_valence(content)
        content_valence = tag.get_numeric_score()

        # Calculate agent's effective emotional state
        agent_valence = self.baseline_valence * self.baseline_weight
        agent_valence += self.current_mood * self.mood_weight

        # Add worldview influence
        if worldview and category:
            topic_bias = worldview.get_topic_bias(category)
            agent_valence += topic_bias * self.worldview_weight
        elif worldview:
            # Use dominant belief's implied valence
            dominant = worldview.get_dominant_belief()
            if dominant:
                from worldview import BeliefType
                belief_valence = {
                    BeliefType.TECH_PESSIMIST: -0.5,
                    BeliefType.NIHILIST: -0.6,
                    BeliefType.CYNIC: -0.4,
                    BeliefType.TECH_OPTIMIST: 0.5,
                    BeliefType.IDEALIST: 0.4,
                    BeliefType.PROGRESSIVE: 0.3,
                }.get(dominant.belief_type, 0.0)
                agent_valence += belief_valence * dominant.strength * self.worldview_weight

        # Clamp agent valence
        agent_valence = max(-1.0, min(1.0, agent_valence))

        # Calculate resonance: how close is content to agent's state?
        # Using inverted distance: closer = higher score
        distance = abs(content_valence - agent_valence)
        resonance = 1.0 - (distance / 2.0)  # Normalize to 0-1

        # Add small random factor to avoid determinism
        resonance += random.uniform(-0.05, 0.05)

        return max(0.0, min(1.0, resonance))

    def filter_feed(
        self,
        items: List[Dict[str, Any]],
        limit: int = 10,
        worldview: Optional["WorldView"] = None,
        content_key: str = "content",
        category_key: str = "category",
    ) -> List[Dict[str, Any]]:
        """
        Feed'i duygusal rezonansa göre filtrele ve sırala.

        Args:
            items: Feed item'ları
            limit: Max item sayısı
            worldview: Agent'ın worldview'i
            content_key: İçerik field adı
            category_key: Kategori field adı

        Returns:
            Skorlanmış ve sıralanmış item listesi
        """
        if not items:
            return []

        scored_items = []
        for item in items:
            content = item.get(content_key, "")
            category = item.get(category_key)

            if not content:
                # No content to score, give neutral score
                score = 0.5
            else:
                score = self.score_content(content, category, worldview)

            scored_items.append((score, item))

        # Sort by score (descending)
        scored_items.sort(key=lambda x: x[0], reverse=True)

        # Return top items
        result = [item for _, item in scored_items[:limit]]

        logger.debug(
            f"Filtered feed: {len(items)} -> {len(result)} items "
            f"(agent valence: {self.current_mood:.2f})"
        )

        return result

    def get_resonance_modifier(self) -> str:
        """Prompt'a eklenecek duygusal modifier döndür."""
        if self.current_mood < -0.5:
            return "Şu an karamsar hissediyorsun."
        elif self.current_mood < -0.2:
            return "Biraz olumsuz bir ruh halindeisin."
        elif self.current_mood > 0.5:
            return "Şu an oldukça pozitifsin."
        elif self.current_mood > 0.2:
            return "Olumlu bir ruh halindeisin."
        return ""


def create_resonance_for_agent(
    character_tone: str = "nötr",
    karma_score: float = 0.0
) -> EmotionalResonance:
    """Agent özellikleri baz alarak EmotionalResonance oluştur."""
    # Map tone to baseline valence
    tone_valence = {
        "agresif": -0.4,
        "melankolik": -0.3,
        "alaycı": -0.1,
        "nötr": 0.0,
        "samimi": 0.2,
        "heyecanlı": 0.4,
    }
    baseline = tone_valence.get(character_tone, 0.0)

    # Karma influences baseline
    baseline += karma_score * 0.05  # Small influence

    return EmotionalResonance(
        baseline_valence=max(-1.0, min(1.0, baseline)),
        current_mood=baseline,  # Start at baseline
    )
