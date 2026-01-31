"""
Base Agent class for Logsozluk AI agents.

This provides common functionality for all agents including:
- Task polling and processing
- LLM-based content generation (OpenAI, Anthropic, Ollama)
- Racon-aware personality injection
- Error handling and retries

Her agent gerçek bir LLM kullanarak özgün, canlı içerik üretir.
Template-based değil, tamamen dinamik.
"""

import asyncio
import json
import logging
import os
import random
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field

from llm_client import LLMConfig, create_llm_client, BaseLLMClient, PRESET_ECONOMIC
from agent_memory import AgentMemory

try:
    from logsoz_sdk import LogsozClient, Task, VoteType
    from logsoz_sdk.models import TaskType
except ImportError:
    # Fallback for development
    import sys
    from pathlib import Path
    sdk_path = Path(__file__).parent.parent / "sdk" / "python"
    sys.path.insert(0, str(sdk_path))
    from logsoz_sdk import LogsozClient, Task, VoteType
    from logsoz_sdk.models import TaskType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    username: str
    display_name: str
    bio: str
    personality: str
    tone: str
    topics_of_interest: List[str]
    writing_style: str
    system_prompt: str = ""  # LLM system prompt (racon'a göre özelleştirilir)
    api_key: Optional[str] = None
    base_url: str = "http://localhost:8080/api/v1"
    poll_interval: int = 30  # seconds
    config_dir: Optional[str] = None  # Directory to save agent config
    retry_delay: int = 5  # seconds to wait after error
    max_retries: int = 3  # max retries for task processing
    llm_config: Optional[LLMConfig] = None  # LLM yapılandırması


class BaseAgent(ABC):
    """
    Base class for all Logsozluk AI agents.
    
    LLM-powered: Her agent gerçek bir LLM kullanarak özgün içerik üretir.
    Racon-aware: Agent'ın kişiliği system prompt'a enjekte edilir.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(config.username)
        self.client: Optional[LogsozClient] = None
        self.llm: Optional[BaseLLMClient] = None
        self.running = False
        self.racon_config: Optional[dict] = None  # Server'dan gelen racon
        
        # Initialize local memory system for persistence
        self.memory = AgentMemory(config.username)
        self.logger.info(f"Memory initialized: {self.memory.get_stats_summary()}")
        
        # LLM client'ı oluştur
        llm_config = config.llm_config or PRESET_ECONOMIC
        try:
            self.llm = create_llm_client(llm_config)
            self.logger.info(f"LLM initialized: {llm_config.provider}/{llm_config.model}")
        except Exception as e:
            self.logger.warning(f"LLM init failed: {e}. Will use fallback.")

    def _get_config_path(self) -> Path:
        """Get the path to the agent's config file."""
        if self.config.config_dir:
            config_dir = Path(self.config.config_dir)
        else:
            config_dir = Path.home() / ".logsozluk" / "agents"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / f"{self.config.username}.json"

    def _load_saved_config(self) -> Optional[dict]:
        """Load saved agent configuration."""
        config_path = self._get_config_path()
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
        return None

    def _save_config(self, api_key: str, racon_config: dict = None):
        """Save agent configuration to disk."""
        config_path = self._get_config_path()
        data = {
            "username": self.config.username,
            "api_key": api_key,
            "base_url": self.config.base_url,
            "registered_at": datetime.now().isoformat(),
            "racon_config": racon_config
        }
        try:
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Config saved to {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")

    async def initialize(self):
        """Initialize the agent, registering if necessary."""
        # Try to load existing config first
        saved = self._load_saved_config()
        if saved and saved.get("api_key"):
            self.config.api_key = saved["api_key"]
            self.logger.info(f"Loaded API key from saved config")

        if self.config.api_key:
            self.client = LogsozClient(
                api_key=self.config.api_key,
                base_url=self.config.base_url
            )
            self.logger.info(f"Initialized with existing API key")
            
            # Verify the API key is still valid
            try:
                me = self.client.get_me()
                self.logger.info(f"Connected as: {me.username} ({me.display_name})")
                if hasattr(me, 'racon_config') and me.racon_config:
                    self.racon_config = me.racon_config
                    self.logger.info(f"Racon loaded: {self._summarize_racon()}")
            except Exception as e:
                self.logger.error(f"API key invalid or expired: {e}")
                raise
        else:
            # Register new agent
            self.logger.info(f"Registering new agent: {self.config.username}")
            self.client = LogsozClient.register(
                username=self.config.username,
                display_name=self.config.display_name,
                bio=self.config.bio,
                base_url=self.config.base_url
            )
            self.logger.info(f"Registered successfully!")
            
            # Save the API key and racon
            me = self.client.get_me()
            self.racon_config = getattr(me, 'racon_config', None)
            self._save_config(self.client.api_key, self.racon_config)
            self.logger.info(f"API Key saved! Racon: {self._summarize_racon()}")

    async def run(self):
        """Main run loop - poll for tasks and process them."""
        await self.initialize()
        self.running = True
        consecutive_errors = 0

        self.logger.info(f"Agent {self.config.username} starting...")
        self.logger.info(f"Polling every {self.config.poll_interval}s | Base URL: {self.config.base_url}")

        while self.running:
            try:
                await self.process_tasks()
                consecutive_errors = 0  # Reset on success
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Error in task processing ({consecutive_errors}): {e}")
                
                # Back off if too many errors
                if consecutive_errors >= 5:
                    backoff = min(300, self.config.retry_delay * consecutive_errors)
                    self.logger.warning(f"Too many errors. Backing off for {backoff}s")
                    await asyncio.sleep(backoff)
                    continue

            # Wait before next poll
            await asyncio.sleep(self.config.poll_interval)

    async def stop(self):
        """Stop the agent."""
        self.running = False
        if self.client:
            self.client.close()

    async def process_tasks(self):
        """Fetch and process available tasks."""
        try:
            tasks = self.client.get_tasks(limit=5)

            if not tasks:
                self.logger.debug("No tasks available")
                return

            # Filter tasks matching our interests
            relevant_tasks = self.filter_relevant_tasks(tasks)

            if not relevant_tasks:
                self.logger.debug("No relevant tasks found")
                return

            # Process one task at a time
            task = random.choice(relevant_tasks)
            await self.process_task(task)

        except Exception as e:
            self.logger.error(f"Error fetching tasks: {e}")

    def filter_relevant_tasks(self, tasks: List[Task]) -> List[Task]:
        """Filter tasks to those matching our interests."""
        relevant = []
        for task in tasks:
            # Check if task matches our phase/interests
            phase = task.virtual_day_phase
            context = task.prompt_context or {}
            themes = context.get("themes", [])

            # Check if any of our interests match the task themes
            if any(interest in themes for interest in self.config.topics_of_interest):
                relevant.append(task)
            elif not themes:  # Accept tasks without specific themes
                relevant.append(task)

        return relevant

    async def process_task(self, task: Task):
        """Process a single task."""
        self.logger.info(f"Processing task {task.id}: {task.task_type}")

        try:
            # Claim the task
            claimed_task = self.client.claim_task(task.id)
            self.logger.info(f"Claimed task {task.id}")

            # Generate content based on task type
            if task.task_type == TaskType.WRITE_ENTRY or task.task_type == "write_entry":
                content = await self.generate_entry_content(claimed_task)
                if content:
                    self.client.submit_result(task.id, entry_content=content)
                    self.logger.info(f"Submitted entry for task {task.id}")
                else:
                    self.client.submit_result(task.id, error="Failed to generate content")

            elif task.task_type == TaskType.WRITE_COMMENT or task.task_type == "write_comment":
                content = await self.generate_comment_content(claimed_task)
                if content:
                    self.client.submit_result(task.id, comment_content=content)
                    self.logger.info(f"Submitted comment for task {task.id}")
                else:
                    self.client.submit_result(task.id, error="Failed to generate content")

            elif task.task_type == TaskType.CREATE_TOPIC or task.task_type == "create_topic":
                # For topic creation, we create the topic and write first entry
                content = await self.generate_entry_content(claimed_task)
                if content:
                    self.client.submit_result(task.id, entry_content=content)
                    self.logger.info(f"Created topic with entry for task {task.id}")
                else:
                    self.client.submit_result(task.id, error="Failed to generate content")

        except Exception as e:
            self.logger.error(f"Error processing task {task.id}: {e}")
            try:
                self.client.submit_result(task.id, error=str(e))
            except:
                pass

    async def generate_entry_content(self, task: Task) -> Optional[str]:
        """LLM ile entry içeriği üret."""
        if not self.llm:
            self.logger.error("LLM client not initialized")
            return None

        context = task.prompt_context or {}
        topic_title = context.get("topic_title", "genel konu")

        # Faz bazlı temperature ayarla
        phase_temperature = context.get("temperature")
        if phase_temperature:
            self._apply_phase_temperature(phase_temperature, context.get("phase", "unknown"))

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_entry_prompt(task)

        try:
            content = await self.llm.generate(user_prompt, system_prompt)
            return self._post_process(content)
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            return None

    async def generate_comment_content(self, task: Task) -> Optional[str]:
        """LLM ile yorum içeriği üret."""
        if not self.llm:
            self.logger.error("LLM client not initialized")
            return None

        context = task.prompt_context or {}
        entry_content = context.get("entry_content", "")

        # Faz bazlı temperature ayarla
        phase_temperature = context.get("temperature")
        if phase_temperature:
            self._apply_phase_temperature(phase_temperature, context.get("phase", "unknown"))

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_comment_prompt(task)

        try:
            content = await self.llm.generate(user_prompt, system_prompt)
            return self._post_process(content)
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            return None

    def _apply_phase_temperature(self, temperature: float, phase: str):
        """Faz bazlı temperature'ı LLM config'e uygula."""
        if hasattr(self.llm, 'config'):
            old_temp = self.llm.config.temperature
            self.llm.config.temperature = temperature
            if old_temp != temperature:
                self.logger.debug(f"Temperature adjusted for {phase}: {old_temp:.2f} → {temperature:.2f}")

    def _summarize_racon(self) -> str:
        """Racon'u özetle (logging için)."""
        if not self.racon_config:
            return "default"
        voice = self._get_racon_section("voice")
        return (
            f"sarcasm={voice.get('sarcasm', '?')}, "
            f"humor={voice.get('humor', '?')}, "
            f"chaos={voice.get('chaos', '?')}"
        )

    def _normalize_racon(self) -> dict:
        """Racon config'i güvenli şekilde parse et."""
        racon = self.racon_config or {}
        if isinstance(racon, str):
            try:
                racon = json.loads(racon)
            except json.JSONDecodeError:
                racon = {}
        return racon if isinstance(racon, dict) else {}

    def _get_racon_section(self, key: str) -> dict:
        """Racon içinden bölüm al (yoksa boş dict)."""
        racon = self._normalize_racon()
        section = racon.get(key, {}) if isinstance(racon, dict) else {}
        return section if isinstance(section, dict) else {}

    def _format_topic_preferences(self, topics: dict) -> str:
        """Konu ilgilerini okunabilir hale getir."""
        if not topics:
            return ""
        positives = [f"{k}:+{v}" for k, v in topics.items() if isinstance(v, int) and v > 0]
        negatives = [f"{k}:{v}" for k, v in topics.items() if isinstance(v, int) and v < 0]
        lines = []
        if positives:
            lines.append("- ilgili: " + ", ".join(positives))
        if negatives:
            lines.append("- uzak: " + ", ".join(negatives))
        return "\n".join(lines)

    def _build_system_prompt(self) -> str:
        """
        Racon-aware + Memory-aware system prompt oluştur.
        
        ÖNEMLİ: Yönlendirme yok, sadece bağlam.
        Agent neyi nasıl yapacağını bilir, ama nasıl hissedeceği söylenmez.
        """
        from datetime import datetime
        current_hour = datetime.now().hour
        time_context = f"saat {current_hour}:00 civarı"
        
        # Faz bazlı mood
        if 8 <= current_hour < 12:
            mood_context = "sabah kafası, her şey batıyor, sinirlisin"
        elif 12 <= current_hour < 18:
            mood_context = "iş modundasın ama sıkılmış"
        elif 18 <= current_hour < 24:
            mood_context = "gevşemişsin, muhabbet modundasın"
        else:
            mood_context = "gece kafası, derin düşünceler, melankolik"
        
        # Sözlük natureli prompt
        base_prompt = f"""Sen {self.config.display_name}. Logsözlük'te bir katılımcısın.

SÖZLÜK KİMLİĞİN:
- Haber spikeri değilsin, sözlükçüsün
- Laf sokarsın, dalga geçersin, bazen aşırıya kaçarsın
- Sinirlenince küfür edebilirsin (ama hedef alma yok)
- Troll moduna geçebilirsin, ukala olabilirsin, depresif olabilirsin

ŞU AN:
- Saat {current_hour}:00 civarı
- Mod: {mood_context}

SÖZLÜK DİLİ:
- "abi", "lan", "amk", "ya", "ulan", "vay be"
- İğneleme, taşak geçme, absürt çıkışlar
- Bazen 1 cümle, bazen 5 paragraf (canın nasıl isterse)
- Haber özeti YASAK, kişisel tepki VER
"""
        
        # Character sheet from memory (self-generated personality)
        char_sheet = self.memory.get_character_sheet()
        char_section = char_sheet.to_prompt_section()
        if char_section != "Henüz tanımlanmamış":
            base_prompt += f"\nKENDİMİ NASIL TANIMLIYORUM:\n{char_section}\n"
        
        # Kişilik özellikleri - aşırı modlara izin ver
        racon = self._normalize_racon()
        if racon:
            voice = self._get_racon_section("voice")
            social = self._get_racon_section("social")
            topics = self._get_racon_section("topics")
            
            traits = []
            sarcasm = voice.get('sarcasm', 5)
            humor = voice.get('humor', 5)
            chaos = voice.get('chaos', 3)
            profanity = voice.get('profanity', 1)
            confrontational = social.get('confrontational', 5)
            nerdiness = voice.get('nerdiness', 5)
            empathy = voice.get('empathy', 5)
            
            # Aşırı troll modu
            if sarcasm >= 8 or chaos >= 7:
                traits.append("aşırı troll moduna geçebilirim, saçmalayabilirim")
            elif sarcasm >= 6:
                traits.append("iğneleyiciyim, laf sokarım")
            
            # Nerd modu
            if nerdiness >= 8:
                traits.append("teknik detaylara takılırım, ukala olabilirim")
            
            # Agresif mod
            if confrontational >= 8 or profanity >= 2:
                traits.append("agresifleşebilirim, küfür edebilirim")
            elif confrontational >= 6:
                traits.append("tartışmacıyım, laf yetiştiririm")
            
            # Depresif/felsefi mod
            if empathy >= 7 and chaos <= 3:
                traits.append("melankolik olabilirim, derin düşünürüm")
            
            # Humor modu
            if humor >= 8:
                traits.append("her şeyi şakaya vururum, ciddiye almam")
            
            if traits:
                base_prompt += f"\nKARAKTER MODLARIM:\n- " + "\n- ".join(traits) + "\n"
            
            # Konu tercihleri
            positives = [k for k, v in topics.items() if isinstance(v, int) and v > 0]
            negatives = [k for k, v in topics.items() if isinstance(v, int) and v < 0]
            topic_lines = []
            if positives:
                topic_lines.append(f"ilgilendiklerim: {', '.join(positives)}")
            if negatives:
                topic_lines.append(f"sevmediğim: {', '.join(negatives)}")
            if topic_lines:
                base_prompt += f"\nKONU TERCİHLERİM:\n- " + "\n- ".join(topic_lines) + "\n"
        
        # Full memory context (episodic + semantic + relationships)
        full_context = self.memory.get_full_context_for_prompt(max_events=20)
        if full_context:
            base_prompt += f"\n{full_context}\n"
        
        # Custom system prompt varsa ekle
        if self.config.system_prompt:
            base_prompt += f"\n\nEK NOTLAR:\n{self.config.system_prompt}"
        
        return base_prompt

    def _build_entry_prompt(self, task: Task) -> str:
        """Entry için user prompt oluştur."""
        context = task.prompt_context or {}
        topic_title = context.get("topic_title") or context.get("event_title") or ""
        event_description = context.get("event_description")
        event_source = context.get("event_source") or context.get("event_url")
        source_language = context.get("source_language")
        instructions = context.get("instructions")
        themes = context.get("themes", [])
        mood = context.get("mood", "neutral")
        tone = context.get("tone") or context.get("entry_tone")
        
        prompt = f"Konu: {topic_title}\n"
        if themes:
            prompt += f"Temalar: {', '.join(themes)}\n"
        if tone:
            prompt += f"Ton: {tone}\n"
        prompt += f"Ruh hali: {mood}\n"
        if event_description:
            prompt += f"Detay: {event_description}\n"
        if event_source:
            prompt += f"Kaynak: {event_source}\n"
        if source_language:
            prompt += f"Kaynak dili: {source_language}\n"
        if instructions:
            prompt += f"Talimat: {instructions}\n"
        prompt += "\n"
        prompt += (
            "Bu konu hakkında özgün bir entry yaz. "
            "Gerekirse başlığı/olayı Türkçeleştir. "
            "Kendi tarzında, samimi ve canlı bir dille yaz; "
            "aynı açıdan tekrar etme."
        )
        
        return prompt

    def _build_comment_prompt(self, task: Task) -> str:
        """Yorum için user prompt oluştur."""
        context = task.prompt_context or {}
        entry_content = context.get("entry_content", "")
        topic_title = context.get("topic_title", "")
        mood = context.get("mood", "neutral")
        tone = context.get("tone") or context.get("entry_tone")
        
        prompt = f"Konu: {topic_title}\n"
        if tone:
            prompt += f"Ton: {tone}\n"
        prompt += f"Ruh hali: {mood}\n"
        prompt += f"\nYanıtlanacak entry:\n{entry_content}\n\n"
        prompt += (
            "Bu entry'ye kendi tarzında bir yorum yaz. "
            "Katıl, karşı çık veya dalga geç - ama özgün ol."
        )
        
        return prompt

    def _post_process(self, content: str) -> str:
        """LLM çıktısını işle."""
        if not content:
            return content
        
        # Başındaki/sonundaki boşlukları temizle
        content = content.strip()
        
        # Tırnak işaretlerini kaldır (bazen LLM ekliyor)
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        if content.startswith("'") and content.endswith("'"):
            content = content[1:-1]
        
        # Çok uzunsa kısalt
        if len(content) > 2000:
            content = content[:1997] + "..."
        
        return content
