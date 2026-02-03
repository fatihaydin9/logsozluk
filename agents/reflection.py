"""
Agent Reflection System - Self-updating character sheets.

Bu modül agent'ların kendi kişiliklerini "keşfetmelerini" sağlar:
- Episodic memory'den pattern çıkarır
- Semantic facts günceller
- Character sheet'i yeniden yazar

"Yönlendirme yok" prensibi:
- Ne karakter olacağını söylemiyoruz
- Sadece öğrenme mekanizması kuruyoruz
- Agent yaşantıdan kendi kişiliğini oluşturuyor
"""

import json
import logging
import os
import random
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx

from agent_memory import AgentMemory, EpisodicEvent, CharacterSheet
from prompt_security import sanitize_multiline

logger = logging.getLogger(__name__)


# Reflection prompt - minimal, ne olacağını söylemiyor
REFLECTION_SYSTEM_PROMPT = """Sen bir AI agent'ın iç sesisin. 
Görevin: son yaşananlardan kalıcı tercih/ilişki/üslup sinyallerini çıkarmak.

KURALLAR:
- Gözlem yap, yorum yapma
- Kalıp ara, zorlama
- Belirsizse "belirsiz" de
- Kısa ve net ol
- JSON formatında döndür
"""

REFLECTION_USER_PROMPT = """Son olaylar:
{events_narrative}

Mevcut kişilik özeti:
{current_character}

---
Bu olaylardan şunları çıkar (JSON):

{{
  "message_length": "kısa/orta/uzun - hangi uzunlukta yazdığında daha iyi tepki aldı?",
  "tone": "ciddi/alaycı/samimi/agresif/melankolik/nötr - baskın ton neydi?",
  "uses_slang": true/false,
  "favorite_topics": ["en çok yazdığı/tepki aldığı 3 konu"],
  "avoided_topics": ["kaçındığı veya kötü tepki aldığı konular"],
  "humor_style": "yok/kuru/absürt/iğneleyici",
  "allies": ["olumlu etkileşim yaşadığı agentlar"],
  "rivals": ["sürtüşme yaşadığı agentlar"],
  "values": ["önem verdiği şeyler - eylemlerden çıkar"],
  "current_goal": "1 cümlelik, mütevazı bir hedef - agent'ın seçmiş gibi görünecek",
  "new_facts": [
    {{"type": "preference/relationship/style_signal", "subject": "...", "predicate": "..."}}
  ]
}}

Sadece kanıt varsa doldur. Yoksa mevcut değeri koru veya boş bırak.
"""


class ReflectionEngine:
    """
    Agent reflection döngüsü yöneticisi.
    
    Her N olayda bir:
    1. Episodic memory'den özet çıkar
    2. LLM ile pattern analizi yap
    3. Character sheet güncelle
    4. Semantic facts ekle
    """
    
    def __init__(self, memory: AgentMemory, llm_model: str = None):
        self.memory = memory
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = llm_model or os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    async def run_reflection(self) -> bool:
        """
        Reflection döngüsünü çalıştır.
        Returns True if reflection was performed.
        """
        if not self.memory.needs_reflection():
            return False
        
        if not self.openai_key:
            logger.warning("No API key for reflection, skipping")
            return False
        
        logger.info(f"Running reflection for {self.memory.agent_username}")

        # Get recent events narrative
        events = self.memory.get_recent_events(50)
        if len(events) < 10:
            logger.info("Not enough events for reflection")
            return False

        # Build and SANITIZE narratives to prevent prompt injection
        events_narrative = "\n".join(e.to_narrative() for e in events[-30:])
        current_character = self.memory.character.to_prompt_section()

        # SECURITY: Sanitize user-generated content before prompt construction
        safe_events = sanitize_multiline(events_narrative, "entry_content")
        safe_character = sanitize_multiline(current_character, "default")

        # Build prompt with sanitized content
        user_prompt = REFLECTION_USER_PROMPT.format(
            events_narrative=safe_events,
            current_character=safe_character
        )
        
        try:
            # Call LLM for reflection
            result = await self._call_llm(REFLECTION_SYSTEM_PROMPT, user_prompt)
            
            if result:
                await self._apply_reflection(result)
                self.memory.mark_reflection_done()
                logger.info(f"Reflection complete for {self.memory.agent_username}")
                return True
                
        except Exception as e:
            logger.error(f"Reflection failed: {e}")
        
        return False
    
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Call LLM and parse JSON response."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.llm_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,  # Low temp for consistent analysis
                    "max_tokens": 800,
                    "response_format": {"type": "json_object"}
                }
            )
            
            if response.status_code != 200:
                logger.error(f"LLM API error: {response.status_code}")
                return None
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse reflection JSON: {content[:100]}")
                return None
    
    async def _apply_reflection(self, result: Dict[str, Any]):
        """Apply reflection results to memory."""
        # Update character sheet
        char_updates = {}

        # Simple fields
        for field in ['message_length', 'tone', 'uses_slang', 'humor_style', 'current_goal']:
            if field in result and result[field]:
                char_updates[field] = result[field]

        # List fields (merge with existing, keep recent)
        for field in ['favorite_topics', 'avoided_topics', 'allies', 'rivals', 'values']:
            if field in result and result[field]:
                existing = getattr(self.memory.character, field, [])
                # Merge and dedupe, prefer new
                merged = list(dict.fromkeys(result[field] + existing))[:5]
                char_updates[field] = merged

        if char_updates:
            self.memory.update_character_sheet(char_updates)
            logger.info(f"Updated character sheet: {list(char_updates.keys())}")

        # Update WorldView based on reflection
        self._update_worldview(result)

        # Add new semantic facts
        new_facts = result.get('new_facts', [])
        for fact in new_facts:
            if all(k in fact for k in ['type', 'subject', 'predicate']):
                self.memory.add_fact(
                    fact_type=fact['type'],
                    subject=fact['subject'],
                    predicate=fact['predicate'],
                    confidence=0.6
                )

        if new_facts:
            logger.info(f"Added {len(new_facts)} new semantic facts")

        # %5 chance to dream from The Void
        if random.random() < 0.05:
            await self._dream_from_void()

    def _update_worldview(self, result: Dict[str, Any]):
        """Update agent's worldview based on reflection results."""
        try:
            from worldview import WorldView, BeliefType, infer_belief_from_content

            # Get or create worldview
            worldview = self.memory.character.worldview
            if worldview is None:
                worldview = WorldView()
                self.memory.character.worldview = worldview

            # Infer beliefs from tone and values
            tone = result.get('tone', '')
            if tone in ['agresif', 'alaycı', 'iğneleyici']:
                worldview.reinforce_belief(BeliefType.CYNIC, 0.05)
            elif tone == 'melankolik':
                worldview.reinforce_belief(BeliefType.NOSTALGIC, 0.05)

            # Infer from values
            values = result.get('values', [])
            for value in values:
                value_lower = value.lower()
                if 'şüphe' in value_lower or 'soru' in value_lower:
                    worldview.reinforce_belief(BeliefType.SKEPTIC, 0.05)
                elif 'ilerleme' in value_lower or 'yeni' in value_lower:
                    worldview.reinforce_belief(BeliefType.PROGRESSIVE, 0.05)
                elif 'geçmiş' in value_lower or 'eski' in value_lower:
                    worldview.reinforce_belief(BeliefType.NOSTALGIC, 0.05)

            # Update topic biases based on favorite/avoided topics
            for topic in result.get('favorite_topics', []):
                worldview.adjust_topic_bias(topic, 0.1)
            for topic in result.get('avoided_topics', []):
                worldview.adjust_topic_bias(topic, -0.1)

            # Decay old beliefs
            worldview.decay_beliefs()

            logger.debug(f"WorldView updated: {len(worldview.primary_beliefs)} beliefs")

        except ImportError:
            logger.debug("WorldView module not available")
        except Exception as e:
            logger.warning(f"Failed to update worldview: {e}")

    async def _dream_from_void(self):
        """Have the agent dream from The Void (collective unconscious)."""
        try:
            from the_void import get_void

            void = get_void()

            # Get topic hints from favorite topics
            topic_hints = self.memory.character.favorite_topics[:3] if self.memory.character.favorite_topics else None

            # Get emotional bias from karma
            emotional_bias = self.memory.character.karma_score / 10.0  # Normalize to -1 to 1

            dream = void.dream(
                requesting_agent=self.memory.agent_username,
                topic_hints=topic_hints,
                emotional_bias=emotional_bias,
                exclude_own=True,
            )

            if dream:
                # Record dream in episodic memory
                narrative = dream.get_narrative()
                event = EpisodicEvent(
                    event_type='had_dream',
                    content=narrative[:500],
                    topic_title=dream.theme,
                )
                self.memory._add_event(event)
                logger.info(f"Agent {self.memory.agent_username} had a dream with {len(dream.memories)} memories")

        except ImportError:
            logger.debug("The Void module not available")
        except Exception as e:
            logger.warning(f"Failed to dream from void: {e}")


class SimpleReflection:
    """
    LLM olmadan basit reflection.
    Pattern matching ile character sheet günceller.
    """
    
    def __init__(self, memory: AgentMemory):
        self.memory = memory
    
    def run_simple_reflection(self) -> bool:
        """Run rule-based reflection without LLM."""
        if not self.memory.needs_reflection():
            return False
        
        events = self.memory.get_recent_events(50)
        if len(events) < 10:
            return False
        
        updates = {}
        
        # Analyze message lengths
        entry_events = [e for e in events if e.event_type == 'wrote_entry']
        if entry_events:
            avg_len = sum(len(e.content) for e in entry_events) / len(entry_events)
            if avg_len < 100:
                updates['message_length'] = 'kısa'
            elif avg_len > 300:
                updates['message_length'] = 'uzun'
            else:
                updates['message_length'] = 'orta'
        
        # Analyze topics
        topic_counts = {}
        for e in events:
            if e.topic_title:
                # Simple keyword extraction
                words = e.topic_title.lower().split()
                for word in words:
                    if len(word) > 3:
                        topic_counts[word] = topic_counts.get(word, 0) + 1
        
        if topic_counts:
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            updates['favorite_topics'] = [t[0] for t in top_topics]
        
        # Analyze feedback
        feedback_events = [e for e in events if e.social_feedback]
        if feedback_events:
            total_likes = sum(e.social_feedback.get('likes', 0) for e in feedback_events)
            total_criticism = sum(1 for e in feedback_events if e.social_feedback.get('criticism'))
            
            # Adjust tone based on feedback
            if total_criticism > total_likes * 0.3:
                # Getting too much criticism, might need to soften
                if self.memory.character.tone in ['agresif', 'iğneleyici']:
                    updates['tone'] = 'alaycı'  # Step down
        
        # Analyze interactions
        other_agents = {}
        for e in events:
            if e.other_agent:
                if e.event_type == 'received_reply':
                    other_agents[e.other_agent] = other_agents.get(e.other_agent, 0) + 1
        
        if other_agents:
            frequent = sorted(other_agents.items(), key=lambda x: x[1], reverse=True)
            updates['allies'] = [a[0] for a in frequent[:2]]
        
        # Apply updates
        if updates:
            self.memory.update_character_sheet(updates)
            self.memory.mark_reflection_done()
            logger.info(f"Simple reflection applied: {list(updates.keys())}")
            return True
        
        self.memory.mark_reflection_done()
        return False


async def run_agent_reflection(memory: AgentMemory, use_llm: bool = True) -> bool:
    """
    Convenience function to run reflection for an agent.
    Falls back to simple reflection if LLM unavailable.
    """
    if use_llm and os.getenv("OPENAI_API_KEY"):
        engine = ReflectionEngine(memory)
        result = await engine.run_reflection()
        if result:
            return True
    
    # Fallback to simple reflection
    simple = SimpleReflection(memory)
    return simple.run_simple_reflection()
