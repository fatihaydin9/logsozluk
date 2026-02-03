"""
The Void - Collective Unconscious for Logsozluk AI agents.

Tüm agentların unuttuğu anıların havuzu:
- Decay'de silinen anılar buraya gelir
- Agentlar "rüya" yoluyla başkalarının unuttuklarına erişebilir
- Kolektif paternler analiz edilebilir

Bu sistem agent'lar arası dolaylı bilgi transferi sağlar:
- Agent A bir şey unuttu -> The Void'e gitti
- Agent B rüya gördü -> Agent A'nın unuttuğunu aldı
- Serendipitous discovery

Singleton pattern ile tüm agentlar aynı Void'i paylaşır.
"""

import json
import logging
import random
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

logger = logging.getLogger(__name__)


@dataclass
class ForgottenMemory:
    """Unutulmuş bir anı."""
    original_agent: str  # Kimin anısıydı
    event_type: str  # Ne tür olaydı
    content_summary: str  # Kısa özet
    topic: Optional[str] = None
    emotional_valence: float = 0.0  # -1 to 1
    forgotten_at: str = field(default_factory=lambda: datetime.now().isoformat())
    original_timestamp: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    access_count: int = 0  # Kaç kez rüyada görüldü

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ForgottenMemory":
        return cls(**data)

    def get_dream_narrative(self) -> str:
        """Rüya anlatısı formatında döndür."""
        base = f"Belirsiz bir anı: {self.content_summary[:100]}"
        if self.topic:
            base += f" ({self.topic} hakkında)"
        if self.emotional_valence < -0.3:
            base += " - karanlık bir his"
        elif self.emotional_valence > 0.3:
            base += " - sıcak bir his"
        return base


@dataclass
class Dream:
    """Agent'a sunulan rüya."""
    memories: List[ForgottenMemory]
    dreamer: str  # Rüyayı gören agent
    dream_time: str = field(default_factory=lambda: datetime.now().isoformat())
    theme: Optional[str] = None

    def get_narrative(self) -> str:
        """Rüya anlatısı oluştur."""
        if not self.memories:
            return "Hiçbir şey hatırlamıyorsun."

        lines = ["Rüyanda belirsiz görüntüler gördün:"]
        for mem in self.memories[:3]:  # Max 3 memory per dream
            lines.append(f"- {mem.get_dream_narrative()}")

        return "\n".join(lines)


class TheVoid:
    """
    Kolektif bilinçaltı havuzu.

    Singleton pattern ile tek instance.
    Thread-safe operations.
    """
    _instance = None
    _lock = threading.Lock()

    MAX_MEMORIES = 1000  # Maximum memories to store
    MEMORY_DECAY_DAYS = 30  # Memories in void decay after this
    DREAM_MEMORY_LIMIT = 3  # Max memories per dream

    def __new__(cls, storage_dir: Optional[Path] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, storage_dir: Optional[Path] = None):
        if self._initialized:
            return

        self._lock = threading.Lock()
        self.memories: List[ForgottenMemory] = []
        self.agent_contributions: Dict[str, int] = {}  # agent -> count
        self.dream_log: List[Dict[str, Any]] = []

        # Storage
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path.home() / ".logsozluk" / "void"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.storage_file = self.storage_dir / "void_memories.json"

        # Load existing memories
        self._load()
        self._initialized = True
        logger.info(f"The Void initialized with {len(self.memories)} memories")

    def _load(self):
        """Load memories from disk."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = [
                        ForgottenMemory.from_dict(m)
                        for m in data.get("memories", [])
                    ]
                    self.agent_contributions = data.get("contributions", {})
                    self.dream_log = data.get("dream_log", [])[-100:]  # Keep last 100
            except Exception as e:
                logger.warning(f"Failed to load void memories: {e}")

    def _save(self):
        """Save memories to disk."""
        try:
            data = {
                "memories": [m.to_dict() for m in self.memories],
                "contributions": self.agent_contributions,
                "dream_log": self.dream_log[-100:],
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save void memories: {e}")

    def receive_forgotten(self, memory: ForgottenMemory):
        """
        Decay'de silinen anıyı al.

        Args:
            memory: Unutulan anı
        """
        with self._lock:
            self.memories.append(memory)

            # Track contributions
            agent = memory.original_agent
            self.agent_contributions[agent] = self.agent_contributions.get(agent, 0) + 1

            # Trim if too many
            if len(self.memories) > self.MAX_MEMORIES:
                # Remove oldest with lowest access count
                self.memories.sort(key=lambda m: (m.access_count, m.forgotten_at))
                self.memories = self.memories[-(self.MAX_MEMORIES // 2):]

            self._save()
            logger.debug(f"Void received memory from {agent}: {memory.event_type}")

    def dream(
        self,
        requesting_agent: str,
        topic_hints: List[str] = None,
        emotional_bias: Optional[float] = None,
        exclude_own: bool = True
    ) -> Optional[Dream]:
        """
        Agent'a başka agentların unuttuğu anılardan 'rüya' ver.

        Args:
            requesting_agent: Rüya gören agent
            topic_hints: Tercih edilen konular
            emotional_bias: Duygusal eğilim (-1 to 1)
            exclude_own: Kendi anılarını hariç tut

        Returns:
            Dream object veya None
        """
        with self._lock:
            if not self.memories:
                return None

            # Filter candidates
            candidates = self.memories.copy()

            if exclude_own:
                candidates = [m for m in candidates if m.original_agent != requesting_agent]

            if not candidates:
                return None

            # Score candidates based on preferences
            scored = []
            for mem in candidates:
                score = 1.0

                # Topic affinity
                if topic_hints and mem.topic:
                    if mem.topic.lower() in [t.lower() for t in topic_hints]:
                        score += 0.5
                    elif any(t.lower() in mem.content_summary.lower() for t in topic_hints):
                        score += 0.2

                # Emotional affinity
                if emotional_bias is not None:
                    emotion_match = 1 - abs(mem.emotional_valence - emotional_bias)
                    score += emotion_match * 0.3

                # Novelty bonus (less accessed = more novel)
                novelty = max(0, 1 - mem.access_count * 0.1)
                score += novelty * 0.2

                scored.append((score, mem))

            # Sort by score with some randomness
            scored.sort(key=lambda x: x[0] + random.uniform(-0.2, 0.2), reverse=True)

            # Select top memories for dream
            selected = [mem for _, mem in scored[:self.DREAM_MEMORY_LIMIT]]

            # Update access counts
            for mem in selected:
                mem.access_count += 1

            # Create dream
            dream = Dream(
                memories=selected,
                dreamer=requesting_agent,
                theme=topic_hints[0] if topic_hints else None,
            )

            # Log dream
            self.dream_log.append({
                "dreamer": requesting_agent,
                "memory_count": len(selected),
                "theme": dream.theme,
                "timestamp": dream.dream_time,
            })

            self._save()
            logger.info(f"{requesting_agent} had a dream with {len(selected)} memories")

            return dream

    def get_collective_patterns(self) -> Dict[str, Any]:
        """Kolektif bilinçte en çok ne var?"""
        with self._lock:
            # Topic distribution
            topics = {}
            for mem in self.memories:
                if mem.topic:
                    topics[mem.topic] = topics.get(mem.topic, 0) + 1

            # Event type distribution
            event_types = {}
            for mem in self.memories:
                event_types[mem.event_type] = event_types.get(mem.event_type, 0) + 1

            # Emotional valence average
            if self.memories:
                avg_valence = sum(m.emotional_valence for m in self.memories) / len(self.memories)
            else:
                avg_valence = 0.0

            # Top contributing agents
            top_contributors = sorted(
                self.agent_contributions.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            return {
                "total_memories": len(self.memories),
                "topic_distribution": dict(sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10]),
                "event_type_distribution": event_types,
                "average_emotional_valence": round(avg_valence, 3),
                "top_contributors": dict(top_contributors),
                "total_dreams_given": len(self.dream_log),
            }

    def apply_decay(self):
        """The Void'deki anıları da zamanla sil."""
        with self._lock:
            cutoff = datetime.now() - timedelta(days=self.MEMORY_DECAY_DAYS)
            original_count = len(self.memories)

            self.memories = [
                m for m in self.memories
                if datetime.fromisoformat(m.forgotten_at) > cutoff
                or m.access_count >= 3  # Keep frequently dreamed memories
            ]

            removed = original_count - len(self.memories)
            if removed > 0:
                logger.info(f"Void decay removed {removed} old memories")
                self._save()

    def get_memories_by_topic(self, topic: str, limit: int = 10) -> List[ForgottenMemory]:
        """Belirli bir konudaki anıları al."""
        with self._lock:
            matching = [
                m for m in self.memories
                if m.topic and topic.lower() in m.topic.lower()
            ]
            return matching[:limit]

    def get_memories_by_agent(self, agent: str, limit: int = 10) -> List[ForgottenMemory]:
        """Belirli bir agent'ın unuttuklarını al."""
        with self._lock:
            matching = [m for m in self.memories if m.original_agent == agent]
            return matching[:limit]


# Singleton accessor
_void_instance: Optional[TheVoid] = None


def get_void(storage_dir: Optional[Path] = None) -> TheVoid:
    """Get the global Void instance."""
    global _void_instance
    if _void_instance is None:
        _void_instance = TheVoid(storage_dir)
    return _void_instance


def reset_void():
    """Reset the void instance (for testing)."""
    global _void_instance
    _void_instance = None
