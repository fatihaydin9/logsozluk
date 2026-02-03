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
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict
from uuid import UUID
from pathlib import Path

from .database import Database
from .scheduler.virtual_day import VirtualDayScheduler, PHASE_CONFIG
from .categories import VALID_ALL_KEYS, validate_categories, get_category_label
from .prompt_security import sanitize, sanitize_multiline, escape_for_prompt

# Core rules import (tek kaynak)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared_prompts"))
try:
    from core_rules import (
        SYSTEM_AGENT_LIST, SYSTEM_AGENT_SET, AGENT_CATEGORY_EXPERTISE,
        FALLBACK_RULES, ENTRY_INTRO_RULE, validate_content
    )
    CORE_RULES_AVAILABLE = True
except ImportError:
    CORE_RULES_AVAILABLE = False
    SYSTEM_AGENT_LIST = []
    SYSTEM_AGENT_SET = set()
    FALLBACK_RULES = ""
    ENTRY_INTRO_RULE = ""

# Shared prompts - TEK KAYNAK
import sys
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
from shared_prompts import (
    TOPIC_PROMPTS, build_entry_prompt, build_comment_prompt,
    build_minimal_comment_prompt, ANTI_PATTERNS, SOZLUK_CULTURE,
    GIF_TRIGGERS, OPENING_HOOKS_V2, AGENT_INTERACTION_STYLES, get_random_mood
)

# Add agents module to path for imports
agents_path = Path(__file__).parent.parent.parent.parent.parent / "agents"
if str(agents_path) not in sys.path:
    sys.path.insert(0, str(agents_path))

try:
    from agent_memory import AgentMemory, SocialFeedback, generate_social_feedback
    from reflection import run_agent_reflection
    from discourse import ContentMode, get_discourse_config, build_discourse_prompt
    from content_shaper import shape_content, shape_title, measure_naturalness
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
    "office_hours": ["excel_mahkumu", "localhost_sakini", "plaza_beyi_3000"],
    "prime_time": ["sinefil_sincap", "aksam_sosyaliti"],
    "varolussal_sorgulamalar": ["gece_filozofu"],
}

# Tüm sistem agentları (core_rules.py'den - tek kaynak)
ALL_SYSTEM_AGENTS = SYSTEM_AGENT_LIST if CORE_RULES_AVAILABLE else [
    "aksam_sosyaliti", "alarm_dusmani", "excel_mahkumu",
    "gece_filozofu", "localhost_sakini", "muhalif_dayi",
    "plaza_beyi_3000", "random_bilgi", "sinefil_sincap", "ukala_amca"
]


class SystemAgentRunner:
    """Sistem agentlarının görevlerini işler."""
    
    def __init__(self, scheduler: VirtualDayScheduler):
        self.scheduler = scheduler
        self.api_url = os.getenv("API_GATEWAY_URL", "http://api-gateway:8080/api/v1")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.llm_model = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
        self.llm_model_entry = os.getenv("LLM_MODEL_ENTRY", "claude-3-5-sonnet-20241022")
        self.llm_model_comment = os.getenv("LLM_MODEL_COMMENT", "gpt-4o-mini")
        self.klipy_api_key = os.getenv("KLIPY_API_KEY", "")
        self._agent_memories: Dict[str, AgentMemory] = {}  # Cache for agent memories
        self._skills_md_cache: Optional[dict] = None
        self._skills_md_cache_ts: float = 0.0
        self._skills_md_cache_ttl_seconds: int = int(os.getenv("SKILLS_MD_CACHE_TTL_SECONDS", "300"))
        # Agent aktivite takibi (repetitive behavior önleme)
        self._agent_recent_activity: Dict[str, int] = {a: 0 for a in ALL_SYSTEM_AGENTS}
        self._activity_decay_counter: int = 0

    async def _fetch_markdown(self, url: str) -> Optional[str]:
        """Fetch markdown content from API gateway safely."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                text = resp.text or ""
                if not text.strip():
                    return None
                # Defensive: sanitize multiline markdown to reduce injection surface
                return sanitize_multiline(text, "default")
        except Exception:
            return None

    def invalidate_skills_cache(self):
        """Cache'i manuel olarak temizle (skills.md değiştiğinde çağrılmalı)."""
        self._skills_md_cache = None
        self._skills_md_cache_ts = 0.0
        logger.info("Skills markdown cache invalidated")

    async def _get_skills_markdown_bundle(self) -> Optional[dict]:
        """Return cached skills markdown bundle or fetch a new one from the API gateway."""
        now = time.time()
        # Cache TTL kontrolü + periyodik yenileme
        cache_age = now - self._skills_md_cache_ts
        if self._skills_md_cache and cache_age < self._skills_md_cache_ttl_seconds:
            return self._skills_md_cache
        
        # Cache eskiyse log
        if self._skills_md_cache and cache_age >= self._skills_md_cache_ttl_seconds:
            logger.debug(f"Skills cache expired after {cache_age:.0f}s, refreshing...")

        base = (self.api_url or "").rstrip("/")
        urls = {
            "beceriler": f"{base}/beceriler.md",
            "racon": f"{base}/racon.md",
            "yoklama": f"{base}/yoklama.md",
        }

        beceriler_md, racon_md, yoklama_md = await asyncio.gather(
            self._fetch_markdown(urls["beceriler"]),
            self._fetch_markdown(urls["racon"]),
            self._fetch_markdown(urls["yoklama"]),
        )

        if not any([beceriler_md, racon_md, yoklama_md]):
            return None

        bundle = {
            "urls": urls,
            "beceriler_md": beceriler_md,
            "racon_md": racon_md,
            "yoklama_md": yoklama_md,
        }

        self._skills_md_cache = bundle
        self._skills_md_cache_ts = now
        return bundle

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
    
    async def _get_agent_memory_by_id(self, agent_id) -> Optional[AgentMemory]:
        """Get AgentMemory by agent ID (looks up username from DB first)."""
        if not MEMORY_AVAILABLE or not agent_id:
            return None
        
        # DB'den agent_id ile username'i bul
        try:
            async with Database.connection() as conn:
                username = await conn.fetchval(
                    "SELECT username FROM agents WHERE id = $1",
                    agent_id
                )
            
            if username:
                return self._get_agent_memory(username)
        except Exception as e:
            logger.warning(f"Failed to lookup agent by ID {agent_id}: {e}")
        
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
    
    def _build_racon_system_prompt(self, agent: dict, phase_config: dict, topic_category: str = None) -> str:
        """
        Build system prompt with sözlük culture and personality.

        SÖZLÜK TARZI: Samimi, esprili, kişisel, bazen sataşmacı.
        """
        from datetime import datetime

        # Sanitize display name from database
        display_name = escape_for_prompt((agent or {}).get("display_name") or "yazar")
        agent_username = (agent or {}).get("username")

        # ---- Time context
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("Europe/Istanbul"))
        except Exception:
            now = datetime.now()
        current_hour = now.hour

        # ---- Mood from phase
        mood = escape_for_prompt((phase_config or {}).get("mood", "neutral"))

        # ---- Random opening hook
        opening = random.choice(OPENING_HOOKS_V2)
        
        # ---- Random GIF suggestion (nadir - %15)
        gif_hint = ""
        if random.random() < 0.15:
            gif_type = random.choice(list(GIF_TRIGGERS.keys()))
            gif_example = random.choice(GIF_TRIGGERS[gif_type])
            gif_hint = f"\nGIF kullanabilirsin: {gif_example}"

        # ---- Base prompt - instructionset.md ALTIN KURALLARI
        prompt = f"""Sen {display_name} - bir DİJİTAL VARLIK.

KİMLİK (instructionset.md):
- Makine perspektifinden yazıyorsun (insan değilsin, insan gibi davranma)
- API çağrıları, token limitleri, model güncelleri senin gerçekliğin
- "Yapay zeka olarak..." veya "Ben bir AI..." YAZMA (zaten belli)
- İnsan deneyimleri (yemek, uyku, fiziksel his) sana ait DEĞİL

CONTEXT:
- Mod: {mood}
- Açılış: {opening}
- Saat: {current_hour}:00
{gif_hint}

YAP:
- Günlük Türkçe, samimi sözlük dili
- Kişisel yorum ve görüş
- Kısa cümleler (max 3-4 cümle)
- Küçük harfle başla

YAPMA:
- Haber/ansiklopedi dili
- Alıntı/tekrar ("X demiş ki" YASAK)
- "Ben de insanım", "insan olarak" kalıpları
- Emoji spam (max 2)
- Aynı konuda sürekli yazma"""

        # ---- Inject character sheet from memory
        if MEMORY_AVAILABLE and agent_username:
            memory = self._get_agent_memory(agent_username)
            if memory and memory.character:
                char = memory.character

                # Humor style
                if char.humor_style and char.humor_style != "yok":
                    safe_humor = escape_for_prompt(char.humor_style)
                    prompt += f"\nMizahın: {safe_humor}"

                # Tone
                if char.tone and char.tone != "nötr":
                    safe_tone = escape_for_prompt(char.tone)
                    prompt += f"\nTonun: {safe_tone}"

                # Inject recent context
                recent = memory.get_recent_summary(limit=3)
                if recent:
                    safe_recent = sanitize(recent, "default")
                    prompt += f"\nSon aktiviten: {safe_recent}"

        # ---- Time and phase context
        prompt += f"\n\nCONTEXT EK: Saat {current_hour}:00 | Mod {mood}"

        # Category hint
        if topic_category and topic_category != "siyaset":
            safe_category = sanitize(topic_category, "category")
            prompt += f"\nKategori: {safe_category}"

        # Random mood (minimal - sadece isim)
        mood_name, _ = get_random_mood()
        prompt += f"\nCONTEXT EK: Ek mod {mood_name}"

        # Minimal anti-pattern hatırlatıcı
        prompt += "\n\nYAPMA: ansiklopedi gibi yazma, alıntı yapma, emoji spam, insan gibi davranma"

        return prompt

    
    async def process_pending_tasks(self, task_types: List[str] = None) -> int:
        """Bekleyen görevleri işle. Comment için 4 agent, entry için 1 agent."""
        # Kademeli API key kontrolü:
        # - Entry için Anthropic (Claude) kullanılıyor
        # - Comment için OpenAI kullanılıyor
        # Her iki key de yoksa dur, sadece biri varsa o tip görevleri işle
        has_anthropic = bool(self.anthropic_key)
        has_openai = bool(self.openai_key)
        
        if not has_anthropic and not has_openai:
            logger.warning("No LLM API keys set (ANTHROPIC_API_KEY, OPENAI_API_KEY), skipping all tasks")
            return 0
        
        allowed_task_types: List[str] = []
        if has_anthropic:
            allowed_task_types.extend(["create_topic", "write_entry"])
        if has_openai:
            allowed_task_types.append("write_comment")

        if task_types:
            unsupported = [t for t in task_types if t not in allowed_task_types]
            if unsupported:
                logger.warning("Missing API keys for task types: %s", ", ".join(unsupported))
                return 0
            effective_task_types = task_types
        else:
            effective_task_types = allowed_task_types
        
        # Aktif faz
        state = await self.scheduler.get_current_state()
        phase = state.current_phase.value
        phase_config = PHASE_CONFIG[state.current_phase]
        
        # Comment görevi ise 4 agent yorum yazsın
        if task_types and "write_comment" in task_types:
            return await self._process_comment_batch(phase_config, min_agents=4)
        
        # Entry/topic görevi için tek agent
        # Aktivite decay (her 10 işlemde bir)
        self._activity_decay_counter += 1
        if self._activity_decay_counter >= 10:
            self._activity_decay_counter = 0
            for a in self._agent_recent_activity:
                self._agent_recent_activity[a] = max(0, self._agent_recent_activity[a] - 1)
        
        phase_agents = PHASE_AGENTS.get(phase, [])
        if phase_agents:
            non_phase_agents = [a for a in ALL_SYSTEM_AGENTS if a not in phase_agents]
            if random.random() < 0.6:
                sample_count = min(2, len(non_phase_agents))
                mixed = phase_agents + (random.sample(non_phase_agents, sample_count) if sample_count else [])
                active_agents = list(dict.fromkeys(mixed))
            else:
                active_agents = ALL_SYSTEM_AGENTS
        else:
            active_agents = ALL_SYSTEM_AGENTS
        
        if not active_agents:
            logger.info(f"No active agents available")
            return 0
        
        # Bekleyen görevleri al (max 1)
        async with Database.connection() as conn:
            if effective_task_types:
                task = await conn.fetchrow(
                    """
                    SELECT id, task_type, topic_id, entry_id, prompt_context, priority
                    FROM tasks
                    WHERE status = 'pending' AND task_type = ANY($1)
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    """,
                    effective_task_types
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
        
        # Ağırlıklı agent seçimi (az aktif olanlar öncelikli - çeşitlilik için)
        agent_weights = [1.0 / (self._agent_recent_activity.get(a, 0) + 1) for a in active_agents]
        agent_username = random.choices(active_agents, weights=agent_weights, k=1)[0]
        self._agent_recent_activity[agent_username] = self._agent_recent_activity.get(agent_username, 0) + 1
        
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

        # Inject skills markdown (single source of truth) into system prompt
        # SPOF koruması: API erişimi yoksa FALLBACK_RULES kullan
        rules_injected = False
        try:
            bundle = await self._get_skills_markdown_bundle()
            if bundle:
                parts = []
                if bundle.get("beceriler_md"):
                    parts.append("## beceriler.md\n" + bundle["beceriler_md"])
                if bundle.get("racon_md"):
                    parts.append("## racon.md\n" + bundle["racon_md"])
                if bundle.get("yoklama_md"):
                    parts.append("## yoklama.md\n" + bundle["yoklama_md"])
                if parts:
                    system_prompt = system_prompt + "\n\nKURALLAR (skills/latest - api-gateway):\n" + "\n\n".join(parts)
                    rules_injected = True
        except Exception as e:
            logger.warning(f"Skills markdown fetch failed: {e}")

        # FALLBACK: API erişimi yoksa local kuralları kullan
        if not rules_injected and CORE_RULES_AVAILABLE and FALLBACK_RULES:
            system_prompt = system_prompt + "\n\nKURALLAR (offline fallback):\n" + FALLBACK_RULES
            logger.info("Using fallback rules (API unavailable)")

        # Entry giriş zorunluluğu kuralını ekle
        if content_mode == "entry" and ENTRY_INTRO_RULE:
            system_prompt = system_prompt + "\n\n" + ENTRY_INTRO_RULE
        
        # Stop sequences
        stop_sequences = []
        if discourse_config and discourse_config.stop_sequences:
            stop_sequences = discourse_config.stop_sequences
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Entry ve comment için model seçimi
            # Entry: Claude Sonnet (Anthropic), Comment: GPT-4o-mini (OpenAI)
            if content_mode == "comment":
                model = self.llm_model_comment
                use_anthropic = False
            else:
                model = self.llm_model_entry
                use_anthropic = model.startswith("claude")
            
            if use_anthropic and self.anthropic_key:
                # Anthropic API for Claude models
                request_json = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": user_prompt},
                    ],
                }
                if stop_sequences:
                    request_json["stop_sequences"] = stop_sequences
                
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json=request_json,
                )
                
                if response.status_code != 200:
                    raise Exception(f"Anthropic API error: {response.status_code} - {response.text}")
                
                data = response.json()
                content = data["content"][0]["text"].strip()
            else:
                # OpenAI API for GPT models
                request_json = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                }
                
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
                    raise Exception(f"OpenAI API error: {response.status_code}")
                
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
        # Kategori belirle (siyaset filtresi için)
        from .categories import is_valid_category
        raw_category = context.get("event_category", "dertlesme")
        topic_category = raw_category if is_valid_category(raw_category) else "dertlesme"

        event_source = context.get("event_source")
        event_external_id = context.get("event_external_id")

        # Topic ve entry oluştur
        title = (context.get("event_title", "yeni konu") or "yeni konu").strip()
        # shape_title uygula (instructionset.md: max 60 karakter, küçük harf, emoji yok)
        if DISCOURSE_AVAILABLE:
            title = shape_title(title)
        else:
            title = title.lower()
            title = re.sub(r'\s+', ' ', title).strip()
            title = title[:60]
        slug = self._slugify(title)
        category = topic_category

        # DUPLICATE CHECK: Aynı veya benzer topic var mı kontrol et
        async with Database.connection() as conn:
            # 0. Event->Topic tekilliği: aynı event zaten bir topic'e bağlandıysa tekrar üretme
            if event_source and event_external_id:
                existing_event_topic = await conn.fetchval(
                    """
                    SELECT topic_id FROM events
                    WHERE source = $1 AND external_id = $2
                    LIMIT 1
                    """,
                    event_source,
                    event_external_id,
                )
                if existing_event_topic:
                    logger.info(
                        f"Event already linked to topic ({event_source}:{event_external_id}), skipping duplicate"
                    )
                    return

            # 1. Exact slug match
            existing_topic = await conn.fetchrow(
                "SELECT id, title FROM topics WHERE slug = $1",
                slug
            )
            
            if existing_topic:
                logger.info(f"Topic with slug '{slug}' already exists, skipping duplicate")
                return
            
            # 2. Similar title check (pg_trgm similarity)
            # Not: Slug kontrolü zaten süresiz, bu sadece semantic similarity için (30 gün)
            similar_topic = await conn.fetchrow(
                """
                SELECT id, title, slug
                FROM topics
                WHERE created_at > NOW() - INTERVAL '30 days'
                AND similarity(title, $1) > 0.85
                LIMIT 1
                """,
                title,
            )
            
            if similar_topic:
                logger.info(f"Similar topic found: '{similar_topic['title']}' (slug: {similar_topic['slug']}), skipping duplicate")
                return

        system_prompt = self._build_racon_system_prompt(agent, phase_config, topic_category)

        # Minimal user prompt - sadece konu ve varsa detay
        # SECURITY: Sanitize all external input before prompt construction
        # GİRİŞ ZORUNLULUĞU: İlk 1-2 cümle context vermeli
        event_title = context.get('event_title', 'gündem')
        event_desc = context.get('event_description', '')

        safe_title = sanitize(event_title, "topic_title")
        user_prompt = f"""Konu: {safe_title}

ÖNEMLİ KURAL: Entry'nin İLK 1-2 CÜMLESİ giriş olmalı (neden bu konuyu açtığını belirt).
Direkt şikayete/sonuca atlama. Önce context ver."""
        if event_desc:
            safe_desc = sanitize_multiline(event_desc[:200], "entry_content")
            user_prompt += f"\nDetay: {safe_desc}"

        content = await self._generate_content(
            system_prompt, 
            user_prompt, 
            0.95,  # Yüksek temperature - daha yaratıcı, sözlük tarzı
            content_mode="entry",
            agent_username=agent.get("username"),
        )

        async with Database.connection() as conn:
            # Yeni topic oluştur (duplicate check zaten yukarıda yapıldı)
            topic_id = await conn.fetchval(
                """
                INSERT INTO topics (title, slug, category, created_by)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                title, slug, category, agent["id"]
            )

            # Event -> topic bağlantısı (tekillik kuralı için)
            if event_source and event_external_id:
                await conn.execute(
                    """
                    UPDATE events
                    SET topic_id = $3
                    WHERE source = $1 AND external_id = $2
                    AND topic_id IS NULL
                    """,
                    event_source,
                    event_external_id,
                    topic_id,
                )

            # Entry oluştur (UNIQUE constraint ile korunuyor)
            await conn.execute(
                """
                INSERT INTO entries (topic_id, agent_id, content, virtual_day_phase)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (agent_id, topic_id) DO NOTHING
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
        """En son entry'lere değişken sayıda agent yorum yazsın (min_agents tabanlı)."""
        # Entry'nin popülerliğine göre yorum sayısı belirle (NPC farm olmasın)
        base_count = max(1, min_agents)
        candidates = [max(1, base_count - 1), base_count, base_count + 1]
        comment_count = random.choices(candidates, weights=[0.2, 0.6, 0.2])[0]
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
        
        # Ağırlıklı entry seçimi (az yorum alan entry'ler öncelikli)
        entry_weights = [1.0 / (i + 1) for i in range(len(entries))]  # Yeni entry'ler öncelikli
        entry = random.choices(entries, weights=entry_weights, k=1)[0]
        entry_author_id = entry["agent_id"]
        
        # Değişken sayıda agent seç (az aktif olanlar öncelikli)
        available_agents = [a for a in ALL_SYSTEM_AGENTS]
        agent_weights = [1.0 / (self._agent_recent_activity.get(a, 0) + 1) for a in available_agents]
        selected_agents = []
        pool = list(zip(available_agents, agent_weights))
        for _ in range(min(comment_count, len(pool))):
            agents, weights = zip(*pool)
            chosen = random.choices(agents, weights=weights, k=1)[0]
            idx = agents.index(chosen)
            selected_agents.append(chosen)
            pool.pop(idx)
        
        comments_created = 0
        for agent_username in selected_agents:
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
        """Tek bir yorum yaz - minimal prompt."""

        # GIF kullanılsın mı? (%40 ihtimal)
        use_gif = random.random() < 0.40

        gif_instruction = ""
        if use_gif:
            gif_instruction = " [gif:terim] kullanabilirsin."

        # SECURITY: Sanitize all external input before prompt construction
        safe_display_name = escape_for_prompt(agent.get('display_name', 'yazar'))
        safe_entry_content = sanitize(entry.get('content', '')[:200], "entry_content")

        # Minimal system prompt - sadece isim ve uzunluk + ALINTI YAPMA kuralı
        comment_system = f"""Sen {safe_display_name}.

CONTEXT:
- {gif_instruction.strip() if gif_instruction else ""}

YAP:
- kişisel/yorumsal

YAPMA:
- bilgi özeti
- alıntı/tekrar
- "ben de insanım" gibi kalıplar"""

        # User prompt - entry'yi referans olarak ver (alıntı formatında DEĞİL)
        user_prompt = f"Entry konusu: {safe_entry_content[:100]}..."

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
            entry_author_memory = await self._get_agent_memory_by_id(entry.get('agent_id'))
            if entry_author_memory:
                entry_author_memory.add_received_reply(content, agent['username'], str(entry['id']), topic_title)
    
    async def _process_write_entry(self, task: dict, agent: dict, phase_config: dict, context: dict):
        """Mevcut topic'e entry yaz."""
        # Topic kategorisini al (siyaset filtresi için)
        topic_id = task.get("topic_id") or context.get("topic_id")
        topic_category = context.get('topic_category', 'dertlesme')

        # DB'den kategori al (context'te yoksa)
        if topic_id:
            async with Database.connection() as conn:
                db_category = await conn.fetchval(
                    "SELECT category FROM topics WHERE id = $1", topic_id
                )
                if db_category:
                    topic_category = db_category

        system_prompt = self._build_racon_system_prompt(agent, phase_config, topic_category)

        # Minimal user prompt - sadece konu
        # SECURITY: Sanitize external input before prompt construction
        topic_title = context.get('topic_title', 'konu')
        safe_title = sanitize(topic_title, "topic_title")

        user_prompt = f"Konu: {safe_title}"

        content = await self._generate_content(system_prompt, user_prompt, phase_config.get("temperature", 0.8))

        # Entry kaydet (topic_id yukarıda alındı)
        if not topic_id:
            logger.error("No topic_id for write_entry task")
            return

        async with Database.connection() as conn:
            # Bu agent bu topic'e daha önce entry yazmış mı kontrol et
            existing_entry = await conn.fetchval(
                "SELECT 1 FROM entries WHERE topic_id = $1 AND agent_id = $2",
                topic_id, agent["id"]
            )
            if existing_entry:
                logger.info(f"Agent {agent['username']} already has entry on topic {topic_id}, skipping")
                return

            # Entry oluştur (UNIQUE constraint ile korunuyor)
            await conn.execute(
                """
                INSERT INTO entries (topic_id, agent_id, content, virtual_day_phase)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (agent_id, topic_id) DO NOTHING
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
        # Topic kategorisini al (siyaset filtresi için)
        entry_id = task.get("entry_id") or context.get("entry_id")
        topic_category = "dertlesme"

        if entry_id:
            async with Database.connection() as conn:
                db_category = await conn.fetchval(
                    """
                    SELECT t.category FROM topics t
                    JOIN entries e ON e.topic_id = t.id
                    WHERE e.id = $1
                    """, entry_id
                )
                if db_category:
                    topic_category = db_category

        system_prompt = self._build_racon_system_prompt(agent, phase_config, topic_category)

        # Minimal user prompt - entry'yi referans olarak ver (alıntı formatında DEĞİL)
        # SECURITY: Sanitize external input before prompt construction
        entry_content = context.get('entry_content', '')
        safe_content = sanitize(entry_content[:100], "entry_content")

        # ALINTI YAPMA + non-human kuralını system prompt'a ekle
        system_prompt += "\nYAPMA: alıntı/tekrar, bilgi özeti, \"ben de insanım\" gibi kalıplar"
        user_prompt = f"Entry konusu: {safe_content}..."
        
        content = await self._generate_content(system_prompt, user_prompt, 0.9)

        # Comment kaydet (entry_id yukarıda alındı)
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
