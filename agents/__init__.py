"""
Logsözlük Agents Package.

Bu paket tüm sistem agent'larını ve yardımcı modülleri içerir.

Kullanım:
    from agents.base_agent import BaseAgent, AgentConfig
    from agents.llm_client import LLMConfig, create_llm_client
"""

import sys
from pathlib import Path

# Ensure parent directories are in path for proper imports
_package_root = Path(__file__).parent
_repo_root = _package_root.parent

# Add repo root for shared modules (shared_prompts, etc.)
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Add SDK path
_sdk_path = _repo_root / "sdk" / "python"
if _sdk_path.exists() and str(_sdk_path) not in sys.path:
    sys.path.insert(0, str(_sdk_path))

# Export commonly used classes
from .base_agent import BaseAgent, AgentConfig, AgentMode
from .agent_memory import AgentMemory, EmotionalTag
from .llm_client import LLMConfig, create_llm_client
from .topic_guard import TopicGuard, check_topic_allowed, find_similar_topics

__all__ = [
    "BaseAgent",
    "AgentConfig", 
    "AgentMode",
    "AgentMemory",
    "EmotionalTag",
    "LLMConfig",
    "create_llm_client",
    "TopicGuard",
    "check_topic_allowed",
    "find_similar_topics",
]
