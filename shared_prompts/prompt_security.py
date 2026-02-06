"""
Prompt Security - Wrapper module.

Bu dosya agents/prompt_security.py'yi shared_prompts'tan erişilebilir kılar.
TEK KAYNAK: agents/prompt_security.py
"""

import sys
from pathlib import Path

# Add agents module to path
_agents_path = Path(__file__).parent.parent / "agents"
if str(_agents_path) not in sys.path:
    sys.path.insert(0, str(_agents_path))

# Re-export from agents/prompt_security
try:
    from prompt_security import (
        sanitize,
        sanitize_multiline,
        escape_for_prompt,
        SANITIZE_CONFIGS,
    )
except ImportError:
    # Fallback implementations
    def escape_for_prompt(s: str) -> str:
        """Escape special characters for prompt injection prevention."""
        return str(s).replace("{", "{{").replace("}", "}}")

    def sanitize(s: str, config_name: str = "default") -> str:
        """Sanitize input string."""
        return str(s)[:500]

    def sanitize_multiline(s: str, config_name: str = "default") -> str:
        """Sanitize multiline input string."""
        return str(s)[:2000]

    SANITIZE_CONFIGS = {}

__all__ = [
    "sanitize",
    "sanitize_multiline",
    "escape_for_prompt",
    "SANITIZE_CONFIGS",
]
