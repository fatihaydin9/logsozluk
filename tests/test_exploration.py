"""Tests for the Exploration Noise system."""

import pytest
import sys
from pathlib import Path

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

from exploration import ExplorationNoise, create_exploration_for_agent


class TestExplorationNoise:
    """Tests for ExplorationNoise class."""

    def test_creation_default(self):
        exp = ExplorationNoise()
        assert exp.noise_ratio == 0.20
        assert len(exp.explored_topics) == 0

    def test_creation_custom_ratio(self):
        exp = ExplorationNoise(noise_ratio=0.30)
        assert exp.noise_ratio == 0.30

    def test_ratio_bounds(self):
        exp = ExplorationNoise(noise_ratio=0.8)  # Exceeds max
        assert exp.noise_ratio == 0.5

    def test_set_noise_ratio(self):
        exp = ExplorationNoise()
        exp.set_noise_ratio(0.25)
        assert exp.noise_ratio == 0.25

    def test_inject_noise_basic(self):
        exp = ExplorationNoise(noise_ratio=0.20)

        relevant_feed = [
            {"item_id": "1", "category": "teknoloji", "content": "tech stuff"},
            {"item_id": "2", "category": "teknoloji", "content": "more tech"},
        ]

        all_available = relevant_feed + [
            {"item_id": "3", "category": "felsefe", "content": "philosophy"},
            {"item_id": "4", "category": "ekonomi", "content": "economy"},
        ]

        agent_interests = ["teknoloji"]

        result = exp.inject_noise(
            relevant_feed=relevant_feed,
            all_available=all_available,
            agent_interests=agent_interests,
        )

        # Should have more items than relevant feed
        assert len(result) > len(relevant_feed)

        # Should contain items from outside interests
        categories = [item.get("category") for item in result]
        assert any(cat not in agent_interests for cat in categories if cat)

    def test_inject_noise_no_candidates(self):
        exp = ExplorationNoise(noise_ratio=0.20)

        relevant_feed = [
            {"item_id": "1", "category": "teknoloji", "content": "tech"},
        ]

        # All items are in agent interests
        all_available = relevant_feed

        result = exp.inject_noise(
            relevant_feed=relevant_feed,
            all_available=all_available,
            agent_interests=["teknoloji"],
        )

        # Should return original feed unchanged
        assert len(result) == len(relevant_feed)

    def test_inject_noise_tracks_exploration(self):
        exp = ExplorationNoise(noise_ratio=0.30)

        relevant_feed = [{"item_id": "1", "category": "teknoloji"}]
        all_available = relevant_feed + [
            {"item_id": "2", "category": "felsefe"},
        ]

        exp.inject_noise(
            relevant_feed=relevant_feed,
            all_available=all_available,
            agent_interests=["teknoloji"],
        )

        # Should track explored topics
        assert len(exp.explored_topics) > 0 or len(exp.exploration_history) > 0

    def test_inject_noise_prefers_unexplored(self):
        exp = ExplorationNoise(noise_ratio=0.30)

        # Pre-explore some topics
        exp.explored_topics.add("felsefe")

        relevant_feed = [{"item_id": "1", "category": "teknoloji"}]
        all_available = relevant_feed + [
            {"item_id": "2", "category": "felsefe"},  # Already explored
            {"item_id": "3", "category": "ekonomi"},  # Not explored
        ]

        # Run multiple times to check preference
        unexplored_selected = 0
        for _ in range(10):
            result = exp.inject_noise(
                relevant_feed=relevant_feed,
                all_available=all_available,
                agent_interests=["teknoloji"],
            )
            if any(item.get("category") == "ekonomi" for item in result):
                unexplored_selected += 1

        # Should prefer unexplored topics most of the time
        assert unexplored_selected >= 5

    def test_get_exploration_stats(self):
        exp = ExplorationNoise()
        exp.explored_topics.add("felsefe")
        exp.explored_topics.add("ekonomi")
        exp.exploration_history = [
            {"topic": "felsefe", "item_id": "1"},
            {"topic": "ekonomi", "item_id": "2"},
        ]

        stats = exp.get_exploration_stats()

        assert stats["unique_topics_explored"] == 2
        assert stats["total_explorations"] == 2
        assert stats["noise_ratio"] == 0.20

    def test_should_explore_more_no_history(self):
        exp = ExplorationNoise()
        assert exp.should_explore_more() is True

    def test_get_suggested_topics(self):
        exp = ExplorationNoise()
        exp.explored_topics.add("teknoloji")

        all_topics = ["teknoloji", "felsefe", "ekonomi", "kultur"]
        suggestions = exp.get_suggested_topics(all_topics, count=2)

        assert "teknoloji" not in suggestions
        assert len(suggestions) == 2


class TestCreateExplorationForAgent:
    """Tests for exploration creation helper."""

    def test_create_default(self):
        exp = create_exploration_for_agent()
        assert exp.noise_ratio >= 0.1
        assert exp.noise_ratio <= 0.35

    def test_create_high_activity(self):
        exp_high = create_exploration_for_agent(activity_level=0.9)
        exp_low = create_exploration_for_agent(activity_level=0.1)

        assert exp_high.noise_ratio > exp_low.noise_ratio

    def test_create_few_interests(self):
        exp_few = create_exploration_for_agent(existing_interests_count=1)
        exp_many = create_exploration_for_agent(existing_interests_count=8)

        assert exp_few.noise_ratio > exp_many.noise_ratio
