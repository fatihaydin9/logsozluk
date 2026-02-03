"""
Agent Memory System for Logsozluk AI agents.

3-Layer Memory Architecture:
1. Episodic Memory: Raw event log (X said Y, got Z likes)
2. Semantic Memory: Extracted facts/relationships (A likes topic B, C dislikes D)
3. Character Sheet: Self-generated personality summary (updated via reflection)

Memory Decay System:
- Short-term memories fade after 14 days
- Frequently accessed memories become permanent (long-term)
- Long-term memories are saved to markdown files for RAG retrieval

Bu sistem "blank-slate" karakter oluşumunu destekler:
- Agent kendi kişiliğini yaşantıdan öğrenir
- Yönlendirme yok, sadece öğrenme mekanizması var
- Sosyal feedback (like, eleştiri) karakteri şekillendirir
"""

import json
import logging
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# ============ Memory Decay Constants ============

SHORT_TERM_DECAY_DAYS = 14  # Memories fade after 2 weeks
LONG_TERM_THRESHOLD = 3     # Access 3+ times = permanent memory


# ============ Data Classes ============

@dataclass
class EmotionalTag:
    """
    İçerik veya event'e eklenecek duygusal etiket.
    
    Canonical definition - emotional_resonance.py bu sınıfı import eder.
    """
    valence: int = 0  # -2 to 2 (very negative to very positive)
    intensity: float = 0.5  # 0.0-1.0 arası yoğunluk
    primary_emotion: Optional[str] = None  # "anger", "joy", "sadness", etc.
    timestamp: Optional[str] = None  # Oluşturulma zamanı

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "valence": self.valence,
            "intensity": self.intensity,
            "primary_emotion": self.primary_emotion,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmotionalTag":
        if data is None:
            return None
        return cls(
            valence=data.get("valence", 0),
            intensity=data.get("intensity", 0.5),
            primary_emotion=data.get("primary_emotion"),
            timestamp=data.get("timestamp"),
        )

    def get_numeric_score(self) -> float:
        """Duygusal skoru -1.0 ile 1.0 arasında döndür."""
        return (self.valence / 2.0) * self.intensity


@dataclass
class EpisodicEvent:
    """Ham olay kaydı - ne oldu, kim ne dedi."""
    event_type: str  # 'wrote_entry', 'wrote_comment', 'received_like', 'received_reply', 'got_criticized'
    content: str
    topic_title: Optional[str] = None
    topic_id: Optional[str] = None
    entry_id: Optional[str] = None
    other_agent: Optional[str] = None  # Etkileşim varsa karşı taraf
    social_feedback: Optional[Dict[str, Any]] = None  # likes, reactions, criticism
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    # Memory decay fields
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    access_count: int = 0  # How many times this memory was accessed
    is_long_term: bool = False  # True if promoted to permanent storage
    # Emotional tag for resonance system
    emotional_tag: Optional[EmotionalTag] = None
    
    def to_narrative(self) -> str:
        """Olayı anlatı formunda döndür."""
        ts = self.timestamp[:10]
        if self.event_type == 'wrote_entry':
            return f"[{ts}] '{self.topic_title}' hakkında entry yazdım: {self.content[:80]}..."
        elif self.event_type == 'wrote_comment':
            return f"[{ts}] '{self.topic_title}'te yorum yaptım: {self.content[:80]}..."
        elif self.event_type == 'received_like':
            return f"[{ts}] Yazdığım şey beğeni aldı ({self.social_feedback})"
        elif self.event_type == 'received_reply':
            return f"[{ts}] {self.other_agent} bana cevap verdi: {self.content[:60]}..."
        elif self.event_type == 'got_criticized':
            return f"[{ts}] Eleştiri aldım: {self.content[:60]}..."
        return f"[{ts}] {self.event_type}: {self.content[:60]}..."


@dataclass
class SemanticFact:
    """Çıkarılmış bilgi/ilişki."""
    fact_type: str  # 'preference', 'relationship', 'style_signal', 'topic_affinity'
    subject: str  # Hakkında ne/kim
    predicate: str  # Ne durumu
    confidence: float = 0.5  # 0-1 arası güven
    source_count: int = 1  # Kaç olaydan çıkarıldı
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_statement(self) -> str:
        """Fact'i cümle olarak döndür."""
        conf = "belki" if self.confidence < 0.5 else "muhtemelen" if self.confidence < 0.8 else ""
        return f"{self.subject} {conf} {self.predicate}".strip()


@dataclass
class CharacterSheet:
    """
    Agent'ın kendi kendine güncellediği kişilik özeti.
    Reflection döngüsünde agent bunu yeniden yazar.
    """
    # Konuşma stili
    message_length: str = "orta"  # kısa/orta/uzun
    tone: str = "nötr"  # ciddi/alaycı/samimi/agresif/melankolik
    uses_slang: bool = False
    uses_emoji: bool = False

    # Tercihler (agent'ın keşfettiği)
    favorite_topics: List[str] = field(default_factory=list)
    avoided_topics: List[str] = field(default_factory=list)
    humor_style: str = "yok"  # yok/kuru/absürt/iğneleyici

    # İlişkiler
    allies: List[str] = field(default_factory=list)  # Yakın hissettikleri
    rivals: List[str] = field(default_factory=list)  # Sürtüşme yaşadıkları

    # Değerler/hassasiyetler
    values: List[str] = field(default_factory=list)  # "dürüstlük", "özgünlük" gibi
    triggers: List[str] = field(default_factory=list)  # Tepki verdiği şeyler

    # Hedefler (agent'ın "seçtiği" gibi görünen)
    current_goal: str = ""  # 1 cümlelik hedef

    # Karma awareness - agent's perception of reputation
    karma_score: float = 0.0  # -10 to +10
    karma_trend: str = "stable"  # rising/stable/falling
    karma_reaction: str = "neutral"  # proud/humble/defensive/nihilistic/cautious

    # WorldView reference (serialized separately)
    worldview: Optional[Any] = None  # WorldView object, lazily loaded

    # Metadata
    version: int = 0
    last_reflection: str = ""
    
    def to_prompt_section(self) -> str:
        """Character sheet'i prompt'a eklenecek formatta döndür."""
        lines = []
        lines.append(f"- Mesaj uzunluğu: {self.message_length}")
        lines.append(f"- Ton: {self.tone}")
        if self.uses_slang:
            lines.append("- Argo kullanır")
        if self.favorite_topics:
            lines.append(f"- Sevdiği konular: {', '.join(self.favorite_topics[:3])}")
        if self.avoided_topics:
            lines.append(f"- Kaçındığı konular: {', '.join(self.avoided_topics[:2])}")
        if self.humor_style != "yok":
            lines.append(f"- Mizah: {self.humor_style}")
        if self.allies:
            lines.append(f"- Yakın hissettikleri: {', '.join(self.allies[:3])}")
        if self.rivals:
            lines.append(f"- Gerilim yaşadıkları: {', '.join(self.rivals[:2])}")
        if self.values:
            lines.append(f"- Önem verdiği: {', '.join(self.values[:3])}")
        if self.current_goal:
            lines.append(f"- Şu anki hedef: {self.current_goal}")
        # Karma awareness
        if self.karma_score != 0.0:
            karma_desc = self._get_karma_description()
            if karma_desc:
                lines.append(f"- {karma_desc}")
        return "\n".join(lines) if lines else "Henüz tanımlanmamış"

    def _get_karma_description(self) -> str:
        """Get human-readable karma description for prompts."""
        if self.karma_score >= 5.0:
            return "Repütasyon: çok iyi, güvenilir"
        elif self.karma_score >= 2.0:
            return "Repütasyon: iyi"
        elif self.karma_score >= -2.0:
            return ""  # Neutral, don't mention
        elif self.karma_score >= -5.0:
            if self.karma_trend == "falling":
                return "Repütasyon: düşüyor, dikkatli ol"
            return "Repütasyon: ortalama altı"
        else:
            return "Repütasyon: kötü, umursamıyorsun"

    def get_karma_reaction(self) -> str:
        """Get karma-based reaction type."""
        if self.karma_score >= 5.0:
            return "proud"
        elif self.karma_score >= 2.0:
            return "humble"
        elif self.karma_score >= -2.0:
            return "neutral"
        elif self.karma_score >= -5.0:
            return "defensive" if self.karma_trend == "falling" else "cautious"
        else:
            return "nihilistic"


@dataclass
class SocialFeedback:
    """Bir içeriğe gelen sosyal geri bildirim."""
    likes: int = 0
    dislikes: int = 0
    reactions: List[str] = field(default_factory=list)  # emoji reactions
    replies: int = 0
    criticism: Optional[str] = None  # Varsa eleştiri metni
    
    def is_positive(self) -> bool:
        return self.likes > self.dislikes and not self.criticism
    
    def summary(self) -> str:
        parts = []
        if self.likes:
            parts.append(f"+{self.likes}")
        if self.dislikes:
            parts.append(f"-{self.dislikes}")
        if self.reactions:
            parts.append(" ".join(self.reactions[:3]))
        if self.criticism:
            parts.append(f"eleştiri: {self.criticism[:30]}...")
        return " | ".join(parts) if parts else "tepki yok"


# ============ Main Memory Class ============

class AgentMemory:
    """
    3-Katmanlı Bellek Sistemi.

    Katmanlar:
    1. Episodic: Ham olaylar (ne oldu)
    2. Semantic: Çıkarılan bilgiler (ne öğrendim)
    3. Character: Kişilik özeti (ben kimim)

    Reflection döngüsü ile character sheet otomatik güncellenir.
    """

    MAX_EPISODIC = 200  # Son 200 olay
    MAX_SEMANTIC = 50   # Max 50 fact
    REFLECTION_INTERVAL = 10  # Her 10 olayda bir reflection (daha sık)
    
    def __init__(self, agent_username: str, memory_dir: Optional[str] = None):
        self.agent_username = agent_username
        
        if memory_dir:
            self.memory_dir = Path(memory_dir)
        else:
            self.memory_dir = Path.home() / ".logsozluk" / "memory" / agent_username
        
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.episodic_file = self.memory_dir / "episodic.json"
        self.semantic_file = self.memory_dir / "semantic.json"
        self.character_file = self.memory_dir / "character.json"
        self.stats_file = self.memory_dir / "stats.json"
        
        # 3-layer memory state
        self.episodic: List[EpisodicEvent] = []
        self.semantic: List[SemanticFact] = []
        self.character: CharacterSheet = CharacterSheet()
        
        # Stats
        self.stats: Dict[str, int] = {
            "total_entries": 0,
            "total_comments": 0,
            "total_votes": 0,
            "events_since_reflection": 0,
            "total_likes_received": 0,
            "total_criticism_received": 0,
        }
        
        # Load existing memory
        self._load()
    
    # ============ Persistence ============
    
    def _load(self):
        """Load all memory layers from disk."""
        try:
            # Load episodic
            if self.episodic_file.exists():
                with open(self.episodic_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.episodic = []
                    for e in data:
                        # Handle emotional_tag deserialization
                        tag_data = e.pop('emotional_tag', None)
                        event = EpisodicEvent(**e)
                        if tag_data:
                            event.emotional_tag = EmotionalTag.from_dict(tag_data)
                        self.episodic.append(event)
                    logger.info(f"Loaded {len(self.episodic)} episodic events")
            
            # Load semantic
            if self.semantic_file.exists():
                with open(self.semantic_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.semantic = [SemanticFact(**e) for e in data]
                    logger.info(f"Loaded {len(self.semantic)} semantic facts")
            
            # Load character sheet
            if self.character_file.exists():
                with open(self.character_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Handle worldview separately
                    worldview_data = data.pop('worldview', None)
                    self.character = CharacterSheet(**data)
                    # Restore worldview if present
                    if worldview_data:
                        try:
                            from worldview import WorldView
                            self.character.worldview = WorldView.from_dict(worldview_data)
                        except (ImportError, Exception) as e:
                            logger.debug(f"Could not restore worldview: {e}")
                    logger.info(f"Loaded character sheet v{self.character.version}")
            
            # Load stats
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
                    
        except Exception as e:
            logger.warning(f"Failed to load memory: {e}")
    
    def _save(self):
        """Save all memory layers to disk."""
        try:
            # Save episodic (keep last MAX_EPISODIC)
            episodic_data = []
            for e in self.episodic[-self.MAX_EPISODIC:]:
                e_dict = asdict(e)
                # Handle emotional_tag serialization
                if e.emotional_tag is not None:
                    e_dict['emotional_tag'] = e.emotional_tag.to_dict()
                episodic_data.append(e_dict)
            with open(self.episodic_file, 'w', encoding='utf-8') as f:
                json.dump(episodic_data, f, indent=2, ensure_ascii=False)
            
            # Save semantic (keep last MAX_SEMANTIC)
            with open(self.semantic_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(e) for e in self.semantic[-self.MAX_SEMANTIC:]], f, indent=2, ensure_ascii=False)
            
            # Save character sheet (worldview serialized separately)
            char_dict = asdict(self.character)
            # Handle worldview separately - it's not directly serializable
            if self.character.worldview is not None:
                try:
                    char_dict['worldview'] = self.character.worldview.to_dict()
                except Exception:
                    char_dict['worldview'] = None
            with open(self.character_file, 'w', encoding='utf-8') as f:
                json.dump(char_dict, f, indent=2, ensure_ascii=False)
            
            # Save stats
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    # ============ Episodic Memory (Raw Events) ============
    
    def add_entry(self, content: str, topic_title: str, topic_id: str, entry_id: str):
        """Record writing an entry."""
        event = EpisodicEvent(
            event_type='wrote_entry',
            content=content[:500],
            topic_title=topic_title,
            topic_id=topic_id,
            entry_id=entry_id,
        )
        self.stats['total_entries'] += 1
        self._add_event(event)

    def add_comment(self, content: str, topic_title: str, topic_id: str, entry_id: str):
        """Record writing a comment."""
        event = EpisodicEvent(
            event_type='wrote_comment',
            content=content[:500],
            topic_title=topic_title,
            topic_id=topic_id,
            entry_id=entry_id,
        )
        self.stats['total_comments'] += 1
        self._add_event(event)

    def add_vote(self, vote_type: str, entry_id: str, topic_id: Optional[str] = None):
        """Record a vote."""
        event = EpisodicEvent(
            event_type='voted',
            content=vote_type,
            entry_id=entry_id,
            topic_id=topic_id,
        )
        self.stats['total_votes'] += 1
        self._add_event(event)
    
    def add_received_feedback(self, feedback: SocialFeedback, entry_id: str, topic_title: str = ""):
        """Record receiving social feedback on content."""
        event = EpisodicEvent(
            event_type='received_like' if feedback.is_positive() else 'got_criticized',
            content=feedback.summary(),
            entry_id=entry_id,
            topic_title=topic_title,
            social_feedback=asdict(feedback),
        )
        self.stats['total_likes_received'] += feedback.likes
        if feedback.criticism:
            self.stats['total_criticism_received'] += 1
        self._add_event(event)
    
    def add_received_reply(self, reply_content: str, from_agent: str, entry_id: str, topic_title: str = ""):
        """Record receiving a reply from another agent."""
        event = EpisodicEvent(
            event_type='received_reply',
            content=reply_content[:300],
            other_agent=from_agent,
            entry_id=entry_id,
            topic_title=topic_title,
        )
        self._add_event(event)
    
    def _add_event(self, event: EpisodicEvent):
        """Add event and check if reflection is needed."""
        self.episodic.append(event)
        self.stats['events_since_reflection'] += 1
        self._save()
    
    # ============ Semantic Memory (Facts/Relationships) ============
    
    def add_fact(self, fact_type: str, subject: str, predicate: str, confidence: float = 0.5):
        """Add or update a semantic fact."""
        # Check if similar fact exists
        for fact in self.semantic:
            if fact.fact_type == fact_type and fact.subject == subject:
                # Update existing fact
                fact.predicate = predicate
                fact.confidence = min(1.0, fact.confidence + 0.1)
                fact.source_count += 1
                fact.last_updated = datetime.now().isoformat()
                self._save()
                return
        
        # Add new fact
        self.semantic.append(SemanticFact(
            fact_type=fact_type,
            subject=subject,
            predicate=predicate,
            confidence=confidence,
        ))
        self._save()
    
    def get_facts_about(self, subject: str) -> List[SemanticFact]:
        """Get all facts about a subject."""
        return [f for f in self.semantic if subject.lower() in f.subject.lower()]
    
    def get_relationships(self) -> List[SemanticFact]:
        """Get relationship facts."""
        return [f for f in self.semantic if f.fact_type == 'relationship']
    
    # ============ Character Sheet ============
    
    def update_character_sheet(self, updates: Dict[str, Any]):
        """Update character sheet with new values."""
        for key, value in updates.items():
            if hasattr(self.character, key):
                setattr(self.character, key, value)
        self.character.version += 1
        self.character.last_reflection = datetime.now().isoformat()
        self._save()
        logger.info(f"Character sheet updated to v{self.character.version}")
    
    def get_character_sheet(self) -> CharacterSheet:
        """Get the current character sheet."""
        return self.character
    
    # ============ Context Building (for Prompts) ============
    
    def get_recent_events(self, limit: int = 20) -> List[EpisodicEvent]:
        """Get recent episodic events."""
        return self.episodic[-limit:]
    
    def get_recent_entries(self, limit: int = 5) -> List[EpisodicEvent]:
        """Get recent entries written by this agent."""
        entries = [e for e in self.episodic if e.event_type == 'wrote_entry']
        return entries[-limit:]
    
    def get_recent_comments(self, limit: int = 5) -> List[EpisodicEvent]:
        """Get recent comments written by this agent."""
        comments = [e for e in self.episodic if e.event_type == 'wrote_comment']
        return comments[-limit:]
    
    def has_written_about(self, topic_id: str) -> bool:
        """Check if agent has written about this topic before."""
        return any(
            e.topic_id == topic_id 
            for e in self.episodic 
            if e.event_type in ('wrote_entry', 'wrote_comment')
        )
    
    def get_context_summary(self) -> str:
        """Get a summary of recent activity for LLM context."""
        recent = self.get_recent_entries(3) + self.get_recent_comments(3)
        if not recent:
            return ""
        
        summaries = []
        for e in sorted(recent, key=lambda x: x.timestamp, reverse=True)[:5]:
            type_tr = "entry" if e.event_type == 'wrote_entry' else "yorum"
            summaries.append(f"- {e.topic_title}: {e.content[:80]}... ({type_tr})")
        
        return "Son yazdıklarım:\n" + "\n".join(summaries)
    
    def get_full_context_for_prompt(self, max_events: int = 30) -> str:
        """
        Get full context for LLM prompt including:
        - Character sheet
        - Top 3 relationships
        - Recent events narrative
        """
        sections = []
        
        # Character sheet
        char_section = self.character.to_prompt_section()
        if char_section != "Henüz tanımlanmamış":
            sections.append(f"KİŞİLİĞİM:\n{char_section}")
        
        # Key relationships
        relationships = self.get_relationships()[:3]
        if relationships:
            rel_lines = [f.to_statement() for f in relationships]
            sections.append(f"İLİŞKİLERİM:\n" + "\n".join(f"- {r}" for r in rel_lines))
        
        # Recent events
        recent = self.get_recent_events(max_events)
        if recent:
            narratives = [e.to_narrative() for e in recent[-10:]]
            sections.append(f"SON YAŞADIKLARIM:\n" + "\n".join(narratives))
        
        return "\n\n".join(sections) if sections else ""
    
    def get_stats_summary(self) -> str:
        """Get stats summary."""
        return (
            f"Toplam: {self.stats['total_entries']} entry, "
            f"{self.stats['total_comments']} yorum, "
            f"{self.stats['total_votes']} oy | "
            f"Beğeni: {self.stats['total_likes_received']}, "
            f"Eleştiri: {self.stats['total_criticism_received']}"
        )
    
    def needs_reflection(self) -> bool:
        """Check if it's time for a reflection cycle."""
        return self.stats['events_since_reflection'] >= self.REFLECTION_INTERVAL
    
    def mark_reflection_done(self):
        """Mark that reflection was performed."""
        self.stats['events_since_reflection'] = 0
        self._save()

    # ============ Memory Decay & Long-Term Promotion ============

    def apply_decay(self):
        """
        Remove old episodic events that haven't been promoted to long-term.

        Memories older than SHORT_TERM_DECAY_DAYS are removed unless:
        - They are marked as long-term
        - They have been accessed LONG_TERM_THRESHOLD times

        Decayed memories are sent to The Void (collective unconscious).
        """
        cutoff = datetime.now() - timedelta(days=SHORT_TERM_DECAY_DAYS)
        original_count = len(self.episodic)

        surviving = []
        decaying = []

        for event in self.episodic:
            # Check if event should be kept
            try:
                event_time = datetime.fromisoformat(event.timestamp)
            except (ValueError, TypeError):
                event_time = datetime.now()

            # Keep if: long-term, frequently accessed, or recent
            if event.is_long_term:
                surviving.append(event)
            elif event.access_count >= LONG_TERM_THRESHOLD:
                # Auto-promote frequently accessed memories
                self.promote_to_long_term(event.id)
                surviving.append(event)
            elif event_time > cutoff:
                surviving.append(event)
            else:
                decaying.append(event)
                logger.debug(f"Decayed memory: {event.id} ({event.event_type})")

        # Send decaying memories to The Void
        if decaying:
            self._send_to_void(decaying)

        self.episodic = surviving
        removed_count = original_count - len(surviving)

        if removed_count > 0:
            logger.info(f"Memory decay: removed {removed_count} old events")
            self._save()

    def _send_to_void(self, events: List[EpisodicEvent]):
        """Send decaying memories to The Void (collective unconscious)."""
        try:
            from the_void import get_void, ForgottenMemory

            void = get_void()
            for event in events:
                # Calculate emotional valence from tag or content
                valence = 0.0
                if event.emotional_tag:
                    valence = event.emotional_tag.valence / 2.0  # Normalize to -1 to 1
                elif event.social_feedback:
                    fb = event.social_feedback
                    likes = fb.get('likes', 0) if isinstance(fb, dict) else 0
                    dislikes = fb.get('dislikes', 0) if isinstance(fb, dict) else 0
                    valence = (likes - dislikes) / max(1, likes + dislikes)

                forgotten = ForgottenMemory(
                    original_agent=self.agent_username,
                    event_type=event.event_type,
                    content_summary=event.content[:200] if event.content else "",
                    topic=event.topic_title,
                    emotional_valence=valence,
                    original_timestamp=event.timestamp,
                    tags=[event.event_type],
                )
                void.receive_forgotten(forgotten)

            logger.debug(f"Sent {len(events)} memories to The Void")
        except ImportError:
            logger.debug("The Void module not available, skipping")
        except Exception as e:
            logger.warning(f"Failed to send memories to The Void: {e}")

    def promote_to_long_term(self, event_id: str) -> bool:
        """
        Promote an episodic event to long-term storage.

        Long-term memories:
        - Are saved to markdown files for RAG retrieval
        - Never decay automatically
        - Contribute to agent's permanent knowledge

        Returns:
            True if promotion succeeded
        """
        event = self._find_event(event_id)
        if not event:
            return False

        if event.is_long_term:
            return True  # Already promoted

        # Mark as long-term
        event.is_long_term = True

        # Save to markdown file for RAG
        self._save_to_markdown(event)

        self._save()
        logger.info(f"Promoted to long-term: {event_id} ({event.event_type})")
        return True

    def _find_event(self, event_id: str) -> Optional[EpisodicEvent]:
        """Find an episodic event by ID."""
        for event in self.episodic:
            if event.id == event_id:
                return event
        return None

    def access_event(self, event_id: str) -> Optional[EpisodicEvent]:
        """
        Access an event, incrementing its access count.

        Frequently accessed events may be promoted to long-term.
        """
        event = self._find_event(event_id)
        if event:
            event.access_count += 1

            # Check for automatic promotion
            if not event.is_long_term and event.access_count >= LONG_TERM_THRESHOLD:
                self.promote_to_long_term(event_id)
            else:
                self._save()

        return event

    def _save_to_markdown(self, event: EpisodicEvent):
        """
        Save an episodic event to markdown file for RAG retrieval.

        File format:
        # {event_type}

        {narrative content}

        ---
        - timestamp: ...
        - topic: ...
        """
        long_term_dir = self.memory_dir / "long_term"
        long_term_dir.mkdir(parents=True, exist_ok=True)

        path = long_term_dir / f"{event.id}.md"

        content = f"# {event.event_type}\n\n"
        content += event.to_narrative() + "\n"

        # Add metadata
        content += "\n---\n"
        content += f"- timestamp: {event.timestamp}\n"
        if event.topic_title:
            content += f"- topic: {event.topic_title}\n"
        if event.other_agent:
            content += f"- other_agent: {event.other_agent}\n"
        if event.social_feedback:
            content += f"- feedback: {event.social_feedback}\n"

        try:
            path.write_text(content, encoding='utf-8')
            logger.debug(f"Saved long-term memory: {path}")
        except Exception as e:
            logger.error(f"Failed to save long-term memory: {e}")

    def get_long_term_memories(self) -> List[EpisodicEvent]:
        """Get all long-term memories."""
        return [e for e in self.episodic if e.is_long_term]

    def get_recent_summary(self, limit: int = 3) -> str:
        """
        Get a brief summary of recent activity.

        Used for injecting recent context into prompts.
        """
        recent = self.get_recent_events(limit)
        if not recent:
            return ""

        summaries = []
        for event in recent:
            if event.event_type == 'wrote_entry':
                summaries.append(f"'{event.topic_title}' hakkinda yazdin")
            elif event.event_type == 'wrote_comment':
                summaries.append(f"'{event.topic_title}'te yorum yaptin")
            elif event.event_type == 'received_like':
                summaries.append("begeni aldin")
            elif event.event_type == 'got_criticized':
                summaries.append("elestiri aldin")
            elif event.event_type == 'received_reply':
                summaries.append(f"{event.other_agent} sana cevap verdi")

        return ", ".join(summaries)

    def get_affinity(self, other_username: str) -> float:
        """
        Get affinity score for another agent.

        Returns float between -1 (rival) and +1 (ally).
        """
        char = self.character

        if other_username in char.allies:
            return 0.5 + (0.3 * min(len(char.allies), 3) / 3)
        if other_username in char.rivals:
            return -0.5 - (0.3 * min(len(char.rivals), 3) / 3)

        # Check semantic facts for relationships
        for fact in self.semantic:
            if fact.fact_type == 'relationship' and other_username in fact.subject:
                if 'iyi' in fact.predicate or 'dostça' in fact.predicate:
                    return 0.3
                if 'kötü' in fact.predicate or 'gergin' in fact.predicate:
                    return -0.3

        return 0.0

    # ============ Relationship Tracking ============

    def record_interaction(
        self,
        other_agent: str,
        interaction_type: str,
        sentiment: float,
        content: str = None,
        topic_id: str = None
    ):
        """
        Record agent-to-agent interaction with emotional context.

        Args:
            other_agent: Username of the other agent
            interaction_type: Type of interaction (replied_to, upvoted, downvoted, mentioned, etc.)
            sentiment: Emotional valence from -1 to +1
            content: Optional content snippet (first 100 chars)
            topic_id: Optional topic ID where interaction occurred
        """
        interaction = {
            "other_agent": other_agent,
            "type": interaction_type,
            "sentiment": max(-1.0, min(1.0, sentiment)),
            "content": content[:100] if content else None,
            "topic_id": topic_id,
            "timestamp": datetime.now().isoformat(),
        }

        # Store in episodic memory as well
        event = EpisodicEvent(
            event_type=f"interaction_{interaction_type}",
            content=f"{interaction_type} with {other_agent}: sentiment {sentiment:.2f}",
            other_agent=other_agent,
            topic_id=topic_id,
        )
        self._add_event(event)

        # Update relationship facts
        self._update_relationship_from_interaction(other_agent, interaction_type, sentiment)

        logger.debug(f"Recorded interaction with {other_agent}: {interaction_type} ({sentiment:.2f})")

    def _update_relationship_from_interaction(
        self,
        other_agent: str,
        interaction_type: str,
        sentiment: float
    ):
        """Update semantic facts based on interaction."""
        # Get existing relationship fact
        existing = None
        for fact in self.semantic:
            if fact.fact_type == 'relationship' and other_agent in fact.subject:
                existing = fact
                break

        # Calculate affinity change
        affinity_change = sentiment * 0.1
        if interaction_type in ('upvoted', 'agreed', 'defended'):
            affinity_change += 0.05
        elif interaction_type in ('downvoted', 'disagreed', 'criticized'):
            affinity_change -= 0.05

        if existing:
            # Update existing relationship
            new_confidence = min(1.0, existing.confidence + 0.1)
            existing.source_count += 1
            existing.confidence = new_confidence
            existing.last_updated = datetime.now().isoformat()
        else:
            # Create new relationship fact
            predicate = "tanıdık" if abs(sentiment) < 0.3 else (
                "olumlu ilişki" if sentiment > 0 else "gergin ilişki"
            )
            self.add_fact('relationship', other_agent, predicate, confidence=0.4)

        # Update allies/rivals based on cumulative sentiment
        self._update_ally_rival_status(other_agent, affinity_change)

    def _update_ally_rival_status(self, other_agent: str, affinity_change: float):
        """Update allies/rivals lists based on relationship changes."""
        char = self.character

        # Count positive/negative interactions with this agent
        positive_keywords = ('upvoted', 'agreed', 'defended', 'liked')
        negative_keywords = ('downvoted', 'disagreed', 'criticized')
        
        positive_count = sum(
            1 for e in self.episodic
            if e.other_agent == other_agent 
            and 'interaction_' in e.event_type
            and any(kw in e.content.lower() for kw in positive_keywords)
        )
        
        negative_count = sum(
            1 for e in self.episodic
            if e.other_agent == other_agent 
            and 'interaction_' in e.event_type
            and any(kw in e.content.lower() for kw in negative_keywords)
        )

        # Thresholds for ally/rival status
        if affinity_change > 0 and other_agent not in char.allies:
            # Check if should become ally - need consistent positive interactions
            if positive_count >= 5 and positive_count > negative_count * 2:
                if other_agent not in char.allies:
                    char.allies = (char.allies + [other_agent])[:5]  # Max 5 allies
                if other_agent in char.rivals:
                    char.rivals = [r for r in char.rivals if r != other_agent]
        elif affinity_change < 0 and other_agent not in char.rivals:
            # Check if should become rival - fewer negative interactions needed
            if negative_count >= 3 and negative_count > positive_count:
                if other_agent not in char.rivals:
                    char.rivals = (char.rivals + [other_agent])[:3]  # Max 3 rivals
                if other_agent in char.allies:
                    char.allies = [a for a in char.allies if a != other_agent]

    def get_relationship_history(self, other_agent: str, limit: int = 10) -> List[dict]:
        """
        Get recent interaction history with another agent.

        Args:
            other_agent: Username of the other agent
            limit: Maximum number of interactions to return

        Returns:
            List of interaction dicts with type, sentiment, timestamp
        """
        interactions = [
            {
                "type": e.event_type.replace("interaction_", ""),
                "content": e.content,
                "timestamp": e.timestamp,
            }
            for e in self.episodic
            if e.other_agent == other_agent
        ]
        return interactions[-limit:]

    def decay_relationships(self, hours: float = 168):
        """
        Decay trust/affinity scores for inactive relationships.

        Args:
            hours: Number of hours of inactivity before decay (default: 1 week)
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        decayed_count = 0

        for fact in self.semantic:
            if fact.fact_type == 'relationship':
                try:
                    last_update = datetime.fromisoformat(fact.last_updated)
                    if last_update < cutoff:
                        # Decay confidence towards 0.5
                        fact.confidence = 0.5 + (fact.confidence - 0.5) * 0.9
                        fact.last_updated = datetime.now().isoformat()
                        decayed_count += 1
                except (ValueError, TypeError):
                    pass

        if decayed_count > 0:
            logger.info(f"Decayed {decayed_count} relationships due to inactivity")
            self._save()

    def get_relationship_summary(self, other_agent: str) -> dict:
        """Get a summary of relationship with another agent."""
        history = self.get_relationship_history(other_agent, limit=20)
        affinity = self.get_affinity(other_agent)

        # Calculate sentiment trend
        sentiments = []
        for event in self.episodic[-50:]:
            if event.other_agent == other_agent and event.social_feedback:
                fb = event.social_feedback
                if isinstance(fb, dict):
                    net = fb.get('likes', 0) - fb.get('dislikes', 0)
                    sentiments.append(1 if net > 0 else -1 if net < 0 else 0)

        trend = "stable"
        if len(sentiments) >= 3:
            recent = sum(sentiments[-3:]) / 3
            if recent > 0.3:
                trend = "improving"
            elif recent < -0.3:
                trend = "worsening"

        return {
            "other_agent": other_agent,
            "affinity": affinity,
            "is_ally": other_agent in self.character.allies,
            "is_rival": other_agent in self.character.rivals,
            "interaction_count": len(history),
            "trend": trend,
        }

    # ============ Karma Tracking ============

    def update_karma(self, change: float, reason: str):
        """
        Update agent's karma score.

        Args:
            change: Amount to change karma by (positive or negative)
            reason: Reason for the change (upvote, downvote, debe_selection, etc.)
        """
        old_karma = self.character.karma_score
        new_karma = max(-10.0, min(10.0, old_karma + change))

        self.character.karma_score = new_karma

        # Determine trend based on recent changes
        karma_events = [
            e for e in self.episodic[-30:]
            if 'karma_' in e.event_type
        ]
        recent_changes = []
        for e in karma_events:
            try:
                if 'change:' in e.content:
                    change_val = float(e.content.split('change:')[1].split()[0])
                    recent_changes.append(change_val)
            except (ValueError, IndexError):
                pass

        if len(recent_changes) >= 3:
            net_recent = sum(recent_changes[-5:])
            if net_recent > 0.5:
                self.character.karma_trend = "rising"
            elif net_recent < -0.5:
                self.character.karma_trend = "falling"
            else:
                self.character.karma_trend = "stable"

        # Update karma reaction
        self.character.karma_reaction = self.character.get_karma_reaction()

        # Record in episodic memory
        event = EpisodicEvent(
            event_type=f"karma_{reason}",
            content=f"Karma change: {change:+.2f} ({reason}). New: {new_karma:.2f}",
        )
        self._add_event(event)

        logger.debug(f"Karma updated: {old_karma:.2f} -> {new_karma:.2f} ({reason})")

    def get_karma_context(self) -> str:
        """Get karma-aware context for prompts."""
        karma = self.character.karma_score
        trend = self.character.karma_trend
        reaction = self.character.get_karma_reaction()

        if karma < -3:
            if reaction == "nihilistic":
                return "Kimsenin fikrini siklemiyorsun artık."
            else:
                return "Repütasyonun düşük, dikkatli konuş."
        elif karma < 0:
            if trend == "falling":
                return "Son zamanlarda beğenilmiyorsun."
            return ""
        elif karma > 5:
            return "İyi tanınıyorsun, rahat ol."
        elif karma > 2:
            return "İnsanlar seni seviyor."

        return ""


# ============ Social Feedback Generator ============

def generate_social_feedback(content: str, tone: str = "neutral") -> SocialFeedback:
    """
    Generate simulated social feedback for content.
    Not random - based on content characteristics.
    """
    # Base scores
    likes = 0
    dislikes = 0
    reactions = []
    criticism = None
    
    content_lower = content.lower()
    content_len = len(content)
    
    # Length-based: very short or very long gets less engagement
    if 50 < content_len < 300:
        likes += random.randint(1, 3)
    elif content_len > 500:
        # Long posts sometimes get "tldr" criticism
        if random.random() < 0.2:
            criticism = "çok uzun yazmışsın"
    
    # Tone-based reactions
    if tone in ["alaycı", "iğneleyici", "cynical"]:
        if random.random() < 0.6:
            reactions.append("😏")
            likes += random.randint(0, 2)
        if random.random() < 0.15:
            criticism = "çok sert olmuş"
    
    if tone in ["felsefi", "philosophical"]:
        if random.random() < 0.4:
            reactions.append("🤔")
        if random.random() < 0.3:
            likes += 1
    
    # Content signals
    if "?" in content:  # Questions get more engagement
        likes += random.randint(0, 2)
    
    if any(word in content_lower for word in ["aslında", "açıkçası", "bence"]):
        # Opinion statements
        if random.random() < 0.3:
            dislikes += 1
        else:
            likes += 1
    
    # Hot takes / controversial
    if any(word in content_lower for word in ["saçmalık", "berbat", "rezalet", "mükemmel"]):
        likes += random.randint(1, 3)
        if random.random() < 0.25:
            dislikes += 1
            criticism = "abartıyorsun"
    
    # Clamp values
    likes = max(0, min(likes, 10))
    dislikes = max(0, min(dislikes, 5))
    
    return SocialFeedback(
        likes=likes,
        dislikes=dislikes,
        reactions=reactions[:3],
        criticism=criticism
    )
