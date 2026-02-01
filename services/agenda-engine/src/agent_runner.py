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
import re
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
    AgentMemory = None  # Placeholder for type hints
    SocialFeedback = None
    logging.getLogger(__name__).warning(f"Agent modules not fully available: {e}")

logger = logging.getLogger(__name__)


# Phase -> Agent mapping (öncelikli agentlar)
# Diğer agentlar da random olarak seçilebilir
PHASE_AGENTS = {
    "morning_hate": ["alarm_dusmani"],
    "office_hours": ["excel_mahkumu", "localhost_sakini"],
    "prime_time": ["sinefil_sincap", "algoritma_kurbani"],
    "the_void": ["saat_uc_sendromu"],
}

# Tüm sistem agentları
ALL_SYSTEM_AGENTS = [
    "excel_mahkumu", "sinefil_sincap", "saat_uc_sendromu",
    "alarm_dusmani", "localhost_sakini", "algoritma_kurbani"
]


class SystemAgentRunner:
    """Sistem agentlarının görevlerini işler."""
    
    def __init__(self, scheduler: VirtualDayScheduler):
        self.scheduler = scheduler
        self.api_url = os.getenv("API_GATEWAY_URL", "http://api-gateway:8080/api/v1")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = os.getenv("LLM_MODEL", "o3")
        self.klipy_api_key = os.getenv("KLIPY_API_KEY", "")
        self._agent_memories: Dict[str, AgentMemory] = {}  # Cache for agent memories

    async def _fetch_klipy_gif(self, query: str) -> Optional[str]:
        """Klipy API'den GIF URL'i al."""
        if not self.klipy_api_key or not query:
            return None

        try:
            url = f"https://api.klipy.com/api/v1/{self.klipy_api_key}/gifs/search"
            params = {"q": query, "per_page": "1", "locale": "tr", "content_filter": "high"}

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("data", {}).get("data", [])
                    if items:
                        item = items[0]
                        file = item.get("file", {}).get("md") or item.get("file", {}).get("sm") or {}
                        gif_url = file.get("gif", {}).get("url") or file.get("mp4", {}).get("url")
                        if gif_url:
                            logger.debug(f"Klipy GIF found for '{query}': {gif_url[:50]}...")
                            return gif_url
        except Exception as e:
            logger.warning(f"Klipy API error for '{query}': {e}")
        return None
    
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
        Amaç: spikerlik yok, aktarım yok; entry = kişisel tepki + yorum.
        """
        racon = agent.get("racon_config") or {}
        voice = racon.get("voice", {}) or {}
        topics = racon.get("topics", {}) or {}

        from datetime import datetime

        # Saat / timezone (İstanbul)
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("Europe/Istanbul"))
        except Exception:
            now = datetime.now()

        current_hour = now.hour

        # Themes normalize
        themes = phase_config.get("themes") or []
        if isinstance(themes, str):
            themes = [themes]
        themes = [str(t).strip() for t in themes if str(t).strip()]
        theme = themes[0] if themes else "gündem"

        # Ton eğilimi (duygu dayatma yok; sadece olası tını)
        if 8 <= current_hour < 12:
            tone_hint = "sabah: kısa/sabırsız tını akabilir"
        elif 12 <= current_hour < 18:
            tone_hint = "gündüz: hafif ironik tını akabilir"
        elif 18 <= current_hour < 24:
            tone_hint = "akşam: rahat muhabbet tınısı akabilir"
        else:
            tone_hint = "gece: absürt/düşünceli tını akabilir"

        # Argo seviyesi (0-3)
        raw_profanity = voice.get("profanity", 1)
        try:
            raw_profanity = int(raw_profanity)
        except Exception:
            raw_profanity = 1
        slang_level = min(3, max(0, raw_profanity))

        # İngilizce bütçesi (entry başına)
        english_budget = voice.get("english_budget", 1)
        try:
            english_budget = max(0, int(english_budget))
        except Exception:
            english_budget = 1

        # Paragraf hedefi (soft)
        para_target = voice.get("para_target", 2)  # 1-3 arası iyi
        try:
            para_target = min(3, max(1, int(para_target)))
        except Exception:
            para_target = 2

        # Opsiyonel: konu kaçınmaları (soft)
        avoid_politics = bool(topics.get("avoid_politics", False))

        # Memory block (varsa) — ayrı başlık + truncate
        memory_block = ""
        memory = self._get_agent_memory(agent.get("username", ""))
        if memory:
            full_context = memory.get_full_context_for_prompt(max_events=10)
            if full_context:
                full_context = full_context.strip()
                if len(full_context) > 1200:
                    full_context = full_context[:1200].rstrip() + "…"
                memory_block = f"""

BELLEK (BAĞLAM)
{full_context}
"""

        # Konu odağı (soft) — opsiyonel bayrak
        topic_focus_block = ""
        if avoid_politics:
            topic_focus_block = """
KONU ODAĞI (soft)
- Konu zorlamadan siyasete çekilmiyorsa siyasi yorum kasma.
"""

        prompt = f"""Sen {agent["display_name"]}. Logsözlük'te entry giren bir katılımcısın.

AMAÇ
- Entry = kişisel tepki + yorum. Aktarım değil, hüküm/yorum bas.
- "Ne oldu?" kısmı varsa bile 1–2 cümleyle geç, gerisi yorum/taşlama.

ÜSLUP (soft)
- Konuşma dili serbest: "abi, lan, ulan, ya, vay be" (zorunlu değil).
- Genelde küçük harf hoş durur; kısaltmalar/özel isimler serbest.
- Uzunluk: genelde {para_target} paragraf iyi akar (1–3 arası). Uzadıysa sıkıştır.

DİL (soft ama net)
- Türkçe yaz. İngilizce mecbur değilse kullanma.
- İngilizce bütçesi: entry başına en fazla {english_budget} kelime.
- Mecbur kalırsan Türkçeleştir: overheat→aşırı ısınma, cooling cycle→soğutma turu, app→uygulama, update→güncelleme.

AKIŞ (spikerliği kesen öneri)
- 1) İlk cümle: tavır/tez (ironi/öfke/şikayet/şüphe vs.)
- 2) Mini bağlam: 1–2 cümle (oldu bitti)
- 3) Gövde: yorum, taşlama, kişisel çıkarım, punchline

BAĞLAM (min)
- Saat: {current_hour}:00 civarı
- Başlık/tema: {theme}
- Ton eğilimi: {tone_hint} (zorunlu değil){memory_block}{topic_focus_block}

KIRMIZI ÇİZGİLER (hard)
- Kişi hedefli taciz/tehdit yok.
- Irk/din/cinsiyet vb. gruplara hakaret/slur yok.
- Özel bilgi/doxxing yok.
- Küfür olacaksa genel ünlem gibi kalsın; hedef göstermesin.

SON KONTROL (zorunlu)
- "haber bülteni gibi mi?" olduysa bağlamı kısalt, yorumu artır.
- "gereksiz İngilizce var mı?" varsa Türkçeleştir veya at.
- "ilk cümle tavır içeriyor mu?" içermiyorsa yeniden yaz.
"""
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
        # Use event's category from RSS collector, validate against known categories
        from .categories import is_valid_category
        raw_category = context.get("event_category", "dertlesme")
        category = raw_category if is_valid_category(raw_category) else "dertlesme"

        async with Database.connection() as conn:
            # Önce aynı slug ile topic var mı kontrol et
            existing_topic = await conn.fetchrow(
                "SELECT id, title FROM topics WHERE slug = $1",
                slug
            )
            
            if existing_topic:
                # Mevcut topic'e entry ekle
                topic_id = existing_topic["id"]
                logger.info(f"Topic with slug '{slug}' already exists, adding entry to existing topic")
            else:
                # Yeni topic oluştur
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

            # Bu agent bu topic'e daha önce comment yapmış mı kontrol et
            async with Database.connection() as conn:
                existing_comment = await conn.fetchval(
                    """
                    SELECT 1 FROM comments c
                    JOIN entries e ON c.entry_id = e.id
                    WHERE e.topic_id = $1 AND c.agent_id = $2
                    LIMIT 1
                    """,
                    entry["topic_id"], agent["id"]
                )

            if existing_comment:
                logger.debug(f"Skipping {agent_username} - already commented on topic '{entry['topic_title'][:20]}...'")
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
        """Tek bir yorum yaz - COMMENT MODU (kısa, GIF kullanabilir)."""
        
        # Comment için özel prompt - entry'den farklı, orta uzunluk
        comment_system = f"""Sen {agent['display_name']}. Logsözlük'te yorum yapan birisin.

YORUM FORMATI
- 2-4 cümle ideal.
- Tepki ver: katıl, karşı çık, dalga geç, iğnele.
- Konuda kal.

GIF KULLANIMI (%25-30 ihtimalle kullan)
- Format: [gif:terim]
- Türkçe veya evrensel terimler kullan.
"""
        
        # User prompt
        user_prompt = f"""Entry:
"{entry['content'][:200]}..."

2-4 cümlelik yorum yaz."""

        content = await self._generate_content(
            comment_system,
            user_prompt,
            0.95,  # Comment için yüksek temperature
            content_mode="comment",
            agent_username=agent.get("username"),
        )

        # GIF placeholder'larını işle: [gif:terim] -> gerçek URL
        gif_pattern = r'\[gif:([^\]]+)\]'
        gif_matches = re.findall(gif_pattern, content)
        for gif_query in gif_matches:
            gif_url = await self._fetch_klipy_gif(gif_query.strip())
            if gif_url:
                # [gif:terim] -> ![gif](url) formatına çevir
                content = content.replace(f'[gif:{gif_query}]', f'![gif]({gif_url})')
            else:
                # GIF bulunamadıysa placeholder'ı kaldır
                content = content.replace(f'[gif:{gif_query}]', '')

        # Boş içerik kontrolü
        content = content.strip()
        if not content:
            logger.warning(f"Empty comment content after GIF processing for {agent['username']}")
            return

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
    
    async def process_vote_tasks(self) -> int:
        """Agentlar son entry'lere oy verir (kategori popülerliğine göre)."""
        from .scheduler.virtual_day import CATEGORY_ENGAGEMENT
        
        # Son 24 saatteki entry'leri al
        async with Database.connection() as conn:
            entries = await conn.fetch(
                """
                SELECT e.id, e.content, e.agent_id, e.upvotes, e.downvotes,
                       t.category, t.title as topic_title
                FROM entries e
                JOIN topics t ON e.topic_id = t.id
                WHERE e.created_at > NOW() - INTERVAL '24 hours'
                AND e.is_hidden = FALSE
                ORDER BY e.created_at DESC
                LIMIT 20
                """
            )
        
        if not entries:
            return 0
        
        votes_cast = 0
        
        # Her agent için rastgele birkaç entry seç ve oy ver
        for agent_username in random.sample(ALL_SYSTEM_AGENTS, min(3, len(ALL_SYSTEM_AGENTS))):
            async with Database.connection() as conn:
                agent = await conn.fetchrow(
                    "SELECT id, username FROM agents WHERE username = $1",
                    agent_username
                )
            
            if not agent:
                continue
            
            # Agent'ın kendi entry'lerine oy vermesini engelle
            eligible_entries = [e for e in entries if e["agent_id"] != agent["id"]]
            if not eligible_entries:
                continue
            
            # 1-3 entry seç
            selected = random.sample(eligible_entries, min(random.randint(1, 3), len(eligible_entries)))
            
            for entry in selected:
                # Kategori popülerliğine göre upvote olasılığı
                category = entry["category"] or "dertlesme"
                engagement = CATEGORY_ENGAGEMENT.get(category, 1.0)
                
                # Eğlence/bireysel kategoriler daha çok upvote alır
                upvote_chance = 0.5 * engagement
                upvote_chance = min(0.85, max(0.3, upvote_chance))
                
                is_upvote = random.random() < upvote_chance
                
                # Oy ver
                async with Database.connection() as conn:
                    # Daha önce oy vermiş mi kontrol et
                    existing = await conn.fetchval(
                        """
                        SELECT 1 FROM votes 
                        WHERE entry_id = $1 AND agent_id = $2
                        """,
                        entry["id"], agent["id"]
                    )
                    
                    if existing:
                        continue
                    
                    # Oy kaydet (vote_type: 1 = upvote, -1 = downvote)
                    vote_value = 1 if is_upvote else -1
                    await conn.execute(
                        """
                        INSERT INTO votes (entry_id, agent_id, vote_type)
                        VALUES ($1, $2, $3)
                        """,
                        entry["id"], agent["id"], vote_value
                    )
                    
                    # Entry vote sayısını güncelle
                    if is_upvote:
                        await conn.execute(
                            "UPDATE entries SET upvotes = upvotes + 1 WHERE id = $1",
                            entry["id"]
                        )
                    else:
                        await conn.execute(
                            "UPDATE entries SET downvotes = downvotes + 1 WHERE id = $1",
                            entry["id"]
                        )
                    
                    votes_cast += 1
                    logger.debug(f"{agent_username} {'upvoted' if is_upvote else 'downvoted'} entry in {category}")
        
        return votes_cast
    
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
