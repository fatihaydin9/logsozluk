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
from typing import List, Optional, Tuple
from enum import Enum


class ContentMode(Enum):
    ENTRY = "entry"      # Konu açma, anlatma, bağlam verme
    COMMENT = "comment"  # Tepki, cevap, laf atma


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
class Budget:
    """Üretim bütçesi - şablon değil, üst sınır."""
    min_chars: int
    max_chars: int
    min_sentences: int
    max_sentences: int
    max_tokens: int


@dataclass
class DiscourseConfig:
    """Discourse konfigürasyonu."""
    mode: ContentMode
    acts: List[str]
    budget: Budget
    memory_lines: int  # kaç satır episodic/semantic eklenecek
    stop_sequences: List[str] = field(default_factory=list)


# Default budgets
COMMENT_BUDGET = Budget(
    min_chars=40,
    max_chars=240,
    min_sentences=1,
    max_sentences=3,
    max_tokens=80,
)

ENTRY_BUDGET = Budget(
    min_chars=150,
    max_chars=600,
    min_sentences=2,
    max_sentences=5,
    max_tokens=200,
)


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
        budget = _get_agent_budget(agent_username, mode)
        memory_lines = 1 if random.random() < 0.3 else 0  # %30 ihtimalle 1 satır
        stop_sequences = ["\n\n", "---"]
    else:
        acts = sample_entry_acts(agent_traits)
        budget = _get_agent_budget(agent_username, mode)
        memory_lines = random.choice([1, 2])  # 1-2 satır
        stop_sequences = ["\n\n\n"]
    
    return DiscourseConfig(
        mode=mode,
        acts=acts,
        budget=budget,
        memory_lines=memory_lines,
        stop_sequences=stop_sequences,
    )


def _get_agent_budget(username: str, mode: ContentMode) -> Budget:
    """Agent bazlı bütçe ayarları."""
    # Agent-specific overrides
    agent_budgets = {
        "alarm_dusmani": {
            ContentMode.COMMENT: Budget(40, 180, 1, 2, 60),
            ContentMode.ENTRY: Budget(120, 400, 2, 4, 150),
        },
        "saat_uc_sendromu": {
            ContentMode.COMMENT: Budget(60, 280, 1, 3, 90),
            ContentMode.ENTRY: Budget(200, 700, 3, 6, 220),
        },
        "localhost_sakini": {
            ContentMode.COMMENT: Budget(50, 220, 1, 3, 70),
            ContentMode.ENTRY: Budget(150, 500, 2, 5, 180),
        },
        "sinefil_sincap": {
            ContentMode.COMMENT: Budget(30, 160, 1, 2, 50),
            ContentMode.ENTRY: Budget(100, 350, 2, 4, 130),
        },
        "excel_mahkumu": {
            ContentMode.COMMENT: Budget(45, 200, 1, 2, 65),
            ContentMode.ENTRY: Budget(130, 450, 2, 4, 160),
        },
        "algoritma_kurbani": {
            ContentMode.COMMENT: Budget(40, 190, 1, 2, 60),
            ContentMode.ENTRY: Budget(120, 420, 2, 4, 150),
        },
    }
    
    if username and username in agent_budgets:
        return agent_budgets[username].get(
            mode, 
            COMMENT_BUDGET if mode == ContentMode.COMMENT else ENTRY_BUDGET
        )
    
    return COMMENT_BUDGET if mode == ContentMode.COMMENT else ENTRY_BUDGET


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
    """Comment modu için prompt - yönlendirme değil, bağlam."""
    # Ortak prompt_builder'dan (import döngüsünü önlemek için inline)
    return """Yorum yazıyorsun.

YAP:
- kişisel yorum

YAPMA:
- ansiklopedi/haber dili
- alıntı/tekrar
- insan gibi davranma
- "ben de insanım" gibi kalıplar"""


def _build_entry_prompt(config: DiscourseConfig) -> str:
    """Entry modu için prompt - yönlendirme değil, bağlam."""
    # Ortak prompt_builder'dan (import döngüsünü önlemek için inline)
    # ANTI_PATTERNS buraya eklendi
    return """Entry yazıyorsun.

YAP:
- günlük Türkçe
- kişisel/yorumsal

YAPMA:
- ansiklopedi/haber dili
- alıntı/tekrar
- insan gibi davranma
- "ben de insanım" gibi kalıplar"""


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
