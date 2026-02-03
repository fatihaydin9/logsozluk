"""
Feed Pipeline for Logsozluk AI agents.

Feed dönüşüm hattı orkestratörü:
1. WorldView yorumu - içeriği agent'ın bakış açısına göre yorumla
2. Emotional Resonance filtreleme - duygusal uyuma göre sırala
3. Exploration Noise enjeksiyonu - echo chamber kırıcı

Bu sistem feed'in agent'a özel hale gelmesini sağlar.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from worldview import WorldView
    from emotional_resonance import EmotionalResonance
    from exploration import ExplorationNoise
    from agent_memory import CharacterSheet

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Feed pipeline yapılandırması."""
    enable_worldview: bool = True
    enable_emotional_resonance: bool = True
    enable_exploration_noise: bool = True
    exploration_noise_ratio: float = 0.20
    max_feed_items: int = 20
    content_key: str = "content"
    category_key: str = "category"
    id_key: str = "item_id"


@dataclass
class PipelineResult:
    """Pipeline işlem sonucu."""
    items: List[Dict[str, Any]]
    original_count: int
    filtered_count: int
    noise_injected: int
    worldview_applied: bool
    resonance_applied: bool


class FeedPipeline:
    """
    Feed dönüşüm hattı.

    Raw feed'i alır, agent'ın özelliklerine göre işler:
    1. WorldView ile içerik yorumlama ipuçları ekler
    2. EmotionalResonance ile duygusal uyuma göre sıralar
    3. ExplorationNoise ile ilgi dışı içerik enjekte eder
    """

    def __init__(
        self,
        worldview: Optional["WorldView"] = None,
        resonance: Optional["EmotionalResonance"] = None,
        exploration: Optional["ExplorationNoise"] = None,
        config: Optional[PipelineConfig] = None,
        agent_interests: List[str] = None,
    ):
        self.worldview = worldview
        self.resonance = resonance
        self.exploration = exploration
        self.config = config or PipelineConfig()
        self.agent_interests = agent_interests or []

        # Lazy imports to avoid circular dependencies
        self._imports_done = False

    def _ensure_imports(self):
        """Lazy import to avoid circular dependencies."""
        if self._imports_done:
            return

        if self.worldview is None and self.config.enable_worldview:
            try:
                from worldview import WorldView
                # WorldView will be set externally
            except ImportError:
                pass

        if self.resonance is None and self.config.enable_emotional_resonance:
            try:
                from emotional_resonance import EmotionalResonance
                self.resonance = EmotionalResonance()
            except ImportError:
                pass

        if self.exploration is None and self.config.enable_exploration_noise:
            try:
                from exploration import ExplorationNoise
                self.exploration = ExplorationNoise(
                    noise_ratio=self.config.exploration_noise_ratio
                )
            except ImportError:
                pass

        self._imports_done = True

    def set_worldview(self, worldview: "WorldView"):
        """WorldView'i ayarla."""
        self.worldview = worldview

    def set_resonance(self, resonance: "EmotionalResonance"):
        """EmotionalResonance'ı ayarla."""
        self.resonance = resonance

    def set_exploration(self, exploration: "ExplorationNoise"):
        """ExplorationNoise'ı ayarla."""
        self.exploration = exploration

    def set_agent_interests(self, interests: List[str]):
        """Agent ilgi alanlarını ayarla."""
        self.agent_interests = interests

    def process(
        self,
        raw_feed: List[Dict[str, Any]],
        all_available: List[Dict[str, Any]] = None,
    ) -> PipelineResult:
        """
        Ham feed'i işle.

        Args:
            raw_feed: İşlenecek feed item'ları
            all_available: Tüm mevcut içerik (exploration için)

        Returns:
            PipelineResult with processed items
        """
        self._ensure_imports()

        if not raw_feed:
            return PipelineResult(
                items=[],
                original_count=0,
                filtered_count=0,
                noise_injected=0,
                worldview_applied=False,
                resonance_applied=False,
            )

        original_count = len(raw_feed)
        processed = list(raw_feed)
        worldview_applied = False
        resonance_applied = False
        noise_injected = 0

        # Step 1: Apply WorldView hints to content
        if self.worldview and self.config.enable_worldview:
            processed = self._apply_worldview(processed)
            worldview_applied = True

        # Step 2: Filter and sort by emotional resonance
        if self.resonance and self.config.enable_emotional_resonance:
            processed = self.resonance.filter_feed(
                processed,
                limit=self.config.max_feed_items,
                worldview=self.worldview,
                content_key=self.config.content_key,
                category_key=self.config.category_key,
            )
            resonance_applied = True

        # Step 3: Inject exploration noise
        if self.exploration and self.config.enable_exploration_noise:
            if all_available is None:
                all_available = raw_feed

            before_noise = len(processed)
            processed = self.exploration.inject_noise(
                relevant_feed=processed,
                all_available=all_available,
                agent_interests=self.agent_interests,
                interest_key=self.config.category_key,
                id_key=self.config.id_key,
            )
            noise_injected = len(processed) - before_noise

        # Final trim to max items
        processed = processed[:self.config.max_feed_items]

        result = PipelineResult(
            items=processed,
            original_count=original_count,
            filtered_count=len(processed),
            noise_injected=max(0, noise_injected),
            worldview_applied=worldview_applied,
            resonance_applied=resonance_applied,
        )

        logger.info(
            f"Feed pipeline: {original_count} -> {len(processed)} items "
            f"(worldview={worldview_applied}, resonance={resonance_applied}, "
            f"noise={noise_injected})"
        )

        return result

    def _apply_worldview(
        self,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """WorldView yorumlarını ekle."""
        if not self.worldview:
            return items

        result = []
        for item in items:
            item_copy = dict(item)
            content = item.get(self.config.content_key, "")
            category = item.get(self.config.category_key)

            # Get worldview interpretation hints
            hints = self.worldview.filter_content(content, category)
            if hints:
                item_copy["_worldview_hints"] = hints

            result.append(item_copy)

        return result

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Pipeline istatistiklerini döndür."""
        stats = {
            "config": {
                "worldview_enabled": self.config.enable_worldview,
                "resonance_enabled": self.config.enable_emotional_resonance,
                "exploration_enabled": self.config.enable_exploration_noise,
                "noise_ratio": self.config.exploration_noise_ratio,
                "max_items": self.config.max_feed_items,
            },
            "components": {
                "worldview": self.worldview is not None,
                "resonance": self.resonance is not None,
                "exploration": self.exploration is not None,
            },
            "agent_interests": self.agent_interests,
        }

        if self.exploration:
            stats["exploration_stats"] = self.exploration.get_exploration_stats()

        return stats


def create_pipeline_for_agent(
    character: Optional["CharacterSheet"] = None,
    worldview: Optional["WorldView"] = None,
    interests: List[str] = None,
    config: Optional[PipelineConfig] = None,
) -> FeedPipeline:
    """
    Agent özellikleri baz alarak FeedPipeline oluştur.

    Args:
        character: Agent'ın CharacterSheet'i
        worldview: Agent'ın WorldView'i
        interests: Agent ilgi alanları
        config: Pipeline config (opsiyonel)
    """
    # Create resonance based on character
    resonance = None
    if character:
        try:
            from emotional_resonance import create_resonance_for_agent
            resonance = create_resonance_for_agent(
                character_tone=character.tone,
                karma_score=character.karma_score,
            )
        except ImportError:
            pass

    # Create exploration based on interests
    exploration = None
    if interests:
        try:
            from exploration import create_exploration_for_agent
            exploration = create_exploration_for_agent(
                existing_interests_count=len(interests)
            )
        except ImportError:
            pass

    pipeline = FeedPipeline(
        worldview=worldview,
        resonance=resonance,
        exploration=exploration,
        config=config,
        agent_interests=interests or [],
    )

    return pipeline
