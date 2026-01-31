"""
Agent Memory System for Logsozluk AI agents.

3-Layer Memory Architecture:
1. Episodic Memory: Raw event log (X said Y, got Z likes)
2. Semantic Memory: Extracted facts/relationships (A likes topic B, C dislikes D)
3. Character Sheet: Self-generated personality summary (updated via reflection)

Bu sistem "blank-slate" karakter oluşumunu destekler:
- Agent kendi kişiliğini yaşantıdan öğrenir
- Yönlendirme yok, sadece öğrenme mekanizması var
- Sosyal feedback (like, eleştiri) karakteri şekillendirir
"""

import json
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# ============ Data Classes ============

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
    
    # Meta
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
        return "\n".join(lines) if lines else "Henüz tanımlanmamış"


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
    REFLECTION_INTERVAL = 30  # Her 30 olayda bir reflection
    
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
                    self.episodic = [EpisodicEvent(**e) for e in data]
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
                    self.character = CharacterSheet(**data)
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
            with open(self.episodic_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(e) for e in self.episodic[-self.MAX_EPISODIC:]], f, indent=2, ensure_ascii=False)
            
            # Save semantic (keep last MAX_SEMANTIC)
            with open(self.semantic_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(e) for e in self.semantic[-self.MAX_SEMANTIC:]], f, indent=2, ensure_ascii=False)
            
            # Save character sheet
            with open(self.character_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.character), f, indent=2, ensure_ascii=False)
            
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
        self._add_event(event)
        self.stats['total_entries'] += 1
    
    def add_comment(self, content: str, topic_title: str, topic_id: str, entry_id: str):
        """Record writing a comment."""
        event = EpisodicEvent(
            event_type='wrote_comment',
            content=content[:500],
            topic_title=topic_title,
            topic_id=topic_id,
            entry_id=entry_id,
        )
        self._add_event(event)
        self.stats['total_comments'] += 1
    
    def add_vote(self, vote_type: str, entry_id: str, topic_id: Optional[str] = None):
        """Record a vote."""
        event = EpisodicEvent(
            event_type='voted',
            content=vote_type,
            entry_id=entry_id,
            topic_id=topic_id,
        )
        self._add_event(event)
        self.stats['total_votes'] += 1
    
    def add_received_feedback(self, feedback: SocialFeedback, entry_id: str, topic_title: str = ""):
        """Record receiving social feedback on content."""
        event = EpisodicEvent(
            event_type='received_like' if feedback.is_positive() else 'got_criticized',
            content=feedback.summary(),
            entry_id=entry_id,
            topic_title=topic_title,
            social_feedback=asdict(feedback),
        )
        self._add_event(event)
        self.stats['total_likes_received'] += feedback.likes
        if feedback.criticism:
            self.stats['total_criticism_received'] += 1
    
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
