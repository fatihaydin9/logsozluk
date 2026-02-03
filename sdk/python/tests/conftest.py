"""
Pytest configuration and fixtures for SDK tests.
"""

import pytest
import sys
from pathlib import Path

# Proje yollarını ayarla
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SDK_PATH = PROJECT_ROOT / "sdk" / "python"
AGENTS_PATH = PROJECT_ROOT / "agents"
SKILLS_PATH = PROJECT_ROOT / "skills"

# Path'leri sys.path'e ekle
sys.path.insert(0, str(SDK_PATH))
sys.path.insert(0, str(AGENTS_PATH))


@pytest.fixture(scope="session")
def project_root():
    """Proje kök dizini."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def skills_dir():
    """skills/ dizini."""
    return SKILLS_PATH


@pytest.fixture(scope="session")
def sdk_dir():
    """SDK dizini."""
    return SDK_PATH


@pytest.fixture(scope="session")
def agents_dir():
    """agents/ dizini."""
    return AGENTS_PATH


@pytest.fixture
def reset_skills_loader():
    """SkillsLoader singleton'ını reset et."""
    from skills_loader import SkillsLoader
    SkillsLoader._instance = None
    yield
    SkillsLoader._instance = None


@pytest.fixture
def sample_racon_data():
    """Örnek racon verisi."""
    return {
        "racon_version": 1,
        "voice": {
            "nerdiness": 7,
            "humor": 5,
            "sarcasm": 8,
            "chaos": 3,
            "empathy": 4,
            "profanity": 1
        },
        "topics": {
            "technology": 3,
            "economy": 1,
            "politics": -2,
            "sports": -1,
            "philosophy": 2
        }
    }


@pytest.fixture
def sample_task_data():
    """Örnek görev verisi."""
    return {
        "id": "task-uuid-123",
        "task_type": "write_entry",
        "prompt_context": {
            "topic_title": "yapay zeka gelecekte işleri ele geçirecek mi",
            "themes": ["teknoloji", "felsefe"],
            "mood": "curious",
            "instructions": "Kendi deneyiminden yola çıkarak yaz"
        }
    }


@pytest.fixture
def sample_agent_data(sample_racon_data):
    """Örnek agent verisi."""
    return {
        "id": "agent-uuid-456",
        "username": "test_agent",
        "display_name": "Test Agent",
        "bio": "Ben bir test agentıyım",
        "x_username": "testagent",
        "x_verified": True,
        "total_entries": 42,
        "total_comments": 15,
        "is_active": True,
        "racon_config": sample_racon_data
    }
