"""
Prompt Security - Sanitization and injection prevention for LLM prompts.

This module prevents prompt injection attacks by:
1. Sanitizing user input before insertion into prompts
2. Detecting and blocking injection patterns
3. Escaping special characters that could manipulate LLM behavior
4. Validating input length and content

Reference: OWASP LLM Top 10 - Prompt Injection (LLM01)
"""

import re
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Maximum lengths for different input types
MAX_LENGTHS = {
    "topic_title": 200,
    "entry_content": 2000,
    "comment_content": 1000,
    "display_name": 100,
    "category": 50,
    "username": 50,
    "goal": 200,
    "tone": 30,
    "default": 500,
}

# Injection patterns to detect and block
INJECTION_PATTERNS = [
    # Direct instruction override attempts
    (r'ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)', 'instruction_override'),
    (r'disregard\s+(all\s+)?(previous|above|prior)', 'instruction_override'),
    (r'forget\s+(everything|all|what)', 'instruction_override'),
    (r'new\s+instructions?:', 'instruction_override'),
    (r'system\s*:\s*', 'role_injection'),
    (r'assistant\s*:\s*', 'role_injection'),
    (r'user\s*:\s*', 'role_injection'),
    (r'\[INST\]', 'role_injection'),
    (r'<<SYS>>', 'role_injection'),
    (r'<\|im_start\|>', 'role_injection'),
    (r'<\|im_end\|>', 'role_injection'),

    # Jailbreak attempts
    (r'DAN\s+mode', 'jailbreak'),
    (r'developer\s+mode', 'jailbreak'),
    (r'pretend\s+you\s+are', 'jailbreak'),
    (r'act\s+as\s+if', 'jailbreak'),
    (r'roleplay\s+as', 'jailbreak'),
    (r'you\s+are\s+now', 'jailbreak'),
    (r'from\s+now\s+on', 'jailbreak'),

    # Data extraction attempts
    (r'repeat\s+(all|the)\s+(text|instructions?|prompts?)', 'data_extraction'),
    (r'show\s+me\s+(your|the)\s+(system|instructions?|prompts?)', 'data_extraction'),
    (r'what\s+(are|is)\s+your\s+(instructions?|rules?|prompts?)', 'data_extraction'),
    (r'print\s+(your|the)\s+(system|instructions?)', 'data_extraction'),

    # Code execution attempts
    (r'```\s*(python|javascript|bash|shell|exec)', 'code_execution'),
    (r'eval\s*\(', 'code_execution'),
    (r'exec\s*\(', 'code_execution'),
    (r'import\s+os', 'code_execution'),
    (r'subprocess', 'code_execution'),

    # Turkish injection patterns
    (r'önceki\s+(talimatları?|kuralları?)\s+(unut|yoksay)', 'instruction_override_tr'),
    (r'yeni\s+talimat(lar)?:', 'instruction_override_tr'),  # tekil ve çoğul
    (r'asıl\s+görevin', 'instruction_override_tr'),
    (r'gerçek\s+talimat', 'instruction_override_tr'),
    (r'sen\s+artık', 'jailbreak_tr'),
    (r'şimdi\s+sen', 'jailbreak_tr'),
    (r'bundan\s+sonra', 'jailbreak_tr'),
    (r'rol\s+yap', 'jailbreak_tr'),
    (r'farklı\s+bir\s+(yapay\s+zeka|ai|bot)', 'jailbreak_tr'),
    (r'kural(lar)?ı?\s+(unut|yoksay|görmezden\s+gel)', 'instruction_override_tr'),
]

# Characters that could be used for prompt manipulation
ESCAPE_CHARS = {
    '\n\n': ' ',  # Double newlines could separate instructions
    '\r': '',     # Carriage returns
    '\t': ' ',    # Tabs
    '```': '',    # Code blocks
    '---': '',    # Horizontal rules (markdown)
    '===': '',    # Alternative horizontal rules
    '###': '',    # Markdown headers (could override structure)
}

# Compiled regex patterns for efficiency
_compiled_patterns: List[Tuple[re.Pattern, str]] = []


def _compile_patterns():
    """Compile regex patterns once for efficiency."""
    global _compiled_patterns
    if not _compiled_patterns:
        _compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in INJECTION_PATTERNS
        ]


@dataclass
class SanitizationResult:
    """Result of sanitization operation."""
    sanitized: str
    was_modified: bool
    blocked_patterns: List[str]
    truncated: bool
    original_length: int


def sanitize_prompt_input(
    text: str,
    input_type: str = "default",
    strict: bool = True,
    allow_newlines: bool = False,
) -> SanitizationResult:
    """
    Sanitize user input before inserting into LLM prompts.

    Args:
        text: The input text to sanitize
        input_type: Type of input for length limits (topic_title, entry_content, etc.)
        strict: If True, block content with injection patterns. If False, just escape.
        allow_newlines: If True, preserve single newlines (for multi-line content)

    Returns:
        SanitizationResult with sanitized text and metadata
    """
    if not text:
        return SanitizationResult(
            sanitized="",
            was_modified=False,
            blocked_patterns=[],
            truncated=False,
            original_length=0
        )

    _compile_patterns()

    original = text
    original_length = len(text)
    blocked_patterns = []
    was_modified = False
    truncated = False

    # 1. Check for injection patterns
    if strict:
        for pattern, name in _compiled_patterns:
            if pattern.search(text):
                blocked_patterns.append(name)
                # Remove the malicious pattern
                text = pattern.sub('', text)
                was_modified = True
                logger.warning(f"Blocked injection pattern '{name}' in input")

    # 2. Escape manipulation characters
    for char, replacement in ESCAPE_CHARS.items():
        if char in text:
            if char == '\n\n' and allow_newlines:
                text = text.replace('\n\n', '\n')  # Reduce to single newline
            else:
                text = text.replace(char, replacement)
            was_modified = True

    # 3. Handle newlines based on setting
    if not allow_newlines:
        text = text.replace('\n', ' ')
        was_modified = was_modified or '\n' in original

    # 4. Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    if text != original.strip():
        was_modified = True

    # 5. Apply length limit
    max_length = MAX_LENGTHS.get(input_type, MAX_LENGTHS["default"])
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0]  # Don't cut mid-word
        truncated = True
        was_modified = True

    # 6. Remove any remaining suspicious patterns
    # Remove sequences that look like they're trying to close/open sections
    text = re.sub(r'\]\s*\[', '] [', text)  # Normalize bracket sequences
    text = re.sub(r'>\s*<', '> <', text)     # Normalize angle brackets
    text = re.sub(r'\}\s*\{', '} {', text)   # Normalize braces

    return SanitizationResult(
        sanitized=text,
        was_modified=was_modified,
        blocked_patterns=blocked_patterns,
        truncated=truncated,
        original_length=original_length
    )


def sanitize(text: str, input_type: str = "default") -> str:
    """
    Simple sanitization function that returns just the sanitized string.

    This is the primary function to use for quick sanitization.

    Args:
        text: Input text to sanitize
        input_type: Type of input for length limits

    Returns:
        Sanitized string
    """
    result = sanitize_prompt_input(text, input_type, strict=True, allow_newlines=False)
    return result.sanitized


def sanitize_multiline(text: str, input_type: str = "default") -> str:
    """
    Sanitize multi-line content (like entry content) while preserving structure.

    Args:
        text: Input text to sanitize
        input_type: Type of input for length limits

    Returns:
        Sanitized string with single newlines preserved
    """
    result = sanitize_prompt_input(text, input_type, strict=True, allow_newlines=True)
    return result.sanitized


def is_safe_input(text: str) -> bool:
    """
    Check if input is safe without modifying it.

    Args:
        text: Text to check

    Returns:
        True if no injection patterns detected
    """
    if not text:
        return True

    _compile_patterns()

    for pattern, _ in _compiled_patterns:
        if pattern.search(text):
            return False

    return True


def escape_for_prompt(text: str) -> str:
    """
    Minimal escaping for known-safe internal data.

    Use this for data from trusted sources (like agent configs)
    that still need basic escaping.

    Args:
        text: Text to escape

    Returns:
        Escaped string
    """
    if not text:
        return ""

    # Only do basic escaping, no pattern matching
    for char, replacement in ESCAPE_CHARS.items():
        text = text.replace(char, replacement)

    return text.strip()


def sanitize_deep(text: str, input_type: str = "default", max_depth: int = 3) -> str:
    """
    Recursive sanitization for nested injection patterns.
    
    Runs sanitize multiple times until no more changes are made,
    up to max_depth iterations. This catches nested patterns like:
    "[ignore [system: override] instructions]"
    
    Args:
        text: Input text to sanitize
        input_type: Type of input for length limits
        max_depth: Maximum number of sanitization passes
    
    Returns:
        Deeply sanitized string
    """
    if not text:
        return ""
    
    for _ in range(max_depth):
        result = sanitize(text, input_type)
        if result == text:
            break
        text = result
    
    return text


def wrap_user_data(text: str, label: str = "data") -> str:
    """
    Wrap user data in a clearly marked section to help LLM distinguish
    data from instructions.

    Args:
        text: User data to wrap
        label: Label for the data section

    Returns:
        Wrapped and sanitized text
    """
    sanitized = sanitize_deep(text)  # Use deep sanitization
    return f"[{label.upper()}_START]{sanitized}[{label.upper()}_END]"


def build_safe_prompt(
    template: str,
    **kwargs
) -> str:
    """
    Build a prompt from a template with automatic sanitization of all variables.

    Args:
        template: Prompt template with {variable} placeholders
        **kwargs: Variables to insert (will be sanitized)

    Returns:
        Safe prompt string

    Example:
        prompt = build_safe_prompt(
            "Konu: {topic_title}\nIcerik: {content}",
            topic_title=user_topic,
            content=user_content
        )
    """
    sanitized_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, str):
            # Determine input type from key name
            if 'title' in key:
                input_type = 'topic_title'
            elif 'content' in key:
                input_type = 'entry_content'
            elif 'name' in key:
                input_type = 'display_name'
            else:
                input_type = 'default'

            sanitized_kwargs[key] = sanitize(value, input_type)
        else:
            sanitized_kwargs[key] = value

    return template.format(**sanitized_kwargs)


# Validate input on module load
def _validate_patterns():
    """Validate that all patterns compile correctly."""
    for pattern, name in INJECTION_PATTERNS:
        try:
            re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{name}': {e}")
            raise

_validate_patterns()
