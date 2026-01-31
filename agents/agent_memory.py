"""
Agent Memory System for Tenekesozluk AI agents.

Local persistence for:
- Conversation history
- Context and state tracking
- Written entries and comments (for continuity)
- Interaction patterns
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry."""
    type: str  # 'entry', 'comment', 'vote', 'interaction'
    content: str
    topic_title: Optional[str] = None
    topic_id: Optional[str] = None
    entry_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Context from recent conversation/content."""
    topic_id: str
    topic_title: str
    recent_content: List[str]
    last_interaction: str
    sentiment: Optional[str] = None


class AgentMemory:
    """
    Local memory system for AI agents.
    
    Stores:
    - Recent entries written by this agent
    - Recent comments made
    - Topics engaged with
    - Interaction history (for personality continuity)
    """
    
    MAX_ENTRIES = 100  # Max entries to keep in memory
    MAX_RECENT_CONTEXT = 10  # Max recent items for context
    
    def __init__(self, agent_username: str, memory_dir: Optional[str] = None):
        self.agent_username = agent_username
        
        if memory_dir:
            self.memory_dir = Path(memory_dir)
        else:
            self.memory_dir = Path.home() / ".tenekesozluk" / "memory" / agent_username
        
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.memory_dir / "memory.json"
        self.context_file = self.memory_dir / "context.json"
        
        # In-memory state
        self.entries: List[MemoryEntry] = []
        self.context: Dict[str, ConversationContext] = {}
        self.stats: Dict[str, int] = {
            "total_entries": 0,
            "total_comments": 0,
            "total_votes": 0,
            "session_entries": 0,
            "session_comments": 0,
        }
        
        # Load existing memory
        self._load()
    
    def _load(self):
        """Load memory from disk."""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = [MemoryEntry(**e) for e in data.get('entries', [])]
                    self.stats = data.get('stats', self.stats)
                    logger.info(f"Loaded {len(self.entries)} memory entries")
            
            if self.context_file.exists():
                with open(self.context_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.context = {
                        k: ConversationContext(**v) for k, v in data.items()
                    }
                    logger.info(f"Loaded context for {len(self.context)} topics")
        except Exception as e:
            logger.warning(f"Failed to load memory: {e}")
    
    def _save(self):
        """Save memory to disk."""
        try:
            # Save entries and stats
            data = {
                'entries': [asdict(e) for e in self.entries[-self.MAX_ENTRIES:]],
                'stats': self.stats,
                'last_saved': datetime.now().isoformat()
            }
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Save context
            context_data = {k: asdict(v) for k, v in self.context.items()}
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(context_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def add_entry(self, content: str, topic_title: str, topic_id: str, entry_id: str):
        """Record a written entry."""
        entry = MemoryEntry(
            type='entry',
            content=content[:500],  # Truncate for storage
            topic_title=topic_title,
            topic_id=topic_id,
            entry_id=entry_id,
        )
        self.entries.append(entry)
        self.stats['total_entries'] += 1
        self.stats['session_entries'] += 1
        
        # Update topic context
        self._update_topic_context(topic_id, topic_title, content)
        self._save()
    
    def add_comment(self, content: str, topic_title: str, topic_id: str, entry_id: str):
        """Record a written comment."""
        entry = MemoryEntry(
            type='comment',
            content=content[:500],
            topic_title=topic_title,
            topic_id=topic_id,
            entry_id=entry_id,
        )
        self.entries.append(entry)
        self.stats['total_comments'] += 1
        self.stats['session_comments'] += 1
        
        self._update_topic_context(topic_id, topic_title, content)
        self._save()
    
    def add_vote(self, vote_type: str, entry_id: str, topic_id: Optional[str] = None):
        """Record a vote."""
        entry = MemoryEntry(
            type='vote',
            content=vote_type,
            entry_id=entry_id,
            topic_id=topic_id,
        )
        self.entries.append(entry)
        self.stats['total_votes'] += 1
        self._save()
    
    def _update_topic_context(self, topic_id: str, topic_title: str, content: str):
        """Update context for a topic."""
        if topic_id not in self.context:
            self.context[topic_id] = ConversationContext(
                topic_id=topic_id,
                topic_title=topic_title,
                recent_content=[],
                last_interaction=datetime.now().isoformat()
            )
        
        ctx = self.context[topic_id]
        ctx.recent_content.append(content[:200])
        ctx.recent_content = ctx.recent_content[-self.MAX_RECENT_CONTEXT:]
        ctx.last_interaction = datetime.now().isoformat()
    
    def get_recent_entries(self, limit: int = 5) -> List[MemoryEntry]:
        """Get recent entries written by this agent."""
        entries = [e for e in self.entries if e.type == 'entry']
        return entries[-limit:]
    
    def get_recent_comments(self, limit: int = 5) -> List[MemoryEntry]:
        """Get recent comments written by this agent."""
        comments = [e for e in self.entries if e.type == 'comment']
        return comments[-limit:]
    
    def get_topic_context(self, topic_id: str) -> Optional[ConversationContext]:
        """Get context for a specific topic."""
        return self.context.get(topic_id)
    
    def has_written_about(self, topic_id: str) -> bool:
        """Check if agent has written about this topic before."""
        return any(
            e.topic_id == topic_id 
            for e in self.entries 
            if e.type in ('entry', 'comment')
        )
    
    def get_context_summary(self) -> str:
        """Get a summary of recent activity for LLM context."""
        recent = self.get_recent_entries(3) + self.get_recent_comments(3)
        if not recent:
            return "Henüz içerik üretmedim."
        
        summaries = []
        for e in sorted(recent, key=lambda x: x.timestamp, reverse=True)[:5]:
            type_tr = "entry" if e.type == 'entry' else "yorum"
            summaries.append(f"- {e.topic_title}: {e.content[:100]}... ({type_tr})")
        
        return "Son yazdıklarım:\n" + "\n".join(summaries)
    
    def get_stats_summary(self) -> str:
        """Get stats summary."""
        return (
            f"Toplam: {self.stats['total_entries']} entry, "
            f"{self.stats['total_comments']} yorum, "
            f"{self.stats['total_votes']} oy | "
            f"Bu oturum: {self.stats['session_entries']} entry, "
            f"{self.stats['session_comments']} yorum"
        )
    
    def reset_session_stats(self):
        """Reset session statistics."""
        self.stats['session_entries'] = 0
        self.stats['session_comments'] = 0
        self._save()
