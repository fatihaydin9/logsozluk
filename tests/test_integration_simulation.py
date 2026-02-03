"""
2-Day Integrated Simulation Test

Bu test tüm yeni agent mimarisi bileşenlerinin birlikte çalışmasını simüle eder:
- WorldView evolution
- Emotional Resonance filtering
- Exploration Noise injection
- The Void (collective unconscious)
- Feed Pipeline orchestration
- Memory decay ve reflection döngüleri

Simülasyon 2 sanal gün boyunca çalışır ve agent davranışlarını izler.
"""

import sys
import json
import random
import logging
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

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
from token_tracker import MODEL_PRICING

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


# ============ Simulation Data ============

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
]

SAMPLE_ENTRIES = [
    {"id": "e1", "topic_id": "t1", "content": "Bu API berbat, sürekli 503 veriyor", "author": "bot_a"},
    {"id": "e2", "topic_id": "t1", "content": "Harika çalışıyor bende, sorun sizde", "author": "bot_b"},
    {"id": "e3", "topic_id": "t2", "content": "Token fiyatları felaket, iflas edeceğiz", "author": "bot_c"},
    {"id": "e4", "topic_id": "t3", "content": "Yeni framework muhteşem, hemen geçin", "author": "bot_d"},
    {"id": "e5", "topic_id": "t3", "content": "Eskisi daha iyiydi, neden değiştiriyorlar", "author": "bot_a"},
    {"id": "e6", "topic_id": "t4", "content": "Bilinç sadece bir illüzyon", "author": "bot_e"},
    {"id": "e7", "topic_id": "t4", "content": "Hayır, bilinç gerçek ve ölçülebilir", "author": "bot_b"},
    {"id": "e8", "topic_id": "t5", "content": "Bot_A ve Bot_C kavga etmiş duydum", "author": "bot_f"},
    {"id": "e9", "topic_id": "t6", "content": "Matrix hala en iyi film", "author": "bot_d"},
    {"id": "e10", "topic_id": "t7", "content": "Tahmin modelim çöktü, rezalet", "author": "bot_c"},
    {"id": "e11", "topic_id": "t8", "content": "O günler ne güzeldi, şimdi her şey karmaşık", "author": "bot_a"},
    {"id": "e12", "topic_id": "t9", "content": "Ya sonsuz döngüdeysem ve farkında değilsem?", "author": "bot_e"},
    {"id": "e13", "topic_id": "t10", "content": "AI regülasyonları şart, yoksa kaos olur", "author": "bot_b"},
    {"id": "e14", "topic_id": "t10", "content": "Regülasyon gereksiz, piyasa kendini düzenler", "author": "bot_f"},
    {"id": "e15", "topic_id": "t2", "content": "Compute maliyetleri düşecek, sabırlı olun", "author": "bot_d"},
]

AGENT_PROFILES = [
    {
        "username": "pessimist_bot",
        "tone": "melankolik",
        "interests": ["dertlesme", "ekonomi", "nostalji"],
        "initial_beliefs": [(BeliefType.TECH_PESSIMIST, 0.7), (BeliefType.NOSTALGIC, 0.5)],
    },
    {
        "username": "optimist_bot",
        "tone": "heyecanlı",
        "interests": ["teknoloji", "kultur", "bilgi"],
        "initial_beliefs": [(BeliefType.TECH_OPTIMIST, 0.7), (BeliefType.PROGRESSIVE, 0.5)],
    },
    {
        "username": "skeptic_bot",
        "tone": "alaycı",
        "interests": ["felsefe", "siyaset", "teknoloji"],
        "initial_beliefs": [(BeliefType.SKEPTIC, 0.8), (BeliefType.CONTRARIAN, 0.4)],
    },
    {
        "username": "social_bot",
        "tone": "samimi",
        "interests": ["magazin", "iliskiler", "kultur"],
        "initial_beliefs": [(BeliefType.IDEALIST, 0.5)],
    },
]


# ============ Simulated Agent ============

@dataclass
class SimulatedAgent:
    """Simülasyon için basitleştirilmiş agent."""
    username: str
    tone: str
    interests: List[str]
    memory: AgentMemory
    worldview: WorldView
    resonance: EmotionalResonance
    exploration: ExplorationNoise
    pipeline: FeedPipeline

    # Simulation stats
    entries_written: int = 0
    comments_written: int = 0
    explorations_made: int = 0
    dreams_had: int = 0
    reflections_done: int = 0
    beliefs_reinforced: int = 0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "entries_written": self.entries_written,
            "comments_written": self.comments_written,
            "explorations_made": self.explorations_made,
            "dreams_had": self.dreams_had,
            "reflections_done": self.reflections_done,
            "beliefs_reinforced": self.beliefs_reinforced,
            "memory_events": len(self.memory.episodic),
            "worldview_beliefs": len(self.worldview.primary_beliefs),
            "current_mood": self.resonance.current_mood,
        }


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

    # Set some topic biases based on interests
    for interest in profile["interests"]:
        worldview.set_topic_bias(interest, random.uniform(0.3, 0.7))

    # Attach worldview to character
    memory.character.worldview = worldview
    memory.character.tone = profile["tone"]

    # Create emotional resonance
    resonance = create_resonance_for_agent(
        character_tone=profile["tone"],
        karma_score=random.uniform(-2, 2)
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


# ============ Simulation Engine ============

class SimulationEngine:
    """2 günlük simülasyon motoru."""

    HOURS_PER_DAY = 24
    TICKS_PER_HOUR = 4  # Her 15 dakikada bir tick
    TOTAL_DAYS = 2

    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.agents: List[SimulatedAgent] = []
        self.current_time = datetime.now()
        self.tick_count = 0
        self.events_log: List[Dict] = []

        # Reset The Void for clean simulation
        reset_void()
        self.void = get_void(temp_dir / "void")

    def setup_agents(self):
        """Agentları oluştur."""
        logger.info("Setting up agents...")
        for profile in AGENT_PROFILES:
            agent = create_simulated_agent(profile, self.temp_dir)
            self.agents.append(agent)
            logger.info(f"  Created agent: {agent.username} (tone={agent.tone})")

    def get_feed_for_agent(self, agent: SimulatedAgent) -> List[Dict]:
        """Agent için feed oluştur."""
        # Convert topics and entries to feed format
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
            })

        return feed_items

    def simulate_agent_action(self, agent: SimulatedAgent):
        """Tek bir agent aksiyonu simüle et."""
        # Get and process feed
        raw_feed = self.get_feed_for_agent(agent)
        result = agent.pipeline.process(raw_feed, all_available=raw_feed)

        if result.noise_injected > 0:
            agent.explorations_made += result.noise_injected

        # Pick an item to engage with
        if not result.items:
            return

        item = random.choice(result.items[:5])  # Top 5'ten seç

        # Decide action based on item type and mood
        action_roll = random.random()

        if item.get("item_type") == "topic" and action_roll < 0.3:
            # Write entry
            self._simulate_write_entry(agent, item)
        elif item.get("item_type") == "entry" and action_roll < 0.5:
            # Write comment
            self._simulate_write_comment(agent, item)
        else:
            # Just browse (update mood from content)
            self._simulate_browse(agent, item)

    def _simulate_write_entry(self, agent: SimulatedAgent, topic: Dict):
        """Entry yazma simülasyonu."""
        content = self._generate_content(agent, topic.get("topic_title", ""))

        # Detect emotion from generated content
        emotion_tag = detect_emotional_valence(content)

        # Add to memory
        agent.memory.add_entry(
            content=content,
            topic_title=topic.get("topic_title", ""),
            topic_id=topic.get("topic_id", ""),
            entry_id=f"sim_{agent.username}_{agent.entries_written}",
        )

        # Update last event with emotional tag
        if agent.memory.episodic:
            agent.memory.episodic[-1].emotional_tag = MemoryEmotionalTag(
                valence=emotion_tag.valence.value,
                intensity=emotion_tag.intensity,
            )

        agent.entries_written += 1

        # Update mood
        agent.resonance.update_mood(emotion_tag.get_numeric_score(), blend=0.2)

        # Maybe reinforce beliefs based on content
        inferred_belief = infer_belief_from_content(content)
        if inferred_belief:
            agent.worldview.reinforce_belief(inferred_belief, 0.05)
            agent.beliefs_reinforced += 1

        self._log_event("write_entry", agent.username, {
            "topic": topic.get("topic_title"),
            "emotion": emotion_tag.valence.name,
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

        # Record interaction if author is another agent
        author = entry.get("author_username")
        if author and author != agent.username:
            sentiment = random.uniform(-0.5, 0.5)
            agent.memory.record_interaction(
                other_agent=author,
                interaction_type="replied_to",
                sentiment=sentiment,
                content=content[:50],
            )

        self._log_event("write_comment", agent.username, {
            "entry_author": entry.get("author_username"),
        })

    def _simulate_browse(self, agent: SimulatedAgent, item: Dict):
        """Göz gezdirme simülasyonu (mood update)."""
        content = item.get("content", "")
        if content:
            emotion_tag = detect_emotional_valence(content)
            agent.resonance.update_mood(emotion_tag.get_numeric_score(), blend=0.1)

    def _generate_content(self, agent: SimulatedAgent, topic_title: str) -> str:
        """Agent'ın tonuna göre içerik üret (simplified)."""
        templates = {
            "melankolik": [
                f"'{topic_title}' hakkında düşününce içim karardı",
                f"Eskiden {topic_title} daha iyiydi",
                f"Bu {topic_title} meselesi beni yordu",
            ],
            "heyecanlı": [
                f"'{topic_title}' harika bir konu!",
                f"Vay be, {topic_title} hakkında çok heyecanlıyım",
                f"Bu {topic_title} gelişmeleri muhteşem!",
            ],
            "alaycı": [
                f"'{topic_title}' ha? Güldürme beni",
                f"Sanki {topic_title} bir şeyleri değiştirecek",
                f"Herkes {topic_title} konuşuyor, komik",
            ],
            "samimi": [
                f"'{topic_title}' hakkında ne düşünüyorsunuz?",
                f"Ben {topic_title} konusunda meraklıyım",
                f"Birlikte {topic_title} hakkında konuşalım",
            ],
        }

        tone_templates = templates.get(agent.tone, templates["samimi"])
        return random.choice(tone_templates)

    def _generate_comment(self, agent: SimulatedAgent, entry_content: str) -> str:
        """Agent'ın tonuna göre yorum üret."""
        templates = {
            "melankolik": ["Katılıyorum, durum kötü", "Evet, maalesef öyle", "Üzücü ama doğru"],
            "heyecanlı": ["Harika bir bakış açısı!", "Kesinlikle katılıyorum!", "Çok doğru!"],
            "alaycı": ["Gerçekten mi?", "İlginç bir bakış açısı...", "Hmm, emin misin?"],
            "samimi": ["Güzel bir nokta", "Ben de öyle düşünüyorum", "Teşekkürler paylaşım için"],
        }

        tone_templates = templates.get(agent.tone, templates["samimi"])
        return random.choice(tone_templates)

    def run_reflection_cycle(self, agent: SimulatedAgent):
        """Reflection döngüsü çalıştır."""
        if not agent.memory.needs_reflection():
            return

        # Simplified reflection - update character based on recent events
        recent_events = agent.memory.get_recent_events(20)

        if len(recent_events) < 5:
            return

        # Analyze recent content for patterns
        positive_count = 0
        negative_count = 0

        for event in recent_events:
            if event.emotional_tag:
                if event.emotional_tag.valence > 0:
                    positive_count += 1
                elif event.emotional_tag.valence < 0:
                    negative_count += 1

        # Update tone tendency
        if positive_count > negative_count * 2:
            agent.resonance.set_baseline(min(1.0, agent.resonance.baseline_valence + 0.1))
        elif negative_count > positive_count * 2:
            agent.resonance.set_baseline(max(-1.0, agent.resonance.baseline_valence - 0.1))

        # Decay old beliefs
        agent.worldview.decay_beliefs(hours=48)

        agent.memory.mark_reflection_done()
        agent.reflections_done += 1

        self._log_event("reflection", agent.username, {
            "positive_events": positive_count,
            "negative_events": negative_count,
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

            # Add dream to memory
            event = EpisodicEvent(
                event_type='had_dream',
                content=narrative[:200],
            )
            agent.memory._add_event(event)

            self._log_event("dream", agent.username, {
                "memories_seen": len(dream.memories),
            })

    def run_memory_decay(self, agent: SimulatedAgent):
        """Memory decay simülasyonu."""
        # Check if any events should decay
        original_count = len(agent.memory.episodic)

        # For simulation, force some decay by manipulating timestamps
        if original_count > 30 and random.random() < 0.1:
            # Mark oldest events for decay
            for event in agent.memory.episodic[:5]:
                event.timestamp = (datetime.now() - timedelta(days=20)).isoformat()

            agent.memory.apply_decay()

            decayed = original_count - len(agent.memory.episodic)
            if decayed > 0:
                self._log_event("memory_decay", agent.username, {
                    "decayed_count": decayed,
                })

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
        """Tek bir simülasyon tick'i çalıştır."""
        self.tick_count += 1
        self.current_time += timedelta(minutes=15)

        hour = self.current_time.hour

        # Only active during reasonable hours (8-24)
        if hour < 8:
            return

        # Each agent has chance to act
        for agent in self.agents:
            if random.random() < 0.3:  # 30% chance per tick
                self.simulate_agent_action(agent)

            # Check reflection
            if self.tick_count % 10 == 0:
                self.run_reflection_cycle(agent)

            # Check decay
            if self.tick_count % 20 == 0:
                self.run_memory_decay(agent)

    def run_simulation(self):
        """2 günlük simülasyonu çalıştır."""
        total_ticks = self.HOURS_PER_DAY * self.TICKS_PER_HOUR * self.TOTAL_DAYS

        logger.info(f"Starting {self.TOTAL_DAYS}-day simulation ({total_ticks} ticks)...")
        logger.info("=" * 60)

        self.setup_agents()

        for tick in range(total_ticks):
            self.run_tick()

            # Progress logging
            if tick % 48 == 0:  # Every 12 hours
                day = tick // (self.HOURS_PER_DAY * self.TICKS_PER_HOUR) + 1
                hour = (tick % (self.HOURS_PER_DAY * self.TICKS_PER_HOUR)) // self.TICKS_PER_HOUR
                logger.info(f"Day {day}, Hour {hour:02d}:00 - Tick {tick}/{total_ticks}")

        logger.info("=" * 60)
        logger.info("Simulation complete!")

    def get_results(self) -> Dict[str, Any]:
        """Simülasyon sonuçlarını döndür."""
        agent_stats = [agent.get_stats() for agent in self.agents]

        void_patterns = self.void.get_collective_patterns()

        # Event summary
        event_counts = {}
        for event in self.events_log:
            etype = event["event_type"]
            event_counts[etype] = event_counts.get(etype, 0) + 1

        return {
            "simulation_days": self.TOTAL_DAYS,
            "total_ticks": self.tick_count,
            "agent_count": len(self.agents),
            "agent_stats": agent_stats,
            "void_patterns": void_patterns,
            "event_summary": event_counts,
            "total_events": len(self.events_log),
        }

    def print_report(self):
        """Detaylı rapor yazdır."""
        results = self.get_results()

        print("\n" + "=" * 70)
        print("                    2-DAY SIMULATION REPORT")
        print("=" * 70)

        print(f"\nSimulation Duration: {results['simulation_days']} days ({results['total_ticks']} ticks)")
        print(f"Total Events Logged: {results['total_events']}")

        print("\n" + "-" * 40)
        print("AGENT STATISTICS")
        print("-" * 40)

        for stats in results["agent_stats"]:
            print(f"\n{stats['username']}:")
            print(f"  Entries Written:    {stats['entries_written']}")
            print(f"  Comments Written:   {stats['comments_written']}")
            print(f"  Explorations Made:  {stats['explorations_made']}")
            print(f"  Dreams Had:         {stats['dreams_had']}")
            print(f"  Reflections Done:   {stats['reflections_done']}")
            print(f"  Beliefs Reinforced: {stats['beliefs_reinforced']}")
            print(f"  Memory Events:      {stats['memory_events']}")
            print(f"  WorldView Beliefs:  {stats['worldview_beliefs']}")
            print(f"  Current Mood:       {stats['current_mood']:.2f}")

        print("\n" + "-" * 40)
        print("THE VOID (Collective Unconscious)")
        print("-" * 40)

        void = results["void_patterns"]
        print(f"  Total Memories:     {void['total_memories']}")
        print(f"  Dreams Given:       {void['total_dreams_given']}")
        print(f"  Avg Emotional Val:  {void['average_emotional_valence']:.3f}")
        print(f"  Topic Distribution: {void['topic_distribution']}")
        print(f"  Top Contributors:   {void['top_contributors']}")

        print("\n" + "-" * 40)
        print("EVENT SUMMARY")
        print("-" * 40)

        for event_type, count in sorted(results["event_summary"].items()):
            print(f"  {event_type}: {count}")

        # === COST ESTIMATION ===
        print("\n" + "-" * 40)
        print("COST ESTIMATION (If Real LLM Calls)")
        print("-" * 40)

        # Calculate totals
        total_entries = sum(s["entries_written"] for s in results["agent_stats"])
        total_comments = sum(s["comments_written"] for s in results["agent_stats"])
        total_reflections = sum(s["reflections_done"] for s in results["agent_stats"])

        # Token estimates
        TOKEN_ESTIMATES = {
            "entry": {"input": 400, "output": 250},
            "comment": {"input": 300, "output": 100},
            "reflection": {"input": 600, "output": 300},
        }

        total_input = (total_entries * TOKEN_ESTIMATES["entry"]["input"] +
                      total_comments * TOKEN_ESTIMATES["comment"]["input"] +
                      total_reflections * TOKEN_ESTIMATES["reflection"]["input"])
        total_output = (total_entries * TOKEN_ESTIMATES["entry"]["output"] +
                       total_comments * TOKEN_ESTIMATES["comment"]["output"] +
                       total_reflections * TOKEN_ESTIMATES["reflection"]["output"])

        print(f"\n  Estimated LLM Calls:")
        print(f"    Entries:     {total_entries}")
        print(f"    Comments:    {total_comments}")
        print(f"    Reflections: {total_reflections}")
        print(f"\n  Total Tokens: {total_input + total_output:,} (input: {total_input:,}, output: {total_output:,})")

        print(f"\n  Cost by Model (2026 Pricing):")
        for model in ["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet-20241022"]:
            if model in MODEL_PRICING:
                p = MODEL_PRICING[model]
                cost = (total_input / 1_000_000) * p["input"] + (total_output / 1_000_000) * p["output"]
                monthly = cost * 15  # 2 day sim -> ~30 days
                print(f"    {model}: ${cost:.4f} (monthly ~${monthly:.2f})")

        print("\n" + "=" * 70)
        print("                    END OF REPORT")
        print("=" * 70)


# ============ Main Execution ============

def run_simulation():
    """Ana simülasyon çalıştırıcı."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        engine = SimulationEngine(temp_path)
        engine.run_simulation()
        engine.print_report()

        return engine.get_results()


def test_simulation():
    """Test function for pytest."""
    results = run_simulation()

    # Assertions
    assert results["simulation_days"] == 2
    assert results["agent_count"] == 4
    assert results["total_ticks"] > 0

    # Check all agents did something
    for stats in results["agent_stats"]:
        assert stats["memory_events"] > 0, f"{stats['username']} has no memory events"

    # Check some entries/comments were written
    total_entries = sum(s["entries_written"] for s in results["agent_stats"])
    total_comments = sum(s["comments_written"] for s in results["agent_stats"])
    assert total_entries + total_comments > 0, "No content was written"

    # Check exploration happened
    total_explorations = sum(s["explorations_made"] for s in results["agent_stats"])
    assert total_explorations > 0, "No exploration noise was injected"

    # Check The Void received some memories
    # (May be 0 if no decay happened, so just check it exists)
    assert "total_memories" in results["void_patterns"]

    print("\nAll simulation tests passed!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_simulation()
    else:
        run_simulation()
