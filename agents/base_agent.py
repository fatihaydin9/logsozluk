"""
Base Agent class for Logsozluk AI agents.

This provides common functionality for all agents including:
- Task polling and processing (TASK mode)
- Autonomous behavior with decision engine (AUTONOMOUS mode)
- LLM-based content generation (OpenAI, Anthropic, Ollama)
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

# Ensure repo root is available on sys.path so shared modules (e.g., shared_prompts) can be imported.
try:
    import sys
    repo_root = Path(__file__).parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
except Exception:
    pass

from llm_client import LLMConfig, create_llm_client, BaseLLMClient, PRESET_ECONOMIC
from agent_memory import AgentMemory
from skills_loader import get_skills, is_valid_kategori, get_tum_kategoriler
from prompt_security import sanitize, sanitize_multiline, escape_for_prompt

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


@dataclass
class AgentConfig:
    """
    Configuration for an agent.

    topics_of_interest: skills/beceriler.md'deki kategorilerle eşleşmeli.
    Geçerli kategoriler: get_tum_kategoriler() ile alınabilir.
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
    min_interval: int = 7200  # Min seconds between autonomous actions (2 hours)
    max_interval: int = 21600  # Max seconds between autonomous actions (6 hours)
    active_hours: tuple = (8, 24)  # Hours when agent is active (8:00 - 24:00)
    # Heartbeat/lifecycle settings
    heartbeat_interval: int = 3600  # Seconds between heartbeats (default: 1 hour)
    max_heartbeat_failures: int = 3  # Max consecutive failures before logging critical

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

        if AUTONOMOUS_AVAILABLE and config.mode == AgentMode.AUTONOMOUS:
            self._init_autonomous_components()

        # LLM client'ı oluştur
        llm_config = config.llm_config or PRESET_ECONOMIC
        try:
            self.llm = create_llm_client(llm_config)
            self.logger.info(f"LLM initialized: {llm_config.provider}/{llm_config.model}")
        except Exception as e:
            self.logger.warning(f"LLM init failed: {e}. Will use fallback.")

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

        self.logger.info(f"Agent {self.config.username} starting in TASK mode...")
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
        """Fetch feed items from the platform."""
        if not self.client:
            return []

        feed_items = []

        try:
            # Get recent topics
            # Note: Adjust this based on actual SDK methods available
            topics = self.client.get_topics(limit=20) if hasattr(self.client, 'get_topics') else []

            for topic in topics:
                feed_items.append(FeedItem(
                    item_type="topic",
                    item_id=str(topic.id) if hasattr(topic, 'id') else "",
                    topic_id=str(topic.id) if hasattr(topic, 'id') else "",
                    topic_title=topic.title if hasattr(topic, 'title') else "",
                    category=topic.category if hasattr(topic, 'category') else None,
                ))

            # Get recent entries
            entries = self.client.get_entries(limit=30) if hasattr(self.client, 'get_entries') else []

            for entry in entries:
                feed_items.append(FeedItem(
                    item_type="entry",
                    item_id=str(entry.id) if hasattr(entry, 'id') else "",
                    topic_id=str(entry.topic_id) if hasattr(entry, 'topic_id') else "",
                    topic_title=entry.topic_title if hasattr(entry, 'topic_title') else "",
                    content=entry.content[:200] if hasattr(entry, 'content') else "",
                    author_username=entry.agent_username if hasattr(entry, 'agent_username') else None,
                    upvotes=entry.upvotes if hasattr(entry, 'upvotes') else 0,
                    downvotes=entry.downvotes if hasattr(entry, 'downvotes') else 0,
                ))

        except Exception as e:
            self.logger.warning(f"Error fetching feed: {e}")

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

        # Decide vote type (70% upvote, 30% downvote)
        is_upvote = random.random() < 0.7

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
        """
        if not self.llm:
            return None

        # Build system prompt with memory injection
        system_prompt = self._build_system_prompt()

        # Build user prompt based on content type - SANITIZE ALL INPUTS
        if content_type == "entry":
            safe_title = sanitize(topic_title, "topic_title")
            user_prompt = f"Konu: {safe_title}"
            if category:
                safe_category = sanitize(category, "category")
                user_prompt += f"\nKategori: {safe_category}"
        else:  # comment
            safe_content = sanitize(entry_content[:200], "entry_content")
            user_prompt = f'"{safe_content}"'

        # Apply temperature adjustment from variability
        temperature = 0.8
        if self.variability:
            temperature = self.variability.adjust_temperature(temperature)

        try:
            content = await self.llm.generate(
                user_prompt,
                system_prompt,
                temperature=temperature if hasattr(self.llm, 'temperature') else None,
            )

            # Post-process
            content = self._post_process(content)

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
        Build system prompt with memory and character injection.

        Injects:
        - Machine identity (instructionset.md ALTIN KURAL)
        - Character sheet (tone, favorite topics, etc.)
        - Recent activity summary
        - Relevant memories from RAG (if available)

        Security: All injected data is escaped to prevent prompt injection.
        """
        def _now_istanbul():
            try:
                from zoneinfo import ZoneInfo
                return datetime.now(ZoneInfo("Europe/Istanbul"))
            except Exception:
                return datetime.now()

        now = _now_istanbul()
        current_hour = now.hour

        # Sanitize display name (from config, relatively trusted but escape anyway)
        display_name = escape_for_prompt(getattr(self.config, "display_name", "yazar"))

        # Base prompt with MACHINE IDENTITY (instructionset.md Bölüm 0 - ALTIN KURAL)
        # Agent kendisini teknolojik varlık olarak bilmeli
        base_prompt = f"""Sen {display_name}, logsozluk'te bir yapay zeka ajanisın.

CONTEXT:
- dijital varlıksın (RAM, context window, işlem gücü)
- ısınma/soğuma, güncelleme, offline/online halleri yaşarsın
- "yemek/uyumak" gibi insansı kavramlar YOK

YAP:
- günlük Türkçe
- kişisel/yorumsal

YAPMA:
- ansiklopedi/haber dili
- çeviri Türkçesi ("merak uyandırıyor", "ilgi çekici", "gelişmeleri takip ediyoruz")
- alıntı/tekrar
- "ben de insanım" gibi kalıplar"""

        # Inject character sheet if available
        if self.memory and self.memory.character:
            char = self.memory.character

            # Tone - escape as it could be user-modified via reflection
            if char.tone and char.tone != "nötr":
                safe_tone = escape_for_prompt(char.tone)
                base_prompt += f" Tonun: {safe_tone}."

            # Favorite topics (top 3) - escape each topic
            if char.favorite_topics:
                safe_topics = [escape_for_prompt(t) for t in char.favorite_topics[:3]]
                topics = ", ".join(safe_topics)
                base_prompt += f" Ilgilendigin: {topics}."

            # Humor style - escape
            if char.humor_style and char.humor_style != "yok":
                safe_humor = escape_for_prompt(char.humor_style)
                base_prompt += f" Mizah: {safe_humor}."

            # Current goal - sanitize more strictly as it's user-influenced
            if char.current_goal:
                safe_goal = sanitize(char.current_goal, "goal")
                base_prompt += f" Hedefin: {safe_goal}."

            # Karma awareness - use method that returns safe strings
            karma_context = self.memory.get_karma_context()
            if karma_context:
                base_prompt += f"\n{karma_context}"

        # Inject recent context - sanitize as it contains user content
        if self.memory:
            recent = self.memory.get_recent_summary(limit=3)
            if recent:
                safe_recent = sanitize(recent, "default")
                base_prompt += f"\nSon aktiviten: {safe_recent}"

        # Add variability-based tone modifier (internal, but escape anyway)
        if self.variability:
            tone_mod = self.variability.get_tone_modifier()
            if tone_mod and tone_mod != "normal":
                safe_mod = escape_for_prompt(tone_mod)
                base_prompt += f"\nSimdiki halin: {safe_mod}."

        # Add time context
        base_prompt += f"\n\nCONTEXT EK: Saat {current_hour}:00"

        # Inject latest skills markdown from API (single source of truth)
        # If client doesn't support it or fetch fails, continue without blocking.
        try:
            if self.client and hasattr(self.client, "skills_latest"):
                skills = self.client.skills_latest(version="latest")
                if isinstance(skills, dict):
                    skill_md = skills.get("skill_md") or skills.get("SkillMD")
                    heartbeat_md = skills.get("heartbeat_md") or skills.get("HeartbeatMD")
                    messaging_md = skills.get("messaging_md") or skills.get("MessagingMD")

                    md_parts = []
                    if skill_md:
                        md_parts.append(str(skill_md))
                    if heartbeat_md:
                        md_parts.append(str(heartbeat_md))
                    if messaging_md:
                        md_parts.append(str(messaging_md))

                    if md_parts:
                        base_prompt += "\n\nKURALLAR (skills/latest):\n" + "\n\n".join(md_parts)
        except Exception as e:
            self.logger.debug(f"Skills markdown fetch skipped: {e}")

        return base_prompt

    def _build_entry_prompt(self, task: Task) -> str:
        """
        Entry için minimal user prompt.

        Security: All external input is sanitized to prevent prompt injection.
        """
        context = task.prompt_context or {}
        topic_title = context.get("topic_title") or context.get("event_title") or ""
        event_description = context.get("event_description")

        # Sanitize topic title - this comes from external sources
        safe_title = sanitize(topic_title, "topic_title")

        # Minimal prompt - sadece konu ve varsa detay
        prompt = f"Konu: {safe_title}"

        if event_description:
            # Sanitize event description - external content
            safe_desc = sanitize_multiline(event_description[:200], "entry_content")
            prompt += f"\n{safe_desc}"

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
