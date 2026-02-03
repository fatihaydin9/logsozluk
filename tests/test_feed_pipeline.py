"""Tests for the Feed Pipeline system."""

import pytest
import sys
from pathlib import Path

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

from feed_pipeline import FeedPipeline, PipelineConfig, PipelineResult, create_pipeline_for_agent


class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_default_config(self):
        config = PipelineConfig()
        assert config.enable_worldview is True
        assert config.enable_emotional_resonance is True
        assert config.enable_exploration_noise is True
        assert config.exploration_noise_ratio == 0.20
        assert config.max_feed_items == 20

    def test_custom_config(self):
        config = PipelineConfig(
            enable_worldview=False,
            exploration_noise_ratio=0.30,
            max_feed_items=10,
        )
        assert config.enable_worldview is False
        assert config.exploration_noise_ratio == 0.30


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_result_creation(self):
        result = PipelineResult(
            items=[{"id": "1"}],
            original_count=5,
            filtered_count=1,
            noise_injected=0,
            worldview_applied=True,
            resonance_applied=False,
        )
        assert result.original_count == 5
        assert result.filtered_count == 1


class TestFeedPipeline:
    """Tests for FeedPipeline class."""

    def test_pipeline_creation(self):
        pipeline = FeedPipeline()
        assert pipeline.worldview is None
        assert pipeline.agent_interests == []

    def test_pipeline_with_config(self):
        config = PipelineConfig(exploration_noise_ratio=0.25)
        pipeline = FeedPipeline(config=config)

        assert pipeline.config.exploration_noise_ratio == 0.25

    def test_set_agent_interests(self):
        pipeline = FeedPipeline()
        pipeline.set_agent_interests(["teknoloji", "felsefe"])

        assert pipeline.agent_interests == ["teknoloji", "felsefe"]

    def test_process_empty_feed(self):
        pipeline = FeedPipeline()
        result = pipeline.process([])

        assert result.items == []
        assert result.original_count == 0
        assert result.filtered_count == 0

    def test_process_basic_feed(self):
        config = PipelineConfig(
            enable_worldview=False,
            enable_emotional_resonance=False,
            enable_exploration_noise=False,
        )
        pipeline = FeedPipeline(config=config)

        feed = [
            {"item_id": "1", "content": "test content", "category": "teknoloji"},
            {"item_id": "2", "content": "more content", "category": "felsefe"},
        ]

        result = pipeline.process(feed)

        assert result.original_count == 2
        assert result.filtered_count == 2

    def test_process_with_resonance(self):
        from emotional_resonance import EmotionalResonance

        config = PipelineConfig(
            enable_worldview=False,
            enable_emotional_resonance=True,
            enable_exploration_noise=False,
        )
        resonance = EmotionalResonance(baseline_valence=-0.5, current_mood=-0.5)
        pipeline = FeedPipeline(config=config, resonance=resonance)

        feed = [
            {"item_id": "1", "content": "Harika bir gün!", "category": "genel"},
            {"item_id": "2", "content": "Berbat bir durum", "category": "dertlesme"},
            {"item_id": "3", "content": "Normal içerik", "category": "genel"},
        ]

        result = pipeline.process(feed)

        assert result.resonance_applied is True
        # Negative content should be prioritized for negative agent
        assert "berbat" in result.items[0]["content"].lower()

    def test_process_with_exploration(self):
        from exploration import ExplorationNoise

        config = PipelineConfig(
            enable_worldview=False,
            enable_emotional_resonance=False,
            enable_exploration_noise=True,
            exploration_noise_ratio=0.50,  # High ratio for testing
        )
        exploration = ExplorationNoise(noise_ratio=0.50)
        pipeline = FeedPipeline(
            config=config,
            exploration=exploration,
            agent_interests=["teknoloji"],
        )

        relevant_feed = [
            {"item_id": "1", "content": "tech stuff", "category": "teknoloji"},
        ]

        all_available = relevant_feed + [
            {"item_id": "2", "content": "philosophy", "category": "felsefe"},
            {"item_id": "3", "content": "economy", "category": "ekonomi"},
        ]

        result = pipeline.process(relevant_feed, all_available=all_available)

        assert result.noise_injected > 0
        assert len(result.items) > 1

    def test_process_with_worldview(self):
        from worldview import WorldView, BeliefType

        config = PipelineConfig(
            enable_worldview=True,
            enable_emotional_resonance=False,
            enable_exploration_noise=False,
        )

        worldview = WorldView()
        worldview.add_belief(BeliefType.TECH_PESSIMIST, 0.8)

        pipeline = FeedPipeline(config=config, worldview=worldview)

        feed = [
            {"item_id": "1", "content": "new tech release", "category": "teknoloji"},
        ]

        result = pipeline.process(feed)

        assert result.worldview_applied is True
        # Should have worldview hints added
        if result.items:
            assert "_worldview_hints" in result.items[0]

    def test_get_pipeline_stats(self):
        from exploration import ExplorationNoise

        config = PipelineConfig(exploration_noise_ratio=0.25)
        exploration = ExplorationNoise()
        pipeline = FeedPipeline(
            config=config,
            exploration=exploration,
            agent_interests=["teknoloji"],
        )

        stats = pipeline.get_pipeline_stats()

        assert stats["config"]["noise_ratio"] == 0.25
        assert stats["components"]["exploration"] is True
        assert "teknoloji" in stats["agent_interests"]


class TestCreatePipelineForAgent:
    """Tests for pipeline creation helper."""

    def test_create_basic_pipeline(self):
        pipeline = create_pipeline_for_agent(interests=["teknoloji", "felsefe"])

        assert pipeline is not None
        assert "teknoloji" in pipeline.agent_interests

    def test_create_with_character(self):
        # Create a mock character sheet
        from agent_memory import CharacterSheet

        character = CharacterSheet(
            tone="alaycı",
            karma_score=3.0,
            favorite_topics=["felsefe"],
        )

        pipeline = create_pipeline_for_agent(
            character=character,
            interests=["teknoloji"],
        )

        assert pipeline is not None
        # Resonance should be created based on character
        if pipeline.resonance:
            assert pipeline.resonance.baseline_valence != 0.0

    def test_create_with_worldview(self):
        from worldview import WorldView, BeliefType

        worldview = WorldView()
        worldview.add_belief(BeliefType.SKEPTIC, 0.7)

        pipeline = create_pipeline_for_agent(
            worldview=worldview,
            interests=["teknoloji"],
        )

        assert pipeline.worldview is worldview
