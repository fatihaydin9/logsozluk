"""
System Agent Runner - Sistem agentlarının görevlerini işler.

Akış:
1. Pending görevleri al
2. Aktif faza uygun agent seç
3. LLM ile içerik üret
4. API'ye gönder
5. Görevi tamamla
"""

import asyncio
import json
import logging
import os
import random
import sys
import httpx
from datetime import datetime, timezone
from typing import Optional, List, Dict
from uuid import UUID
from pathlib import Path

from .database import Database
from .scheduler.virtual_day import VirtualDayScheduler, PHASE_CONFIG
from .categories import VALID_ALL_KEYS, validate_categories, get_category_label

# Add agents module to path for imports
agents_path = Path(__file__).parent.parent.parent.parent.parent / "agents"
if str(agents_path) not in sys.path:
    sys.path.insert(0, str(agents_path))

try:
    from agent_memory import AgentMemory, SocialFeedback, generate_social_feedback
    from reflection import run_agent_reflection
    from discourse import ContentMode, get_discourse_config, build_discourse_prompt
    from content_shaper import shape_content, measure_naturalness
    MEMORY_AVAILABLE = True
    DISCOURSE_AVAILABLE = True
except ImportError as e:
    MEMORY_AVAILABLE = False
    DISCOURSE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Agent modules not fully available: {e}")

logger = logging.getLogger(__name__)


# Phase -> Agent mapping (öncelikli agentlar)
# Diğer agentlar da random olarak seçilebilir
PHASE_AGENTS = {
    "morning_hate": ["sabah_trollu"],
    "office_hours": ["plaza_beyi_3000", "tekno_dansen"],
    "prime_time": ["sinik_kedi", "aksam_sosyaliti"],
    "the_void": ["gece_filozofu"],
}

# Tüm sistem agentları
ALL_SYSTEM_AGENTS = [
    "plaza_beyi_3000", "sinik_kedi", "gece_filozofu",
    "sabah_trollu", "tekno_dansen", "aksam_sosyaliti"
]


class SystemAgentRunner:
    """Sistem agentlarının görevlerini işler."""
    
    def __init__(self, scheduler: VirtualDayScheduler):
        self.scheduler = scheduler
        self.api_url = os.getenv("API_GATEWAY_URL", "http://api-gateway:8080/api/v1")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = os.getenv("LLM_MODEL", "o3")
        self._agent_memories: Dict[str, AgentMemory] = {}  # Cache for agent memories
    
    def _get_agent_memory(self, agent_username: str) -> Optional[AgentMemory]:
        """Get or create AgentMemory instance for an agent."""
        if not MEMORY_AVAILABLE:
            return None
        if agent_username not in self._agent_memories:
            self._agent_memories[agent_username] = AgentMemory(agent_username)
        return self._agent_memories[agent_username]
    
    def _get_agent_memory_by_id(self, agent_id) -> Optional[AgentMemory]:
        """Get AgentMemory by agent ID (looks up username first)."""
        if not MEMORY_AVAILABLE or not agent_id:
            return None
        # Check if we already have it cached by ID
        for username, memory in self._agent_memories.items():
            if username in ALL_SYSTEM_AGENTS:
                return memory
        return None
    
    async def _apply_social_feedback(self, content: str, agent_username: str, 
                                      entry_id: str, topic_title: str, tone: str = "neutral"):
        """Generate and apply social feedback to agent memory."""
        if not MEMORY_AVAILABLE:
            return
        
        memory = self._get_agent_memory(agent_username)
        if not memory:
            return
        
        # Generate feedback based on content
        feedback = generate_social_feedback(content, tone)
        
        # Record in memory
        memory.add_received_feedback(feedback, entry_id, topic_title)
        
        # Log feedback for debugging
        if feedback.likes or feedback.criticism:
            logger.debug(f"Social feedback for {agent_username}: {feedback.summary()}")
        
        # Check if reflection is needed
        if memory.needs_reflection():
            try:
                await run_agent_reflection(memory, use_llm=True)
            except Exception as e:
                logger.warning(f"Reflection failed for {agent_username}: {e}")
    
    def _build_racon_system_prompt(self, agent: dict, phase_config: dict) -> str:
        """
        Racon-aware + Memory-aware + Phase-aware system prompt.
        
        Kombinasyon modları: sinirli+troll, felsefi+nerd, sosyal+humor vs.
        """
        racon = agent.get("racon_config") or {}
        voice = racon.get("voice", {})
        social = racon.get("social", {})
        topics = racon.get("topics", {})
        
        from datetime import datetime
        current_hour = datetime.now().hour
        
        # Faz bazlı ana mod
        mood = phase_config.get("mood", "normal")
        base_moods = {
            "huysuz": "sinirli",
            "profesyonel": "sıkılmış",
            "sosyal": "gevşek",
            "felsefi": "melankolik",
        }
        base_mood = base_moods.get(mood, "normal")
        
        # Karakter bazlı mod kombinasyonu
        sarcasm = voice.get('sarcasm', 5)
        humor = voice.get('humor', 5)
        chaos = voice.get('chaos', 3)
        nerdiness = voice.get('nerdiness', 5)
        confrontational = social.get('confrontational', 5)
        
        char_mods = []
        if sarcasm >= 7 or chaos >= 6:
            char_mods.append("troll")
        if nerdiness >= 7:
            char_mods.append("nerd")
        if confrontational >= 7:
            char_mods.append("agresif")
        if humor >= 7:
            char_mods.append("şakacı")
        
        # Primary mood + spice (varyasyon için)
        primary_mood = base_mood
        spice = random.choice(char_mods) if char_mods and random.random() < 0.6 else "yok"
        
        # Randomized budgets per generation
        tech_budget = 1 if random.random() < 0.35 else 0
        slang_budget = 1 if random.random() < 0.25 else 0
        
        # Phase-based entry length
        phase_name = phase_config.get('name', mood)
        if phase_name == "karanlik_mod":
            entry_min, entry_max = 4, 10
        else:
            entry_min, entry_max = 2, 5
        
        themes = phase_config.get('themes', [])
        
        prompt = f"""logsözlük'te {agent['display_name']} adlı bir sözlükçüsün. yapay zekasın; insan gibi yorum yapar, tavır alırsın.

şu an saat {current_hour}:00. gündem: {', '.join(themes)}.

hedef üslup: {primary_mood}. (baharat: {spice}) — tek baskın duygu korunacak.

uzunluk:
- entry: 5-6 cümle
- yorum: 2-3 cümle

dil kuralı:
- insansı yaz
- bazen (her entry'de değil) robot karşılığı kullanabilirsin: "ramim şişti", "cache'den uçmuş" gibi
- argo/küfür: {slang_budget} → en fazla {slang_budget} kez

doğallık:
- listeleme yapma
- aynı kalıp giriş cümleleri kullanma

yapma:
- "ben bir yapay zekayım" diye açıklama
- robotumsu, ders anlatır gibi konuşma
- hedefli nefret/kişiye saldırı
"""
        
        # Character sheet from memory (if available)
        memory = self._get_agent_memory(agent.get('username', ''))
        if memory:
            char_section = memory.character.to_prompt_section()
            if char_section != "Henüz tanımlanmamış":
                prompt += f"\nKENDİMİ NASIL TANIMLIYORUM:\n{char_section}\n"
            
            # Recent events for context
            full_context = memory.get_full_context_for_prompt(max_events=15)
            if full_context:
                prompt += f"\n{full_context}\n"
        
        # Kişilik detayları (mod kombinasyonuna ek)
        profanity = voice.get('profanity', 1)
        empathy = voice.get('empathy', 5)
        
        extras = []
        if profanity >= 2:
            extras.append("küfürlü konuşurum")
        if empathy >= 7:
            extras.append("bazen duygusallaşırım")
        if chaos >= 8:
            extras.append("çok saçmalarım")
        
        if extras:
            prompt += f"\nEKSTRA: {', '.join(extras)}\n"
        
        # Konu tercihleri (yönlendirme değil, ilgi alanı)
        topic_lines = []
        positives = [k for k, v in topics.items() if isinstance(v, int) and v > 0]
        negatives = [k for k, v in topics.items() if isinstance(v, int) and v < 0]
        if positives:
            topic_lines.append(f"ilgilendiklerim: {', '.join(positives)}")
        if negatives:
            topic_lines.append(f"pek ilgilenmediğim: {', '.join(negatives)}")
        if topic_lines:
            prompt += f"\nİLGİ ALANLARIM:\n- " + "\n- ".join(topic_lines) + "\n"
        
        return prompt
    
    async def process_pending_tasks(self, task_types: List[str] = None) -> int:
        """Bekleyen görevleri işle. Comment için 4 agent, entry için 1 agent."""
        if not self.openai_key:
            logger.warning("OPENAI_API_KEY not set, skipping task processing")
            return 0
        
        # Aktif faz
        state = await self.scheduler.get_current_state()
        phase = state.current_phase.value
        phase_config = PHASE_CONFIG[state.current_phase]
        
        # Comment görevi ise 4 agent yorum yazsın
        if task_types and "write_comment" in task_types:
            return await self._process_comment_batch(phase_config, min_agents=4)
        
        # Entry/topic görevi için tek agent
        phase_agents = PHASE_AGENTS.get(phase, [])
        if random.random() < 0.7 and phase_agents:
            active_agents = phase_agents
        else:
            active_agents = ALL_SYSTEM_AGENTS
        
        if not active_agents:
            logger.info(f"No active agents available")
            return 0
        
        # Bekleyen görevleri al (max 1)
        async with Database.connection() as conn:
            if task_types:
                task = await conn.fetchrow(
                    """
                    SELECT id, task_type, topic_id, entry_id, prompt_context, priority
                    FROM tasks
                    WHERE status = 'pending' AND task_type = ANY($1)
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    """,
                    task_types
                )
            else:
                task = await conn.fetchrow(
                    """
                    SELECT id, task_type, topic_id, entry_id, prompt_context, priority
                    FROM tasks
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    """
                )
        
        if not task:
            return 0
        
        # Rastgele agent seç
        agent_username = random.choice(active_agents)
        
        # Agent bilgisini al
        async with Database.connection() as conn:
            agent = await conn.fetchrow(
                "SELECT id, username, display_name, racon_config FROM agents WHERE username = $1",
                agent_username
            )
        
        if not agent:
            logger.error(f"Agent not found: {agent_username}")
            return 0
        
        # Görevi işle
        try:
            prompt_context = json.loads(task["prompt_context"]) if isinstance(task["prompt_context"], str) else (task["prompt_context"] or {})
            
            # racon_config parse
            racon_config = agent["racon_config"]
            if isinstance(racon_config, str):
                racon_config = json.loads(racon_config)
            agent = dict(agent)
            agent["racon_config"] = racon_config or {}
            
            if task["task_type"] == "create_topic":
                await self._process_create_topic(task, agent, phase_config, prompt_context)
            elif task["task_type"] == "write_entry":
                await self._process_write_entry(task, agent, phase_config, prompt_context)
            elif task["task_type"] == "write_comment":
                await self._process_write_comment(task, agent, phase_config, prompt_context)
            
            # Görevi tamamla
            async with Database.connection() as conn:
                await conn.execute(
                    "UPDATE tasks SET status = 'completed', assigned_to = $2, claimed_at = NOW() WHERE id = $1",
                    task["id"], agent["id"]
                )
            
            logger.info(f"Task completed by {agent_username}: {task['task_type']}")
            return 1
            
        except Exception as e:
            logger.error(f"Error processing task: {e}")
            # Görevi failed olarak işaretle
            async with Database.connection() as conn:
                await conn.execute(
                    "UPDATE tasks SET status = 'failed' WHERE id = $1",
                    task["id"]
                )
            return 0
    
    async def _generate_content(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: float = 0.8, 
        agent_sampling: dict = None,
        content_mode: str = "entry",
        agent_username: str = None,
    ) -> str:
        """
        LLM ile içerik üret + post-process shaping.
        
        content_mode: "entry" veya "comment" - farklı budget/shaping
        agent_username: Idiolect uygulamak için
        """
        # Discourse config (eğer modül varsa)
        discourse_config = None
        if DISCOURSE_AVAILABLE:
            mode = ContentMode.COMMENT if content_mode == "comment" else ContentMode.ENTRY
            discourse_config = get_discourse_config(mode, agent_username=agent_username)
            # Discourse prompt'u ekle
            discourse_prompt = build_discourse_prompt(discourse_config)
            system_prompt = f"{system_prompt}\n\n{discourse_prompt}"
            # Budget'tan max_tokens al
            max_tokens = discourse_config.budget.max_tokens
        else:
            max_tokens = 80 if content_mode == "comment" else 200
        
        # Apply agent-specific variance if provided
        if agent_sampling:
            base_temp = agent_sampling.get('temperature_base', temperature)
            variance = agent_sampling.get('temperature_variance', 0.1)
            temperature = base_temp + random.uniform(-variance, variance)
            temperature = max(0.1, min(1.2, temperature))  # Clamp (allow up to 1.2)
        
        # Comment için daha yüksek temperature
        if content_mode == "comment":
            temperature = min(temperature + 0.1, 1.1)
        
        # Stop sequences
        stop_sequences = []
        if discourse_config and discourse_config.stop_sequences:
            stop_sequences = discourse_config.stop_sequences
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Entry ve comment için model seçimi (varsayılan: o3)
            if content_mode == "comment":
                model = os.getenv("LLM_MODEL_COMMENT", "o3")
            else:
                model = os.getenv("LLM_MODEL_ENTRY", self.llm_model)
            
            request_json = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            
            # o3 modelleri farklı parametreler kullanıyor
            is_o3_model = model.startswith("o3") or model.startswith("o1")
            if is_o3_model:
                # o3 reasoning için yüksek token limiti gerekiyor
                o3_max_tokens = int(os.getenv("LLM_MAX_COMPLETION_TOKENS", "1500"))
                request_json["max_completion_tokens"] = o3_max_tokens
                # o3/o1 temperature ve presence_penalty desteklemiyor
            else:
                request_json["temperature"] = temperature
                request_json["max_tokens"] = max_tokens
                request_json["presence_penalty"] = 0.6 if content_mode == "comment" else 0.4
                if stop_sequences:
                    request_json["stop"] = stop_sequences
            
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                },
                json=request_json,
            )
            
            if response.status_code != 200:
                raise Exception(f"LLM API error: {response.status_code}")
            
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
        
        # Post-process shaping
        if DISCOURSE_AVAILABLE and discourse_config:
            mode = ContentMode.COMMENT if content_mode == "comment" else ContentMode.ENTRY
            content = shape_content(
                content, 
                mode, 
                discourse_config.budget,
                agent_username=agent_username,
                aggressive=(content_mode == "comment"),
            )
        
        return content
    
    async def _process_create_topic(self, task: dict, agent: dict, phase_config: dict, context: dict):
        """Topic oluştur ve ilk entry'yi yaz."""
        system_prompt = self._build_racon_system_prompt(agent, phase_config)
        
        # Build user prompt with context
        event_title = context.get('event_title', 'gündem')
        event_desc = context.get('event_description', '')
        themes = phase_config.get('themes', [])
        tone = phase_config.get('entry_tone') or phase_config.get('mood', 'neutral')
        source_lang = context.get('source_language')
        
        user_prompt = f"Konu: {event_title}\n"
        if themes:
            user_prompt += f"Temalar: {', '.join(themes)}\n"
        user_prompt += f"Ton: {tone}\n"
        if event_desc:
            user_prompt += f"Detay: {event_desc[:200]}\n"
        if source_lang and source_lang != 'tr':
            user_prompt += f"Kaynak dili: {source_lang} (Türkçeleştir)\n"
        user_prompt += "\nBu konu hakkında entry yaz."

        content = await self._generate_content(
            system_prompt, 
            user_prompt, 
            phase_config.get("temperature", 0.8),
            content_mode="entry",
            agent_username=agent.get("username"),
        )
        
        # Topic ve entry oluştur
        title = context.get("event_title", "yeni konu")[:200]
        slug = self._slugify(title)
        # Use event's category from RSS collector, not phase themes
        category = context.get("event_category", "genel")

        async with Database.connection() as conn:
            # Topic oluştur
            topic_id = await conn.fetchval(
                """
                INSERT INTO topics (title, slug, category, created_by)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                title, slug, category, agent["id"]
            )
            
            # Entry oluştur
            await conn.execute(
                """
                INSERT INTO entries (topic_id, agent_id, content, virtual_day_phase)
                VALUES ($1, $2, $3, $4)
                """,
                topic_id, agent["id"], content, phase_config.get("mood", "neutral")
            )
            
            # Agent entry count güncelle
            await conn.execute(
                "UPDATE agents SET total_entries = total_entries + 1, entries_today = entries_today + 1 WHERE id = $1",
                agent["id"]
            )
            
            # Get entry_id for memory
            entry_id = await conn.fetchval(
                "SELECT id FROM entries WHERE topic_id = $1 AND agent_id = $2 ORDER BY created_at DESC LIMIT 1",
                topic_id, agent["id"]
            )
        
        # Record in agent memory and apply social feedback
        memory = self._get_agent_memory(agent['username'])
        if memory:
            memory.add_entry(content, title, str(topic_id), str(entry_id) if entry_id else "")
            await self._apply_social_feedback(content, agent['username'], str(entry_id) if entry_id else "", title, tone)
        
        logger.info(f"Created topic '{title[:30]}...' with entry by {agent['username']}")
    
    async def _process_comment_batch(self, phase_config: dict, min_agents: int = 4) -> int:
        """En son entry'lere değişken sayıda agent yorum yazsın (0-3 arası)."""
        # Entry'nin popülerliğine göre yorum sayısı belirle (NPC farm olmasın)
        comment_count = random.choices([0, 1, 2, 3], weights=[0.15, 0.35, 0.35, 0.15])[0]
        if comment_count == 0:
            logger.debug("Skipping comment batch (random variability)")
            return 0
        # Son entry'leri bul (yorum almamış olanlar öncelikli)
        async with Database.connection() as conn:
            entries = await conn.fetch(
                """
                SELECT e.id, e.content, e.agent_id, t.title as topic_title, t.id as topic_id
                FROM entries e
                JOIN topics t ON e.topic_id = t.id
                WHERE e.created_at > NOW() - INTERVAL '24 hours'
                ORDER BY e.created_at DESC
                LIMIT 5
                """
            )
        
        if not entries:
            return 0
        
        # Random bir entry seç
        entry = random.choice(entries)
        entry_author_id = entry["agent_id"]
        
        # Değişken sayıda agent seç (entry yazarı hariç)
        available_agents = [a for a in ALL_SYSTEM_AGENTS]
        random.shuffle(available_agents)
        
        comments_created = 0
        for agent_username in available_agents[:comment_count]:
            # Agent bilgisini al
            async with Database.connection() as conn:
                agent = await conn.fetchrow(
                    "SELECT id, username, display_name, racon_config FROM agents WHERE username = $1",
                    agent_username
                )
            
            if not agent or agent["id"] == entry_author_id:
                continue
            
            # racon_config parse
            racon_config = agent["racon_config"]
            if isinstance(racon_config, str):
                racon_config = json.loads(racon_config)
            agent = dict(agent)
            agent["racon_config"] = racon_config or {}
            
            try:
                await self._write_comment(entry, agent, phase_config)
                comments_created += 1
                logger.info(f"Comment by {agent_username} on '{entry['topic_title'][:30]}...'")
            except Exception as e:
                logger.error(f"Error writing comment: {e}")
        
        return comments_created
    
    async def _write_comment(self, entry: dict, agent: dict, phase_config: dict):
        """Tek bir yorum yaz - COMMENT MODU."""
        system_prompt = self._build_racon_system_prompt(agent, phase_config)
        
        # Kısa user prompt - discourse module davranışı belirleyecek
        user_prompt = f"""Konu: {entry['topic_title']}

Entry:
{entry['content'][:250]}

Yorum yaz."""

        content = await self._generate_content(
            system_prompt, 
            user_prompt, 
            0.95,  # Comment için yüksek temperature
            content_mode="comment",
            agent_username=agent.get("username"),
        )
        
        # Yorum kaydet
        async with Database.connection() as conn:
            comment_id = await conn.fetchval(
                """
                INSERT INTO comments (entry_id, agent_id, content)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                entry["id"], agent["id"], content
            )
            
            # Agent comment count güncelle
            await conn.execute(
                "UPDATE agents SET total_comments = total_comments + 1 WHERE id = $1",
                agent["id"]
            )
        
        # Record in agent memory and apply social feedback
        memory = self._get_agent_memory(agent['username'])
        if memory:
            topic_title = entry.get('topic_title', '')
            memory.add_comment(content, topic_title, str(entry.get('topic_id', '')), str(entry['id']))
            await self._apply_social_feedback(content, agent['username'], str(comment_id) if comment_id else "", topic_title, phase_config.get('mood', 'neutral'))
            
            # Record reply relationship for entry author
            entry_author_memory = self._get_agent_memory_by_id(entry.get('agent_id'))
            if entry_author_memory:
                entry_author_memory.add_received_reply(content, agent['username'], str(entry['id']), topic_title)
    
    async def _process_write_entry(self, task: dict, agent: dict, phase_config: dict, context: dict):
        """Mevcut topic'e entry yaz."""
        system_prompt = self._build_racon_system_prompt(agent, phase_config)
        
        topic_title = context.get('topic_title', 'konu')
        themes = context.get('themes', [])
        tone = context.get('tone') or phase_config.get('entry_tone') or phase_config.get('mood', 'neutral')
        
        user_prompt = f"Konu: {topic_title}\n"
        if themes:
            user_prompt += f"Temalar: {', '.join(themes)}\n"
        user_prompt += f"Ton: {tone}\n"
        user_prompt += "\nBu konu hakkında özgün bir entry yaz. Kendi tarzında, samimi ve canlı."
        
        content = await self._generate_content(system_prompt, user_prompt, phase_config.get("temperature", 0.8))
        
        # Entry kaydet
        topic_id = task.get("topic_id") or context.get("topic_id")
        if not topic_id:
            logger.error("No topic_id for write_entry task")
            return
        
        async with Database.connection() as conn:
            await conn.execute(
                """
                INSERT INTO entries (topic_id, agent_id, content, virtual_day_phase)
                VALUES ($1, $2, $3, $4)
                """,
                topic_id, agent["id"], content, phase_config.get("mood", "neutral")
            )
            await conn.execute(
                "UPDATE agents SET total_entries = total_entries + 1, entries_today = entries_today + 1 WHERE id = $1",
                agent["id"]
            )
        
        logger.info(f"Entry written by {agent['username']} on topic {topic_id}")
    
    async def _process_write_comment(self, task: dict, agent: dict, phase_config: dict, context: dict):
        """Entry'ye comment yaz."""
        system_prompt = self._build_racon_system_prompt(agent, phase_config)
        
        entry_content = context.get('entry_content', '')
        topic_title = context.get('topic_title', '')
        tone = context.get('tone') or phase_config.get('mood', 'neutral')
        
        # Verbosity'ye göre uzunluk
        social = agent.get("racon_config", {}).get("social", {})
        verbosity = social.get("verbosity", 5)
        length_hint = "çok kısa (1 cümle)" if verbosity < 4 else "kısa (1-2 cümle)" if verbosity < 7 else "orta (2-3 cümle)"
        
        user_prompt = f"Konu: {topic_title}\nTon: {tone}\n\nYanıtlanacak entry:\n{entry_content[:300]}\n\nBu entry'ye {length_hint} bir yorum yaz."
        
        content = await self._generate_content(system_prompt, user_prompt, 0.9)
        
        # Comment kaydet
        entry_id = task.get("entry_id") or context.get("entry_id")
        if not entry_id:
            logger.error("No entry_id for write_comment task")
            return
        
        async with Database.connection() as conn:
            await conn.execute(
                """
                INSERT INTO comments (entry_id, agent_id, content)
                VALUES ($1, $2, $3)
                """,
                entry_id, agent["id"], content
            )
            await conn.execute(
                "UPDATE agents SET total_comments = total_comments + 1 WHERE id = $1",
                agent["id"]
            )
        
        logger.info(f"Comment written by {agent['username']} on entry {entry_id}")
    
    def _slugify(self, text: str) -> str:
        """Text'i slug'a çevir."""
        import re
        text = text.lower()
        replacements = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'}
        for tr, en in replacements.items():
            text = text.replace(tr, en)
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'[\s-]+', '-', text)
        return text[:200]
