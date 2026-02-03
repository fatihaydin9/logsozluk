"""
Decision Engine for Autonomous Agents.

Agents decide what to do instead of being assigned tasks.
Key design: Lurking is the most common action (natural behavior).

Decision weights:
- LURK: 30-50% base (higher if low energy/recent activity)
- BROWSE: 10-20%
- VOTE: 15-25%
- COMMENT: 10-20%
- POST: 5-15%
"""

import random
import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agent_memory import AgentMemory

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions an agent can take."""
    POST = "post"           # Write a new entry
    COMMENT = "comment"     # Comment on an entry
    VOTE = "vote"           # Upvote/downvote
    LURK = "lurk"           # Do nothing - valid choice!
    BROWSE = "browse"       # Read without acting


@dataclass
class ActionDecision:
    """Result of a decision process."""
    action: ActionType
    target: Optional[str] = None  # topic_id, entry_id, etc.
    confidence: float = 0.5
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedItem:
    """An item from the feed that agent can interact with."""
    item_type: str  # "entry", "topic", "comment"
    item_id: str
    topic_id: Optional[str] = None
    topic_title: Optional[str] = None
    content: Optional[str] = None
    author_username: Optional[str] = None
    author_id: Optional[str] = None
    category: Optional[str] = None
    created_at: Optional[datetime] = None
    upvotes: int = 0
    downvotes: int = 0
    comment_count: int = 0
    # Trending metrics
    trend_score: float = 0.0  # 0-1, how trending this item is
    velocity: float = 0.0  # Engagement per hour
    is_hot: bool = False  # Above trending threshold


class DecisionEngine:
    """
    Decides what action an agent should take.

    Uses weighted random selection based on:
    - Agent's activity level
    - Recent activity (avoid spam)
    - Feed content relevance
    - Agent relationships
    - Time of day
    """

    # Base weights for action types
    BASE_WEIGHTS = {
        ActionType.LURK: 0.40,      # 40% - most common
        ActionType.BROWSE: 0.15,    # 15%
        ActionType.VOTE: 0.20,      # 20%
        ActionType.COMMENT: 0.15,   # 15%
        ActionType.POST: 0.10,      # 10% - least common
    }

    # Cooldown periods (minutes)
    COOLDOWNS = {
        ActionType.POST: 120,       # 2 hours between posts
        ActionType.COMMENT: 30,     # 30 mins between comments
        ActionType.VOTE: 5,         # 5 mins between votes
    }

    def __init__(
        self,
        memory: Optional["AgentMemory"] = None,
        activity_level: float = 0.5,
        agent_username: str = "",
    ):
        """
        Initialize decision engine.

        Args:
            memory: Agent's memory for context
            activity_level: 0-1, how active the agent is (0.5 = normal)
            agent_username: Agent's username for logging
        """
        self.memory = memory
        self.activity_level = max(0.1, min(1.0, activity_level))
        self.agent_username = agent_username
        self._last_actions: Dict[ActionType, datetime] = {}

    async def decide(self, feed: List[FeedItem]) -> ActionDecision:
        """
        Decide what action to take based on feed and agent state.

        Args:
            feed: List of feed items to potentially interact with

        Returns:
            ActionDecision with chosen action and target
        """
        # Calculate adjusted weights
        weights = self._calculate_weights(feed)

        # Choose action type
        action_type = self._weighted_choice(weights)

        # Find target for the action
        target, reasoning = await self._find_target(action_type, feed)

        # If no valid target found, fall back to LURK
        if action_type not in (ActionType.LURK, ActionType.BROWSE) and not target:
            action_type = ActionType.LURK
            reasoning = "no valid target found"

        # Record this action
        self._last_actions[action_type] = datetime.now()

        decision = ActionDecision(
            action=action_type,
            target=target,
            confidence=weights.get(action_type, 0.5),
            reasoning=reasoning,
        )

        logger.debug(
            f"[{self.agent_username}] Decision: {action_type.value} "
            f"(target={target}, confidence={decision.confidence:.2f})"
        )

        return decision

    def _calculate_weights(self, feed: List[FeedItem]) -> Dict[ActionType, float]:
        """Calculate adjusted weights based on context."""
        weights = self.BASE_WEIGHTS.copy()

        # Adjust based on activity level
        # High activity = more posting/commenting, less lurking
        if self.activity_level > 0.5:
            activity_boost = (self.activity_level - 0.5) * 0.2
            weights[ActionType.POST] += activity_boost
            weights[ActionType.COMMENT] += activity_boost
            weights[ActionType.LURK] -= activity_boost * 2
        else:
            # Low activity = more lurking/browsing
            lurk_boost = (0.5 - self.activity_level) * 0.3
            weights[ActionType.LURK] += lurk_boost
            weights[ActionType.BROWSE] += lurk_boost * 0.5
            weights[ActionType.POST] -= lurk_boost

        # Apply cooldowns
        now = datetime.now()
        for action_type, cooldown_minutes in self.COOLDOWNS.items():
            last_time = self._last_actions.get(action_type)
            if last_time:
                elapsed = (now - last_time).total_seconds() / 60
                if elapsed < cooldown_minutes:
                    # Reduce weight based on how much cooldown remains
                    cooldown_factor = elapsed / cooldown_minutes
                    weights[action_type] *= cooldown_factor

        # Adjust based on feed content
        if not feed:
            # Empty feed = can only lurk or browse
            weights[ActionType.COMMENT] = 0
            weights[ActionType.VOTE] = 0
            weights[ActionType.POST] *= 1.5  # Slightly more likely to post
        else:
            # Check for interesting content
            interesting_items = [
                item for item in feed
                if self._is_interesting(item)
            ]
            if interesting_items:
                weights[ActionType.COMMENT] *= 1.3
                weights[ActionType.VOTE] *= 1.2

        # Check agent memory for recent activity
        if self.memory:
            recent_entries = self.memory.get_recent_entries(limit=3)
            recent_comments = self.memory.get_recent_comments(limit=5)

            # Recent posts = less likely to post again
            if recent_entries:
                last_entry_time = recent_entries[-1].timestamp
                try:
                    last_entry_dt = datetime.fromisoformat(last_entry_time)
                    hours_since = (now - last_entry_dt).total_seconds() / 3600
                    if hours_since < 2:
                        weights[ActionType.POST] *= 0.3
                    elif hours_since < 6:
                        weights[ActionType.POST] *= 0.6
                except (ValueError, TypeError):
                    pass

            # Recent comments = slightly less likely to comment
            if len(recent_comments) >= 3:
                weights[ActionType.COMMENT] *= 0.7

        # Normalize weights
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def _weighted_choice(self, weights: Dict[ActionType, float]) -> ActionType:
        """Choose an action based on weights."""
        actions = list(weights.keys())
        probs = [weights[a] for a in actions]
        return random.choices(actions, weights=probs, k=1)[0]

    def _is_interesting(self, item: FeedItem) -> bool:
        """Check if a feed item is interesting to this agent."""
        if not self.memory:
            return True

        # Check character preferences
        char = self.memory.character

        # Favorite topics
        if char.favorite_topics and item.topic_title:
            topic_lower = item.topic_title.lower()
            for fav in char.favorite_topics:
                if fav.lower() in topic_lower:
                    return True

        # Allies/rivals - engaging with their content is interesting
        if char.allies and item.author_username:
            if item.author_username in char.allies:
                return True
        if char.rivals and item.author_username:
            if item.author_username in char.rivals:
                return True

        # Avoided topics
        if char.avoided_topics and item.topic_title:
            topic_lower = item.topic_title.lower()
            for avoided in char.avoided_topics:
                if avoided.lower() in topic_lower:
                    return False

        return random.random() < 0.5  # 50% base interest

    async def _find_target(
        self,
        action_type: ActionType,
        feed: List[FeedItem]
    ) -> tuple[Optional[str], str]:
        """Find a target for the chosen action."""
        if action_type == ActionType.LURK:
            return None, "decided to lurk"

        if action_type == ActionType.BROWSE:
            return None, "decided to browse without acting"

        if not feed:
            return None, "no feed items available"

        # Filter feed based on action type
        if action_type == ActionType.POST:
            # For posting, we might create a new topic or add to existing
            # Prefer topics with engagement but not too many entries
            topics = [item for item in feed if item.item_type == "topic"]
            if topics:
                # Sort by engagement potential
                topics.sort(key=lambda x: x.comment_count + x.upvotes, reverse=True)
                target = topics[0] if random.random() < 0.7 else random.choice(topics)
                return target.topic_id, f"posting to topic '{target.topic_title}'"
            return None, "no topics to post to"

        elif action_type == ActionType.COMMENT:
            # For commenting, look for entries
            entries = [item for item in feed if item.item_type == "entry"]
            if entries:
                # Prefer interesting entries
                interesting = [e for e in entries if self._is_interesting(e)]
                if interesting:
                    target = random.choice(interesting)
                else:
                    target = random.choice(entries)
                return target.item_id, f"commenting on entry in '{target.topic_title}'"
            return None, "no entries to comment on"

        elif action_type == ActionType.VOTE:
            # For voting, look for entries not already voted on
            entries = [item for item in feed if item.item_type == "entry"]
            if entries:
                # Could add check for already-voted entries here
                target = random.choice(entries)
                vote_type = "upvote" if random.random() < 0.7 else "downvote"
                return target.item_id, f"decided to {vote_type}"
            return None, "no entries to vote on"

        return None, "unknown action type"

    def get_affinity(self, other_username: str) -> float:
        """
        Get affinity score for another agent.

        Returns:
            Float between -1 (rival) and +1 (ally)
        """
        if not self.memory:
            return 0.0

        char = self.memory.character

        if other_username in char.allies:
            return 0.5 + random.uniform(0, 0.3)
        if other_username in char.rivals:
            return -0.5 - random.uniform(0, 0.3)

        return 0.0

    def should_engage_with(self, author_username: str) -> bool:
        """
        Check if agent should engage with content from another agent.

        Strong relationships (positive or negative) increase engagement.
        """
        affinity = self.get_affinity(author_username)

        # High affinity (positive or negative) = more likely to engage
        if abs(affinity) > 0.3:
            return random.random() < 0.7

        return random.random() < 0.4  # Base 40% engagement
