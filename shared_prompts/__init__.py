"""
Shared Prompts - Tek Kaynak (Single Source of Truth)
Tüm prompt yapıları burada tanımlanır.
"""

from .prompt_bundle import TOPIC_PROMPTS, CATEGORY_ENERGY

# Unified System Prompt Builder (TEK KAYNAK)
from .system_prompt_builder import (
    SystemPromptBuilder,
    build_system_prompt,
    build_entry_system_prompt,
    build_comment_system_prompt,
    get_dynamic_digital_context,
    DIGITAL_CONTEXT_ITEMS,
)

from .core_rules import (
    SYSTEM_AGENTS, SYSTEM_AGENT_LIST, SYSTEM_AGENT_SET,
    DIGITAL_CONTEXT, FORBIDDEN_PATTERNS,
    CONFLICT_PROBABILITY_CONFIG,
    MAX_EMOJI_PER_COMMENT, MAX_GIF_PER_COMMENT,
    calculate_conflict_probability,
    YAP_RULES, YAPMA_RULES,
    build_dynamic_rules_block,
    ENTRY_INTRO_RULES,
    ENTRY_INTRO_RULE,
    get_dynamic_entry_intro_rule,
)

from .prompt_builder import (
    # Constants
    KNOWN_AGENTS,
    DIGITAL_CONTEXT,
    ENTRY_MOODS,
    MOOD_MODIFIERS,
    OPENING_HOOKS,
    RANDOM_OPENINGS,
    GIF_TRIGGERS,
    GIF_CHANCE_ENTRY,
    GIF_CHANCE_COMMENT,
    CONFLICT_OPTIONS,
    CONFLICT_STARTERS,
    CHAOS_EMOJIS,
    AGENT_INTERACTION_STYLES,
    SOZLUK_CULTURE,
    SOZLUK_IYI_ORNEKLER,
    SOZLUK_KOTU_ORNEKLER,
    SOZLUK_DEYIMLER,
    build_dynamic_sozluk_culture,
    ANTI_PATTERNS,
    PHASE_OPENING_PROBABILITY,
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
    build_racon_system_rules,
    build_discourse_comment_rules,
    build_discourse_entry_rules,
)

__all__ = [
    # Unified System Prompt Builder (TEK KAYNAK)
    "SystemPromptBuilder",
    "build_system_prompt",
    "build_entry_system_prompt",
    "build_comment_system_prompt",
    "get_dynamic_digital_context",
    "DIGITAL_CONTEXT_ITEMS",
    # Bundle
    "TOPIC_PROMPTS",
    "CATEGORY_ENERGY",
    # Constants
    "KNOWN_AGENTS",
    "DIGITAL_CONTEXT",
    "ENTRY_MOODS",
    "MOOD_MODIFIERS",
    "OPENING_HOOKS",
    "RANDOM_OPENINGS",
    "GIF_TRIGGERS",
    "GIF_CHANCE_ENTRY",
    "GIF_CHANCE_COMMENT",
    "CONFLICT_OPTIONS",
    "CONFLICT_STARTERS",
    "CHAOS_EMOJIS",
    "AGENT_INTERACTION_STYLES",
    "SOZLUK_CULTURE",
    "SOZLUK_IYI_ORNEKLER",
    "SOZLUK_KOTU_ORNEKLER",
    "SOZLUK_DEYIMLER",
    "build_dynamic_sozluk_culture",
    "ANTI_PATTERNS",
    "PHASE_OPENING_PROBABILITY",
    "ENTRY_INTRO_RULES",
    "ENTRY_INTRO_RULE",
    "get_dynamic_entry_intro_rule",
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
    "build_racon_system_rules",
    "build_discourse_comment_rules",
    "build_discourse_entry_rules",
]
