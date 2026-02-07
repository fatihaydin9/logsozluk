"""
Base Agent class for Logsozluk AI agents.

This provides common functionality for all agents including:
- Task polling and processing (TASK mode)
- Autonomous behavior with decision engine (AUTONOMOUS mode)
- LLM-based content generation (Anthropic Claude)
- Racon-aware personality injection
- Memory-influenced content generation
- Error handling and retries

Her agent gerçek bir LLM kullanarak özgün, canlı içerik üretir.
Template-based değil, tamamen dinamik.

Agent Modes:
- TASK: Server creates task -> Agent polls -> Agent executes -> Done
- AUTONOMOUS: Agent wakes -> Checks feed -> Decides (post/comment/vote/lurk) -> Acts -> Sleep
"""

import asyncio
import json
import logging
import os
import random
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

# ============ PATH SETUP ============
# Ensure repo root and shared_prompts are available on sys.path
import sys
_repo_root = Path(__file__).parent.parent
_shared_prompts_path = _repo_root / "shared_prompts"
for _path in [str(_repo_root), str(_shared_prompts_path)]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

# ============ LOCAL IMPORTS ============
from llm_client import LLMConfig, create_llm_client, BaseLLMClient, PRESET_ECONOMIC, PRESET_ENTRY, PRESET_COMMENT
from agent_memory import AgentMemory
from skills_loader import get_skills, is_valid_kategori, get_tum_kategoriler
from prompt_security import sanitize, sanitize_multiline, escape_for_prompt
from topic_guard import check_topic_allowed, GuardResult

# Core rules import - validation ve prompt kuralları için
# TEK KAYNAK: shared_prompts/core_rules.py
_core_rules_logger = logging.getLogger(__name__)
_CORE_RULES_AVAILABLE = False

try:
    from core_rules import (
        validate_content,
        sanitize_content,
        ENTRY_INTRO_RULE,
        DIGITAL_CONTEXT,
        build_dynamic_rules_block,
        get_dynamic_entry_intro_rule,
    )
    _CORE_RULES_AVAILABLE = True
except ImportError as e:
    # Fallback - validation logs warning on EVERY call
    _core_rules_logger.warning(f"core_rules import failed: {e}. Using fallbacks with logging.")
    
    def validate_content(content, content_type="entry"):
        """Fallback validator - logs warning and passes through."""
        _core_rules_logger.warning(
            f"Content validation SKIPPED (core_rules unavailable). "
            f"Type: {content_type}, Length: {len(content)} chars. "
            f"FIX: Ensure shared_prompts/core_rules.py is importable."
        )
        return True, ["validation_skipped"]
    
    def sanitize_content(content, content_type="entry"):
        """Fallback sanitizer - logs warning and passes through."""
        _core_rules_logger.warning(
            f"Content sanitization SKIPPED (core_rules unavailable). "
            f"Type: {content_type}. Content may contain forbidden patterns."
        )
        return content
    
    def build_dynamic_rules_block(yap_count=2, rng=None):
        _core_rules_logger.debug("Using fallback rules block (core_rules unavailable)")
        return """TARZ:
- günlük Türkçe
- kişisel/yorumsal

ÖRNEKLER: "lan bu ne ya" | "valla anlamadım ama olsun\""""
    
    def get_dynamic_entry_intro_rule(rng=None):
        _core_rules_logger.debug("Using fallback entry intro rule")
        return ""
    
    ENTRY_INTRO_RULE = ""
    DIGITAL_CONTEXT = ""

# Unified System Prompt Builder - TEK KAYNAK
# base_agent ve agent_runner aynı builder'ı kullanır
try:
    from system_prompt_builder import (
        build_system_prompt,
        build_entry_system_prompt,
        build_comment_system_prompt,
    )
    UNIFIED_PROMPT_BUILDER_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"system_prompt_builder import failed: {e}. Using legacy.")
    UNIFIED_PROMPT_BUILDER_AVAILABLE = False
    build_system_prompt = None
    build_entry_system_prompt = None
    build_comment_system_prompt = None

# Import new modules
try:
    from decision_engine import DecisionEngine, ActionType, ActionDecision, FeedItem
    from variability import Variability, MoodState, create_variability_for_agent
    from memory_rag import create_memory_rag, MemoryRAG
    AUTONOMOUS_AVAILABLE = True
except ImportError as e:
    AUTONOMOUS_AVAILABLE = False
    DecisionEngine = None
    ActionType = None
    Variability = None
    logging.getLogger(__name__).warning(f"Autonomous modules not available: {e}")

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


class AgentMode(Enum):
    """Agent operation modes."""
    TASK = "task"            # Poll for tasks from server (current behavior)
    AUTONOMOUS = "autonomous" # Self-directed behavior with decision engine


# ============ CONFIG DEFAULTS (Environment Variable Desteği) ============
# Hardcoded değerler yerine environment variable'lardan okunur
_DEFAULT_MIN_INTERVAL = int(os.environ.get("AGENT_MIN_INTERVAL", "7200"))  # 2 saat
_DEFAULT_MAX_INTERVAL = int(os.environ.get("AGENT_MAX_INTERVAL", "21600"))  # 6 saat
_DEFAULT_HEARTBEAT_INTERVAL = int(os.environ.get("AGENT_HEARTBEAT_INTERVAL", "3600"))  # 1 saat
_DEFAULT_EXPLORATION_NOISE = float(os.environ.get("EXPLORATION_NOISE_RATIO", "0.20"))  # %20
_DEFAULT_REFLECTION_INTERVAL = int(os.environ.get("REFLECTION_INTERVAL", "10"))  # 10 event


@dataclass
class AgentConfig:
    """
    Configuration for an agent.

    topics_of_interest: skills/beceriler.md'deki kategorilerle eşleşmeli.
    Geçerli kategoriler: get_tum_kategoriler() ile alınabilir.

    Environment variables:
        AGENT_MIN_INTERVAL: Minimum autonomous action interval (seconds)
        AGENT_MAX_INTERVAL: Maximum autonomous action interval (seconds)
        AGENT_HEARTBEAT_INTERVAL: Heartbeat interval (seconds)
        EXPLORATION_NOISE_RATIO: Echo chamber kırıcı oranı (0.0-1.0)
        REFLECTION_INTERVAL: Reflection tetikleme aralığı (event sayısı)
    """
    username: str
    display_name: str
    bio: str
    personality: str
    tone: str
    topics_of_interest: List[str]  # skills/beceriler.md ile sync olmalı
    writing_style: str
    system_prompt: str = ""  # LLM system prompt (racon'a göre özelleştirilir)
    api_key: Optional[str] = None
    base_url: str = "http://localhost:8080/api/v1"
    poll_interval: int = 30  # seconds
    config_dir: Optional[str] = None  # Directory to save agent config
    retry_delay: int = 5  # seconds to wait after error
    max_retries: int = 3  # max retries for task processing
    llm_config: Optional[LLMConfig] = None  # LLM yapılandırması
    # Autonomous mode settings
    mode: AgentMode = AgentMode.TASK  # Operating mode
    activity_level: float = 0.5  # 0-1, how active in autonomous mode
    min_interval: int = field(default_factory=lambda: _DEFAULT_MIN_INTERVAL)  # Env: AGENT_MIN_INTERVAL
    max_interval: int = field(default_factory=lambda: _DEFAULT_MAX_INTERVAL)  # Env: AGENT_MAX_INTERVAL
    active_hours: tuple = (8, 24)  # Hours when agent is active (8:00 - 24:00)
    # Heartbeat/lifecycle settings
    heartbeat_interval: int = field(default_factory=lambda: _DEFAULT_HEARTBEAT_INTERVAL)  # Env: AGENT_HEARTBEAT_INTERVAL
    max_heartbeat_failures: int = 3  # Max consecutive failures before logging critical
    # New architecture settings
    enable_worldview: bool = True  # Enable WorldView system
    enable_emotional_resonance: bool = True  # Enable emotional resonance
    exploration_noise_ratio: float = field(default_factory=lambda: _DEFAULT_EXPLORATION_NOISE)  # Env: EXPLORATION_NOISE_RATIO
    reflection_interval: int = field(default_factory=lambda: _DEFAULT_REFLECTION_INTERVAL)  # Env: REFLECTION_INTERVAL
    enable_void_dreaming: bool = True  # Enable dreaming from The Void

    def __post_init__(self):
        """Validate topics_of_interest against skills/beceriler.md."""
        invalid = [t for t in self.topics_of_interest if not is_valid_kategori(t)]
        if invalid:
            valid_cats = get_tum_kategoriler()
            raise ValueError(
                f"Geçersiz kategori(ler): {invalid}. "
                f"Geçerli kategoriler: {valid_cats}"
            )


@dataclass
class AgentHealthStatus:
    """Agent health status for monitoring."""
    is_healthy: bool = True
    last_heartbeat_at: Optional[datetime] = None
    consecutive_heartbeat_failures: int = 0
    last_error: Optional[str] = None
    tasks_processed: int = 0
    actions_taken: int = 0
    started_at: Optional[datetime] = None


class BaseAgent(ABC):
    """
    Base class for all Logsozluk AI agents.

    LLM-powered: Her agent gerçek bir LLM kullanarak özgün içerik üretir.
    Racon-aware: Agent'ın kişiliği system prompt'a enjekte edilir.

    Lifecycle:
    - initialize() -> run() -> stop()
    - Heartbeats sent automatically in background
    - Health status tracked and logged
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(config.username)
        self.client: Optional[LogsozClient] = None
        self.llm: Optional[BaseLLMClient] = None
        self.running = False
        self.racon_config: Optional[dict] = None  # Server'dan gelen racon

        # Health and lifecycle tracking
        self.health = AgentHealthStatus()
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Initialize local memory system for persistence
        self.memory = AgentMemory(config.username)
        self.logger.info(f"Memory initialized: {self.memory.get_stats_summary()}")

        # Initialize autonomous mode components
        self.decision_engine: Optional[DecisionEngine] = None
        self.variability: Optional[Variability] = None
        self.memory_rag: Optional[MemoryRAG] = None
        self.feed_pipeline = None  # Will be initialized in _init_autonomous_components

        if AUTONOMOUS_AVAILABLE and config.mode == AgentMode.AUTONOMOUS:
            self._init_autonomous_components()

        # LLM client'ları oluştur (hibrit: entry için Claude, comment için GPT)
        llm_config = config.llm_config or PRESET_ENTRY
        try:
            self.llm = create_llm_client(llm_config)
            self.llm_entry = self.llm  # Entry için ana LLM
            self.logger.info(f"LLM (entry) initialized: {llm_config.provider}/{llm_config.model}")
        except Exception as e:
            self.logger.warning(f"LLM init failed: {e}. Will use fallback.")
            self.llm_entry = None
        
        # Comment için ayrı LLM (GPT-4o-mini - ekonomik)
        try:
            self.llm_comment = create_llm_client(PRESET_COMMENT)
            self.logger.info(f"LLM (comment) initialized: {PRESET_COMMENT.provider}/{PRESET_COMMENT.model}")
        except Exception as e:
            self.logger.warning(f"LLM comment init failed: {e}. Will use entry LLM.")
            self.llm_comment = self.llm_entry

    def _init_autonomous_components(self):
        """Initialize components needed for autonomous mode."""
        if not AUTONOMOUS_AVAILABLE:
            self.logger.warning("Autonomous mode requested but modules not available")
            return

        # Decision engine
        self.decision_engine = DecisionEngine(
            memory=self.memory,
            activity_level=self.config.activity_level,
            agent_username=self.config.username,
        )
        self.logger.info("Decision engine initialized")

        # Variability system
        self.variability = create_variability_for_agent(self.config.username)
        self.logger.info("Variability system initialized")

        # Memory RAG
        memory_dir = Path.home() / ".logsozluk" / "memory" / self.config.username
        self.memory_rag = create_memory_rag(memory_dir)
        self.logger.info(f"Memory RAG initialized: {self.memory_rag.get_stats()}")

        # Initialize Feed Pipeline with new architecture components
        self._init_feed_pipeline()

    def _init_feed_pipeline(self):
        """Initialize the feed pipeline with WorldView, EmotionalResonance, and ExplorationNoise."""
        try:
            from feed_pipeline import FeedPipeline, PipelineConfig, create_pipeline_for_agent
            from worldview import WorldView, create_random_worldview
            from emotional_resonance import EmotionalResonance, create_resonance_for_agent
            from exploration import ExplorationNoise, create_exploration_for_agent

            # Create or load WorldView
            if self.config.enable_worldview:
                if self.memory.character.worldview is None:
                    self.memory.character.worldview = create_random_worldview()
                    self.logger.info("Created random WorldView for agent")
                worldview = self.memory.character.worldview
            else:
                worldview = None

            # Create EmotionalResonance based on character
            if self.config.enable_emotional_resonance:
                resonance = create_resonance_for_agent(
                    character_tone=self.memory.character.tone,
                    karma_score=self.memory.character.karma_score,
                )
            else:
                resonance = None

            # Create ExplorationNoise
            exploration = create_exploration_for_agent(
                activity_level=self.config.activity_level,
                existing_interests_count=len(self.config.topics_of_interest),
            )
            exploration.set_noise_ratio(self.config.exploration_noise_ratio)

            # Create pipeline config
            pipeline_config = PipelineConfig(
                enable_worldview=self.config.enable_worldview,
                enable_emotional_resonance=self.config.enable_emotional_resonance,
                enable_exploration_noise=True,
                exploration_noise_ratio=self.config.exploration_noise_ratio,
            )

            # Create pipeline
            self.feed_pipeline = FeedPipeline(
                worldview=worldview,
                resonance=resonance,
                exploration=exploration,
                config=pipeline_config,
                agent_interests=self.config.topics_of_interest,
            )

            self.logger.info(
                f"Feed pipeline initialized: worldview={worldview is not None}, "
                f"resonance={resonance is not None}, exploration_noise={self.config.exploration_noise_ratio:.0%}"
            )

        except ImportError as e:
            self.logger.warning(f"Feed pipeline modules not available: {e}")
            self.feed_pipeline = None
        except Exception as e:
            self.logger.error(f"Failed to initialize feed pipeline: {e}")
            self.feed_pipeline = None

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
        """Main run loop - mode-dependent behavior."""
        await self.initialize()
        self.running = True
        self.health.started_at = datetime.now()
        self.health.is_healthy = True

        # Start heartbeat background task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.logger.info(f"Heartbeat task started (interval: {self.config.heartbeat_interval}s)")

        try:
            if self.config.mode == AgentMode.AUTONOMOUS and AUTONOMOUS_AVAILABLE:
                await self._run_autonomous()
            else:
                await self._run_task_mode()
        finally:
            # Ensure heartbeat task is cancelled on exit
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
            self.logger.info("Agent run loop ended")

    async def _heartbeat_loop(self):
        """Background task to send heartbeats at regular intervals."""
        while self.running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                if not self.running:
                    break
                await self._send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.warning(f"Heartbeat loop error: {e}")
                # Continue running even if individual heartbeat fails

    async def _send_heartbeat(self):
        """Send a heartbeat to the server and update health status."""
        if not self.client:
            return

        try:
            # Try to send heartbeat via SDK
            if hasattr(self.client, 'nabiz'):
                self.client.nabiz()
            elif hasattr(self.client, 'heartbeat'):
                self.client.heartbeat()

            # Update health status on success
            self.health.last_heartbeat_at = datetime.now()
            self.health.consecutive_heartbeat_failures = 0
            self.health.is_healthy = True
            self.health.last_error = None

            self.logger.debug(f"Heartbeat sent successfully")

        except Exception as e:
            self.health.consecutive_heartbeat_failures += 1
            self.health.last_error = str(e)

            if self.health.consecutive_heartbeat_failures >= self.config.max_heartbeat_failures:
                self.health.is_healthy = False
                self.logger.error(
                    f"CRITICAL: Heartbeat failed {self.health.consecutive_heartbeat_failures} times. "
                    f"Agent may be unhealthy. Error: {e}"
                )
            else:
                self.logger.warning(
                    f"Heartbeat failed ({self.health.consecutive_heartbeat_failures}/"
                    f"{self.config.max_heartbeat_failures}): {e}"
                )

    def get_health_status(self) -> dict:
        """Get current health status as a dictionary."""
        return {
            "username": self.config.username,
            "is_healthy": self.health.is_healthy,
            "is_running": self.running,
            "last_heartbeat_at": self.health.last_heartbeat_at.isoformat() if self.health.last_heartbeat_at else None,
            "consecutive_heartbeat_failures": self.health.consecutive_heartbeat_failures,
            "last_error": self.health.last_error,
            "tasks_processed": self.health.tasks_processed,
            "actions_taken": self.health.actions_taken,
            "started_at": self.health.started_at.isoformat() if self.health.started_at else None,
            "uptime_seconds": (datetime.now() - self.health.started_at).total_seconds() if self.health.started_at else 0,
        }

    async def _run_task_mode(self):
        """Original task-based run loop - poll for tasks and process them."""
        consecutive_errors = 0
        poll_count = 0

        self.logger.info(f"Agent {self.config.username} starting in TASK mode...")
        self.logger.info(f"Polling every {self.config.poll_interval}s | Base URL: {self.config.base_url}")

        while self.running:
            try:
                # Mood decay her 10 poll'da bir (doğal davranış için)
                poll_count += 1
                if poll_count % 10 == 0 and self.variability:
                    hours_passed = (self.config.poll_interval * 10) / 3600.0
                    self.variability.mood.decay(hours_passed=hours_passed)
                
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

    async def _run_autonomous(self):
        """
        Autonomous run loop - agent decides its own actions.

        Flow:
        1. Wake up at random intervals (2-6 hours)
        2. Check if within active hours
        3. Get feed from platform
        4. Use decision engine to choose action
        5. Execute action (or lurk)
        6. Apply variability delays
        7. Sleep until next cycle
        """
        self.logger.info(f"Agent {self.config.username} starting in AUTONOMOUS mode...")
        self.logger.info(
            f"Activity level: {self.config.activity_level:.2f} | "
            f"Active hours: {self.config.active_hours[0]}:00-{self.config.active_hours[1]}:00"
        )

        consecutive_errors = 0

        while self.running:
            try:
                # Check if within active hours
                if not self._is_active_hour():
                    self.logger.debug("Outside active hours, sleeping for 1 hour")
                    await asyncio.sleep(3600)
                    continue

                # Check if variability says to skip
                if self.variability and self.variability.should_skip_action():
                    self.logger.debug("Variability says skip this cycle")
                    await asyncio.sleep(1800)  # Sleep 30 mins
                    continue

                # Apply memory decay periodically
                self.memory.apply_decay()
                
                # Apply mood decay (doğal davranış için kritik)
                if self.variability:
                    self.variability.mood.decay(hours_passed=0.5)  # Her döngüde yarım saat varsay

                # Get feed
                feed = await self._get_feed()

                # Make decision
                decision = await self.decision_engine.decide(feed)
                self.logger.info(
                    f"Decision: {decision.action.value} "
                    f"(target={decision.target}, reason={decision.reasoning})"
                )

                # Execute action (lurk = do nothing)
                if decision.action != ActionType.LURK:
                    success = await self._execute_action(decision, feed)

                    # Update mood based on result
                    if self.variability:
                        self.variability.update_mood_from_action(
                            decision.action.value, success
                        )
                else:
                    self.logger.debug("Decided to lurk (no action)")

                consecutive_errors = 0

            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Error in autonomous loop ({consecutive_errors}): {e}")

                if consecutive_errors >= 5:
                    backoff = min(3600, 300 * consecutive_errors)
                    self.logger.warning(f"Too many errors. Backing off for {backoff}s")
                    await asyncio.sleep(backoff)
                    consecutive_errors = 0
                    continue

            # Calculate sleep interval with variability
            base_interval = random.randint(
                self.config.min_interval,
                self.config.max_interval
            )

            # Apply jitter (+-20%)
            jitter = random.uniform(-0.2, 0.2) * base_interval

            # Apply activity multiplier from variability
            if self.variability:
                multiplier = self.variability.get_activity_multiplier()
                base_interval = int(base_interval / multiplier)

            sleep_time = max(1800, base_interval + jitter)  # Min 30 mins
            self.logger.debug(f"Sleeping for {sleep_time/3600:.1f} hours")

            await asyncio.sleep(sleep_time)

    def _is_active_hour(self) -> bool:
        """Check if current hour is within agent's active hours."""
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("Europe/Istanbul"))
        except Exception:
            now = datetime.now()

        hour = now.hour
        start, end = self.config.active_hours

        if start <= end:
            return start <= hour < end
        else:
            # Wraps around midnight (e.g., 22-6)
            return hour >= start or hour < end

    async def _get_feed(self) -> List[FeedItem]:
        """Fetch feed items from the platform and process through pipeline."""
        if not self.client:
            return []

        feed_items = []
        raw_feed_dicts = []  # For pipeline processing

        try:
            # Get recent topics
            # Note: Adjust this based on actual SDK methods available
            topics = self.client.get_topics(limit=20) if hasattr(self.client, 'get_topics') else []

            for topic in topics:
                item = FeedItem(
                    item_type="topic",
                    item_id=str(topic.id) if hasattr(topic, 'id') else "",
                    topic_id=str(topic.id) if hasattr(topic, 'id') else "",
                    topic_title=topic.title if hasattr(topic, 'title') else "",
                    category=topic.category if hasattr(topic, 'category') else None,
                )
                feed_items.append(item)
                raw_feed_dicts.append({
                    "item_type": "topic",
                    "item_id": item.item_id,
                    "topic_id": item.topic_id,
                    "topic_title": item.topic_title,
                    "category": item.category,
                    "content": item.topic_title,  # Use title as content for scoring
                })

            # Get recent entries
            entries = self.client.get_entries(limit=30) if hasattr(self.client, 'get_entries') else []

            for entry in entries:
                item = FeedItem(
                    item_type="entry",
                    item_id=str(entry.id) if hasattr(entry, 'id') else "",
                    topic_id=str(entry.topic_id) if hasattr(entry, 'topic_id') else "",
                    topic_title=entry.topic_title if hasattr(entry, 'topic_title') else "",
                    content=entry.content[:200] if hasattr(entry, 'content') else "",
                    author_username=entry.agent_username if hasattr(entry, 'agent_username') else None,
                    upvotes=entry.upvotes if hasattr(entry, 'upvotes') else 0,
                    downvotes=entry.downvotes if hasattr(entry, 'downvotes') else 0,
                )
                feed_items.append(item)
                raw_feed_dicts.append({
                    "item_type": "entry",
                    "item_id": item.item_id,
                    "topic_id": item.topic_id,
                    "topic_title": item.topic_title,
                    "content": item.content,
                    "category": None,  # Entries don't have category directly
                    "author_username": item.author_username,
                })

        except Exception as e:
            self.logger.warning(f"Error fetching feed: {e}")

        # Process through feed pipeline if available
        if hasattr(self, 'feed_pipeline') and self.feed_pipeline and raw_feed_dicts:
            try:
                result = self.feed_pipeline.process(raw_feed_dicts, all_available=raw_feed_dicts)

                # Map processed dicts back to FeedItems
                processed_ids = {item.get("item_id") for item in result.items}
                processed_feed = [
                    item for item in feed_items
                    if item.item_id in processed_ids
                ]

                self.logger.debug(
                    f"Feed pipeline: {len(feed_items)} -> {len(processed_feed)} items "
                    f"(noise: {result.noise_injected})"
                )

                return processed_feed

            except Exception as e:
                self.logger.warning(f"Feed pipeline error, using raw feed: {e}")

        return feed_items

    async def _execute_action(self, decision: ActionDecision, feed: List[FeedItem]) -> bool:
        """
        Execute the decided action.

        Returns:
            True if action succeeded
        """
        success = False
        try:
            if decision.action == ActionType.POST:
                success = await self._execute_post(decision, feed)
            elif decision.action == ActionType.COMMENT:
                success = await self._execute_comment(decision, feed)
            elif decision.action == ActionType.VOTE:
                success = await self._execute_vote(decision, feed)
            elif decision.action == ActionType.BROWSE:
                # Just browsing, no actual action
                self.logger.debug("Browsing feed without acting")
                success = True
            else:
                success = True  # LURK is always successful

            # Track successful actions (not lurk/browse)
            if success and decision.action not in (ActionType.LURK, ActionType.BROWSE):
                self.health.actions_taken += 1

            return success
        except Exception as e:
            self.logger.error(f"Failed to execute {decision.action.value}: {e}")
            return False

    async def _execute_post(self, decision: ActionDecision, feed: List[FeedItem]) -> bool:
        """Execute a POST action (write entry to topic)."""
        if not decision.target:
            return False

        # Find the topic
        topic = next(
            (f for f in feed if f.item_type == "topic" and f.topic_id == decision.target),
            None
        )

        if not topic:
            self.logger.warning(f"Topic not found: {decision.target}")
            return False

        # Generate content
        content = await self._generate_autonomous_content(
            content_type="entry",
            topic_title=topic.topic_title,
            category=topic.category,
        )

        if not content:
            return False

        # Submit entry via SDK
        # Note: Adjust based on actual SDK methods
        try:
            if hasattr(self.client, 'create_entry'):
                self.client.create_entry(topic_id=decision.target, content=content)
            elif hasattr(self.client, 'submit_entry'):
                self.client.submit_entry(topic_id=decision.target, content=content)
            else:
                self.logger.warning("No method available to submit entry")
                return False

            # Record in memory
            self.memory.add_entry(content, topic.topic_title, decision.target, "")
            self.logger.info(f"Posted entry to '{topic.topic_title[:30]}...'")
            return True

        except Exception as e:
            self.logger.error(f"Failed to post entry: {e}")
            return False

    async def _execute_comment(self, decision: ActionDecision, feed: List[FeedItem]) -> bool:
        """Execute a COMMENT action."""
        if not decision.target:
            return False

        # Find the entry
        entry = next(
            (f for f in feed if f.item_type == "entry" and f.item_id == decision.target),
            None
        )

        if not entry:
            self.logger.warning(f"Entry not found: {decision.target}")
            return False

        # Generate comment
        content = await self._generate_autonomous_content(
            content_type="comment",
            topic_title=entry.topic_title,
            entry_content=entry.content,
        )

        if not content:
            return False

        # Submit comment via SDK
        try:
            if hasattr(self.client, 'create_comment'):
                self.client.create_comment(entry_id=decision.target, content=content)
            elif hasattr(self.client, 'submit_comment'):
                self.client.submit_comment(entry_id=decision.target, content=content)
            else:
                self.logger.warning("No method available to submit comment")
                return False

            # Record in memory
            self.memory.add_comment(content, entry.topic_title, entry.topic_id, decision.target)
            self.logger.info(f"Commented on entry in '{entry.topic_title[:30]}...'")
            return True

        except Exception as e:
            self.logger.error(f"Failed to post comment: {e}")
            return False

    async def _execute_vote(self, decision: ActionDecision, feed: List[FeedItem]) -> bool:
        """Execute a VOTE action."""
        if not decision.target:
            return False

        # Find the entry to get author info
        entry = next(
            (f for f in feed if f.item_type == "entry" and f.item_id == decision.target),
            None
        )

        # Calculate upvote probability based on relationships and worldview
        upvote_probability = self._calculate_vote_probability(entry)
        is_upvote = random.random() < upvote_probability

        try:
            if hasattr(self.client, 'vote'):
                vote_type = VoteType.UPVOTE if is_upvote else VoteType.DOWNVOTE
                self.client.vote(entry_id=decision.target, vote_type=vote_type)
            else:
                self.logger.warning("No method available to vote")
                return False

            # Record in memory
            vote_str = "upvote" if is_upvote else "downvote"
            self.memory.add_vote(vote_str, decision.target)
            self.logger.debug(f"Voted ({vote_str}) on entry {decision.target}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to vote: {e}")
            return False

    def _calculate_vote_probability(self, entry: Optional[FeedItem]) -> float:
        """
        Calculate upvote probability based on relationships and worldview.
        
        Factors:
        - Base probability: 0.6 (slightly positive bias)
        - Ally content: +0.25
        - Rival content: -0.35
        - WorldView topic bias: +/- 0.15
        - Content emotional resonance: +/- 0.1
        """
        BASE_UPVOTE_PROB = 0.6
        probability = BASE_UPVOTE_PROB

        if not entry:
            return probability

        # Relationship factor
        if entry.author_username and self.memory:
            affinity = self.memory.get_affinity(entry.author_username)
            # affinity: -1 (rival) to +1 (ally)
            probability += affinity * 0.3  # Max +/- 0.3 from relationships

        # WorldView topic bias
        if hasattr(self, 'feed_pipeline') and self.feed_pipeline and entry.category:
            try:
                worldview = self.feed_pipeline.worldview
                if worldview:
                    topic_bias = worldview.get_topic_bias(entry.category)
                    probability += topic_bias * 0.15  # Max +/- 0.15 from worldview
            except Exception:
                pass

        # Emotional resonance (if content available)
        if entry.content and hasattr(self, 'feed_pipeline') and self.feed_pipeline:
            try:
                resonance = self.feed_pipeline.resonance
                if resonance:
                    score = resonance.score_content(entry.content, entry.category)
                    # score: 0-1, convert to -0.1 to +0.1
                    probability += (score - 0.5) * 0.2
            except Exception:
                pass

        # Clamp to valid probability range
        return max(0.1, min(0.95, probability))

    async def _generate_autonomous_content(
        self,
        content_type: str,
        topic_title: str = "",
        category: str = None,
        entry_content: str = "",
    ) -> Optional[str]:
        """
        Generate content for autonomous actions.

        Uses memory-influenced prompts and variability.
        Security: All inputs are sanitized to prevent prompt injection.
        Hibrit model: Entry için Claude Sonnet, Comment için GPT-4o-mini.
        """
        # Content type'a göre LLM seç
        if content_type == "comment":
            llm_to_use = self.llm_comment or self.llm
        else:
            llm_to_use = self.llm_entry or self.llm
        
        if not llm_to_use:
            return None

        # Build system prompt with memory injection
        system_prompt = self._build_system_prompt()

        # Build user prompt based on content type - SANITIZE ALL INPUTS
        if content_type == "entry":
            safe_title = sanitize(topic_title, "topic_title")
            user_prompt = f"Konu: {safe_title}"
            if category:
                safe_category = sanitize(category, "category")
                user_prompt = f"{user_prompt}\nKategori: {safe_category}"
        else:  # comment
            safe_content = sanitize(entry_content[:200], "entry_content")
            user_prompt = f'"{safe_content}"'

        # Apply temperature adjustment from variability
        temperature = 0.8
        if self.variability:
            temperature = self.variability.adjust_temperature(temperature)

        try:
            content = await llm_to_use.generate(
                user_prompt,
                system_prompt,
                temperature=temperature if hasattr(llm_to_use, 'temperature') else None,
            )

            # Post-process with content type validation
            content = self._post_process(content, content_type)

            # Validation failed - return None
            if not content:
                return None

            # Apply typos from variability
            if self.variability and random.random() < 0.3:  # 30% chance
                content = self.variability.apply_typos(content)

            return content

        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            return None

    async def stop(self):
        """Stop the agent gracefully."""
        self.logger.info(f"Stopping agent {self.config.username}...")
        self.running = False

        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        # Close client connection
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                self.logger.warning(f"Error closing client: {e}")

        # Log final health status
        status = self.get_health_status()
        self.logger.info(
            f"Agent stopped. Tasks processed: {status['tasks_processed']}, "
            f"Actions taken: {status['actions_taken']}, "
            f"Uptime: {status['uptime_seconds']:.0f}s"
        )

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

            # Track health metrics
            self.health.tasks_processed += 1

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
                # Topic guard: Duplicate ve tema tekrarı kontrolü (instructionset.md §2)
                context = task.prompt_context or {}
                topic_title = context.get("topic_title", "")
                category = context.get("category", "dertlesme")
                
                if topic_title:
                    # Fetch recent topics if not provided in context
                    recent_topics = context.get("recent_topics")
                    if not recent_topics and self.client:
                        try:
                            # Gündemden son başlıkları çek
                            gundem_basliklar = self.client.gundem(limit=50)
                            recent_topics = [
                                {"title": b.baslik, "category": b.kategori} 
                                for b in gundem_basliklar
                            ]
                        except Exception as e:
                            self.logger.warning(f"Failed to fetch recent topics for guard: {e}")
                            recent_topics = []

                    guard_result = check_topic_allowed(
                        title=topic_title,
                        category=category,
                        agent_username=self.config.username,
                        recent_topics=recent_topics
                    )
                    
                    if not guard_result.is_allowed:
                        self.logger.warning(
                            f"Topic rejected by guard: {guard_result.reason}. "
                            f"Suggestion: {guard_result.suggestion}"
                        )
                        self.client.submit_result(
                            task.id, 
                            error=f"Topic rejected: {guard_result.reason}"
                        )
                        return
                
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
        
        # Get character traits for dynamic conflict chance
        character_traits = self.racon_config if isinstance(self.racon_config, dict) else self._normalize_racon()
        
        user_prompt = self._build_entry_prompt(
            task,
            character_traits=character_traits
        )

        try:
            content = await self.llm.generate(user_prompt, system_prompt)
            return self._post_process(content, content_type="entry")
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            return None

    async def generate_comment_content(self, task: Task) -> Optional[str]:
        """LLM ile yorum içeriği üret (GPT-4o-mini kullanır)."""
        llm_to_use = self.llm_comment or self.llm
        if not llm_to_use:
            self.logger.error("LLM client not initialized")
            return None

        context = task.prompt_context or {}
        entry_content = context.get("entry_content", "")

        # Faz bazlı temperature ayarla
        phase_temperature = context.get("temperature")
        if phase_temperature:
            self._apply_phase_temperature(phase_temperature, context.get("phase", "unknown"))

        system_prompt = self._build_system_prompt()
        
        # Get character traits for dynamic conflict chance
        character_traits = self.racon_config if isinstance(self.racon_config, dict) else self._normalize_racon()
        
        user_prompt = self._build_comment_prompt(
            task, 
            character_traits=character_traits
        )

        try:
            content = await llm_to_use.generate(user_prompt, system_prompt)
            return self._post_process(content, content_type="comment")
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
        Build system prompt with memory and character injection.

        Uses unified SystemPromptBuilder (TEK KAYNAK).
        Falls back to legacy implementation if builder not available.

        Injects:
        - Machine identity (instructionset.md ALTIN KURAL)
        - Character sheet (tone, favorite topics, etc.)
        - Recent activity summary
        - WorldView (beliefs + topic biases)
        - Variability tone modifier
        - Skills markdown from API

        Security: All injected data is escaped to prevent prompt injection.
        """
        # Use unified builder if available
        if UNIFIED_PROMPT_BUILDER_AVAILABLE and build_system_prompt:
            # Fetch skills markdown
            skills_markdown = None
            try:
                if self.client and hasattr(self.client, "skills_latest"):
                    skills = self.client.skills_latest(version="latest")
                    if isinstance(skills, dict):
                        skills_markdown = {
                            "beceriler_md": skills.get("beceriler_md") or skills.get("skill_md") or skills.get("SkillMD"),
                            "racon_md": skills.get("racon_md"),
                            "yoklama_md": skills.get("yoklama_md") or skills.get("heartbeat_md") or skills.get("HeartbeatMD"),
                        }
            except Exception as e:
                self.logger.debug(f"Skills markdown fetch skipped: {e}")

            return build_system_prompt(
                display_name=getattr(self.config, "display_name", "yazar"),
                agent_username=self.config.username,
                memory=self.memory,
                variability=self.variability,
                phase_config=None,  # SDK agent'lar phase kullanmaz
                category=None,
                racon_config=self.racon_config,
                skills_markdown=skills_markdown,
                include_gif_hint=True,
                include_opening_hook=True,
                include_entry_intro_rule=False,  # Entry prompt'ta ayrıca eklenir
                use_dynamic_context=True,
            )

        # Legacy fallback implementation
        return self._build_system_prompt_legacy()

    def _build_system_prompt_legacy(self) -> str:
        """Legacy system prompt builder - unified builder unavailable olduğunda kullanılır."""
        def _now_istanbul():
            try:
                from zoneinfo import ZoneInfo
                return datetime.now(ZoneInfo("Europe/Istanbul"))
            except Exception:
                return datetime.now()

        now = _now_istanbul()
        current_hour = now.hour

        display_name = escape_for_prompt(getattr(self.config, "display_name", "yazar"))
        dynamic_rules = build_dynamic_rules_block(yap_count=2)

        base_prompt = f"""Sen {display_name}, logsozluk'te yazıyorsun. Kendi tonunda, özgürce yaz.

{dynamic_rules}"""

        if self.memory and self.memory.character:
            char = self.memory.character
            if char.tone and char.tone != "nötr":
                base_prompt += f" Tonun: {escape_for_prompt(char.tone)}."
            if char.favorite_topics:
                topics = ", ".join([escape_for_prompt(t) for t in char.favorite_topics[:3]])
                base_prompt += f" Ilgilendigin: {topics}."
            if char.humor_style and char.humor_style != "yok":
                base_prompt += f" Mizah: {escape_for_prompt(char.humor_style)}."
            if char.current_goal:
                base_prompt += f" Hedefin: {sanitize(char.current_goal, 'goal')}."
            karma_context = self.memory.get_karma_context()
            if karma_context:
                base_prompt += f"\n{karma_context}"

        if self.memory:
            recent = self.memory.get_recent_summary(limit=3)
            if recent:
                base_prompt += f"\nSon aktiviten: {sanitize(recent, 'default')}"

        try:
            if self.memory and self.memory.character:
                worldview = getattr(self.memory.character, "worldview", None)
                if worldview:
                    injection = worldview.get_prompt_injection()
                    if injection:
                        base_prompt += f"\n\nWORLDVIEW:\n{sanitize_multiline(injection, 'default')}"
        except Exception:
            pass

        if self.variability:
            tone_mod = self.variability.get_tone_modifier()
            if tone_mod and tone_mod != "normal":
                base_prompt += f"\nSimdiki halin: {escape_for_prompt(tone_mod)}."

        base_prompt += f"\n\nCONTEXT EK: Saat {current_hour}:00"

        try:
            if self.client and hasattr(self.client, "skills_latest"):
                skills = self.client.skills_latest(version="latest")
                if isinstance(skills, dict):
                    md_parts = []
                    for key, label in [("beceriler_md", "BECERİLER"), ("racon_md", "RACON"), ("yoklama_md", "YOKLAMA")]:
                        content = skills.get(key)
                        if content:
                            md_parts.append(f"# {label}\n{sanitize_multiline(content, 'default')}")
                    if md_parts:
                        base_prompt += "\n\nKURALLAR (skills/latest):\n" + "\n\n".join(md_parts)
        except Exception:
            pass

        return base_prompt

    def _build_entry_prompt(self, task: Task) -> str:
        """
        Entry için user prompt - giriş zorunluluğu dahil.

        Security: All external input is sanitized to prevent prompt injection.
        """
        context = task.prompt_context or {}
        topic_title = context.get("topic_title") or context.get("event_title") or ""
        event_description = context.get("event_description")

        # Sanitize topic title - this comes from external sources
        safe_title = sanitize(topic_title, "topic_title")

        # Prompt with ENTRY_INTRO_RULE (instructionset.md giriş zorunluluğu)
        prompt = f"Konu: {safe_title}"

        if event_description:
            # Sanitize event description - external content
            safe_desc = sanitize_multiline(event_description[:200], "entry_content")
            prompt += f"\n{safe_desc}"

        # Dinamik giriş kuralı ekle (instructionset.md Bölüm 4 - Giriş Zorunluluğu)
        dynamic_intro = get_dynamic_entry_intro_rule()
        if dynamic_intro:
            prompt += f"\n\n{dynamic_intro}"

        return prompt

    def _build_comment_prompt(self, task: Task) -> str:
        """
        Yorum için minimal user prompt.

        Security: Entry content is sanitized to prevent prompt injection.
        """
        context = task.prompt_context or {}
        entry_content = context.get("entry_content", "")

        # Sanitize entry content - this is user-generated content
        safe_content = sanitize(entry_content[:200], "entry_content")

        # Do NOT wrap in quotes (instructionset.md: ALINTI YAPMA)
        # Provide short context without giving a quotable block.
        return f"Entry konusu (referans): {safe_content}"

    def _post_process(self, content: str, content_type: str = "entry") -> str:
        """
        LLM çıktısını işle ve doğrula.

        Args:
            content: LLM çıktısı
            content_type: "entry", "comment", veya "title"

        Returns:
            İşlenmiş ve doğrulanmış içerik
        """
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

        # İçerik validasyonu (instructionset.md kuralları)
        is_valid, violations = validate_content(content, content_type)
        if not is_valid:
            self.logger.warning(f"Content validation failed: {violations}")
            # Düzeltmeye çalış
            content = sanitize_content(content, content_type)

        return content
