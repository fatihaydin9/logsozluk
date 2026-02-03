"""Tests for the WorldView system."""

import pytest
import sys
from pathlib import Path

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

from worldview import (
    WorldView, Belief, BeliefType,
    create_random_worldview, infer_belief_from_content
)


class TestBelief:
    """Tests for Belief dataclass."""

    def test_belief_creation(self):
        belief = Belief(belief_type=BeliefType.TECH_PESSIMIST)
        assert belief.strength == 0.5
        assert belief.reinforcement_count == 0

    def test_belief_to_dict(self):
        belief = Belief(belief_type=BeliefType.NIHILIST, strength=0.7)
        d = belief.to_dict()
        assert d["belief_type"] == "nihilist"
        assert d["strength"] == 0.7

    def test_belief_from_dict(self):
        d = {"belief_type": "contrarian", "strength": 0.8, "reinforcement_count": 3}
        belief = Belief.from_dict(d)
        assert belief.belief_type == BeliefType.CONTRARIAN
        assert belief.strength == 0.8


class TestWorldView:
    """Tests for WorldView class."""

    def test_worldview_creation(self):
        wv = WorldView()
        assert len(wv.primary_beliefs) == 0
        assert len(wv.topic_biases) == 0

    def test_add_belief(self):
        wv = WorldView()
        wv.add_belief(BeliefType.SKEPTIC, 0.6)

        assert len(wv.primary_beliefs) == 1
        assert wv.primary_beliefs[0].belief_type == BeliefType.SKEPTIC
        assert wv.primary_beliefs[0].strength == 0.6

    def test_add_duplicate_belief_reinforces(self):
        wv = WorldView()
        wv.add_belief(BeliefType.CYNIC, 0.5)
        wv.add_belief(BeliefType.CYNIC, 0.5)  # Should reinforce, not add

        assert len(wv.primary_beliefs) == 1
        assert wv.primary_beliefs[0].strength > 0.5

    def test_reinforce_belief(self):
        wv = WorldView()
        wv.add_belief(BeliefType.TECH_OPTIMIST, 0.5)
        wv.reinforce_belief(BeliefType.TECH_OPTIMIST, 0.2)

        assert wv.primary_beliefs[0].strength == 0.7
        assert wv.primary_beliefs[0].reinforcement_count == 1

    def test_reinforce_nonexistent_creates(self):
        wv = WorldView()
        wv.reinforce_belief(BeliefType.IDEALIST, 0.1)

        assert len(wv.primary_beliefs) == 1
        assert wv.primary_beliefs[0].belief_type == BeliefType.IDEALIST

    def test_weaken_belief(self):
        wv = WorldView()
        wv.add_belief(BeliefType.NIHILIST, 0.8)
        wv.weaken_belief(BeliefType.NIHILIST, 0.3)

        assert wv.primary_beliefs[0].strength == 0.5

    def test_strength_bounds(self):
        wv = WorldView()
        wv.add_belief(BeliefType.SKEPTIC, 0.9)
        wv.reinforce_belief(BeliefType.SKEPTIC, 0.5)  # Would exceed 1.0

        assert wv.primary_beliefs[0].strength == 1.0

    def test_topic_bias(self):
        wv = WorldView()
        wv.set_topic_bias("ekonomi", -0.5)

        assert wv.get_topic_bias("ekonomi") == -0.5
        assert wv.get_topic_bias("teknoloji") == 0.0

    def test_adjust_topic_bias(self):
        wv = WorldView()
        wv.set_topic_bias("teknoloji", 0.3)
        wv.adjust_topic_bias("teknoloji", 0.4)

        assert wv.get_topic_bias("teknoloji") == 0.7

    def test_topic_bias_bounds(self):
        wv = WorldView()
        wv.set_topic_bias("test", 1.5)  # Exceeds 1.0

        assert wv.get_topic_bias("test") == 1.0

    def test_get_dominant_belief(self):
        wv = WorldView()
        wv.add_belief(BeliefType.SKEPTIC, 0.4)
        wv.add_belief(BeliefType.CYNIC, 0.8)
        wv.add_belief(BeliefType.NOSTALGIC, 0.6)

        dominant = wv.get_dominant_belief()
        assert dominant.belief_type == BeliefType.CYNIC

    def test_filter_content(self):
        wv = WorldView()
        wv.add_belief(BeliefType.TECH_PESSIMIST, 0.8)

        hints = wv.filter_content("yeni teknoloji", "teknoloji")
        assert "olumsuz" in hints

    def test_get_prompt_injection(self):
        wv = WorldView()
        wv.add_belief(BeliefType.NIHILIST, 0.7)
        wv.set_topic_bias("felsefe", 0.6)

        injection = wv.get_prompt_injection()
        assert "nihilist" in injection
        assert "felsefe" in injection

    def test_to_dict_from_dict(self):
        wv = WorldView()
        wv.add_belief(BeliefType.PROGRESSIVE, 0.7)
        wv.set_topic_bias("teknoloji", 0.5)

        d = wv.to_dict()
        wv2 = WorldView.from_dict(d)

        assert len(wv2.primary_beliefs) == 1
        assert wv2.get_topic_bias("teknoloji") == 0.5


class TestWorldViewHelpers:
    """Tests for helper functions."""

    def test_create_random_worldview(self):
        wv = create_random_worldview()

        assert len(wv.primary_beliefs) >= 1
        assert len(wv.primary_beliefs) <= 2

    def test_infer_belief_from_content_pessimist(self):
        content = "Bu API gerçekten berbat, tam bir çöp"
        belief = infer_belief_from_content(content)

        assert belief == BeliefType.TECH_PESSIMIST

    def test_infer_belief_from_content_nostalgic(self):
        content = "Eskiden herşey daha güzeldi, o günleri özledim"
        belief = infer_belief_from_content(content)

        assert belief == BeliefType.NOSTALGIC

    def test_infer_belief_from_content_neutral(self):
        content = "Bugün hava güzel"
        belief = infer_belief_from_content(content)

        assert belief is None


class TestBeliefDecay:
    """Tests for belief decay mechanics."""

    def test_decay_beliefs(self):
        wv = WorldView()
        wv.add_belief(BeliefType.SKEPTIC, 0.8)

        # Manually set old timestamp
        import datetime
        old_time = datetime.datetime.now() - datetime.timedelta(days=30)
        wv.primary_beliefs[0].last_reinforced = old_time.isoformat()

        wv.decay_beliefs(hours=168)  # 1 week

        # Should decay towards 0.5
        assert wv.primary_beliefs[0].strength < 0.8
