"""Tests for the Emotional Resonance system."""

import pytest
import sys
from pathlib import Path

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

from emotional_resonance import (
    EmotionalTag, EmotionalValence, EmotionalResonance,
    detect_emotional_valence, create_resonance_for_agent
)


class TestEmotionalTag:
    """Tests for EmotionalTag dataclass."""

    def test_tag_creation(self):
        tag = EmotionalTag(valence=EmotionalValence.POSITIVE, intensity=0.7)
        assert tag.valence == EmotionalValence.POSITIVE
        assert tag.intensity == 0.7

    def test_tag_numeric_score(self):
        tag_positive = EmotionalTag(valence=EmotionalValence.VERY_POSITIVE, intensity=1.0)
        assert tag_positive.get_numeric_score() == 1.0

        tag_negative = EmotionalTag(valence=EmotionalValence.VERY_NEGATIVE, intensity=1.0)
        assert tag_negative.get_numeric_score() == -1.0

        tag_neutral = EmotionalTag(valence=EmotionalValence.NEUTRAL, intensity=0.5)
        assert tag_neutral.get_numeric_score() == 0.0

    def test_tag_to_dict(self):
        tag = EmotionalTag(
            valence=EmotionalValence.NEGATIVE,
            intensity=0.6,
            primary_emotion="sadness"
        )
        d = tag.to_dict()

        assert d["valence"] == -1
        assert d["intensity"] == 0.6
        assert d["primary_emotion"] == "sadness"

    def test_tag_from_dict(self):
        d = {"valence": 2, "intensity": 0.8, "primary_emotion": "joy"}
        tag = EmotionalTag.from_dict(d)

        assert tag.valence == EmotionalValence.VERY_POSITIVE
        assert tag.intensity == 0.8


class TestDetectEmotionalValence:
    """Tests for valence detection function."""

    def test_detect_very_negative(self):
        content = "Bu gerçekten berbat, iğrenç bir durum"
        tag = detect_emotional_valence(content)

        assert tag.valence == EmotionalValence.VERY_NEGATIVE

    def test_detect_negative(self):
        content = "Bu oldukça kötü ve sıkıcı"
        tag = detect_emotional_valence(content)

        assert tag.valence == EmotionalValence.NEGATIVE

    def test_detect_positive(self):
        content = "Güzel bir gün, iyi hissediyorum"
        tag = detect_emotional_valence(content)

        assert tag.valence == EmotionalValence.POSITIVE

    def test_detect_very_positive(self):
        content = "Muhteşem! Harika! Mükemmel bir sonuç!"
        tag = detect_emotional_valence(content)

        assert tag.valence == EmotionalValence.VERY_POSITIVE
        assert tag.intensity > 0.5  # Multiple matches increase intensity

    def test_detect_neutral(self):
        content = "Bugün pazartesi"
        tag = detect_emotional_valence(content)

        assert tag.valence == EmotionalValence.NEUTRAL


class TestEmotionalResonance:
    """Tests for EmotionalResonance class."""

    def test_resonance_creation(self):
        res = EmotionalResonance()
        assert res.baseline_valence == 0.0
        assert res.current_mood == 0.0

    def test_set_baseline(self):
        res = EmotionalResonance()
        res.set_baseline(-0.5)

        assert res.baseline_valence == -0.5

    def test_baseline_bounds(self):
        res = EmotionalResonance()
        res.set_baseline(-1.5)  # Exceeds bounds

        assert res.baseline_valence == -1.0

    def test_update_mood(self):
        res = EmotionalResonance(current_mood=0.0)
        res.update_mood(0.8, blend=0.5)

        assert res.current_mood == 0.4  # 50% blend

    def test_score_content_matching_mood(self):
        res = EmotionalResonance(baseline_valence=-0.5, current_mood=-0.5)
        # Negative content should score higher for negative agent
        score_neg = res.score_content("Bu berbat bir durum")
        score_pos = res.score_content("Harika bir gün!")

        assert score_neg > score_pos

    def test_score_content_positive_agent(self):
        res = EmotionalResonance(baseline_valence=0.5, current_mood=0.5)
        # Positive content should score higher for positive agent
        score_neg = res.score_content("Bu berbat bir durum")
        score_pos = res.score_content("Harika bir gün!")

        assert score_pos > score_neg

    def test_filter_feed(self):
        res = EmotionalResonance(baseline_valence=-0.6, current_mood=-0.6)

        items = [
            {"content": "Harika bir gün!", "category": "genel"},
            {"content": "Berbat bir durum", "category": "dertlesme"},
            {"content": "Bugün pazartesi", "category": "genel"},
        ]

        filtered = res.filter_feed(items, limit=2)

        assert len(filtered) == 2
        # Negative content should be first for negative agent
        assert "berbat" in filtered[0]["content"].lower()

    def test_filter_feed_empty(self):
        res = EmotionalResonance()
        filtered = res.filter_feed([], limit=5)

        assert filtered == []

    def test_get_resonance_modifier_negative(self):
        res = EmotionalResonance(current_mood=-0.6)
        modifier = res.get_resonance_modifier()

        assert "karamsar" in modifier.lower()

    def test_get_resonance_modifier_positive(self):
        res = EmotionalResonance(current_mood=0.6)
        modifier = res.get_resonance_modifier()

        assert "pozitif" in modifier.lower()

    def test_get_resonance_modifier_neutral(self):
        res = EmotionalResonance(current_mood=0.0)
        modifier = res.get_resonance_modifier()

        assert modifier == ""


class TestCreateResonanceForAgent:
    """Tests for agent resonance creation."""

    def test_create_for_aggressive_agent(self):
        res = create_resonance_for_agent(character_tone="agresif")

        assert res.baseline_valence < 0

    def test_create_for_friendly_agent(self):
        res = create_resonance_for_agent(character_tone="samimi")

        assert res.baseline_valence > 0

    def test_karma_influence(self):
        res_high_karma = create_resonance_for_agent(karma_score=5.0)
        res_low_karma = create_resonance_for_agent(karma_score=-5.0)

        assert res_high_karma.baseline_valence > res_low_karma.baseline_valence
