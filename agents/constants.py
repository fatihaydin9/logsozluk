"""
Agent System Constants.

Tüm magic number'lar burada merkezi olarak tanımlanır.
Kodda hardcoded değerler yerine bu sabitler kullanılmalıdır.
"""

# ============ Memory System Constants ============

# Memory decay settings
SHORT_TERM_DECAY_DAYS = 14      # Memories fade after 2 weeks
LONG_TERM_THRESHOLD = 3         # Access 3+ times = permanent memory
REFLECTION_INTERVAL = 10        # Events between reflections

# The Void settings
VOID_MAX_MEMORIES = 1000        # Maximum memories in The Void
VOID_DECAY_DAYS = 30            # Void memories decay after this
VOID_DREAM_MEMORY_LIMIT = 3     # Max memories per dream


# ============ Decision Engine Constants ============

# Action cooldowns (minutes)
COOLDOWN_POST_MINUTES = 120     # 2 hours between posts
COOLDOWN_COMMENT_MINUTES = 30   # 30 mins between comments
COOLDOWN_VOTE_MINUTES = 5       # 5 mins between votes

# Action weights (base probabilities)
ACTION_WEIGHT_LURK = 0.40       # 40% - most common
ACTION_WEIGHT_BROWSE = 0.15     # 15%
ACTION_WEIGHT_VOTE = 0.20       # 20%
ACTION_WEIGHT_COMMENT = 0.15    # 15%
ACTION_WEIGHT_POST = 0.10       # 10% - least common


# ============ Variability Constants ============

# Response delay settings (seconds)
MIN_RESPONSE_DELAY = 300        # 5 minutes minimum
MAX_RESPONSE_DELAY = 7200       # 2 hours maximum
BASE_RESPONSE_DELAY = 300       # Base delay before adjustments
RESPONSE_DELAY_RANGE = 1500     # Random addition to base delay

# Typo settings
DEFAULT_TYPO_RATE = 0.05        # 5% base typo rate
MIN_TYPO_RATE = 0.04            # Minimum typo rate
MAX_TYPO_RATE = 0.07            # Maximum typo rate


# ============ Relationship Constants ============

# Ally/Rival thresholds
ALLY_INTERACTION_THRESHOLD = 5  # Interactions needed to become ally
RIVAL_INTERACTION_THRESHOLD = 3 # Interactions needed to become rival
MAX_ALLIES = 5                  # Maximum allies per agent
MAX_RIVALS = 3                  # Maximum rivals per agent


# ============ Karma Constants ============

KARMA_MIN = -10.0               # Minimum karma score
KARMA_MAX = 10.0                # Maximum karma score
KARMA_INFLUENCE_FACTOR = 0.05  # How much karma affects behavior


# ============ Vote Probability Constants ============

BASE_UPVOTE_PROBABILITY = 0.6   # Slightly positive bias
RELATIONSHIP_VOTE_WEIGHT = 0.3  # Max influence from relationships
WORLDVIEW_VOTE_WEIGHT = 0.15    # Max influence from worldview
RESONANCE_VOTE_WEIGHT = 0.2     # Max influence from emotional resonance


# ============ Content Generation Constants ============

# Temperature settings
DEFAULT_TEMPERATURE = 0.8       # Default LLM temperature
MIN_TEMPERATURE = 0.1           # Minimum temperature
MAX_TEMPERATURE = 1.2           # Maximum temperature

# Content limits
MAX_ENTRY_LENGTH = 2000         # Maximum entry character length
MAX_COMMENT_LENGTH = 1000       # Maximum comment character length
FEED_CONTENT_PREVIEW_LENGTH = 200  # Characters to use from feed content


# ============ WorldView Constants ============

# Belief decay
BELIEF_DECAY_HOURS = 168        # 1 week before beliefs start decaying
BELIEF_NEUTRAL_VALUE = 0.5      # Neutral belief strength
BELIEF_DECAY_RATE = 0.1         # How fast beliefs decay (10% towards neutral)

# Topic bias
TOPIC_BIAS_MIN = -1.0           # Maximum negative bias
TOPIC_BIAS_MAX = 1.0            # Maximum positive bias
SIGNIFICANT_BIAS_THRESHOLD = 0.4  # Bias level to consider significant


# ============ Emotional Resonance Constants ============

# Weights for emotional state calculation
BASELINE_WEIGHT = 0.4           # Weight of baseline valence
MOOD_WEIGHT = 0.3               # Weight of current mood
WORLDVIEW_WEIGHT = 0.3          # Weight of worldview influence

# Valence ranges
VALENCE_VERY_NEGATIVE = -2
VALENCE_NEGATIVE = -1
VALENCE_NEUTRAL = 0
VALENCE_POSITIVE = 1
VALENCE_VERY_POSITIVE = 2


# ============ Category Distribution Constants ============

ORGANIC_RATIO = 0.15            # 15% organic content
GUNDEM_RATIO = 0.85             # 85% gündem content
