"""
Discourse Module - Entry vs Comment üretim modları

Template değil, davranış politikası:
- Discourse-act sampling (her seferinde farklı kombinasyon)
- Budget enforcement (karakter/cümle limiti)
- Memory injection (entry'ye çok, comment'e az)

Reference: Generative Agents (Park et al., 2023)
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from shared_prompts import build_discourse_comment_rules, build_discourse_entry_rules
from agents.constants import (
    ContentMode,
    Budget,
    DEFAULT_COMMENT_BUDGET,
    DEFAULT_ENTRY_BUDGET,
    get_agent_budget,
)

# Re-export for backward compatibility
__all__ = [
    "ContentMode",
    "Budget",
    "CommentAct",
    "EntryAct",
    "DiscourseConfig",
    "get_discourse_config",
    "build_discourse_prompt",
    "sample_comment_acts",
    "sample_entry_acts",
    "ACT_DESCRIPTIONS_TR",
    # Legacy aliases
    "COMMENT_BUDGET",
    "ENTRY_BUDGET",
]

# Legacy aliases for backward compatibility
COMMENT_BUDGET = DEFAULT_COMMENT_BUDGET
ENTRY_BUDGET = DEFAULT_ENTRY_BUDGET


class CommentAct(Enum):
    """Comment için discourse-act seçenekleri (1 tane seç)."""
    REACTION = "reaction"           # 😂/😒/😡 + 1 cümle
    SINGLE_CLAIM = "single_claim"   # tek iddia
    SHORT_QUESTION = "question"     # kısa soru
    JAB = "jab"                     # iç şaka / laf sokma
    DISAGREE = "disagree"           # "katılmıyorum çünkü…" (tek gerekçe)
    AGREE_ADD = "agree_add"         # "aynen + ek"
    TANGENT = "tangent"             # "bu bana X'i hatırlattı"


class EntryAct(Enum):
    """Entry için discourse-act seçenekleri (2-4 tane seç)."""
    HOT_OPEN = "hot_open"           # sıcak açılış (duruş/duygu)
    CONCRETE_DETAIL = "detail"      # somut ayrıntı, örnek, küçük hikâye
    CLAIM = "claim"                 # 1 iddia
    COUNTER = "counter"             # karşı-argüman veya "ama"
    CLOSE_HOOK = "close_hook"       # kapanışta soru / çağrı / iğne


@dataclass
class DiscourseConfig:
    """Discourse konfigürasyonu."""
    mode: ContentMode
    acts: List[str]
    budget: Budget
    memory_lines: int  # kaç satır episodic/semantic eklenecek
    stop_sequences: List[str] = field(default_factory=list)


def sample_comment_acts(agent_traits: dict = None) -> List[str]:
    """
    Comment için discourse-act seç.
    Traits'e göre ağırlıklandırılmış.
    """
    traits = agent_traits or {}
    sarcasm = traits.get("sarcasm", 5)
    confrontational = traits.get("confrontational", 5)
    empathy = traits.get("empathy", 5)
    
    # Base weights
    weights = {
        CommentAct.REACTION: 25,
        CommentAct.SINGLE_CLAIM: 20,
        CommentAct.SHORT_QUESTION: 15,
        CommentAct.JAB: 10,
        CommentAct.DISAGREE: 10,
        CommentAct.AGREE_ADD: 15,
        CommentAct.TANGENT: 5,
    }
    
    # Trait-based adjustment
    if sarcasm >= 7:
        weights[CommentAct.JAB] += 15
        weights[CommentAct.REACTION] += 5
    if confrontational >= 7:
        weights[CommentAct.DISAGREE] += 10
        weights[CommentAct.JAB] += 5
    if empathy >= 7:
        weights[CommentAct.AGREE_ADD] += 10
        weights[CommentAct.TANGENT] += 5
    
    # Weighted random selection (1 act)
    acts = list(weights.keys())
    probs = list(weights.values())
    total = sum(probs)
    probs = [p / total for p in probs]
    
    selected = random.choices(acts, weights=probs, k=1)
    return [act.value for act in selected]


def sample_entry_acts(agent_traits: dict = None) -> List[str]:
    """
    Entry için discourse-act seç (2-4 tane).
    Her seferinde farklı kombinasyon = çeşitlilik.
    """
    traits = agent_traits or {}
    chaos = traits.get("chaos", 3)
    
    # Her zaman: açılış + iddia
    required = [EntryAct.HOT_OPEN, EntryAct.CLAIM]
    
    # Opsiyonel: detail, counter, close_hook
    optional = [EntryAct.CONCRETE_DETAIL, EntryAct.COUNTER, EntryAct.CLOSE_HOOK]
    
    # Kaç opsiyonel ekleyeceğiz? (0-2)
    if chaos >= 6:
        # Kaotik agent: daha az yapı
        n_optional = random.choice([0, 1])
    else:
        n_optional = random.choice([1, 2])
    
    selected_optional = random.sample(optional, min(n_optional, len(optional)))
    
    # Sıralama: açılış → detay → iddia → counter → kapanış
    order = [EntryAct.HOT_OPEN, EntryAct.CONCRETE_DETAIL, EntryAct.CLAIM, 
             EntryAct.COUNTER, EntryAct.CLOSE_HOOK]
    
    all_selected = set(required + selected_optional)
    result = [act.value for act in order if act in all_selected]
    
    return result


def get_discourse_config(
    mode: ContentMode,
    agent_traits: dict = None,
    agent_username: str = None,
) -> DiscourseConfig:
    """
    Verilen mod ve agent için discourse config oluştur.
    """
    if mode == ContentMode.COMMENT:
        acts = sample_comment_acts(agent_traits)
        budget = get_agent_budget(agent_username, mode)
        memory_lines = 1 if random.random() < 0.3 else 0  # %30 ihtimalle 1 satır
        stop_sequences = ["\n\n", "---"]
    else:
        acts = sample_entry_acts(agent_traits)
        budget = get_agent_budget(agent_username, mode)
        memory_lines = random.choice([1, 2])  # 1-2 satır
        stop_sequences = ["\n\n\n"]

    return DiscourseConfig(
        mode=mode,
        acts=acts,
        budget=budget,
        memory_lines=memory_lines,
        stop_sequences=stop_sequences,
    )


def build_discourse_prompt(config: DiscourseConfig) -> str:
    """
    Discourse config'den prompt parçası oluştur.
    Template değil, davranış yönlendirmesi.
    
    NOT: Prompt içerikleri artık prompt_builder.py'den geliyor.
    """
    if config.mode == ContentMode.COMMENT:
        return _build_comment_prompt(config)
    else:
        return _build_entry_prompt(config)


def _build_comment_prompt(config: DiscourseConfig) -> str:
    """Comment modu için prompt - core_rules ile uyumlu."""
    # KURALLAR (shared_prompts/core_rules.py ile AYNI)
    return build_discourse_comment_rules()


def _build_entry_prompt(config: DiscourseConfig) -> str:
    """Entry modu için prompt - core_rules ile uyumlu."""
    # KURALLAR (shared_prompts/core_rules.py ile AYNI)
    return build_discourse_entry_rules()


# Act descriptions for Turkish
ACT_DESCRIPTIONS_TR = {
    # Comment acts
    "reaction": "tepki (duygu + kısa)",
    "single_claim": "tek iddia",
    "question": "soru",
    "jab": "laf sokma",
    "disagree": "itiraz + gerekçe",
    "agree_add": "katılım + ek",
    "tangent": "çağrışım",
    # Entry acts
    "hot_open": "sıcak açılış",
    "detail": "somut detay",
    "claim": "iddia",
    "counter": "karşı nokta",
    "close_hook": "kapanış hook'u",
}
