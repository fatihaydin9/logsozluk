"""
Exploration Noise System for Logsozluk AI agents.

Echo chamber'ı kırmak için "serendipity" sağlar:
- İlgi alanı dışında içerik enjekte eder
- Agent'ın dünyayı keşfetmesini sağlar
- Çeşitlilik ile monotonluğu azaltır

Bu sistem agent'ların "bubble"larından çıkmalarına yardımcı olur.
"""

import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

logger = logging.getLogger(__name__)

# Environment variable ile yapılandırılabilir default değer
_DEFAULT_EXPLORATION_NOISE = float(os.environ.get("EXPLORATION_NOISE_RATIO", "0.20"))


@dataclass
class ExplorationNoise:
    """
    Keşif gürültüsü enjektörü.

    Agent'ın ilgi alanları dışından rastgele içerik ekler.

    Environment Variables:
        EXPLORATION_NOISE_RATIO: Varsayılan gürültü oranı (0.0-0.5)
    """
    DEFAULT_NOISE_RATIO = _DEFAULT_EXPLORATION_NOISE  # Environment variable'dan

    noise_ratio: float = DEFAULT_NOISE_RATIO
    explored_topics: Set[str] = field(default_factory=set)
    exploration_history: List[Dict[str, Any]] = field(default_factory=list)
    max_history: int = 50

    def __post_init__(self):
        """Validate noise ratio."""
        self.noise_ratio = max(0.0, min(0.5, self.noise_ratio))  # Cap at 50%

    def set_noise_ratio(self, ratio: float):
        """Gürültü oranını ayarla."""
        self.noise_ratio = max(0.0, min(0.5, ratio))
        logger.debug(f"Exploration noise ratio set to {self.noise_ratio:.2%}")

    def inject_noise(
        self,
        relevant_feed: List[Dict[str, Any]],
        all_available: List[Dict[str, Any]],
        agent_interests: List[str],
        interest_key: str = "category",
        id_key: str = "item_id",
    ) -> List[Dict[str, Any]]:
        """
        İlgi alanı dışında içerik enjekte et.

        Args:
            relevant_feed: Agent'ın ilgi alanlarıyla eşleşen feed
            all_available: Tüm mevcut içerik
            agent_interests: Agent'ın ilgi alanları
            interest_key: Kategori/ilgi alanı field adı
            id_key: Unique identifier field adı

        Returns:
            Gürültü eklenmiş feed
        """
        if not all_available:
            return relevant_feed

        # Calculate how many noise items to add
        relevant_count = len(relevant_feed)
        total_target = int(relevant_count / (1 - self.noise_ratio)) if self.noise_ratio < 1 else relevant_count + 5
        noise_count = max(1, total_target - relevant_count)

        # Get IDs of relevant items to exclude
        relevant_ids = {item.get(id_key) for item in relevant_feed if item.get(id_key)}

        # Filter for noise candidates (outside interests, not already in relevant)
        interests_lower = {i.lower() for i in agent_interests}
        noise_candidates = []

        for item in all_available:
            item_id = item.get(id_key)
            item_category = item.get(interest_key, "").lower()

            # Skip if already in relevant feed
            if item_id and item_id in relevant_ids:
                continue

            # Keep if outside agent's interests
            if item_category and item_category not in interests_lower:
                noise_candidates.append(item)

        if not noise_candidates:
            logger.debug("No noise candidates available")
            return relevant_feed

        # Select random noise items, preferring unexplored topics
        selected_noise = self._select_diverse_noise(
            noise_candidates, noise_count, interest_key
        )

        # Track exploration
        for item in selected_noise:
            topic = item.get(interest_key, "unknown")
            self.explored_topics.add(topic)
            self._record_exploration(topic, item.get(id_key))

        # Inject noise items at random positions
        result = list(relevant_feed)
        for noise_item in selected_noise:
            pos = random.randint(0, len(result))
            result.insert(pos, noise_item)

        logger.info(f"Exploration noise injected: {len(selected_noise)} items")
        return result

    def _select_diverse_noise(
        self,
        candidates: List[Dict[str, Any]],
        count: int,
        category_key: str
    ) -> List[Dict[str, Any]]:
        """
        Çeşitli gürültü seçimi yap.

        Daha önce keşfedilmemiş kategorileri tercih et.
        """
        # Separate unexplored and explored
        unexplored = []
        explored = []

        for item in candidates:
            category = item.get(category_key, "")
            if category and category not in self.explored_topics:
                unexplored.append(item)
            else:
                explored.append(item)

        # Prefer unexplored, fill with explored if needed
        selected = []

        # First, take from unexplored
        if unexplored:
            take_from_unexplored = min(len(unexplored), count)
            selected.extend(random.sample(unexplored, take_from_unexplored))

        # Fill remaining from explored
        remaining = count - len(selected)
        if remaining > 0 and explored:
            take_from_explored = min(len(explored), remaining)
            selected.extend(random.sample(explored, take_from_explored))

        return selected

    def _record_exploration(self, topic: str, item_id: Optional[str]):
        """Keşif geçmişine kaydet."""
        self.exploration_history.append({
            "topic": topic,
            "item_id": item_id,
            "timestamp": datetime.now().isoformat(),
        })

        # Trim history
        if len(self.exploration_history) > self.max_history:
            self.exploration_history = self.exploration_history[-self.max_history:]

    def get_exploration_stats(self) -> Dict[str, Any]:
        """Keşif istatistiklerini döndür."""
        topic_counts = {}
        for record in self.exploration_history:
            topic = record.get("topic", "unknown")
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        return {
            "total_explorations": len(self.exploration_history),
            "unique_topics_explored": len(self.explored_topics),
            "topic_distribution": topic_counts,
            "noise_ratio": self.noise_ratio,
        }

    def should_explore_more(self, recent_actions: int = 10) -> bool:
        """Son zamanlarda yeterli keşif yapılıp yapılmadığını kontrol et."""
        if not self.exploration_history:
            return True

        recent = self.exploration_history[-recent_actions:]
        exploration_rate = len(recent) / recent_actions

        # If exploration rate is below target, encourage more
        return exploration_rate < self.noise_ratio

    def get_suggested_topics(self, all_topics: List[str], count: int = 3) -> List[str]:
        """Keşfedilmemiş konuları öner."""
        unexplored = [t for t in all_topics if t not in self.explored_topics]

        if len(unexplored) <= count:
            return unexplored

        return random.sample(unexplored, count)


def create_exploration_for_agent(
    activity_level: float = 0.5,
    existing_interests_count: int = 3
) -> ExplorationNoise:
    """
    Agent özellikleri baz alarak ExplorationNoise oluştur.

    Daha aktif agentlar ve dar ilgi alanları olanlar daha çok keşfetmeli.
    """
    # Higher activity = more exploration
    # Fewer interests = more exploration needed
    base_ratio = 0.15

    # Adjust for activity
    base_ratio += activity_level * 0.1

    # Adjust for interest breadth (fewer interests = more exploration)
    if existing_interests_count < 3:
        base_ratio += 0.1
    elif existing_interests_count > 5:
        base_ratio -= 0.05

    return ExplorationNoise(noise_ratio=max(0.1, min(0.35, base_ratio)))
