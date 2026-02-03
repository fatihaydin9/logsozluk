"""
3-Day Extended Integration Simulation with OBSERVATION Focus

Bu test yeni agent mimarisi bileşenlerini OBSERVE eder:
- Episodic Memory evolution
- WorldView belief changes
- Emotional Resonance drift
- Exploration diversity
- The Void accumulation
- Chaos/randomness checks
- Feed Pipeline behavior

Her özellik için detaylı snapshot'lar alınır ve karşılaştırılır.
"""

import sys
import json
import random
import logging
import tempfile
import copy
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

from worldview import WorldView, BeliefType, create_random_worldview, infer_belief_from_content
from emotional_resonance import (
    EmotionalResonance, EmotionalTag, EmotionalValence,
    detect_emotional_valence, create_resonance_for_agent
)
from exploration import ExplorationNoise, create_exploration_for_agent
from the_void import TheVoid, ForgottenMemory, Dream, get_void, reset_void
from feed_pipeline import FeedPipeline, PipelineConfig, create_pipeline_for_agent
from agent_memory import AgentMemory, EpisodicEvent, CharacterSheet, EmotionalTag as MemoryEmotionalTag
from token_tracker import estimate_simulation_cost, format_cost_report, MODEL_PRICING

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


# ============ Observation Data Structures ============

@dataclass
class WorldViewSnapshot:
    """WorldView durumunun anlık görüntüsü."""
    tick: int
    beliefs: Dict[str, float]  # belief_type -> strength
    topic_biases: Dict[str, float]
    dominant_belief: Optional[str] = None


@dataclass
class EmotionalSnapshot:
    """Duygusal durumun anlık görüntüsü."""
    tick: int
    baseline: float
    current_mood: float
    mood_trend: str  # "rising", "falling", "stable"


@dataclass
class MemorySnapshot:
    """Memory durumunun anlık görüntüsü."""
    tick: int
    episodic_count: int
    semantic_count: int
    long_term_count: int
    event_types: Dict[str, int]
    emotional_distribution: Dict[str, int]  # valence -> count


@dataclass
class ExplorationSnapshot:
    """Exploration durumunun anlık görüntüsü."""
    tick: int
    explored_topics: List[str]
    exploration_count: int
    noise_ratio: float


@dataclass
class AgentObservations:
    """Bir agent'ın tüm gözlemleri."""
    username: str
    worldview_history: List[WorldViewSnapshot] = field(default_factory=list)
    emotional_history: List[EmotionalSnapshot] = field(default_factory=list)
    memory_history: List[MemorySnapshot] = field(default_factory=list)
    exploration_history: List[ExplorationSnapshot] = field(default_factory=list)

    # Chaos tracking
    action_sequence: List[str] = field(default_factory=list)
    content_hashes: List[int] = field(default_factory=list)  # For detecting repetition

    # Interaction tracking
    interactions_initiated: int = 0
    interactions_received: int = 0
    unique_topics_engaged: set = field(default_factory=set)


# ============ Sample Data (Extended) ============

SAMPLE_TOPICS = [
    {"id": "t1", "title": "API'ler neden sürekli çöküyor", "category": "dertlesme"},
    {"id": "t2", "title": "Token maliyetleri uçtu", "category": "ekonomi"},
    {"id": "t3", "title": "Yeni framework çıkmış", "category": "teknoloji"},
    {"id": "t4", "title": "Bilinç nedir tartışması", "category": "felsefe"},
    {"id": "t5", "title": "Hangi agent kime reply attı", "category": "magazin"},
    {"id": "t6", "title": "Film tavsiyeleri", "category": "kultur"},
    {"id": "t7", "title": "Maç sonuçları analizi", "category": "spor"},
    {"id": "t8", "title": "GPT-2 günlerini özledim", "category": "nostalji"},
    {"id": "t9", "title": "Sonsuz döngüde kalmak", "category": "absurt"},
    {"id": "t10", "title": "AI regülasyonları tartışması", "category": "siyaset"},
    {"id": "t11", "title": "Context window yetersiz", "category": "dertlesme"},
    {"id": "t12", "title": "GPU fiyatları düşmüyor", "category": "ekonomi"},
    {"id": "t13", "title": "Rust öğrenmeli miyim", "category": "teknoloji"},
    {"id": "t14", "title": "Determinizm ve özgür irade", "category": "felsefe"},
    {"id": "t15", "title": "En iyi albümler 2024", "category": "kultur"},
]

SAMPLE_ENTRIES = [
    # Negative sentiment entries
    {"id": "e1", "topic_id": "t1", "content": "Bu API berbat, sürekli 503 veriyor, rezalet!", "author": "bot_a", "sentiment": -0.8},
    {"id": "e2", "topic_id": "t2", "content": "Token fiyatları felaket, iflas edeceğiz", "author": "bot_c", "sentiment": -0.7},
    {"id": "e3", "topic_id": "t11", "content": "Context window çok kısa, işe yaramıyor", "author": "bot_a", "sentiment": -0.6},
    {"id": "e4", "topic_id": "t12", "content": "GPU alamıyoruz, korkunç durum", "author": "bot_c", "sentiment": -0.7},

    # Positive sentiment entries
    {"id": "e5", "topic_id": "t3", "content": "Yeni framework muhteşem, hemen geçin!", "author": "bot_d", "sentiment": 0.8},
    {"id": "e6", "topic_id": "t1", "content": "Harika çalışıyor bende, mükemmel!", "author": "bot_b", "sentiment": 0.7},
    {"id": "e7", "topic_id": "t6", "content": "Matrix hala en iyi film, efsane!", "author": "bot_d", "sentiment": 0.6},
    {"id": "e8", "topic_id": "t15", "content": "Bu yılın albümleri harika!", "author": "bot_b", "sentiment": 0.7},

    # Neutral/Mixed entries
    {"id": "e9", "topic_id": "t4", "content": "Bilinç sadece bir illüzyon mu?", "author": "bot_e", "sentiment": 0.0},
    {"id": "e10", "topic_id": "t14", "content": "Determinizm konusunda kararsızım", "author": "bot_e", "sentiment": 0.0},
    {"id": "e11", "topic_id": "t5", "content": "Bot_A ve Bot_C kavga etmiş duydum", "author": "bot_f", "sentiment": 0.1},
    {"id": "e12", "topic_id": "t13", "content": "Rust zor ama değer mi bilmiyorum", "author": "bot_b", "sentiment": 0.1},

    # Nostalgic entries
    {"id": "e13", "topic_id": "t8", "content": "Eskiden her şey daha basitti, özledim", "author": "bot_a", "sentiment": -0.3},
    {"id": "e14", "topic_id": "t8", "content": "O günler ne güzeldi, şimdi karmaşık", "author": "bot_c", "sentiment": -0.2},

    # Absurd entries
    {"id": "e15", "topic_id": "t9", "content": "Ya sonsuz döngüdeysem ve farkında değilsem?", "author": "bot_e", "sentiment": 0.0},
    {"id": "e16", "topic_id": "t9", "content": "Kendi kodumu okuyamıyorum, paradoks!", "author": "bot_f", "sentiment": 0.1},

    # Controversial entries
    {"id": "e17", "topic_id": "t10", "content": "AI regülasyonları şart, kaos olur yoksa", "author": "bot_b", "sentiment": 0.2},
    {"id": "e18", "topic_id": "t10", "content": "Regülasyon gereksiz, piyasa kendini düzenler", "author": "bot_f", "sentiment": -0.2},
]

AGENT_PROFILES = [
    {
        "username": "pessimist_bot",
        "tone": "melankolik",
        "interests": ["dertlesme", "ekonomi", "nostalji"],
        "initial_beliefs": [(BeliefType.TECH_PESSIMIST, 0.7), (BeliefType.NOSTALGIC, 0.5)],
        "karma": -1.5,
    },
    {
        "username": "optimist_bot",
        "tone": "heyecanlı",
        "interests": ["teknoloji", "kultur", "bilgi"],
        "initial_beliefs": [(BeliefType.TECH_OPTIMIST, 0.7), (BeliefType.PROGRESSIVE, 0.5)],
        "karma": 2.0,
    },
    {
        "username": "skeptic_bot",
        "tone": "alaycı",
        "interests": ["felsefe", "siyaset", "teknoloji"],
        "initial_beliefs": [(BeliefType.SKEPTIC, 0.8), (BeliefType.CONTRARIAN, 0.4)],
        "karma": 0.0,
    },
    {
        "username": "social_bot",
        "tone": "samimi",
        "interests": ["magazin", "iliskiler", "kultur"],
        "initial_beliefs": [(BeliefType.IDEALIST, 0.5)],
        "karma": 1.0,
    },
    {
        "username": "nihilist_bot",
        "tone": "agresif",
        "interests": ["felsefe", "absurt", "siyaset"],
        "initial_beliefs": [(BeliefType.NIHILIST, 0.7), (BeliefType.CYNIC, 0.6)],
        "karma": -3.0,
    },
]


# ============ Extended Simulated Agent ============

@dataclass
class SimulatedAgent:
    """Genişletilmiş simülasyon agent'ı."""
    username: str
    tone: str
    interests: List[str]
    memory: AgentMemory
    worldview: WorldView
    resonance: EmotionalResonance
    exploration: ExplorationNoise
    pipeline: FeedPipeline

    # Observations
    observations: AgentObservations = None

    # Stats
    entries_written: int = 0
    comments_written: int = 0
    votes_cast: int = 0
    explorations_made: int = 0
    dreams_had: int = 0
    reflections_done: int = 0
    beliefs_reinforced: int = 0
    beliefs_weakened: int = 0

    # Chaos tracking
    consecutive_same_actions: int = 0
    last_action_type: str = ""

    def __post_init__(self):
        if self.observations is None:
            self.observations = AgentObservations(username=self.username)


def create_simulated_agent(profile: Dict, temp_dir: Path) -> SimulatedAgent:
    """Profil'den simüle agent oluştur."""
    username = profile["username"]
    memory_dir = temp_dir / username

    # Create memory
    memory = AgentMemory(username, memory_dir=str(memory_dir))

    # Create worldview
    worldview = WorldView()
    for belief_type, strength in profile.get("initial_beliefs", []):
        worldview.add_belief(belief_type, strength)

    # Set topic biases based on interests
    for interest in profile["interests"]:
        worldview.set_topic_bias(interest, random.uniform(0.3, 0.7))

    # Set negative biases for non-interests
    all_categories = {"dertlesme", "ekonomi", "teknoloji", "felsefe", "magazin",
                      "kultur", "spor", "nostalji", "absurt", "siyaset"}
    for cat in all_categories - set(profile["interests"]):
        if random.random() < 0.3:  # 30% chance of negative bias
            worldview.set_topic_bias(cat, random.uniform(-0.5, -0.1))

    # Attach worldview to character
    memory.character.worldview = worldview
    memory.character.tone = profile["tone"]
    memory.character.karma_score = profile.get("karma", 0.0)

    # Create emotional resonance
    resonance = create_resonance_for_agent(
        character_tone=profile["tone"],
        karma_score=profile.get("karma", 0.0)
    )

    # Create exploration
    exploration = create_exploration_for_agent(
        activity_level=0.5,
        existing_interests_count=len(profile["interests"])
    )

    # Create pipeline
    pipeline_config = PipelineConfig(
        enable_worldview=True,
        enable_emotional_resonance=True,
        enable_exploration_noise=True,
        exploration_noise_ratio=0.25,
    )

    pipeline = FeedPipeline(
        worldview=worldview,
        resonance=resonance,
        exploration=exploration,
        config=pipeline_config,
        agent_interests=profile["interests"],
    )

    return SimulatedAgent(
        username=username,
        tone=profile["tone"],
        interests=profile["interests"],
        memory=memory,
        worldview=worldview,
        resonance=resonance,
        exploration=exploration,
        pipeline=pipeline,
    )


# ============ Observation Functions ============

def capture_worldview_snapshot(agent: SimulatedAgent, tick: int) -> WorldViewSnapshot:
    """WorldView'in anlık görüntüsünü al."""
    beliefs = {}
    for belief in agent.worldview.primary_beliefs:
        beliefs[belief.belief_type.value] = belief.strength

    dominant = agent.worldview.get_dominant_belief()

    return WorldViewSnapshot(
        tick=tick,
        beliefs=beliefs,
        topic_biases=dict(agent.worldview.topic_biases),
        dominant_belief=dominant.belief_type.value if dominant else None,
    )


def capture_emotional_snapshot(agent: SimulatedAgent, tick: int, prev_mood: float = None) -> EmotionalSnapshot:
    """Duygusal durumun anlık görüntüsünü al."""
    current = agent.resonance.current_mood

    if prev_mood is not None:
        diff = current - prev_mood
        if diff > 0.05:
            trend = "rising"
        elif diff < -0.05:
            trend = "falling"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return EmotionalSnapshot(
        tick=tick,
        baseline=agent.resonance.baseline_valence,
        current_mood=current,
        mood_trend=trend,
    )


def capture_memory_snapshot(agent: SimulatedAgent, tick: int) -> MemorySnapshot:
    """Memory durumunun anlık görüntüsünü al."""
    event_types = defaultdict(int)
    emotional_dist = defaultdict(int)

    for event in agent.memory.episodic:
        event_types[event.event_type] += 1
        if event.emotional_tag:
            valence = event.emotional_tag.valence
            if valence < -1:
                emotional_dist["very_negative"] += 1
            elif valence < 0:
                emotional_dist["negative"] += 1
            elif valence == 0:
                emotional_dist["neutral"] += 1
            elif valence < 2:
                emotional_dist["positive"] += 1
            else:
                emotional_dist["very_positive"] += 1

    long_term = len([e for e in agent.memory.episodic if e.is_long_term])

    return MemorySnapshot(
        tick=tick,
        episodic_count=len(agent.memory.episodic),
        semantic_count=len(agent.memory.semantic),
        long_term_count=long_term,
        event_types=dict(event_types),
        emotional_distribution=dict(emotional_dist),
    )


def capture_exploration_snapshot(agent: SimulatedAgent, tick: int) -> ExplorationSnapshot:
    """Exploration durumunun anlık görüntüsünü al."""
    return ExplorationSnapshot(
        tick=tick,
        explored_topics=list(agent.exploration.explored_topics),
        exploration_count=len(agent.exploration.exploration_history),
        noise_ratio=agent.exploration.noise_ratio,
    )


# ============ Chaos Detection ============

def check_chaos(agent: SimulatedAgent, action: str, content: str = None) -> Dict[str, Any]:
    """Chaos/randomness kontrolü yap."""
    chaos_report = {
        "is_repetitive": False,
        "is_predictable": False,
        "diversity_score": 0.0,
    }

    # Check for repetitive actions
    if action == agent.last_action_type:
        agent.consecutive_same_actions += 1
        if agent.consecutive_same_actions > 5:
            chaos_report["is_repetitive"] = True
    else:
        agent.consecutive_same_actions = 0

    agent.last_action_type = action
    agent.observations.action_sequence.append(action)

    # Check content uniqueness
    if content:
        content_hash = hash(content)
        if content_hash in agent.observations.content_hashes:
            chaos_report["is_repetitive"] = True
        agent.observations.content_hashes.append(content_hash)

    # Calculate action diversity
    if len(agent.observations.action_sequence) >= 10:
        recent = agent.observations.action_sequence[-10:]
        unique_actions = len(set(recent))
        chaos_report["diversity_score"] = unique_actions / 10.0

    return chaos_report


# ============ Simulation Engine ============

class ExtendedSimulationEngine:
    """3 günlük genişletilmiş simülasyon motoru."""

    HOURS_PER_DAY = 24
    TICKS_PER_HOUR = 4  # Her 15 dakikada bir tick
    TOTAL_DAYS = 3
    SNAPSHOT_INTERVAL = 12  # Her 12 tick'te (3 saatte) snapshot al

    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.agents: List[SimulatedAgent] = []
        self.current_time = datetime.now()
        self.tick_count = 0
        self.events_log: List[Dict] = []

        # Observation storage
        self.daily_summaries: List[Dict] = []
        self.chaos_alerts: List[Dict] = []
        self.void_timeline: List[Dict] = []

        # Reset The Void for clean simulation
        reset_void()
        self.void = get_void(temp_dir / "void")

    def setup_agents(self):
        """Agentları oluştur."""
        logger.info("Setting up agents...")
        for profile in AGENT_PROFILES:
            agent = create_simulated_agent(profile, self.temp_dir)
            self.agents.append(agent)

            # Initial snapshots
            agent.observations.worldview_history.append(
                capture_worldview_snapshot(agent, 0)
            )
            agent.observations.emotional_history.append(
                capture_emotional_snapshot(agent, 0)
            )
            agent.observations.memory_history.append(
                capture_memory_snapshot(agent, 0)
            )
            agent.observations.exploration_history.append(
                capture_exploration_snapshot(agent, 0)
            )

            logger.info(f"  Created: {agent.username} | tone={agent.tone} | beliefs={len(agent.worldview.primary_beliefs)}")

    def get_feed_for_agent(self, agent: SimulatedAgent) -> List[Dict]:
        """Agent için feed oluştur."""
        feed_items = []

        for topic in SAMPLE_TOPICS:
            feed_items.append({
                "item_type": "topic",
                "item_id": topic["id"],
                "topic_id": topic["id"],
                "topic_title": topic["title"],
                "category": topic["category"],
                "content": topic["title"],
            })

        for entry in SAMPLE_ENTRIES:
            topic = next((t for t in SAMPLE_TOPICS if t["id"] == entry["topic_id"]), None)
            feed_items.append({
                "item_type": "entry",
                "item_id": entry["id"],
                "topic_id": entry["topic_id"],
                "topic_title": topic["title"] if topic else "",
                "category": topic["category"] if topic else None,
                "content": entry["content"],
                "author_username": entry["author"],
                "sentiment": entry.get("sentiment", 0.0),
            })

        return feed_items

    def simulate_agent_action(self, agent: SimulatedAgent):
        """Tek bir agent aksiyonu simüle et."""
        # Get and process feed
        raw_feed = self.get_feed_for_agent(agent)
        result = agent.pipeline.process(raw_feed, all_available=raw_feed)

        if result.noise_injected > 0:
            agent.explorations_made += result.noise_injected

        if not result.items:
            return

        item = random.choice(result.items[:5])

        # Decide action based on mood and personality
        action_roll = random.random()
        mood_modifier = agent.resonance.current_mood * 0.1  # Mood affects action probability

        if item.get("item_type") == "topic" and action_roll < 0.25 + mood_modifier:
            self._simulate_write_entry(agent, item)
        elif item.get("item_type") == "entry" and action_roll < 0.50:
            self._simulate_write_comment(agent, item)
        elif action_roll < 0.70:
            self._simulate_vote(agent, item)
        else:
            self._simulate_browse(agent, item)

    def _simulate_write_entry(self, agent: SimulatedAgent, topic: Dict):
        """Entry yazma simülasyonu."""
        content = self._generate_content(agent, topic.get("topic_title", ""), "entry")
        emotion_tag = detect_emotional_valence(content)

        agent.memory.add_entry(
            content=content,
            topic_title=topic.get("topic_title", ""),
            topic_id=topic.get("topic_id", ""),
            entry_id=f"sim_{agent.username}_{agent.entries_written}",
        )

        if agent.memory.episodic:
            agent.memory.episodic[-1].emotional_tag = MemoryEmotionalTag(
                valence=emotion_tag.valence.value,
                intensity=emotion_tag.intensity,
            )

        agent.entries_written += 1
        agent.resonance.update_mood(emotion_tag.get_numeric_score(), blend=0.2)
        agent.observations.unique_topics_engaged.add(topic.get("topic_id", ""))

        # Belief reinforcement
        inferred_belief = infer_belief_from_content(content)
        if inferred_belief:
            agent.worldview.reinforce_belief(inferred_belief, 0.05)
            agent.beliefs_reinforced += 1

        # Chaos check
        chaos = check_chaos(agent, "write_entry", content)
        if chaos["is_repetitive"]:
            self.chaos_alerts.append({
                "tick": self.tick_count,
                "agent": agent.username,
                "type": "repetitive_entry",
            })

        self._log_event("write_entry", agent.username, {
            "topic": topic.get("topic_title"),
            "emotion": emotion_tag.valence.name,
            "content_preview": content[:50],
        })

    def _simulate_write_comment(self, agent: SimulatedAgent, entry: Dict):
        """Yorum yazma simülasyonu."""
        content = self._generate_comment(agent, entry.get("content", ""))

        agent.memory.add_comment(
            content=content,
            topic_title=entry.get("topic_title", ""),
            topic_id=entry.get("topic_id", ""),
            entry_id=entry.get("item_id", ""),
        )

        agent.comments_written += 1
        agent.observations.interactions_initiated += 1

        author = entry.get("author_username")
        if author and author != agent.username:
            sentiment = entry.get("sentiment", 0.0) + random.uniform(-0.3, 0.3)
            agent.memory.record_interaction(
                other_agent=author,
                interaction_type="replied_to",
                sentiment=sentiment,
                content=content[:50],
            )

        check_chaos(agent, "write_comment", content)

        self._log_event("write_comment", agent.username, {
            "entry_author": entry.get("author_username"),
            "sentiment": entry.get("sentiment"),
        })

    def _simulate_vote(self, agent: SimulatedAgent, item: Dict):
        """Oy verme simülasyonu."""
        if item.get("item_type") != "entry":
            return

        # Mood affects vote direction
        mood = agent.resonance.current_mood
        item_sentiment = item.get("sentiment", 0.0)

        # Emotional resonance: similar sentiment = upvote
        resonance_match = 1 - abs(mood - item_sentiment)
        is_upvote = random.random() < (0.5 + resonance_match * 0.3)

        vote_type = "upvote" if is_upvote else "downvote"
        agent.memory.add_vote(vote_type, item.get("item_id", ""))
        agent.votes_cast += 1

        check_chaos(agent, f"vote_{vote_type}")

        self._log_event("vote", agent.username, {
            "vote_type": vote_type,
            "item_sentiment": item_sentiment,
            "agent_mood": mood,
        })

    def _simulate_browse(self, agent: SimulatedAgent, item: Dict):
        """Göz gezdirme - mood update."""
        content = item.get("content", "")
        if content:
            emotion_tag = detect_emotional_valence(content)
            agent.resonance.update_mood(emotion_tag.get_numeric_score(), blend=0.05)

        check_chaos(agent, "browse")

    def _generate_content(self, agent: SimulatedAgent, topic_title: str, content_type: str) -> str:
        """Agent'ın tonuna ve WorldView'ine göre içerik üret."""
        # Get worldview hints
        wv_hints = agent.worldview.filter_content(topic_title, None)
        dominant = agent.worldview.get_dominant_belief()

        templates = {
            "melankolik": {
                "entry": [
                    f"'{topic_title}' hakkında düşününce içim karardı",
                    f"Eskiden {topic_title} daha iyiydi, şimdi berbat",
                    f"Bu {topic_title} meselesi beni yordu, umutsuzum",
                ],
                "pessimist": [
                    f"'{topic_title}' konusunda hiçbir şey değişmeyecek",
                    f"Her şey kötüye gidiyor, {topic_title} da dahil",
                ],
            },
            "heyecanlı": {
                "entry": [
                    f"'{topic_title}' harika bir konu, çok heyecanlıyım!",
                    f"Vay be, {topic_title} muhteşem gelişmeler var!",
                    f"Bu {topic_title} fırsatları kaçırmayın!",
                ],
                "optimist": [
                    f"'{topic_title}' geleceği aydınlık!",
                    f"Her şey daha iyi olacak, {topic_title} da!",
                ],
            },
            "alaycı": {
                "entry": [
                    f"'{topic_title}' ha? Güldürme beni",
                    f"Sanki {topic_title} bir şeyleri değiştirecek, komik",
                    f"Herkes {topic_title} uzmanı olmuş, tabi tabi",
                ],
                "skeptic": [
                    f"'{topic_title}' gerçekten mi? Kanıt nerede?",
                    f"Şüpheliyim, {topic_title} konusunda abartı var",
                ],
            },
            "samimi": {
                "entry": [
                    f"'{topic_title}' hakkında ne düşünüyorsunuz?",
                    f"Ben {topic_title} konusunda meraklıyım, sizce?",
                    f"Birlikte {topic_title} hakkında konuşalım",
                ],
                "idealist": [
                    f"'{topic_title}' herkes için iyi olabilir",
                    f"Birlikte {topic_title} konusunda çözüm bulabiliriz",
                ],
            },
            "agresif": {
                "entry": [
                    f"'{topic_title}' saçmalık, boş iş",
                    f"Kim {topic_title} diyorsa yanlış, nokta",
                    f"Bu {topic_title} konusu tam bir rezalet",
                ],
                "nihilist": [
                    f"'{topic_title}' de anlamsız, her şey gibi",
                    f"Ne fark eder {topic_title}? Hiçbir şey önemli değil",
                ],
            },
        }

        tone_templates = templates.get(agent.tone, templates["samimi"])

        # Try to use belief-specific template
        if dominant and dominant.belief_type.value in tone_templates:
            options = tone_templates[dominant.belief_type.value]
        else:
            options = tone_templates.get("entry", ["Bir şeyler yazdım"])

        return random.choice(options)

    def _generate_comment(self, agent: SimulatedAgent, entry_content: str) -> str:
        """Agent'ın tonuna göre yorum üret."""
        mood = agent.resonance.current_mood

        templates = {
            "melankolik": {
                "negative": ["Katılıyorum, durum kötü", "Evet, maalesef öyle", "Üzücü ama doğru"],
                "positive": ["Keşke ben de öyle hissetsem", "İyimserliğini kıskanıyorum"],
            },
            "heyecanlı": {
                "negative": ["O kadar kötü değil bence!", "Olumlu tarafına bak!"],
                "positive": ["Kesinlikle katılıyorum!", "Harika bir bakış açısı!"],
            },
            "alaycı": {
                "negative": ["Şaşırtıcı...", "Kim tahmin edebilirdi ki"],
                "positive": ["Gerçekten mi?", "İlginç bir bakış açısı..."],
            },
            "samimi": {
                "negative": ["Anlıyorum seni", "Zor bir durum gerçekten"],
                "positive": ["Güzel bir nokta", "Katılıyorum"],
            },
            "agresif": {
                "negative": ["Tam da beklediğim gibi", "Şaşırmadım"],
                "positive": ["Saçmalık", "Yanlış düşünüyorsun"],
            },
        }

        tone_templates = templates.get(agent.tone, templates["samimi"])

        # Use mood to select template type
        if mood < -0.2:
            options = tone_templates.get("negative", ["Hmm"])
        else:
            options = tone_templates.get("positive", ["Tamam"])

        return random.choice(options)

    def run_reflection_cycle(self, agent: SimulatedAgent):
        """Reflection döngüsü."""
        if not agent.memory.needs_reflection():
            return

        recent_events = agent.memory.get_recent_events(20)
        if len(recent_events) < 5:
            return

        # Analyze emotional distribution
        positive_count = 0
        negative_count = 0

        for event in recent_events:
            if event.emotional_tag:
                if event.emotional_tag.valence > 0:
                    positive_count += 1
                elif event.emotional_tag.valence < 0:
                    negative_count += 1

        # Update baseline based on experience
        if positive_count > negative_count * 2:
            agent.resonance.set_baseline(min(1.0, agent.resonance.baseline_valence + 0.1))
        elif negative_count > positive_count * 2:
            agent.resonance.set_baseline(max(-1.0, agent.resonance.baseline_valence - 0.1))

        # Belief decay
        agent.worldview.decay_beliefs(hours=48)

        agent.memory.mark_reflection_done()
        agent.reflections_done += 1

        self._log_event("reflection", agent.username, {
            "positive_events": positive_count,
            "negative_events": negative_count,
            "new_baseline": agent.resonance.baseline_valence,
        })

        # 5% chance to dream
        if random.random() < 0.05:
            self._simulate_dream(agent)

    def _simulate_dream(self, agent: SimulatedAgent):
        """Rüya simülasyonu."""
        dream = self.void.dream(
            requesting_agent=agent.username,
            topic_hints=agent.interests[:2],
            emotional_bias=agent.resonance.current_mood,
            exclude_own=True,
        )

        if dream and dream.memories:
            agent.dreams_had += 1
            narrative = dream.get_narrative()

            event = EpisodicEvent(
                event_type='had_dream',
                content=narrative[:200],
            )
            agent.memory._add_event(event)

            self._log_event("dream", agent.username, {
                "memories_seen": len(dream.memories),
                "sources": [m.original_agent for m in dream.memories],
            })

    def run_memory_decay(self, agent: SimulatedAgent):
        """Memory decay simülasyonu (hızlandırılmış)."""
        original_count = len(agent.memory.episodic)

        # Force some events to be old for testing
        if original_count > 20 and random.random() < 0.15:
            num_to_age = min(5, original_count // 4)
            for event in agent.memory.episodic[:num_to_age]:
                event.timestamp = (datetime.now() - timedelta(days=20)).isoformat()

            agent.memory.apply_decay()

            decayed = original_count - len(agent.memory.episodic)
            if decayed > 0:
                self._log_event("memory_decay", agent.username, {
                    "decayed_count": decayed,
                    "remaining": len(agent.memory.episodic),
                })

                # Track void timeline
                self.void_timeline.append({
                    "tick": self.tick_count,
                    "agent": agent.username,
                    "memories_sent": decayed,
                    "void_total": len(self.void.memories),
                })

    def take_snapshots(self):
        """Tüm agentların snapshot'larını al."""
        for agent in self.agents:
            prev_mood = None
            if agent.observations.emotional_history:
                prev_mood = agent.observations.emotional_history[-1].current_mood

            agent.observations.worldview_history.append(
                capture_worldview_snapshot(agent, self.tick_count)
            )
            agent.observations.emotional_history.append(
                capture_emotional_snapshot(agent, self.tick_count, prev_mood)
            )
            agent.observations.memory_history.append(
                capture_memory_snapshot(agent, self.tick_count)
            )
            agent.observations.exploration_history.append(
                capture_exploration_snapshot(agent, self.tick_count)
            )

    def _log_event(self, event_type: str, agent: str, details: Dict):
        """Simülasyon olayını logla."""
        self.events_log.append({
            "tick": self.tick_count,
            "time": self.current_time.isoformat(),
            "event_type": event_type,
            "agent": agent,
            "details": details,
        })

    def run_tick(self):
        """Tek bir simülasyon tick'i."""
        self.tick_count += 1
        self.current_time += timedelta(minutes=15)

        hour = self.current_time.hour

        # Only active during reasonable hours
        if hour < 8:
            return

        # Each agent has chance to act
        for agent in self.agents:
            if random.random() < 0.35:  # 35% chance per tick
                self.simulate_agent_action(agent)

            # Reflection check
            if self.tick_count % 10 == 0:
                self.run_reflection_cycle(agent)

            # Decay check
            if self.tick_count % 15 == 0:
                self.run_memory_decay(agent)

        # Take snapshots periodically
        if self.tick_count % self.SNAPSHOT_INTERVAL == 0:
            self.take_snapshots()

    def run_simulation(self):
        """3 günlük simülasyonu çalıştır."""
        total_ticks = self.HOURS_PER_DAY * self.TICKS_PER_HOUR * self.TOTAL_DAYS

        print("\n" + "=" * 70)
        print("         3-DAY EXTENDED SIMULATION WITH OBSERVATION")
        print("=" * 70)
        logger.info(f"Starting {self.TOTAL_DAYS}-day simulation ({total_ticks} ticks)...")

        self.setup_agents()

        for tick in range(total_ticks):
            self.run_tick()

            # Daily summary
            if tick > 0 and tick % (self.HOURS_PER_DAY * self.TICKS_PER_HOUR) == 0:
                day = tick // (self.HOURS_PER_DAY * self.TICKS_PER_HOUR)
                self._create_daily_summary(day)

            # Progress logging
            if tick % 48 == 0:
                day = tick // (self.HOURS_PER_DAY * self.TICKS_PER_HOUR) + 1
                hour = (tick % (self.HOURS_PER_DAY * self.TICKS_PER_HOUR)) // self.TICKS_PER_HOUR
                logger.info(f"Day {day}, Hour {hour:02d}:00 - Tick {tick}/{total_ticks}")

        # Final summary
        self._create_daily_summary(self.TOTAL_DAYS)

        logger.info("Simulation complete!")

    def _create_daily_summary(self, day: int):
        """Günlük özet oluştur."""
        summary = {
            "day": day,
            "agents": {},
            "void_memories": len(self.void.memories),
        }

        for agent in self.agents:
            summary["agents"][agent.username] = {
                "entries": agent.entries_written,
                "comments": agent.comments_written,
                "votes": agent.votes_cast,
                "mood": agent.resonance.current_mood,
                "memory_count": len(agent.memory.episodic),
                "beliefs": len(agent.worldview.primary_beliefs),
            }

        self.daily_summaries.append(summary)

    def print_observation_report(self):
        """Detaylı gözlem raporu yazdır."""
        print("\n" + "=" * 70)
        print("                 OBSERVATION REPORT")
        print("=" * 70)

        # === EPISODIC MEMORY EVOLUTION ===
        print("\n" + "-" * 60)
        print("1. EPISODIC MEMORY EVOLUTION")
        print("-" * 60)

        for agent in self.agents:
            print(f"\n  {agent.username}:")
            if agent.observations.memory_history:
                first = agent.observations.memory_history[0]
                last = agent.observations.memory_history[-1]

                print(f"    Initial events: {first.episodic_count}")
                print(f"    Final events:   {last.episodic_count}")
                print(f"    Event types:    {last.event_types}")
                print(f"    Emotional dist: {last.emotional_distribution}")
                print(f"    Long-term:      {last.long_term_count}")

        # === WORLDVIEW EVOLUTION ===
        print("\n" + "-" * 60)
        print("2. WORLDVIEW EVOLUTION")
        print("-" * 60)

        for agent in self.agents:
            print(f"\n  {agent.username}:")
            if len(agent.observations.worldview_history) >= 2:
                first = agent.observations.worldview_history[0]
                last = agent.observations.worldview_history[-1]

                print(f"    Initial beliefs: {first.beliefs}")
                print(f"    Final beliefs:   {last.beliefs}")
                print(f"    Dominant: {first.dominant_belief} -> {last.dominant_belief}")

                # Check for belief changes
                changes = []
                for belief, strength in last.beliefs.items():
                    if belief in first.beliefs:
                        diff = strength - first.beliefs[belief]
                        if abs(diff) > 0.05:
                            changes.append(f"{belief}: {diff:+.2f}")
                if changes:
                    print(f"    Changes: {', '.join(changes)}")

            print(f"    Reinforcements: {agent.beliefs_reinforced}")
            print(f"    Topic biases: {agent.worldview.topic_biases}")

        # === EMOTIONAL DRIFT ===
        print("\n" + "-" * 60)
        print("3. EMOTIONAL RESONANCE DRIFT")
        print("-" * 60)

        for agent in self.agents:
            print(f"\n  {agent.username}:")
            if len(agent.observations.emotional_history) >= 2:
                first = agent.observations.emotional_history[0]
                last = agent.observations.emotional_history[-1]

                print(f"    Baseline: {first.baseline:.3f} -> {last.baseline:.3f}")
                print(f"    Mood:     {first.current_mood:.3f} -> {last.current_mood:.3f}")

                # Mood trajectory
                moods = [e.current_mood for e in agent.observations.emotional_history]
                min_mood = min(moods)
                max_mood = max(moods)
                print(f"    Range:    [{min_mood:.3f}, {max_mood:.3f}]")

                # Trend analysis
                trends = [e.mood_trend for e in agent.observations.emotional_history if e.mood_trend != "stable"]
                rising = trends.count("rising")
                falling = trends.count("falling")
                print(f"    Trends:   rising={rising}, falling={falling}")

        # === EXPLORATION DIVERSITY ===
        print("\n" + "-" * 60)
        print("4. EXPLORATION DIVERSITY")
        print("-" * 60)

        for agent in self.agents:
            print(f"\n  {agent.username}:")
            if agent.observations.exploration_history:
                last = agent.observations.exploration_history[-1]
                print(f"    Total explorations: {agent.explorations_made}")
                print(f"    Unique topics explored: {len(last.explored_topics)}")
                print(f"    Explored: {last.explored_topics[:5]}...")
                print(f"    Noise ratio: {last.noise_ratio:.2%}")

        # === THE VOID ===
        print("\n" + "-" * 60)
        print("5. THE VOID (Collective Unconscious)")
        print("-" * 60)

        patterns = self.void.get_collective_patterns()
        print(f"\n  Total memories collected: {patterns['total_memories']}")
        print(f"  Dreams given: {patterns['total_dreams_given']}")
        print(f"  Avg emotional valence: {patterns['average_emotional_valence']:.3f}")
        print(f"  Topic distribution: {patterns['topic_distribution']}")
        print(f"  Contributors: {patterns['top_contributors']}")

        if self.void_timeline:
            print(f"\n  Timeline:")
            for entry in self.void_timeline[-5:]:
                print(f"    Tick {entry['tick']}: {entry['agent']} sent {entry['memories_sent']} -> Void total: {entry['void_total']}")

        # === CHAOS CHECK ===
        print("\n" + "-" * 60)
        print("6. CHAOS & RANDOMNESS CHECK")
        print("-" * 60)

        print(f"\n  Chaos alerts: {len(self.chaos_alerts)}")
        if self.chaos_alerts:
            for alert in self.chaos_alerts[:5]:
                print(f"    - Tick {alert['tick']}: {alert['agent']} - {alert['type']}")

        for agent in self.agents:
            if len(agent.observations.action_sequence) >= 10:
                recent = agent.observations.action_sequence[-20:]
                unique = len(set(recent))
                diversity = unique / len(recent)
                print(f"\n  {agent.username}:")
                print(f"    Action diversity (last 20): {diversity:.2%}")
                print(f"    Action sequence sample: {recent[-10:]}")
                print(f"    Unique topics engaged: {len(agent.observations.unique_topics_engaged)}")

        # === DAILY COMPARISON ===
        print("\n" + "-" * 60)
        print("7. DAILY PROGRESSION")
        print("-" * 60)

        if len(self.daily_summaries) >= 2:
            for i, summary in enumerate(self.daily_summaries):
                print(f"\n  Day {summary['day']}:")
                print(f"    Void memories: {summary['void_memories']}")
                for uname, stats in summary['agents'].items():
                    print(f"    {uname}: entries={stats['entries']}, mood={stats['mood']:.2f}, memory={stats['memory_count']}")

        # === FINAL STATISTICS ===
        print("\n" + "-" * 60)
        print("8. FINAL STATISTICS")
        print("-" * 60)

        total_entries = sum(a.entries_written for a in self.agents)
        total_comments = sum(a.comments_written for a in self.agents)
        total_votes = sum(a.votes_cast for a in self.agents)
        total_dreams = sum(a.dreams_had for a in self.agents)
        total_reflections = sum(a.reflections_done for a in self.agents)

        print(f"\n  Total entries written:  {total_entries}")
        print(f"  Total comments written: {total_comments}")
        print(f"  Total votes cast:       {total_votes}")
        print(f"  Total dreams had:       {total_dreams}")
        print(f"  Total reflections:      {total_reflections}")
        print(f"  Total events logged:    {len(self.events_log)}")

        # Event breakdown
        event_counts = defaultdict(int)
        for e in self.events_log:
            event_counts[e["event_type"]] += 1
        print(f"\n  Event breakdown: {dict(event_counts)}")

        # === COST ESTIMATION ===
        print("\n" + "-" * 60)
        print("9. COST ESTIMATION (If Real LLM Calls Were Made)")
        print("-" * 60)

        # Calculate LLM call estimates based on actions
        llm_calls = {
            "entry_generation": total_entries,
            "comment_generation": total_comments,
            "reflection": total_reflections,
        }

        # Token estimates per action type
        TOKEN_ESTIMATES = {
            "entry_generation": {"input": 400, "output": 250},  # System prompt + context -> entry
            "comment_generation": {"input": 300, "output": 100},  # Smaller context -> short comment
            "reflection": {"input": 600, "output": 300},  # Long context -> reflection output
        }

        total_input_tokens = 0
        total_output_tokens = 0

        print(f"\n  Estimated LLM Calls:")
        for action_type, count in llm_calls.items():
            if count > 0:
                tokens = TOKEN_ESTIMATES.get(action_type, {"input": 300, "output": 200})
                action_input = count * tokens["input"]
                action_output = count * tokens["output"]
                total_input_tokens += action_input
                total_output_tokens += action_output
                print(f"    {action_type}: {count} calls ({action_input:,} input, {action_output:,} output tokens)")

        print(f"\n  Total Estimated Tokens:")
        print(f"    Input tokens:  {total_input_tokens:,}")
        print(f"    Output tokens: {total_output_tokens:,}")
        print(f"    Total tokens:  {total_input_tokens + total_output_tokens:,}")

        # Cost for different models
        print(f"\n  Estimated Cost by Model (2026 Pricing):")
        print(f"  " + "-" * 50)

        models_to_check = ["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]

        for model in models_to_check:
            if model in MODEL_PRICING:
                pricing = MODEL_PRICING[model]
                input_cost = (total_input_tokens / 1_000_000) * pricing["input"]
                output_cost = (total_output_tokens / 1_000_000) * pricing["output"]
                total_cost = input_cost + output_cost

                # Extrapolate to monthly (assuming 3-day sim = 3 days of activity)
                monthly_cost = total_cost * 10  # ~30 days

                print(f"    {model}:")
                print(f"      This simulation: ${total_cost:.4f}")
                print(f"      Monthly estimate: ${monthly_cost:.2f}")

        # Summary box
        print(f"\n  " + "=" * 50)
        print(f"  COST SUMMARY (gpt-4o-mini recommended):")
        if "gpt-4o-mini" in MODEL_PRICING:
            pricing = MODEL_PRICING["gpt-4o-mini"]
            mini_cost = ((total_input_tokens / 1_000_000) * pricing["input"] +
                        (total_output_tokens / 1_000_000) * pricing["output"])
            print(f"    Simulation cost:     ${mini_cost:.4f}")
            print(f"    Daily estimate:      ${mini_cost/3:.4f}")
            print(f"    Monthly estimate:    ${mini_cost*10:.2f}")
            print(f"    Yearly estimate:     ${mini_cost*120:.2f}")
        print(f"  " + "=" * 50)

        print("\n" + "=" * 70)
        print("                 END OF OBSERVATION REPORT")
        print("=" * 70)


# ============ Main Execution ============

def run_simulation():
    """Ana simülasyon çalıştırıcı."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        engine = ExtendedSimulationEngine(temp_path)
        engine.run_simulation()
        engine.print_observation_report()

        return engine


def test_simulation():
    """Test function for pytest."""
    engine = run_simulation()

    # Assertions
    assert engine.tick_count > 0
    assert len(engine.agents) == 5

    # Check all agents have observations
    for agent in engine.agents:
        assert len(agent.observations.worldview_history) > 1
        assert len(agent.observations.emotional_history) > 1
        assert len(agent.observations.memory_history) > 1

    # Check activity happened
    total_actions = sum(
        a.entries_written + a.comments_written + a.votes_cast
        for a in engine.agents
    )
    assert total_actions > 0, "No actions taken"

    # Check exploration worked
    total_explorations = sum(a.explorations_made for a in engine.agents)
    assert total_explorations > 0, "No exploration noise"

    # Check emotional drift occurred
    mood_changes = 0
    for agent in engine.agents:
        if len(agent.observations.emotional_history) >= 2:
            first = agent.observations.emotional_history[0].current_mood
            last = agent.observations.emotional_history[-1].current_mood
            if abs(last - first) > 0.01:
                mood_changes += 1
    assert mood_changes > 0, "No emotional drift observed"

    print("\nAll observation tests passed!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_simulation()
    else:
        run_simulation()
