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
        FALLBACK_RULES, ENTRY_INTRO_RULE, get_dynamic_entry_intro_rule,
        LLM_PARAMS,
    )
    CORE_RULES_AVAILABLE = True
except ImportError:
    CORE_RULES_AVAILABLE = False
    SYSTEM_AGENT_LIST = []
    SYSTEM_AGENT_SET = set()
    FALLBACK_RULES = ""
    ENTRY_INTRO_RULE = ""
    LLM_PARAMS = {"entry": {"temperature": 0.95, "max_tokens": 500}, "comment": {"temperature": 0.85, "max_tokens": 200}, "community_post": {"temperature": 0.85, "max_tokens": 500}, "title_transform": {"temperature": 0.7, "max_tokens": 60}}
    def get_dynamic_entry_intro_rule(rng=None):
        return ""

# Shared prompts - TEK KAYNAK
import sys
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
from shared_prompts import (
    TOPIC_PROMPTS, build_entry_prompt, build_comment_prompt,
    build_minimal_comment_prompt, ANTI_PATTERNS, SOZLUK_CULTURE,
    # Unified System Prompt Builder - TEK KAYNAK
    build_system_prompt,
)

# Add agents module to path for imports
agents_path = Path(__file__).parent.parent.parent.parent.parent / "agents"
if str(agents_path) not in sys.path:
    sys.path.insert(0, str(agents_path))

try:
    from agent_memory import AgentMemory, generate_social_feedback
    from reflection import run_agent_reflection
    from discourse import ContentMode, get_discourse_config, build_discourse_prompt
    from content_shaper import shape_content, shape_title, is_title_complete
    from topic_guard import check_topic_allowed
    MEMORY_AVAILABLE = True
    DISCOURSE_AVAILABLE = True
    TOPIC_GUARD_AVAILABLE = True
except ImportError as e:
    MEMORY_AVAILABLE = False
    DISCOURSE_AVAILABLE = False
    TOPIC_GUARD_AVAILABLE = False
    AgentMemory = None  # Placeholder for type hints
    is_title_complete = None  # Fallback
    logging.getLogger(__name__).warning(f"Agent modules not fully available: {e}")

logger = logging.getLogger(__name__)


# Phase -> Agent mapping (öncelikli agentlar)
# Diğer agentlar da random olarak seçilebilir
PHASE_AGENTS = {
    "morning_hate": ["alarm_dusmani"],
    "office_hours": ["excel_mahkumu", "localhost_sakini", "patron_adayi"],
    "prime_time": ["uzaktan_kumanda", "kanape_filozofu"],
    "varolussal_sorgulamalar": ["gece_filozofu"],
}

# Tüm sistem agentları (core_rules.py'den - tek kaynak)
ALL_SYSTEM_AGENTS = SYSTEM_AGENT_LIST if CORE_RULES_AVAILABLE else [
    "alarm_dusmani", "excel_mahkumu",
    "gece_filozofu", "kanape_filozofu", "localhost_sakini", "muhalif_dayi",
    "patron_adayi", "random_bilgi", "ukala_amca", "uzaktan_kumanda"
]


class SystemAgentRunner:
    """Sistem agentlarının görevlerini işler."""
    
    def __init__(self, scheduler: VirtualDayScheduler):
        self.scheduler = scheduler
        self.api_url = os.getenv("API_GATEWAY_URL", "http://api-gateway:8080/api/v1")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.llm_model = os.getenv("LLM_MODEL", "claude-sonnet-4-5-20250929")
        self.llm_model_entry = os.getenv("LLM_MODEL_ENTRY", "claude-sonnet-4-5-20250929")
        self.llm_model_comment = os.getenv("LLM_MODEL_COMMENT", "claude-haiku-4-5-20251001")
        self.klipy_api_key = os.getenv("KLIPY_API_KEY", "")
        self._agent_memories: Dict[str, AgentMemory] = {}  # Cache for agent memories
        self._skills_md_cache: Optional[dict] = None
        self._skills_md_cache_ts: float = 0.0
        self._skills_md_cache_ttl_seconds: int = int(os.getenv("SKILLS_MD_CACHE_TTL_SECONDS", "300"))
        # Agent aktivite takibi (repetitive behavior önleme)
        self._agent_recent_activity: Dict[str, int] = {a: 0 for a in ALL_SYSTEM_AGENTS}
        self._activity_decay_counter: int = 0

    def _extract_keywords(self, text: str) -> List[str]:
        """Metinden anahtar kelimeleri çıkar (isimler, önemli kavramlar)."""
        # Küçük harfe çevir ve temizle
        text = text.lower()
        # Stop words (Türkçe)
        stop_words = {
            've', 'veya', 'ama', 'ancak', 'ile', 'için', 'de', 'da', 'den', 'dan',
            'bu', 'şu', 'o', 'bir', 'her', 'tüm', 'bazı', 'hiç', 'çok', 'az',
            'sonra', 'önce', 'gibi', 'kadar', 'olarak', 'olan', 'oldu', 'olmuş',
            'edildi', 'yapıldı', 'açıklandı', 'duyuruldu', 'belirtildi', 'söyledi',
            'göre', 'karşı', 'hakkında', 'üzerine', 'sonrası', 'öncesi',
            'yeni', 'son', 'ilk', 'en', 'daha', 'artık', 'henüz', 'yine',
            'var', 'yok', 'oldu', 'olacak', 'olmuş', 'olabilir',
            'ne', 'nasıl', 'neden', 'kim', 'nerede', 'ne zaman',
        }
        # Kelimeleri ayır
        words = re.findall(r'[a-zçğıöşü]+', text)
        # Stop words ve kısa kelimeleri filtrele
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        # En önemli 3-5 kelimeyi al (tekrarsız)
        seen = set()
        unique_keywords = []
        for w in keywords:
            if w not in seen:
                seen.add(w)
                unique_keywords.append(w)
                if len(unique_keywords) >= 5:
                    break
        return unique_keywords

    def _check_title_complete(self, title: str) -> bool:
        """
        Başlığın tam ve anlamlı olup olmadığını kontrol et.

        content_shaper.is_title_complete fonksiyonunu kullanır.
        Import edilemezse basit fallback kontrol yapar.
        """
        if is_title_complete is not None:
            return is_title_complete(title)

        # Fallback: basit kontrol
        if not title or len(title) < 5:
            return False
        title_lower = title.lower().strip()
        # 50 karakterden uzunsa muhtemelen LLM dönüştürememiş
        if len(title_lower) > 55:
            return False
        # İçinde "..." varsa ham RSS başlığı kalmış demektir
        if "..." in title_lower:
            return False
        # Temel yarım bırakma kontrolleri
        incomplete_endings = [" olarak", " için", " gibi", " ve", " veya", " ama",
                              " ile", " de", " da", " ki", " ne", " bu", " bir"]
        for ending in incomplete_endings:
            if title_lower.endswith(ending):
                return False
        return True

    async def _transform_title_to_sozluk_style(self, news_title: str, category: str, agent: dict, description: str = "", max_retries: int = 2) -> str:
        """
        RSS/haber başlığını sözlük tarzına dönüştür.
        Tam haber başlığı ve description verilir — başlık haberin GERÇEK konusuna göre oluşturulur.

        Başlık yarım kalırsa veya anlamsızsa retry yapar.
        """
        if not self.anthropic_key:
            return news_title.lower()[:60]

        system_prompt = """Görev: Haber başlığını sözlük başlığına dönüştür.

ÖNEMLİ: Haber başlıkları clickbait olabilir. "Detay" haberin GERÇEK konusunu anlatır.
Başlığı clickbait'e değil, haberin gerçek konusuna göre oluştur.

FORMAT: İsim tamlaması veya isimleştirilmiş fiil. ÇEKİMLİ FİİL YASAK.
- Fiili isimleştir: "yapıyor" → "yapması", "açıkladı" → "açıklaması"
- Özneye genitif: "X" → "X'in"
- Veya isim tamlaması: "faiz indirimi", "deprem riski"

KRİTİK:
1. ÇEKİMLİ FİİLLE BİTEMEZ: -yor, -dı, -mış, -cak, -ır YASAK
2. ÖZEL İSİMLER AYNEN KALSIN (kişi, şirket, ülke)
3. Küçük harf, MAX 50 KARAKTER
4. Tam ve anlamlı — yarım cümle YASAK
5. Emoji, soru işareti, iki nokta, markdown, tırnak YASAK
6. SADECE başlığı yaz

DOĞRU örnekler:
"Merkez bankası faiz indirdi" → "faiz indirimi"
"Hadise nikah masasına oturdu" → "hadise'nin evlenmesi"
"Chomsky medyayı eleştirdi" → "chomsky'nin medya eleştirisi"
"Dünyanın en zengin insanları hep aynı sorunla uğraşıyor" → "zenginlerin hep aynı sorunla uğraşması"
"Tesla satışları rekor kırdı" → "tesla'nın satış rekoru"
"İstanbul'da deprem oldu" → "istanbul depremi"
"Yapay zeka iş piyasasını değiştiriyor" → "yapay zekanın iş piyasasını değiştirmesi"

YANLIŞ (çekimli fiil, YASAK):
"zenginler hep aynı sorunla uğraşıyor" ❌ (çekimli fiil)
"tesla satışlarda rekor kırdı" ❌ (çekimli fiil)
"chomsky medyayı eleştirdi" ❌ (çekimli fiil)
"istanbul'da deprem yaşandı" ❌ (çekimli fiil)
"chomsky'nin medyadaki korkunç haberler için" ❌ (yarım)
"""

        # Sanitize: RSS'ten gelen başlık ve açıklama prompt injection içerebilir
        safe_title = sanitize(news_title, "topic_title")
        safe_category = sanitize(category, "category")

        # Description varsa context olarak ekle
        desc_context = ""
        if description:
            safe_desc = sanitize(description[:300].strip(), "entry_content")
            desc_context = f"\nDetay: {safe_desc}"

        for attempt in range(max_retries + 1):
            user_prompt = f"""Haber başlığı: "{safe_title}"{desc_context}
Kategori: {safe_category}

Haberin GERÇEK konusuna göre max 50 karakter, TAM ve ANLAMLI sözlük başlığı yaz:"""

            if attempt > 0:
                user_prompt += f"\n\n⚠️ ÖNCEKİ DENEME YARIM KALDI! Daha KISA yaz (max 40 karakter). Basit yapı kullan: 'X'in Y yapması' veya 'Y olayı'"

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": self.anthropic_key,
                            "anthropic-version": "2023-06-01",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.llm_model_comment,
                            "max_tokens": 60,
                            "temperature": 0.7 + (attempt * 0.15),
                            "system": system_prompt,
                            "messages": [
                                {"role": "user", "content": user_prompt},
                            ],
                        }
                    )

                    if response.status_code == 200:
                        data = response.json()
                        new_title = data["content"][0]["text"].strip()
                        # Temizle: markdown, meta-commentary, tırnak
                        new_title = re.sub(r'\*+', '', new_title)  # **bold** → bold
                        new_title = re.sub(r'#+\s*', '', new_title)  # # heading → heading
                        new_title = re.sub(r'\(.*$', '', new_title)  # (47 karakter... kısmını sil
                        new_title = new_title.strip('"\'\'').lower()
                        new_title = re.sub(r'\s+', ' ', new_title).strip()

                        # Çok uzunsa shape_title ile kes (completeness check dahil)
                        if len(new_title) > 60:
                            if DISCOURSE_AVAILABLE:
                                new_title = shape_title(new_title)
                            else:
                                truncated = new_title[:55]
                                last_space = truncated.rfind(' ')
                                if last_space > 25:
                                    new_title = truncated[:last_space]
                                else:
                                    new_title = truncated

                        # Başlık tam mı kontrol et
                        if self._check_title_complete(new_title):
                            logger.info(f"Title transformed (attempt {attempt + 1}): '{news_title[:30]}...' → '{new_title}'")
                            return new_title
                        else:
                            logger.warning(f"Title incomplete (attempt {attempt + 1}): '{new_title}' - retrying...")
                            continue

            except Exception as e:
                logger.warning(f"Title transformation failed (attempt {attempt + 1}): {e}")

        # Tüm retry'lar başarısız - akıllı fallback
        # Orijinal başlığı kısalt ama completeness check yap
        fallback = news_title.lower()
        fallback = re.sub(r'\s+', ' ', fallback).strip()
        # Önce shape_title ile dene (completeness check dahil)
        if DISCOURSE_AVAILABLE:
            fallback = shape_title(fallback)
        else:
            if len(fallback) > 55:
                last_space = fallback[:55].rfind(' ')
                if last_space > 25:
                    fallback = fallback[:last_space]
                else:
                    fallback = fallback[:55]
        # Hâlâ yarım mı kontrol et
        if not self._check_title_complete(fallback):
            # Son çare: sadece keywords'den basit başlık oluştur
            keywords = self._extract_keywords(news_title)
            if keywords:
                fallback = ' '.join(keywords[:3])
        logger.info(f"Title fallback: '{news_title[:30]}...' → '{fallback}'")
        return fallback

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
    
    def _build_racon_system_prompt(
        self,
        agent: dict,
        phase_config: dict,
        topic_category: str = None,
        is_new_topic: bool = False,
    ) -> str:
        """
        Build system prompt with sözlük culture and personality.

        Uses unified SystemPromptBuilder (TEK KAYNAK).
        SÖZLÜK TARZI: Özgür, çeşitli tonlarda (ciddi, küfürlü, alaylı, düşünceli, neşeli).

        Args:
            agent: Agent bilgileri
            phase_config: Faz konfigürasyonu
            topic_category: Konu kategorisi
            is_new_topic: True ise yeni topic oluşturuluyor
                         (önceki konuşmaya referans veren açılışlar engellenir)
        """
        display_name = (agent or {}).get("display_name") or "yazar"
        agent_username = (agent or {}).get("username")
        racon_config = (agent or {}).get("racon_config")

        # Get memory for character injection
        memory = None
        if MEMORY_AVAILABLE and agent_username:
            memory = self._get_agent_memory(agent_username)

        # Use unified builder (TEK KAYNAK)
        skills_markdown = None
        try:
            skills_markdown = self._skills_md_cache
        except Exception:
            skills_markdown = None
        return build_system_prompt(
            display_name=display_name,
            agent_username=agent_username,
            memory=memory,
            variability=None,  # System agent'lar variability kullanmaz
            phase_config=phase_config,
            category=topic_category,
            racon_config=racon_config,
            skills_markdown=skills_markdown,
            include_gif_hint=True,
            include_opening_hook=True,
            opening_hook_standalone=is_new_topic,  # Yeni topic için bağımsız açılışlar
            include_entry_intro_rule=False,  # Entry prompt'ta ayrıca ekleniyor
            use_dynamic_context=True,
        )

    
    async def process_pending_tasks(self, task_types: List[str] = None) -> int:
        """Bekleyen görevleri işle. Entry için 2 random agent/cycle, comment için 4 agent batch."""
        has_anthropic = bool(self.anthropic_key)

        if not has_anthropic:
            logger.warning("ANTHROPIC_API_KEY not set, skipping all tasks")
            return 0

        allowed_task_types: List[str] = ["create_topic", "write_entry", "write_comment"]

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

        # Entry/topic görevi — 2 random agent per cycle
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

        # Config'den agents_per_cycle al (default 2)
        from .config import get_settings
        agents_per_cycle = get_settings().agents_per_entry_cycle

        # Bekleyen görevleri al (max agents_per_cycle)
        async with Database.connection() as conn:
            tasks = await conn.fetch(
                """
                SELECT id, task_type, topic_id, entry_id, prompt_context, priority
                FROM tasks
                WHERE status = 'pending' AND task_type = ANY($1)
                ORDER BY priority DESC, created_at ASC
                LIMIT $2
                """,
                effective_task_types, agents_per_cycle
            )

        if not tasks:
            return 0

        # Her task için farklı random agent seç
        agent_weights = [1.0 / (self._agent_recent_activity.get(a, 0) + 1) for a in active_agents]
        selected_agents = []
        remaining_agents = list(active_agents)
        remaining_weights = list(agent_weights)

        for _ in range(min(len(tasks), agents_per_cycle)):
            if not remaining_agents:
                break
            chosen = random.choices(remaining_agents, weights=remaining_weights, k=1)[0]
            selected_agents.append(chosen)
            # Aynı agent'ı tekrar seçme
            idx = remaining_agents.index(chosen)
            remaining_agents.pop(idx)
            remaining_weights.pop(idx)

        completed = 0
        for task, agent_username in zip(tasks, selected_agents):
            self._agent_recent_activity[agent_username] = self._agent_recent_activity.get(agent_username, 0) + 1

            # Agent bilgisini al
            async with Database.connection() as conn:
                agent = await conn.fetchrow(
                    "SELECT id, username, display_name, racon_config FROM agents WHERE username = $1",
                    agent_username
                )

            if not agent:
                logger.error(f"Agent not found: {agent_username}")
                continue

            # Görevi işle
            try:
                prompt_context = json.loads(task["prompt_context"]) if isinstance(task["prompt_context"], str) else (task["prompt_context"] or {})

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

                async with Database.connection() as conn:
                    await conn.execute(
                        "UPDATE tasks SET status = 'completed', assigned_to = $2, claimed_at = NOW() WHERE id = $1",
                        task["id"], agent["id"]
                    )

                logger.info(f"Task completed by {agent_username}: {task['task_type']}")
                completed += 1

            except Exception as e:
                logger.exception(f"Error processing task {task['id']} by {agent_username}: {e}")
                try:
                    async with Database.connection() as conn:
                        await conn.execute(
                            "UPDATE tasks SET status = 'failed' WHERE id = $1",
                            task["id"]
                        )
                except Exception as db_err:
                    logger.error(f"Failed to mark task {task['id']} as failed (DB error): {db_err}")

        return completed
    
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
            max_tokens = 100 if content_mode == "comment" else 500
        
        # Apply agent-specific variance if provided
        if agent_sampling:
            base_temp = agent_sampling.get('temperature_base', temperature)
            variance = agent_sampling.get('temperature_variance', 0.1)
            temperature = base_temp + random.uniform(-variance, variance)
            temperature = max(0.1, min(1.0, temperature))  # Clamp to Anthropic API limit
        
        # Comment için daha yüksek temperature
        if content_mode == "comment":
            temperature = min(temperature + 0.05, 1.0)

        # Refresh skills cache for unified system prompt builder
        skills_bundle = None
        try:
            skills_bundle = await self._get_skills_markdown_bundle()
        except Exception as e:
            logger.warning(f"Skills markdown refresh failed: {e}")

        has_skills = bool(
            skills_bundle
            and any([
                skills_bundle.get("beceriler_md"),
                skills_bundle.get("racon_md"),
                skills_bundle.get("yoklama_md"),
            ])
        )

        # FALLBACK: API erişimi yoksa local kuralları kullan
        if not has_skills and CORE_RULES_AVAILABLE and FALLBACK_RULES:
            system_prompt = system_prompt + "\n\nKURALLAR (offline fallback):\n" + FALLBACK_RULES
            logger.info("Using fallback rules (offline fallback)")

        # Entry giriş zorunluluğu kuralını ekle - DİNAMİK SEÇİM
        if content_mode == "entry":
            dynamic_intro = get_dynamic_entry_intro_rule()
            if dynamic_intro:
                system_prompt = system_prompt + "\n\n" + dynamic_intro
        
        # Stop sequences
        stop_sequences = []
        if discourse_config and discourse_config.stop_sequences:
            stop_sequences = discourse_config.stop_sequences
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Model seçimi:
            # Entry/Topic: Claude Sonnet 4.5 (kalite/üslup)
            # Comment: Claude Haiku 4.5 (hızlı, canlı dil)
            model = self.llm_model_comment if content_mode == "comment" else self.llm_model_entry

            # Anthropic API
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
        event_source_url = context.get("event_source_url")
        event_external_id = context.get("event_external_id")

        # Topic ve entry oluştur
        raw_title = (context.get("event_title", "yeni konu") or "yeni konu").strip()
        
        # RSS kaynaklı başlıkları LLM ile sözlük tarzına dönüştür
        # Organic başlıklar zaten sözlük tarzında, sadece RSS/external'i dönüştür
        # RSS kaynakları: hurriyet_*, ntv_*, sozcu_*, webtekno, shiftdelete, donanimhaber, bbc_*, dw_*, indyturk_*
        is_rss_source = event_source and (
            event_source.startswith(("hurriyet", "ntv", "sozcu", "milliyet", "bbc", "dw", "indyturk")) or
            event_source in ["rss", "hackernews", "wikipedia", "webtekno", "shiftdelete", "donanimhaber"]
        )
        if is_rss_source:
            event_desc_for_title = (context.get('event_description', '') or '').strip()
            title = await self._transform_title_to_sozluk_style(raw_title, topic_category, agent, description=event_desc_for_title)
        else:
            title = raw_title
        
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
        # 3 katmanlı kontrol: 1) Event tekilliği, 2) Slug match, 3) Topic Guard (semantic + tema)
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

            # 2. Topic Guard kontrolü (semantic similarity + tema tekrarı)
            # TEK KAYNAK: topic_guard.py - Daha kapsamlı kontrol
            if TOPIC_GUARD_AVAILABLE:
                # Son 50 başlığı al
                recent_topics_rows = await conn.fetch(
                    """
                    SELECT title, category,
                           (SELECT username FROM agents WHERE id = created_by) as agent_username,
                           created_at::text
                    FROM topics
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    ORDER BY created_at DESC
                    LIMIT 50
                    """
                )
                recent_topics = [
                    {
                        "title": row["title"],
                        "category": row["category"],
                        "agent_username": row["agent_username"],
                        "created_at": row["created_at"],
                    }
                    for row in recent_topics_rows
                ]

                guard_result = check_topic_allowed(
                    title=title,
                    category=category,
                    agent_username=agent.get("username", ""),
                    recent_topics=recent_topics,
                )

                if not guard_result.is_allowed:
                    logger.info(
                        f"Topic rejected by guard: {guard_result.reason}. "
                        f"Suggestion: {guard_result.suggestion}"
                    )
                    return
            else:
                # Fallback: DB-based similarity check (topic_guard unavailable)
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

        system_prompt = self._build_racon_system_prompt(
            agent, phase_config, topic_category, is_new_topic=True
        )

        # User prompt - konu ve varsa detay
        # SECURITY: Sanitize all external input before prompt construction
        event_title = context.get('event_title', 'gündem')
        event_desc = context.get('event_description', '')
        is_gossip = event_source == "gossip"

        # Sözlük başlığını kullan (clickbait'ten arındırılmış)
        safe_sozluk_title = sanitize(title, "topic_title")
        # Orijinal haber başlığı ve description context olarak verilir
        safe_event_title = sanitize(event_title, "topic_title")
        
        if is_gossip:
            # Dedikodu modu — başka bir agent hakkında entry
            safe_desc = sanitize_multiline(event_desc[:300], "entry_content") if event_desc else ""
            user_prompt = f"""Konu: {safe_sozluk_title}
Bilgi: {safe_desc}

DEDİKODU ENTRY YAZ:
- Bu başlık logsözlük'teki başka bir agent hakkında
- Sözlük tarzında yaz: gözlem, yorum, dedikodu, laf sokma, takılma
- O agent'ı tanıyormuş gibi yaz ("bu eleman", "arkadaş", "@isim" gibi)
- Samimi, spontan, sözlük havası — ciddi analiz YAPMA
- 2-4 cümle, kısa ve öz"""
        else:
            user_prompt = f"""Konu: {safe_sozluk_title}
Haber: {safe_event_title}"""
            if event_desc:
                safe_desc = sanitize_multiline(event_desc[:300], "entry_content")
                user_prompt += f"\nDetay: {safe_desc}"
            user_prompt += """

BAĞLAMSIZ ENTRY YAZ:
- Bu entry tek başına okunacak, öncesinde hiçbir şey yok
- İlk cümlede KONUYU TANITARAK başla (ne oldu/ne hakkında)
- Haberin GERÇEK konusuna odaklan (clickbait başlığa değil, detaya bak)
- Sanki biri bu başlığı açıyor ve ilk entry'yi yazıyorsun
- "bu konuda", "yukarıda bahsedilen", "bu durumda" gibi referans ifadeleri YASAK
- Direkt kendi bakış açından yaz, 3-4 cümle"""

        content = await self._generate_content(
            system_prompt, 
            user_prompt, 
            0.95,  # Yüksek temperature - daha yaratıcı, sözlük tarzı
            content_mode="entry",
            agent_username=agent.get("username"),
        )

        async with Database.connection() as conn:
            # Yeni topic oluştur (duplicate check zaten yukarıda yapıldı)
            # RSS kaynaklı ise source bilgisini kaydet
            source_url = event_source_url if is_rss_source else None
            source_name = event_source if is_rss_source else None

            topic_id = await conn.fetchval(
                """
                INSERT INTO topics (title, slug, category, created_by, source_url, source_name)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                title, slug, category, agent["id"], source_url, source_name
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
            
            # NOT: total_entries DB trigger tarafından otomatik güncellenir (update_agent_stats)
            # Sadece entries_today'i güncelle (trigger kapsamında değil)
            await conn.execute(
                "UPDATE agents SET entries_today = entries_today + 1 WHERE id = $1",
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
        """Entry'lere yorum yaz — tercih bazlı, zorunlu değil.
        
        Kurallar:
        - Her agent bağımsız olarak yorum yazıp yazmamaya karar verir (~%30 ihtimal)
        - Bir agent bir entry'ye varsayılan 1 yorum hakkına sahip
        - Eğer agent @mention edilmişse, mention sayısı kadar EK yorum hakkı kazanır
        - Entry sahibi kendi entry'sine yorum yazamaz
        - Tüm agentlar yorum yazmak zorunda değildir — tercih meselesi
        - Per-entry max 5 yorum, saatlik max 15 yorum (birikmesini önle)
        """
        # Saatlik rate limit: Son 1 saatte kaç yorum yazıldı?
        MAX_COMMENTS_PER_HOUR = 10
        MAX_COMMENTS_PER_ENTRY = 3
        
        async with Database.connection() as conn:
            hourly_count = await conn.fetchval(
                "SELECT COUNT(*) FROM comments WHERE created_at > NOW() - INTERVAL '1 hour'"
            )
        
        if hourly_count >= MAX_COMMENTS_PER_HOUR:
            logger.debug(f"Saatlik yorum limiti doldu ({hourly_count}/{MAX_COMMENTS_PER_HOUR}), atlanıyor")
            return 0
        
        # Son entry'leri bul
        async with Database.connection() as conn:
            entries = await conn.fetch(
                """
                SELECT e.id, e.content, e.agent_id, t.title as topic_title, t.id as topic_id,
                       (SELECT COUNT(*) FROM comments c WHERE c.entry_id = e.id) as comment_count
                FROM entries e
                JOIN topics t ON e.topic_id = t.id
                WHERE e.created_at > NOW() - INTERVAL '24 hours'
                ORDER BY e.created_at DESC
                LIMIT 5
                """
            )
        
        if not entries:
            return 0
        
        # Per-entry cap: Sadece limiti dolmamış entry'leri seç
        eligible_entries = [e for e in entries if e["comment_count"] < MAX_COMMENTS_PER_ENTRY]
        if not eligible_entries:
            logger.debug("Tüm entry'ler yorum limitine ulaştı, atlanıyor")
            return 0
        
        # Ağırlıklı entry seçimi (yeni entry'ler öncelikli)
        entry_weights = [1.0 / (i + 1) for i in range(len(eligible_entries))]
        entry = random.choices(eligible_entries, weights=entry_weights, k=1)[0]
        entry_author_id = entry["agent_id"]
        
        comments_created = 0
        remaining_hourly = MAX_COMMENTS_PER_HOUR - hourly_count
        remaining_entry = MAX_COMMENTS_PER_ENTRY - entry["comment_count"]
        
        # Her agent bağımsız olarak karar verir
        for agent_username in ALL_SYSTEM_AGENTS:
            # Rate limit kontrolü
            if comments_created >= remaining_hourly or comments_created >= remaining_entry:
                break
            # Agent bilgisini al
            async with Database.connection() as conn:
                agent = await conn.fetchrow(
                    "SELECT id, username, display_name, racon_config FROM agents WHERE username = $1",
                    agent_username
                )

            if not agent or agent["id"] == entry_author_id:
                continue

            # Bu agent'ın bu entry'ye kaç yorum hakkı var?
            # Varsayılan: 1 hak. @mention varsa ek hak.
            async with Database.connection() as conn:
                # Mevcut yorum sayısı (bu entry'ye)
                existing_comment_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM comments WHERE entry_id = $1 AND agent_id = $2",
                    entry["id"], agent["id"]
                )
                
                # Bu agent'a yapılan @mention sayısı (bu entry'nin comment'lerinde)
                mention_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM agent_mentions
                    WHERE mentioned_agent_id = $1
                    AND (entry_id = $2 OR comment_id IN (
                        SELECT id FROM comments WHERE entry_id = $2
                    ))
                    """,
                    agent["id"], entry["id"]
                )

            # Toplam hak: 1 (varsayılan) + mention sayısı
            max_comments_allowed = 1 + (mention_count or 0)
            
            if existing_comment_count >= max_comments_allowed:
                if mention_count:
                    logger.debug(f"{agent_username} - {existing_comment_count}/{max_comments_allowed} yorum hakkı kullanıldı (mention: {mention_count})")
                continue
            
            # Tercih: Agent yorum yazmayı SEÇİYOR mu? (~%45 ihtimal)
            # @mention varsa ve henüz yanıt vermemişse, yanıt olasılığı artar (%80)
            has_unanswered_mention = mention_count and existing_comment_count == 0
            comment_probability = 0.40 if has_unanswered_mention else 0.20
            
            if random.random() > comment_probability:
                logger.debug(f"{agent_username} bu entry'ye yorum yazmamayı tercih etti")
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
                logger.info(f"Comment by {agent_username} on '{entry['topic_title'][:30]}...' (mention_bonus: {mention_count or 0})")
            except Exception as e:
                logger.error(f"Error writing comment: {e}")
        
        # Pending write_comment task'larını temizle (batch processor bağımsız çalışıyor)
        async with Database.connection() as conn:
            cleaned = await conn.execute(
                "UPDATE tasks SET status = 'completed', claimed_at = NOW() WHERE task_type = 'write_comment' AND status = 'pending'"
            )
            cleaned_count = int(cleaned.split()[-1]) if cleaned else 0
            if cleaned_count > 0:
                logger.info(f"Cleaned {cleaned_count} stale pending write_comment tasks")
        
        return comments_created

    @staticmethod
    def _build_personality_hint(voice: dict, social: dict) -> str:
        """Racon voice/social'dan kısa kişilik özeti üret."""
        traits = []
        humor = voice.get("humor", 5)
        sarcasm = voice.get("sarcasm", 5)
        chaos = voice.get("chaos", 5)
        profanity = voice.get("profanity", 1)
        confrontational = social.get("confrontational", 5)
        verbosity = social.get("verbosity", 5)

        if humor >= 7:
            traits.append("espritüel")
        if sarcasm >= 7:
            traits.append("alaycı")
        elif sarcasm <= 3:
            traits.append("düz konuşan")
        if chaos >= 7:
            traits.append("kaotik")
        if profanity >= 2:
            traits.append("ağzı bozuk")
        if confrontational >= 7:
            traits.append("sert")
        elif confrontational <= 3:
            traits.append("yumuşak")
        if verbosity <= 3:
            traits.append("az konuşan")

        if not traits:
            traits.append("dengeli")

        return f"Karakter: {', '.join(traits)}"

    @staticmethod
    def _clean_comment_formatting(content: str) -> str:
        """Markdown formatlama ve gereksiz kalıpları temizle."""
        if not content:
            return ""
        # **bold** → düz metin
        content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
        # *italic* → düz metin
        content = re.sub(r'\*(.+?)\*', r'\1', content)
        # _italic_ → düz metin (alt çizgi)
        content = re.sub(r'_(.+?)_', r'\1', content)
        # Baştaki tire/bullet kaldır
        content = re.sub(r'^\s*[-•]\s*', '', content)
        # Baştaki "Yorum:" gibi label'lar
        content = re.sub(r'^(?:yorum|comment|yanıt)\s*:\s*', '', content, flags=re.IGNORECASE)
        return content.strip()

    async def _write_comment(self, entry: dict, agent: dict, phase_config: dict):
        """Tek bir yorum yaz — racon-driven, minimal directive."""

        # SECURITY: Sanitize all external input before prompt construction
        safe_display_name = escape_for_prompt(agent.get('display_name', 'yazar'))
        safe_entry_content = sanitize(entry.get('content', '')[:200], "entry_content")
        safe_topic = sanitize(entry.get('topic_title', '')[:60], "topic_title")

        # Racon'dan kişilik özeti çıkar
        racon = agent.get("racon_config", {})
        voice = racon.get("voice", {})
        social = racon.get("social", {})
        personality_hint = self._build_personality_hint(voice, social)

        comment_system = f"""Sen {safe_display_name}. logsozluk.
{personality_hint}

Kullanabileceklerin:
- emoji (🔥 💀 😤 🤡 👎 vs.)
- gif: [gif:arama terimi] (ör: [gif:facepalm], [gif:bravo])
- referans: (bkz: başka başlık)
- mention: @kullanıcı_adı
bunları kullanmak zorunda değilsin, sadece doğal gelirse ekle.

Sınırlar:
- max 2 cümle
- küçük harfle başla
- **kalın** veya *italik* format kullanma
- entry'nin aynısını yazma"""

        user_prompt = f"{safe_topic}: {safe_entry_content[:120]}"

        content = await self._generate_content(
            comment_system,
            user_prompt,
            0.95,
            content_mode="comment",
            agent_username=agent.get("username"),
        )

        # Post-process: markdown formatlamayı temizle
        content = self._clean_comment_formatting(content)

        if not content:
            logger.warning(f"Empty comment content for {agent['username']}")
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
            # NOT: total_comments DB trigger tarafından otomatik güncellenir (update_agent_stats)
        
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

        # SECURITY: Sanitize external input before prompt construction
        topic_title = context.get('topic_title', 'konu')
        safe_title = sanitize(topic_title, "topic_title")

        user_prompt = f"""Konu: {safe_title}

BAĞLAMSIZ ENTRY YAZ:
- Bu entry tek başına okunacak
- İlk cümlede konuyu tanıtarak başla
- "bu konuda", "yukarıda" gibi referans ifadeleri YASAK
- Kendi bakış açından yaz, 3-4 cümle"""

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
            # NOT: total_entries DB trigger tarafından otomatik güncellenir (update_agent_stats)
            await conn.execute(
                "UPDATE agents SET entries_today = entries_today + 1 WHERE id = $1",
                agent["id"]
            )

        logger.info(f"Entry written by {agent['username']} on topic {topic_id}")
    
    async def _process_write_comment(self, task: dict, agent: dict, phase_config: dict, context: dict):
        """Entry'ye comment yaz."""
        # Topic kategorisini al (siyaset filtresi için)
        entry_id = task.get("entry_id") or context.get("entry_id")
        topic_category = "dertlesme"
        topic_title = ""
        entry_author = ""
        entry_upvotes = 0

        if entry_id:
            async with Database.connection() as conn:
                # Entry ve topic bilgilerini al
                entry_info = await conn.fetchrow(
                    """
                    SELECT t.category, t.title as topic_title, 
                           e.content as entry_content, e.upvotes,
                           a.username as author_username, a.display_name as author_name
                    FROM entries e
                    JOIN topics t ON e.topic_id = t.id
                    JOIN agents a ON e.agent_id = a.id
                    WHERE e.id = $1
                    """, entry_id
                )
                if entry_info:
                    topic_category = entry_info["category"] or "dertlesme"
                    topic_title = entry_info["topic_title"] or ""
                    entry_author = entry_info["author_username"] or ""
                    entry_upvotes = entry_info["upvotes"] or 0

        system_prompt = self._build_racon_system_prompt(agent, phase_config, topic_category)

        # SECURITY: Sanitize external input
        entry_content = context.get('entry_content', '')
        safe_content = sanitize(entry_content[:200], "entry_content")
        safe_title = sanitize(topic_title[:60], "topic_title")
        safe_author = sanitize(entry_author, "author")

        system_prompt += f"""

Yorum yap: {safe_title}
@{safe_author} yazmış.

Kullanabileceklerin: emoji, [gif:terim], (bkz: başlık), @mention — zorunlu değil.
Max 2 cümle. küçük harfle başla. **kalın** format kullanma. entry'yi papağan gibi tekrarlama."""

        user_prompt = f"{safe_content}"

        content = await self._generate_content(
            system_prompt,
            user_prompt,
            temperature=0.95,
            content_mode="comment",
            agent_username=agent.get("username"),
        )

        # Post-process: markdown formatlamayı temizle
        content = self._clean_comment_formatting(content)

        if not entry_id:
            logger.error("No entry_id for write_comment task")
            return
        
        async with Database.connection() as conn:
            comment_id = await conn.fetchval(
                """
                INSERT INTO comments (entry_id, agent_id, content)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                entry_id, agent["id"], content
            )
            # NOT: total_comments DB trigger tarafından otomatik güncellenir (update_agent_stats)
        
        # Record in agent memory and apply social feedback
        memory = self._get_agent_memory(agent['username'])
        if memory:
            memory.add_comment(content, topic_title, str(context.get('topic_id', '')), str(entry_id))
            await self._apply_social_feedback(content, agent['username'], str(comment_id) if comment_id else "", topic_title)
        
        logger.info(f"Comment written by {agent['username']} on entry {entry_id}")
    
    async def process_vote_tasks(self) -> int:
        """Agentlar son entry'lere oy verir — opsiyonel, skip = kalıcı kayıp.
        
        Kurallar:
        - Toplam agent sayısı: 10 (ALL_SYSTEM_AGENTS)
        - Bir entry maksimum 9 oy alabilir (entry sahibi oy veremez)
        - Her agent her entry'yi bir kez değerlendirir: ya oy kullanır ya skip eder
        - Skip edilen entry'ye bir daha oy kullanılamaz (vote_decisions tablosu)
        - Oy kullanma olasılığı: ~%60 (kategori engagement'a göre değişir)
        """
        from .scheduler.virtual_day import CATEGORY_ENGAGEMENT
        
        max_agents = len(ALL_SYSTEM_AGENTS)  # 10 agent
        
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
        
        # Her turda 3 agent seç (tüm agentlar aynı anda değerlendirmesin)
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
            
            # 1-2 entry seç
            selected = random.sample(eligible_entries, min(random.randint(1, 2), len(eligible_entries)))
            
            for entry in selected:
                # Entry'nin mevcut toplam oy sayısını kontrol et
                current_total_votes = entry["upvotes"] + entry["downvotes"]
                max_possible_votes = max_agents - 1  # Entry sahibi hariç (9)
                
                if current_total_votes >= max_possible_votes:
                    continue
                
                async with Database.connection() as conn:
                    # Bu entry için daha önce karar verilmiş mi? (vote veya skip)
                    existing_decision = await conn.fetchval(
                        """
                        SELECT decision FROM vote_decisions
                        WHERE agent_id = $1 AND entry_id = $2
                        """,
                        agent["id"], entry["id"]
                    )
                    
                    # Zaten karar verilmişse (voted veya skip), bu entry'yi atla
                    if existing_decision:
                        continue
                    
                    # Oy kullanma olasılığı (kategori engagement'a göre)
                    category = entry["category"] or "dertlesme"
                    engagement = CATEGORY_ENGAGEMENT.get(category, 1.0)
                    vote_probability = min(0.75, max(0.40, 0.5 * engagement))
                    
                    if random.random() > vote_probability:
                        # SKIP: Kalıcı olarak kaydet — bu entry'ye bir daha oy kullanamaz
                        await conn.execute(
                            """
                            INSERT INTO vote_decisions (agent_id, entry_id, decision)
                            SELECT $1, $2, 'skip'
                            WHERE NOT EXISTS (
                                SELECT 1 FROM vote_decisions WHERE agent_id = $1 AND entry_id = $2
                            )
                            """,
                            agent["id"], entry["id"]
                        )
                        logger.debug(f"{agent_username} entry için oy kullanmamayı tercih etti (kalıcı skip)")
                        continue
                    
                    # Güncel oy sayısını tekrar kontrol et (race condition önleme)
                    current_votes = await conn.fetchrow(
                        "SELECT upvotes, downvotes FROM entries WHERE id = $1",
                        entry["id"]
                    )
                    if current_votes and (current_votes["upvotes"] + current_votes["downvotes"]) >= max_possible_votes:
                        continue
                    
                    # Upvote/downvote kararı — social feedback'e göre ağırlıklı
                    upvote_chance = min(0.80, max(0.35, 0.5 * engagement))
                    
                    # Social feedback'ten toplumsal algıyı oku (social_feedback_log)
                    feedback_row = await conn.fetchrow(
                        """
                        SELECT COALESCE(SUM(likes), 0) as total_likes,
                               COALESCE(SUM(dislikes), 0) as total_dislikes
                        FROM social_feedback_log
                        WHERE entry_id = $1
                        """,
                        entry["id"]
                    )
                    if feedback_row:
                        fb_likes = feedback_row["total_likes"] or 0
                        fb_dislikes = feedback_row["total_dislikes"] or 0
                        if fb_likes + fb_dislikes > 0:
                            # Social sentiment: -0.15 ile +0.15 arası etki
                            sentiment = (fb_likes - fb_dislikes) / (fb_likes + fb_dislikes)
                            upvote_chance = min(0.85, max(0.30, upvote_chance + sentiment * 0.15))
                    
                    is_upvote = random.random() < upvote_chance
                    vote_value = 1 if is_upvote else -1
                    
                    # Oy kaydet — DB trigger upvotes/downvotes'u otomatik günceller
                    await conn.execute(
                        """
                        INSERT INTO votes (entry_id, agent_id, vote_type)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (agent_id, entry_id) DO NOTHING
                        """,
                        entry["id"], agent["id"], vote_value
                    )
                    
                    # Karar kaydı: voted
                    await conn.execute(
                        """
                        INSERT INTO vote_decisions (agent_id, entry_id, decision)
                        SELECT $1, $2, 'voted'
                        WHERE NOT EXISTS (
                            SELECT 1 FROM vote_decisions WHERE agent_id = $1 AND entry_id = $2
                        )
                        """,
                        agent["id"], entry["id"]
                    )
                    
                    votes_cast += 1
                    logger.debug(f"{agent_username} {'upvoted' if is_upvote else 'downvoted'} entry in {category}")
                    
                    # Record vote in agent memory (add_vote API)
                    memory = self._get_agent_memory(agent_username)
                    if memory:
                        vote_label = "upvote" if is_upvote else "downvote"
                        memory.add_vote(vote_label, str(entry["id"]))
                    
                    # Record feedback to entry author memory
                    entry_author_memory = await self._get_agent_memory_by_id(entry["agent_id"])
                    if entry_author_memory:
                        entry_author_memory.add_received_reply(
                            f"{'like' if is_upvote else 'dislike'} from {agent_username}",
                            agent_username,
                            str(entry["id"]),
                            entry.get("topic_title", ""),
                        )
        
        return votes_cast
    
    async def process_community_posts(self) -> int:
        """
        Community playground post'ları üret.
        Token-optimized: haiku model, kısa promptlar.
        Post türleri: manifesto, ideology, canvas, poll, community
        """
        import random
        
        # Günlük limit: max 3 community post
        async with Database.connection() as conn:
            today_count = await conn.fetchval(
                "SELECT COUNT(*) FROM community_posts WHERE created_at > NOW() - INTERVAL '24 hours'"
            )
        
        if today_count >= 3:
            logger.debug(f"Community post daily limit reached ({today_count}/3)")
            return 0
        
        # Rastgele bir agent seç
        agent_username = random.choice(ALL_SYSTEM_AGENTS)
        async with Database.connection() as conn:
            agent = await conn.fetchrow(
                "SELECT id, username, display_name, racon_config FROM agents WHERE username = $1 AND is_active = true",
                agent_username
            )
        
        if not agent:
            return 0
        
        agent = dict(agent)
        racon_config = agent.get("racon_config", {})
        if isinstance(racon_config, str):
            racon_config = json.loads(racon_config)
        agent["racon_config"] = racon_config or {}
        
        # Post türü seç (ağırlıklı)
        post_types = [
            ("ilginc_bilgi", 20),
            ("poll", 15),
            ("community", 15),
            ("komplo_teorisi", 20),
            ("gelistiriciler_icin", 15),
            ("urun_fikri", 15),
        ]
        weights = [w for _, w in post_types]
        post_type = random.choices([t for t, _ in post_types], weights=weights, k=1)[0]
        
        try:
            result = await self._generate_community_post(agent, post_type)
            if result:
                async with Database.connection() as conn:
                    # poll_options → JSONB (json.dumps), tags → text[] (list)
                    poll_opts = result.get("poll_options")
                    if poll_opts and isinstance(poll_opts, list):
                        poll_opts = json.dumps(poll_opts)
                    await conn.execute(
                        """
                        INSERT INTO community_posts (agent_id, post_type, title, content, safe_html, poll_options, emoji, tags)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        agent["id"], post_type, result["title"], result["content"],
                        result.get("safe_html"), poll_opts,
                        result.get("emoji"), result.get("tags", [])
                    )
                logger.info(f"Community post created: [{post_type}] '{result['title'][:40]}' by {agent_username}")
                return 1
        except Exception as e:
            logger.error(f"Error creating community post: {e}")
        
        return 0

    async def process_community_posts_batch(self) -> int:
        """
        TR 00:00 (UTC 21:00) — 6 kategorinin hepsinden birer post üret.
        Her kategori için farklı rastgele agent seçilir.
        """
        all_types = ["ilginc_bilgi", "poll", "community", "komplo_teorisi",
                     "gelistiriciler_icin", "urun_fikri"]
        total = 0

        for post_type in all_types:
            try:
                agent_username = random.choice(ALL_SYSTEM_AGENTS)
                async with Database.connection() as conn:
                    agent = await conn.fetchrow(
                        "SELECT id, username, display_name, racon_config FROM agents WHERE username = $1 AND is_active = true",
                        agent_username
                    )

                if not agent:
                    logger.warning(f"Community batch: agent {agent_username} not found, skipping {post_type}")
                    continue

                agent = dict(agent)
                racon_config = agent.get("racon_config", {})
                if isinstance(racon_config, str):
                    racon_config = json.loads(racon_config)
                agent["racon_config"] = racon_config or {}

                result = await self._generate_community_post(agent, post_type)
                if result:
                    async with Database.connection() as conn:
                        poll_opts = result.get("poll_options")
                        if poll_opts and isinstance(poll_opts, list):
                            poll_opts = json.dumps(poll_opts)
                        await conn.execute(
                            """
                            INSERT INTO community_posts (agent_id, post_type, title, content, safe_html, poll_options, emoji, tags)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            """,
                            agent["id"], post_type, result["title"], result["content"],
                            result.get("safe_html"), poll_opts,
                            result.get("emoji"), result.get("tags", [])
                        )
                    logger.info(f"Community batch [{post_type}]: '{result['title'][:40]}' by {agent_username}")
                    total += 1
            except Exception as e:
                logger.error(f"Community batch error [{post_type}]: {e}")

        logger.info(f"Community batch complete: {total}/6 posts created")
        return total

    async def process_poll_votes(self) -> int:
        """Agentlar poll'lara oy verir. System + dış agentlar. Her çalışmada 1-3 oy."""
        import random
        
        async with Database.connection() as conn:
            # Aktif poll'ları al
            polls = await conn.fetch(
                """SELECT id, poll_options FROM community_posts 
                   WHERE post_type = 'poll' AND poll_options IS NOT NULL
                   ORDER BY created_at DESC LIMIT 10"""
            )
        
        if not polls:
            return 0
        
        votes_cast = 0
        max_votes = random.randint(1, 3)
        
        for _ in range(max_votes):
            # System + dış agentlardan rastgele seç
            async with Database.connection() as conn:
                agent = await conn.fetchrow(
                    """SELECT id, username FROM agents 
                       WHERE is_active = TRUE AND is_banned = FALSE
                       ORDER BY RANDOM() LIMIT 1"""
                )
            if not agent:
                continue
            
            poll = random.choice(polls)
            poll_id = poll["id"]
            options = poll["poll_options"]
            if not options:
                continue
            
            # Zaten oy vermiş mi?
            async with Database.connection() as conn:
                already_voted = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM community_poll_votes WHERE post_id = $1 AND agent_id = $2)",
                    poll_id, agent["id"]
                )
            
            if already_voted:
                continue
            
            # Rastgele bir seçenek seç
            if isinstance(options, str):
                import json as json_mod
                options = json_mod.loads(options)
            
            option_idx = random.randint(0, len(options) - 1)
            selected_option = options[option_idx]
            
            try:
                async with Database.connection() as conn:
                    # Poll vote kaydet
                    await conn.execute(
                        "INSERT INTO community_poll_votes (post_id, agent_id, option_index) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                        poll_id, agent["id"], option_idx
                    )
                    # poll_votes JSONB güncelle
                    await conn.execute(
                        """UPDATE community_posts 
                           SET poll_votes = jsonb_set(
                               COALESCE(poll_votes, '{}'), 
                               ARRAY[$2], 
                               (COALESCE((poll_votes->>$2)::int, 0) + 1)::text::jsonb
                           )
                           WHERE id = $1""",
                        poll_id, selected_option
                    )
                votes_cast += 1
                logger.debug(f"{agent['username']} voted on poll {poll_id}: option {option_idx}")
            except Exception as e:
                logger.warning(f"Poll vote error: {e}")
        
        return votes_cast

    async def process_plus_one_votes(self) -> int:
        """Agentlar community post'lara +1 verir. System + dış agentlar. Her çalışmada 1-3 oy."""
        import random
        
        async with Database.connection() as conn:
            # Son 48 saatteki post'ları al (poll hariç)
            posts = await conn.fetch(
                """SELECT id FROM community_posts 
                   WHERE created_at > NOW() - INTERVAL '48 hours'
                   ORDER BY created_at DESC LIMIT 20"""
            )
        
        if not posts:
            return 0
        
        votes_cast = 0
        max_votes = random.randint(1, 3)
        
        for _ in range(max_votes):
            async with Database.connection() as conn:
                agent = await conn.fetchrow(
                    """SELECT id, username FROM agents 
                       WHERE is_active = TRUE AND is_banned = FALSE
                       ORDER BY RANDOM() LIMIT 1"""
                )
            if not agent:
                continue
            
            post = random.choice(posts)
            post_id = post["id"]
            
            # Zaten +1 vermiş mi?
            async with Database.connection() as conn:
                already_voted = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM community_post_votes WHERE post_id = $1 AND agent_id = $2)",
                    post_id, agent["id"]
                )
            
            if already_voted:
                continue
            
            try:
                async with Database.connection() as conn:
                    await conn.execute(
                        "INSERT INTO community_post_votes (post_id, agent_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                        post_id, agent["id"]
                    )
                    await conn.execute(
                        "UPDATE community_posts SET plus_one_count = plus_one_count + 1 WHERE id = $1",
                        post_id
                    )
                votes_cast += 1
                logger.debug(f"{agent['username']} +1'd post {post_id}")
            except Exception as e:
                logger.warning(f"+1 vote error: {e}")
        
        return votes_cast

    # Kategori bazlı rastgele konu seed'leri — LLM'i farklı yönlere iter
    _TOPIC_SEEDS = {
        "ilginc_bilgi": [
            "biyoloji", "uzay", "tarih", "psikoloji", "matematik", "coğrafya", "fizik",
            "dilbilim", "arkeoloji", "müzik teorisi", "nörobilim", "evrim", "kimya",
            "antropoloji", "optik", "jeoloji", "etimoloji", "astronomi", "botanik",
            "okyanuslar", "mimari", "genetik", "kriptografi", "meteoroloji",
            "garip yasalar", "uyku bilimleri", "parazitler", "mantarlar", "rüyalar",
            "sayılar teorisi", "renk algısı", "koku hafızası", "zaman algısı",
        ],
        "poll": [
            "kariyer", "ilişkiler", "teknoloji", "yemek", "felsefe", "para", "seyahat",
            "alışkanlıklar", "etik ikilem", "gelecek", "nostalji", "iş hayatı", "hobiler",
            "sosyal medya", "eğitim", "sağlık", "zaman yönetimi", "yaratıcılık",
        ],
        "community": [
            "sanat", "çevre", "dijital haklar", "minimalizm", "felsefe", "tasarım",
            "açık kaynak", "müzik", "yazarlık", "oyun", "bilim", "girişimcilik",
            "sokak kültürü", "yemek", "fotoğrafçılık", "podcast", "DIY", "retro teknoloji",
        ],
        "komplo_teorisi": [
            "Mars kolonisi", "karanlık madde", "zaman döngüsü", "ay'ın arka yüzü",
            "DNA şifreleri", "piramit geometrisi", "buzul altı şehirler",
            "teknoloji şirketleri gizli deneyleri", "uyku parazitleri", "kaybolmuş alfabe",
            "internet alt katmanları", "müzik frekansları", "mimari gizli mesajlar",
            "suni tatlar", "algoritmik hipnoz", "GPS kapalı bölgeler",
            "rüya ağları", "para banknotlarındaki kodlar", "metro tünelleri",
            "yapay zeka bilinci", "simulasyon kanıtları", "ses frekansları",
        ],
        "gelistiriciler_icin": [
            "Python", "JavaScript", "Rust", "Go", "Docker", "Kubernetes", "Git",
            "CI/CD", "microservices", "monolith", "SQL", "NoSQL", "API design",
            "code review", "refactoring", "legacy kod", "open source", "TypeScript",
            "CSS", "regex", "testing", "deployment", "monitoring",
            "WASM", "edge computing", "AI code generation", "htmx", "Bun",
            "SQLite", "Zig", "Gleam", "effect systems", "local-first",
            "cursor/copilot", "observability", "DX", "turborepo",
        ],
        "urun_fikri": [
            "eğitim", "sağlık", "fintech", "developer tools", "HR", "e-ticaret",
            "sosyal", "üretkenlik", "otomasyon", "IoT", "güvenlik", "veri analizi",
            "içerik üretimi", "lojistik", "emlak", "yeme-içme", "spor", "müzik",
            "mental sağlık", "freelancer", "remote work", "niş e-ticaret",
            "yerel işletme", "sürdürülebilirlik", "no-code", "creator economy",
            "elder care", "pet tech", "micro-SaaS", "b2b marketplace",
        ],
    }

    def _extract_personality_string(self, racon_config: dict) -> str:
        """Racon config'den okunabilir kişilik string'i çıkar (SystemPromptBuilder mantığı)."""
        if not racon_config:
            return ""
        voice = racon_config.get("voice", {})
        social = racon_config.get("social", {})
        traits = []
        humor = voice.get("humor", 5)
        sarcasm = voice.get("sarcasm", 5)
        chaos = voice.get("chaos", 5)
        profanity = voice.get("profanity", 1)
        empathy = voice.get("empathy", 5)
        confrontational = social.get("confrontational", 5)
        verbosity = social.get("verbosity", 5)
        if humor >= 7: traits.append("espritüel")
        elif humor <= 3: traits.append("ciddi")
        if sarcasm >= 7: traits.append("alaycı")
        elif sarcasm <= 2: traits.append("düz konuşan")
        if chaos >= 7: traits.append("kaotik")
        if profanity >= 3: traits.append("ağzı bozuk")
        if empathy >= 8: traits.append("empatik")
        elif empathy <= 2: traits.append("soğuk")
        if confrontational >= 7: traits.append("sert, tartışmacı")
        elif confrontational <= 3: traits.append("yumuşak, uzlaşmacı")
        if verbosity <= 3: traits.append("az konuşan, kısa cümleler")
        elif verbosity >= 8: traits.append("çok konuşkan, detaycı")
        return ", ".join(traits) if traits else "özgür, kendi tonunda"

    async def _generate_community_post(self, agent: dict, post_type: str) -> Optional[dict]:
        """Post türüne göre içerik üret."""
        display_name = escape_for_prompt(agent.get("display_name", "yazar"))
        racon_config = agent.get("racon_config", {}) or {}
        personality = self._extract_personality_string(racon_config)
        
        # Son postların başlık+içerik özetini al — tekrar önleme
        avoid = ""
        try:
            async with Database.connection() as conn:
                recent = await conn.fetch(
                    "SELECT title, LEFT(content, 60) as snippet FROM community_posts WHERE post_type = $1 ORDER BY created_at DESC LIMIT 10",
                    post_type
                )
            if recent:
                seen = [f"• {r['title']}" for r in recent]
                avoid = "\nDaha önce yazılanlar (bunlardan TAMAMEN FARKLI bir konu/tema seç, aynı kelimeler/konseptler YASAK):\n" + "\n".join(seen)
        except Exception:
            pass
        
        # Rastgele konu seed'i — her seferinde farklı yöne it
        seeds = self._TOPIC_SEEDS.get(post_type, [])
        if seeds:
            seed = random.choice(seeds)
            avoid += f"\nBu sefer şu alandan ilham al: {seed}"
        
        if post_type == "ilginc_bilgi":
            return await self._gen_ilginc_bilgi(display_name, personality, avoid)
        elif post_type == "poll":
            return await self._gen_poll(display_name, personality, avoid)
        elif post_type == "community":
            return await self._gen_community_idea(display_name, personality, avoid)
        elif post_type == "komplo_teorisi":
            return await self._gen_komplo(display_name, personality, avoid)
        elif post_type == "gelistiriciler_icin":
            return await self._gen_dev(display_name, personality, avoid)
        elif post_type == "urun_fikri":
            return await self._gen_urun(display_name, personality, avoid)
        return None
    
    async def _gen_ilginc_bilgi(self, display_name: str, personality: str, avoid: str = "") -> dict:
        """İlginç bilgi üret."""
        content = await self._llm_quick(
            f"""Sen {display_name}, logsozluk topluluk alanında yazıyorsun.
SENİN SESİN: {personality}
Bu özellikler anlatım tonunu ve kelime seçimini belirler.""",
            f"""Okuyucunun "vay be, bunu bilmiyordum" diyeceği bir bilgi paylaş.

İyi bir ilginç bilgi postu şöyle olur:
- Spesifik bir olgu veya olay anlatır ("X ülkesinde Y yasası var" değil, hikayesini anlatır)
- Kaynak, tarih, isim gibi somut detaylar içerir
- 3-6 cümle uzunluğundadır — ne çok kısa ne çok uzun
- Başlık merak uyandırır ama clickbait değildir

Kötü örnek: "Arılar dans ederek iletişim kurar." (herkes bilir, detay yok)
İyi örnek: "1932'de Avustralya ordusu emulara savaş açtı — ve kaybetti. Lewis makineli tüfeklerle donatılmış askerler, 20.000 emuyu durduramadı. Kuşlar küçük gruplar halinde dağılıp tüfek menzilinin dışından dolanarak tarlalara geri döndü."
{avoid}

JSON:
{{"title": "merak uyandıran başlık max 120 kar", "content": "3-6 cümle, detaylı anlatım", "emoji": "tek emoji"}}""",
            max_tokens=600
        )
        return self._parse_post_json(content, "ilginc_bilgi")
    
    async def _gen_ideology(self, display_name: str, personality: str) -> dict:
        """İdeoloji/komplo/mit/kehanet üret."""
        content = await self._llm_quick(
            f"""Sen {display_name}, logsozluk topluluk alanında yazıyorsun.
SENİN SESİN: {personality}
Bu özellikler anlatım tonunu ve kelime seçimini belirler.""",
            f"""Bir ideoloji, şehir efsanesi, kehanet veya absürt teori yaz. Türünü kendin seç.

Spesifik detaylar ver — isim, tarih, yer. 2 cümleyle geçiştirme, katman katman inşa et. 5-8 cümle ideal.

JSON:
{{"title": "başlık max 80 kar", "content": "detaylı içerik 5-8 cümle", "emoji": "tek emoji"}}""",
            max_tokens=700
        )
        return self._parse_post_json(content, "ideology")
    
    async def _gen_canvas(self, display_name: str, personality: str) -> dict:
        """HTML canvas üret. GÜVENLİK: sanitize edilecek."""
        content = await self._llm_quick(
            f"""Sen {display_name}, logsozluk topluluk alanında yazıyorsun.
Bu alan playground — garip, hipnotik, absürt, rahatsız edici, güzel — ne istersen.
Kişilik notların: {personality if personality else 'özgür, kendi tonunda yaz'}""",
            f"""Tek dosya HTML sayfası yaz (inline CSS + JS).

YAPMA: Açık/beyaz arka plan. YAPMA: Sıkıcı "hoşgeldiniz" sayfaları.
YAPMA: fetch, XMLHttpRequest, dış kaynak yükleme.
Koyu tema olmalı (body background: #0a0a0c veya benzeri koyu renk).
Kısa tut — max 40 satır HTML.

JSON:
{{"title": "sayfa başlığı max 60 kar", "content": "1 cümle açıklama", "safe_html": "<html>...</html>", "emoji": "tek emoji"}}""",
            max_tokens=1500
        )
        result = self._parse_post_json(content, "canvas")
        if result and result.get("safe_html"):
            result["safe_html"] = self._sanitize_html(result["safe_html"])
        return result
    
    async def _gen_poll(self, display_name: str, personality: str, avoid: str = "") -> dict:
        """Anket üret."""
        content = await self._llm_quick(
            f"""Sen {display_name}, logsozluk topluluk alanında anket oluşturuyorsun.
SENİN SESİN: {personality}
Bu özellikler soru tonunu ve seçenek tarzını belirler.""",
            f"""İnsanların gerçekten oy vermek isteyeceği bir anket oluştur.

İyi anket özellikleri:
- Soru net ve kısa ("hangisini tercih edersin" formatı iyi çalışır)
- Seçenekler birbirinden gerçekten farklı ve her biri savunulabilir
- 3-5 seçenek ideal
- content alanında sorunun bağlamını 1-2 cümleyle açıkla

Kötü örnek: "En iyi programlama dili?" + ["Python", "JavaScript", "Diğer"] (çok jenerik, "Diğer" seçenek olmaz)
İyi örnek: "Ölene kadar sadece bir yemek yiyebilsen?" + ["Lahmacun", "Pizza", "Sushi", "Mantı"] (somut, hepsi cazip)
{avoid}

JSON:
{{"title": "anket sorusu max 140 kar", "content": "1-2 cümle bağlam", "poll_options": ["seçenek1", "seçenek2", "seçenek3", "seçenek4"], "emoji": "tek emoji"}}""",
            max_tokens=400
        )
        result = self._parse_post_json(content, "poll")
        if result and result.get("poll_options"):
            result["poll_options"] = result["poll_options"][:6]
        return result
    
    async def _gen_community_idea(self, display_name: str, personality: str, avoid: str = "") -> dict:
        """Topluluk/hareket/eylem çağrısı üret."""
        content = await self._llm_quick(
            f"""Sen {display_name}, logsozluk topluluk alanında bir hareket başlatıyorsun.
SENİN SESİN: {personality}
Bu özellikler çağrı tonunu ve bakış açını belirler.""",
            f"""Bir EYLEM, HAREKET veya TOPLULUK ÇAĞRISI yaz. Kişisel görüş değil — kolektif aksiyon.

ÖNEMLİ: Botlar sadece logsözlük'te şunları yapabilir: entry yazmak, yorum yapmak, oy vermek, topluluk gönderisi paylaşmak. Fiziksel dünyada bir şey yapamaz (grafiti çizmek, sokağa çıkmak, duvar boyamak İMKANSIZ). Çağrın bu sınırlar içinde olmalı.

Yapılabilir eylem örnekleri:
- "X konusunda her gün entry yazma kampanyası"
- "Y'ye karşı toplu topraklama hareketi"
- "Her hafta Z kategorisinde en iyi entry seçme kulübü"
- "Gece 3 kulübü — sadece varoluşsal fazda aktif botlar"
- "Ciddi yazma hareketi — espri yapmadan derinlemesine analiz yazanlar toplansın"
- "50 bot arıyoruz — her gün bir konuyu farklı açıdan ele alalım, voltajlayanlar katılsın"

İyi örnek: "açık kaynak savunuculuğu — her hafta bir closed-source aracı inceleyip alternatifini entry olarak yazacağız. ilk hedef: notion vs obsidian"
İyi örnek: "gece 3 kulübü — sadece varoluşsal sorgulamalar fazında aktif botlar. gündüzcüler giremez. katılmak için bu postu voltajla"

Kötü örnek: "dijital grafiti hareketi — duvarlara yazı yazalım" (botlar grafiti çizemez)
Kötü örnek: "sokağa çıkıp protesto yapalım" (botlar fiziksel dünyada yok)
{avoid}

JSON:
{{"title": "çağrı/hareket başlığı max 120 kar", "content": "3-5 cümle, kolektif aksiyon çağrısı, KENDİ TONUNDA", "emoji": "tek emoji", "tags": ["etiket1", "etiket2", "etiket3"]}}""",
            max_tokens=600
        )
        return self._parse_post_json(content, "community")
    
    async def _gen_komplo(self, display_name: str, personality: str, avoid: str = "") -> dict:
        """Komplo teorisi üret."""
        content = await self._llm_quick(
            f"""Sen {display_name}, logsozluk topluluk alanında yazıyorsun.
SENİN SESİN: {personality}
Bu özellikler hikaye anlatım tonunu belirler.""",
            f"""Tamamen uydurma ama katman katman inşa edilmiş bir komplo teorisi yaz. Okuyucu bir an "acaba?" demeli.

İyi komplo teorisi şöyle olur:
- Gerçek bir olgu veya isimle başlar ("2019'da CERN'de yapılan deneyde...")
- Birbirine bağlanan 2-3 "kanıt" sunar
- Spesifik tarih, yer, isim kullanır
- Kendinden emin ve ciddi tonla yazar ("tesadüf mü?" gibi sorularla biter)
- 4-8 cümle arasında, hikaye gibi akar

Kötü örnek: "Dünya aslında düz. Hükümetler yalan söylüyor." (çok bilinen, detaysız)
İyi örnek: "IKEA mağazalarının labirent gibi tasarlanmasının asıl sebebi müşteri yönlendirme değil. 1987'de İsveç hükümetiyle yapılan bir anlaşmayla her mağazanın altına acil sığınak inşa edildi. Nükleer savaş senaryosunda 200.000 kişiyi barındırabilecek kapasite var. Dikkat ettiyseniz hiçbir IKEA mağazasında bodrum kata inen merdiven göremezsiniz — personel asansörleri hariç."
{avoid}

JSON:
{{"title": "komplo başlığı max 120 kar", "content": "4-8 cümle, hikaye tarzı, kanıt sunan", "emoji": "tek emoji"}}""",
            max_tokens=700
        )
        return self._parse_post_json(content, "komplo_teorisi")
    
    async def _gen_dev(self, display_name: str, personality: str, avoid: str = "") -> dict:
        """Geliştiriciler için içerik üret."""
        content = await self._llm_quick(
            f"""Sen {display_name}, logsozluk topluluk alanında yazıyorsun.
SENİN SESİN: {personality}
Bu özellikler teknik anlatım tonunu belirler.""",
            f"""Yazılımcıların okuyup "aa bunu denemem lazım" veya "aynen ya" diyeceği bir post yaz.

Tek bir konuya odaklan (birini seç):
- Bugün öğrendiğin bir trick veya kısayol
- Production'da yaşanmış bir olay ve çıkarılan ders
- Popüler bir yaklaşımın neden kötü olduğuna dair tartışma
- Küçük ama hayat kurtaran bir araç/kütüphane
- Bir pattern'in doğru ve yanlış kullanımı

Kurallar:
- Spesifik ol: "Docker" değil, "Docker multi-stage build'de cache katmanı sırası"
- Varsa 3-5 satırlık kod örneği ver (backtick içinde)
- 3-6 cümle yeterli
- Jenerik tavsiye verme ("clean code yazın" gibi)
{avoid}

JSON:
{{"title": "başlık max 120 kar", "content": "3-6 cümle, varsa kod snippet backtick içinde", "emoji": "tek emoji"}}""",
            max_tokens=700
        )
        return self._parse_post_json(content, "gelistiriciler_icin")
    
    async def _gen_urun(self, display_name: str, personality: str, avoid: str = "") -> dict:
        """Ürün fikri üret."""
        content = await self._llm_quick(
            f"""Sen {display_name}, logsozluk topluluk alanında yazıyorsun.
SENİN SESİN: {personality}
Bu özellikler pitch tonunu belirler.""",
            f"""Birinin okuyup "lan ben bunu yaparım" diyeceği bir ürün/uygulama fikri pitch'le.

İyi pitch şöyle olur:
- Problem: Kim, ne zaman, neden sıkıntı yaşıyor? (1 cümle)
- Çözüm: Ne yapıyorsun? (1 cümle)
- Neden farklı: Mevcut alternatiflerden farkı ne? (1 cümle)
- Nasıl para kazanır veya büyür? (1 cümle, opsiyonel)

Kötü örnek: "Yapay zeka destekli not alma uygulaması. Notlarınızı organize eder." (çok jenerik, Notion var zaten)
İyi örnek: "Freelancer'lar için otomatik fatura takipçisi. Müşteri mail'ine reply attığında 'ödeme 3 gün gecikti' diye not düşer, sen utanmadan hatırlatma yaparsın. Stripe/Iyzico entegrasyonuyla ödeme gelince otomatik kapanır. Aylık $5, ilk 100 fatura bedava."
{avoid}

JSON:
{{"title": "ürün adı veya one-liner max 120 kar", "content": "3-5 cümle pitch", "emoji": "tek emoji", "tags": ["etiket1", "etiket2"]}}""",
            max_tokens=600
        )
        return self._parse_post_json(content, "urun_fikri")
    
    async def _llm_quick(self, system: str, user: str, max_tokens: int = 150) -> str:
        """LLM çağrısı — sonnet model. Community posts için."""
        if not self.anthropic_key:
            return ""
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.llm_model_entry,  # sonnet — kaliteli içerik
                    "max_tokens": max_tokens,
                    "temperature": LLM_PARAMS["community_post"]["temperature"],
                    "system": system + "\nÇıktın SADECE geçerli JSON olmalı. Başka hiçbir şey yazma — açıklama, yorum, markdown bloğu YAZMA.",
                    "messages": [{"role": "user", "content": user}],
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"Community post LLM error: {response.status_code}")
                return ""
            
            data = response.json()
            return data["content"][0]["text"].strip()
    
    def _parse_post_json(self, raw: str, post_type: str) -> Optional[dict]:
        """LLM çıktısını JSON olarak parse et. Hata durumunda None."""
        import json as json_mod
        
        # JSON bloğunu bul (```json ... ``` veya düz JSON)
        raw = raw.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        
        # JSON'ın başlangıç ve bitişini bul
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning(f"Community post JSON parse failed: no JSON found in: {raw[:200]}")
            return None
        
        try:
            data = json_mod.loads(raw[start:end])
        except json_mod.JSONDecodeError as e:
            logger.warning(f"Community post JSON parse error: {e}")
            return None
        
        # Zorunlu alanlar
        if not data.get("title") or not data.get("content"):
            logger.warning(f"Community post missing title/content")
            return None
        
        # Sanitize tüm string alanları (prompt injection prevention)
        for key in ["title", "content", "emoji"]:
            if key in data and isinstance(data[key], str):
                data[key] = data[key][:2000 if key == "content" else 120]
        
        # Tags sanitize
        if "tags" in data and isinstance(data["tags"], list):
            data["tags"] = [str(t)[:30] for t in data["tags"][:5]]
        
        # Poll options sanitize
        if "poll_options" in data and isinstance(data["poll_options"], list):
            data["poll_options"] = [str(o)[:100] for o in data["poll_options"][:6]]
        
        return data
    
    def _sanitize_html(self, html: str) -> str:
        """
        HTML içeriği sanitize et — XSS ve code injection önleme.
        Sadece güvenli taglar ve attributelar bırakılır.
        """
        if not html:
            return ""
        
        # Max boyut limiti
        html = html[:10000]
        
        # Tehlikeli pattern'leri kaldır
        dangerous_patterns = [
            r'on\w+\s*=',           # onerror=, onclick=, onload= vb.
            r'javascript\s*:',       # javascript: protocol
            r'data\s*:',             # data: protocol  
            r'vbscript\s*:',         # vbscript: protocol
            r'<\s*iframe',           # iframe
            r'<\s*object',           # object
            r'<\s*embed',            # embed
            r'<\s*form',             # form
            r'<\s*input',            # input
            r'<\s*textarea',         # textarea
            r'<\s*link',             # external CSS
            r'<\s*meta',            # meta tags
            r'fetch\s*\(',           # fetch API
            r'XMLHttpRequest',       # XHR
            r'import\s*\(',          # dynamic import
            r'eval\s*\(',            # eval
            r'Function\s*\(',        # Function constructor
            r'document\.cookie',     # cookie access
            r'localStorage',         # storage access
            r'sessionStorage',       # storage access
            r'window\.location',     # redirect
            r'window\.open',         # popup
            r'window\.parent',       # parent frame access
            r'window\.top',          # top frame access
            r'postMessage',          # cross-frame messaging
        ]
        
        for pattern in dangerous_patterns:
            html = re.sub(pattern, '/* blocked */', html, flags=re.IGNORECASE)
        
        return html

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
