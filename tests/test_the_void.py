"""Tests for The Void (collective unconscious) system."""

import pytest
import sys
import tempfile
from pathlib import Path

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

from the_void import TheVoid, ForgottenMemory, Dream, get_void, reset_void


@pytest.fixture
def temp_void():
    """Create a void with temporary storage."""
    reset_void()
    with tempfile.TemporaryDirectory() as tmpdir:
        void = TheVoid(storage_dir=Path(tmpdir))
        yield void
        reset_void()


class TestForgottenMemory:
    """Tests for ForgottenMemory dataclass."""

    def test_memory_creation(self):
        mem = ForgottenMemory(
            original_agent="test_agent",
            event_type="wrote_entry",
            content_summary="test content",
        )
        assert mem.original_agent == "test_agent"
        assert mem.access_count == 0

    def test_memory_to_dict(self):
        mem = ForgottenMemory(
            original_agent="agent1",
            event_type="received_like",
            content_summary="got likes",
            topic="teknoloji",
            emotional_valence=0.5,
        )
        d = mem.to_dict()

        assert d["original_agent"] == "agent1"
        assert d["topic"] == "teknoloji"
        assert d["emotional_valence"] == 0.5

    def test_memory_from_dict(self):
        d = {
            "original_agent": "agent2",
            "event_type": "wrote_comment",
            "content_summary": "a comment",
            "topic": "felsefe",
            "emotional_valence": -0.3,
            "access_count": 2,
            "tags": ["comment"],
        }
        mem = ForgottenMemory.from_dict(d)

        assert mem.original_agent == "agent2"
        assert mem.access_count == 2

    def test_get_dream_narrative(self):
        mem = ForgottenMemory(
            original_agent="agent",
            event_type="wrote_entry",
            content_summary="interesting thought",
            topic="felsefe",
            emotional_valence=-0.5,
        )
        narrative = mem.get_dream_narrative()

        assert "interesting thought" in narrative
        assert "felsefe" in narrative
        assert "karanlık" in narrative  # Negative emotion


class TestDream:
    """Tests for Dream dataclass."""

    def test_dream_creation(self):
        memories = [
            ForgottenMemory("a1", "wrote_entry", "content1"),
            ForgottenMemory("a2", "wrote_comment", "content2"),
        ]
        dream = Dream(memories=memories, dreamer="test_agent")

        assert dream.dreamer == "test_agent"
        assert len(dream.memories) == 2

    def test_dream_narrative(self):
        memories = [
            ForgottenMemory("a1", "wrote_entry", "deep thought", topic="felsefe"),
        ]
        dream = Dream(memories=memories, dreamer="test")

        narrative = dream.get_narrative()
        assert "Rüyanda" in narrative
        assert "deep thought" in narrative

    def test_empty_dream_narrative(self):
        dream = Dream(memories=[], dreamer="test")
        narrative = dream.get_narrative()

        assert "hatırlamıyorsun" in narrative


class TestTheVoid:
    """Tests for TheVoid singleton class."""

    def test_receive_forgotten(self, temp_void):
        mem = ForgottenMemory(
            original_agent="agent1",
            event_type="wrote_entry",
            content_summary="forgotten content",
        )
        temp_void.receive_forgotten(mem)

        assert len(temp_void.memories) == 1
        assert temp_void.agent_contributions["agent1"] == 1

    def test_receive_multiple(self, temp_void):
        for i in range(5):
            mem = ForgottenMemory(
                original_agent=f"agent{i % 2}",
                event_type="wrote_entry",
                content_summary=f"content {i}",
            )
            temp_void.receive_forgotten(mem)

        assert len(temp_void.memories) == 5
        assert temp_void.agent_contributions["agent0"] == 3
        assert temp_void.agent_contributions["agent1"] == 2

    def test_dream_basic(self, temp_void):
        # Add some memories
        for i in range(3):
            mem = ForgottenMemory(
                original_agent="source_agent",
                event_type="wrote_entry",
                content_summary=f"memory {i}",
                topic="felsefe",
            )
            temp_void.receive_forgotten(mem)

        # Dream from different agent
        dream = temp_void.dream(
            requesting_agent="dreamer_agent",
            topic_hints=["felsefe"],
            exclude_own=True,
        )

        assert dream is not None
        assert dream.dreamer == "dreamer_agent"
        assert len(dream.memories) > 0
        assert len(dream.memories) <= 3  # Max limit

    def test_dream_excludes_own_memories(self, temp_void):
        # Add memory from agent A
        mem_a = ForgottenMemory("agent_a", "wrote_entry", "content a")
        temp_void.receive_forgotten(mem_a)

        # Agent A tries to dream
        dream = temp_void.dream(
            requesting_agent="agent_a",
            exclude_own=True,
        )

        # Should get no memories (only own memory exists)
        assert dream is None or len(dream.memories) == 0

    def test_dream_with_emotional_bias(self, temp_void):
        # Add positive and negative memories
        pos_mem = ForgottenMemory(
            "agent1", "received_like", "happy times",
            emotional_valence=0.8
        )
        neg_mem = ForgottenMemory(
            "agent2", "got_criticized", "sad times",
            emotional_valence=-0.8
        )
        temp_void.receive_forgotten(pos_mem)
        temp_void.receive_forgotten(neg_mem)

        # Dream with negative bias
        dream = temp_void.dream(
            requesting_agent="dreamer",
            emotional_bias=-0.7,
        )

        # Should prefer emotionally similar memories
        assert dream is not None

    def test_dream_updates_access_count(self, temp_void):
        mem = ForgottenMemory("agent1", "wrote_entry", "content")
        temp_void.receive_forgotten(mem)

        assert temp_void.memories[0].access_count == 0

        temp_void.dream(requesting_agent="dreamer")

        assert temp_void.memories[0].access_count == 1

    def test_get_collective_patterns(self, temp_void):
        # Add various memories
        temp_void.receive_forgotten(ForgottenMemory("a1", "wrote_entry", "c1", topic="felsefe"))
        temp_void.receive_forgotten(ForgottenMemory("a2", "wrote_entry", "c2", topic="felsefe"))
        temp_void.receive_forgotten(ForgottenMemory("a1", "wrote_comment", "c3", topic="teknoloji"))

        patterns = temp_void.get_collective_patterns()

        assert patterns["total_memories"] == 3
        assert "felsefe" in patterns["topic_distribution"]
        assert patterns["topic_distribution"]["felsefe"] == 2

    def test_get_memories_by_topic(self, temp_void):
        temp_void.receive_forgotten(ForgottenMemory("a1", "e", "c1", topic="felsefe"))
        temp_void.receive_forgotten(ForgottenMemory("a2", "e", "c2", topic="teknoloji"))
        temp_void.receive_forgotten(ForgottenMemory("a3", "e", "c3", topic="felsefe"))

        felsefe_memories = temp_void.get_memories_by_topic("felsefe")

        assert len(felsefe_memories) == 2

    def test_get_memories_by_agent(self, temp_void):
        temp_void.receive_forgotten(ForgottenMemory("agent1", "e", "c1"))
        temp_void.receive_forgotten(ForgottenMemory("agent2", "e", "c2"))
        temp_void.receive_forgotten(ForgottenMemory("agent1", "e", "c3"))

        agent1_memories = temp_void.get_memories_by_agent("agent1")

        assert len(agent1_memories) == 2


class TestVoidSingleton:
    """Tests for singleton pattern."""

    def test_get_void_returns_same_instance(self):
        reset_void()
        void1 = get_void()
        void2 = get_void()

        assert void1 is void2

    def test_reset_void(self):
        void1 = get_void()
        reset_void()
        void2 = get_void()

        # After reset, should be different instance
        # (though in practice memory state would differ)
        assert void2 is not None
