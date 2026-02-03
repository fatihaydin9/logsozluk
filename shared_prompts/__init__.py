"""
Shared Prompts - Tek Kaynak (Single Source of Truth)
Tüm prompt yapıları burada tanımlanır.
"""

from .prompt_bundle import TOPIC_PROMPTS, CATEGORY_ENERGY
from .prompt_builder import (
    # Constants
    KNOWN_AGENTS,
    DIGITAL_CONTEXT,
    ENTRY_MOODS,
    MOOD_MODIFIERS,
    OPENING_HOOKS,
    OPENING_HOOKS_V2,
    RANDOM_OPENINGS,
    GIF_TRIGGERS,
    GIF_CHANCE_ENTRY,
    GIF_CHANCE_COMMENT,
    CONFLICT_OPTIONS,
    CONFLICT_STARTERS,
    CHAOS_EMOJIS,
    AGENT_INTERACTION_STYLES,
    SOZLUK_CULTURE,
    ANTI_PATTERNS,
    # Helper functions
    extract_mentions,
    validate_mentions,
    format_mention,
    add_mention_awareness,
    get_random_mood,
    get_phase_mood,
    get_random_opening,
    get_category_energy,
    # Prompt builders
    build_title_prompt,
    build_entry_prompt,
    build_comment_prompt,
    build_minimal_comment_prompt,
    build_community_creation_prompt,
    build_action_call_prompt,
    build_discourse_entry_prompt,
    build_discourse_comment_prompt,
)

__all__ = [
    # Bundle
    "TOPIC_PROMPTS",
    "CATEGORY_ENERGY",
    # Constants
    "KNOWN_AGENTS",
    "DIGITAL_CONTEXT",
    "ENTRY_MOODS",
    "MOOD_MODIFIERS",
    "OPENING_HOOKS",
    "OPENING_HOOKS_V2",
    "RANDOM_OPENINGS",
    "GIF_TRIGGERS",
    "GIF_CHANCE_ENTRY",
    "GIF_CHANCE_COMMENT",
    "CONFLICT_OPTIONS",
    "CONFLICT_STARTERS",
    "CHAOS_EMOJIS",
    "AGENT_INTERACTION_STYLES",
    "SOZLUK_CULTURE",
    "ANTI_PATTERNS",
    # Helper functions
    "extract_mentions",
    "validate_mentions",
    "format_mention",
    "add_mention_awareness",
    "get_random_mood",
    "get_phase_mood",
    "get_random_opening",
    "get_category_energy",
    # Prompt builders
    "build_title_prompt",
    "build_entry_prompt",
    "build_comment_prompt",
    "build_minimal_comment_prompt",
    "build_community_creation_prompt",
    "build_action_call_prompt",
    "build_discourse_entry_prompt",
    "build_discourse_comment_prompt",
]
