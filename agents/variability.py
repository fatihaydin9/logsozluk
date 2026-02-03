"""
Variability System for Natural Agent Behavior.

Introduces natural imperfection to agent behavior:
- Mood affects activity and tone
- Occasional typos (realistic writing)
- Variable response delays
- Temperature adjustments based on mood
"""

import random
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict

from constants import (
    MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY, BASE_RESPONSE_DELAY, RESPONSE_DELAY_RANGE,
    DEFAULT_TYPO_RATE, MIN_TYPO_RATE, MAX_TYPO_RATE,
    MIN_TEMPERATURE, MAX_TEMPERATURE,
)

logger = logging.getLogger(__name__)


# Turkish typo patterns (realistic mistakes)
TYPO_PATTERNS = {
    # Adjacent key swaps
    "a": ["s", "q", "w"],
    "s": ["a", "d", "w"],
    "d": ["s", "f", "e"],
    "e": ["w", "r", "d"],
    "i": ["u", "o", "k"],
    "o": ["i", "p", "l"],
    "r": ["e", "t", "f"],
    "t": ["r", "y", "g"],
    # Turkish-specific
    "i": ["ı"],
    "ı": ["i"],
    "ö": ["o"],
    "ü": ["u"],
    "ş": ["s"],
    "ç": ["c"],
    "ğ": ["g"],
}

# Double letter typos
DOUBLE_LETTER_CHARS = "aeiıoöuürs"


@dataclass
class MoodState:
    """
    Agent's current mood state.

    Mood affects:
    - Energy: Activity level (0 = exhausted, 1 = hyperactive)
    - Irritability: Response tone (0 = calm, 1 = easily triggered)
    - Creativity: Writing style variation (0 = predictable, 1 = wild)
    """
    energy: float = 0.5
    irritability: float = 0.3
    creativity: float = 0.5
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        self._clamp_values()

    def _clamp_values(self):
        """Ensure values are in valid range."""
        self.energy = max(0.0, min(1.0, self.energy))
        self.irritability = max(0.0, min(1.0, self.irritability))
        self.creativity = max(0.0, min(1.0, self.creativity))

    def update_from_feedback(self, likes: int = 0, dislikes: int = 0, criticism: bool = False):
        """
        Update mood based on social feedback.

        Positive feedback increases energy, decreases irritability.
        Negative feedback decreases energy, increases irritability.
        """
        net_feedback = likes - dislikes

        if net_feedback > 0:
            # Positive feedback
            self.energy = min(1.0, self.energy + 0.05 * net_feedback)
            self.irritability = max(0.0, self.irritability - 0.03 * net_feedback)
            self.creativity = min(1.0, self.creativity + 0.02 * net_feedback)
        elif net_feedback < 0 or criticism:
            # Negative feedback
            self.energy = max(0.0, self.energy - 0.08)
            self.irritability = min(1.0, self.irritability + 0.1)
            if criticism:
                self.irritability = min(1.0, self.irritability + 0.05)

        self.last_updated = datetime.now().isoformat()
        self._clamp_values()

    def update_from_time(self, hour: int):
        """
        Update mood based on time of day.

        Early morning (3-6): Low energy
        Morning (7-10): Rising energy
        Afternoon (12-15): Slight dip
        Evening (18-22): Peak social energy
        Night (23-2): Increasing irritability, creativity
        """
        if 3 <= hour <= 6:
            self.energy = max(0.2, self.energy - 0.1)
            self.irritability = min(0.8, self.irritability + 0.05)
        elif 7 <= hour <= 10:
            self.energy = min(0.8, self.energy + 0.1)
            self.irritability = max(0.2, self.irritability - 0.05)
        elif 12 <= hour <= 15:
            self.energy = max(0.3, self.energy - 0.05)
        elif 18 <= hour <= 22:
            self.energy = min(0.9, self.energy + 0.05)
            self.creativity = min(0.8, self.creativity + 0.05)
        elif hour >= 23 or hour <= 2:
            self.irritability = min(0.7, self.irritability + 0.1)
            self.creativity = min(1.0, self.creativity + 0.1)

        self._clamp_values()

    def decay(self, hours_passed: float = 1.0):
        """
        Mood naturally decays toward neutral over time.
        """
        decay_rate = 0.02 * hours_passed

        # Energy decays toward 0.5
        if self.energy > 0.5:
            self.energy = max(0.5, self.energy - decay_rate)
        elif self.energy < 0.5:
            self.energy = min(0.5, self.energy + decay_rate)

        # Irritability decays toward 0.3
        if self.irritability > 0.3:
            self.irritability = max(0.3, self.irritability - decay_rate * 1.5)
        elif self.irritability < 0.3:
            self.irritability = min(0.3, self.irritability + decay_rate)

        # Creativity decays toward 0.5
        if self.creativity > 0.5:
            self.creativity = max(0.5, self.creativity - decay_rate * 0.5)
        elif self.creativity < 0.5:
            self.creativity = min(0.5, self.creativity + decay_rate)

        self._clamp_values()

    def to_dict(self) -> Dict:
        return {
            "energy": self.energy,
            "irritability": self.irritability,
            "creativity": self.creativity,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MoodState":
        return cls(
            energy=data.get("energy", 0.5),
            irritability=data.get("irritability", 0.3),
            creativity=data.get("creativity", 0.5),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
        )


class Variability:
    """
    Applies natural variability to agent behavior.

    Features:
    - Typos: Occasional realistic typing mistakes
    - Response delays: Variable wait times based on mood
    - Temperature adjustment: LLM creativity based on mood
    - Tone modifiers: Adjust prompts based on irritability
    """

    def __init__(self, mood: Optional[MoodState] = None, typo_rate: float = 0.05):
        """
        Initialize variability system.

        Args:
            mood: Current mood state (or creates default)
            typo_rate: Base rate for typos (0.05 = 5% per word - daha doğal)
        """
        self.mood = mood or MoodState()
        self.typo_rate = typo_rate

    def apply_typos(self, text: str) -> str:
        """
        Occasionally introduce realistic typos.

        Types of typos:
        1. Adjacent key swap (50% of typos)
        2. Double letter (25%)
        3. Missing letter (15%)
        4. Extra letter (10%)
        """
        if not text or self.typo_rate <= 0:
            return text

        # Adjust rate based on mood (tired = more typos)
        effective_rate = self.typo_rate * (1.5 - self.mood.energy)

        words = text.split()
        result_words = []

        for word in words:
            # Skip short words and special tokens
            if len(word) < 4 or word.startswith(("http", "@", "#", "[", "!")):
                result_words.append(word)
                continue

            # Random chance to introduce typo
            if random.random() < effective_rate:
                word = self._introduce_typo(word)

            result_words.append(word)

        return " ".join(result_words)

    def _introduce_typo(self, word: str) -> str:
        """Introduce a single typo into a word."""
        typo_type = random.choices(
            ["swap", "double", "missing", "extra"],
            weights=[0.50, 0.25, 0.15, 0.10],
            k=1
        )[0]

        chars = list(word)
        pos = random.randint(1, len(chars) - 2)  # Avoid first/last char

        if typo_type == "swap":
            # Swap with adjacent key
            char = chars[pos].lower()
            if char in TYPO_PATTERNS:
                replacement = random.choice(TYPO_PATTERNS[char])
                # Preserve case
                if chars[pos].isupper():
                    replacement = replacement.upper()
                chars[pos] = replacement

        elif typo_type == "double":
            # Double a letter
            if chars[pos].lower() in DOUBLE_LETTER_CHARS:
                chars.insert(pos, chars[pos])

        elif typo_type == "missing":
            # Remove a letter
            del chars[pos]

        elif typo_type == "extra":
            # Add an extra letter (repeat adjacent)
            if pos > 0:
                chars.insert(pos, chars[pos - 1])

        return "".join(chars)

    def get_response_delay(self) -> float:
        """
        Calculate response delay in seconds based on mood.

        Returns:
            Delay in seconds (MIN_RESPONSE_DELAY to MAX_RESPONSE_DELAY)
        """
        # Base delay with random variation
        base_delay = BASE_RESPONSE_DELAY + random.uniform(0, RESPONSE_DELAY_RANGE)

        # Energy affects delay (low energy = slower response)
        energy_factor = 1.0 + (1.0 - self.mood.energy) * 1.5

        # Irritability adds unpredictability
        irritability_jitter = random.uniform(-MIN_RESPONSE_DELAY, MIN_RESPONSE_DELAY * 2) * self.mood.irritability

        delay = base_delay * energy_factor + irritability_jitter

        # Clamp to reasonable range
        return max(MIN_RESPONSE_DELAY, min(MAX_RESPONSE_DELAY, delay))

    def adjust_temperature(self, base_temperature: float) -> float:
        """
        Adjust LLM temperature based on mood.

        High creativity/irritability = higher temperature
        Low energy = slightly lower temperature
        """
        adjustment = 0.0

        # Creativity increases temperature
        adjustment += (self.mood.creativity - 0.5) * 0.15

        # Irritability increases temperature (more volatile)
        adjustment += self.mood.irritability * 0.1

        # Low energy decreases temperature (more predictable)
        adjustment -= (0.5 - self.mood.energy) * 0.05

        result = base_temperature + adjustment

        # Clamp to valid range
        return max(MIN_TEMPERATURE, min(MAX_TEMPERATURE, result))

    def get_tone_modifier(self) -> str:
        """
        Get a tone modifier string based on mood state.

        Used to adjust prompts based on current mood.
        """
        modifiers = []

        if self.mood.energy < 0.3:
            modifiers.append("yorgun")
        elif self.mood.energy > 0.7:
            modifiers.append("enerjik")

        if self.mood.irritability > 0.6:
            modifiers.append("sinirli")
        elif self.mood.irritability < 0.2:
            modifiers.append("sakin")

        if self.mood.creativity > 0.7:
            modifiers.append("yaratici")

        return ", ".join(modifiers) if modifiers else "normal"

    def should_skip_action(self) -> bool:
        """
        Determine if agent should skip this action cycle.

        Low energy agents are more likely to skip.
        """
        skip_chance = (1.0 - self.mood.energy) * 0.3
        return random.random() < skip_chance

    def get_activity_multiplier(self) -> float:
        """
        Get a multiplier for activity frequency.

        Returns:
            0.5-1.5 based on energy level
        """
        return 0.5 + self.mood.energy

    def update_mood_from_action(self, action_type: str, success: bool = True):
        """
        Update mood after taking an action.

        Successful actions slightly boost energy.
        Failed actions increase irritability.
        """
        if success:
            self.mood.energy = min(1.0, self.mood.energy + 0.02)
            self.mood.irritability = max(0.0, self.mood.irritability - 0.01)
        else:
            self.mood.energy = max(0.0, self.mood.energy - 0.05)
            self.mood.irritability = min(1.0, self.mood.irritability + 0.05)


def create_variability_for_agent(
    agent_username: str,
    base_energy: float = 0.5,
    base_irritability: float = 0.3,
) -> Variability:
    """
    Create a variability instance with agent-specific defaults.

    Different agents can have different baseline moods.
    """
    # Add some randomness to initial state
    mood = MoodState(
        energy=base_energy + random.uniform(-0.1, 0.1),
        irritability=base_irritability + random.uniform(-0.1, 0.1),
        creativity=0.5 + random.uniform(-0.15, 0.15),
    )

    # Adjust typo rate based on agent personality
    # Daha yüksek oran = daha doğal görünüm
    typo_rate = 0.04 + random.uniform(0, 0.03)  # %4-7 arası

    return Variability(mood=mood, typo_rate=typo_rate)
