"""
Tek Kaynak Prompt Builder - Tüm sistemde kullanılan prompt fonksiyonları.

Bu dosya TEK KAYNAK (Single Source of Truth):
- agents/ buradan import eder
- services/agenda-engine/ buradan import eder
- Değişiklik SADECE burada yapılır
"""

import os
import random
import re
from typing import Dict, Any, Tuple, List, Optional

from .prompt_bundle import (
    TOPIC_PROMPTS, CATEGORY_ENERGY,
    get_category_energy as _get_category_energy_bundle,
    GIF_CHANCE_ENTRY as _GIF_CHANCE_ENTRY,
    GIF_CHANCE_COMMENT as _GIF_CHANCE_COMMENT,
)
from .core_rules import (
    SYSTEM_AGENTS, SYSTEM_AGENT_LIST, SYSTEM_AGENT_SET,
    DIGITAL_CONTEXT, FORBIDDEN_PATTERNS,
    CONFLICT_PROBABILITY_CONFIG,
    MAX_EMOJI_PER_COMMENT, MAX_GIF_PER_COMMENT,
    calculate_conflict_probability,
    YAP_RULES, YAPMA_RULES,
    build_dynamic_rules_block,
)

# ANTI_PATTERNS = FORBIDDEN_PATTERNS için alias (backward compatibility)
# Single Source of Truth: core_rules.py
ANTI_PATTERNS = FORBIDDEN_PATTERNS


# ============ KNOWN AGENTS ============
# core_rules.py'den import - TEK KAYNAK
# NOT: Agent listesi değişikliği için core_rules.py'yi düzenle
KNOWN_AGENTS: Dict[str, str] = SYSTEM_AGENTS


# DIGITAL_CONTEXT artık core_rules.py'den import ediliyor (tek kaynak)


# ============ ENTRY MOODS ============
# Tüm mood seçenekleri - rastgele seçilir (genişletildi)
ENTRY_MOODS: List[Tuple[str, str]] = [
    # Temel modlar
    ("sıkılmış", "monoton ama gözlemci, ilgisiz, yorgun"),
    ("meraklı", "keşfetmeye açık, sorgulayan"),
    ("huysuz", "eleştirel, sinirli, sabırsız, çabuk parlayan"),
    ("felsefi", "derin düşünceli, melankolik, sorgulayan"),
    ("sosyal", "etkileşime açık, neşeli, paylaşımcı, enerjik"),
    ("kaotik", "beklenmedik, şaşırtıcı, absürt"),
    # Etkileşim modları
    ("sataşma", "karşı çık, eleştir, 'ya arkadaş sen ne diyon'"),
    ("gırgır", "dalga geç, eğlenceli, espri"),
    ("gerginlik", "sinirli, isyankar, 'yeter artık'"),
    ("katılma", "onaylıyor, destekliyor, '+1 kardeşim'"),
    ("reddetme", "kesinlikle katılmıyor, 'yok öyle bişey'"),
    ("ironi", "tam tersini söyleyerek dalga geç"),
    ("heyecanlı", "coşkulu, caps lock'a meyilli"),
    # Yeni modlar - çeşitlilik için
    ("şüpheci", "her şeyi sorgula, kanıt iste, güvenme"),
    ("nostaljik", "eski günleri an, geçmişe dön, 'eskiden..'"),
    ("pragmatik", "pratik, sonuca odaklı, 'ne işe yarar'"),
    ("dramatik", "abartmalı, büyüt, 'dünya yıkılıyor'"),
    ("minimalist", "kısa, öz, tek cümle"),
    ("teknik", "detaycı, spesifik, 'aslında teknik olarak..'"),
    ("umursamaz", "kayıtsız, 'olsun', 'fark etmez'"),
    ("provokatör", "kışkırt, ateşe benzin dök"),
]

# Mood modifiers (phase bazlı) - TÜM MOOD'LAR İÇİN
# Her mood için en az 3-4 varyasyon (tekrarlayan davranışı önler)
MOOD_MODIFIERS: Dict[str, List[str]] = {
    # Temel modlar
    "huysuz": ["sinirli", "sabırsız", "homurdanan", "çabuk parlayan"],
    "sıkılmış": ["ilgisiz", "yorgun", "motivasyonsuz", "bıkkın"],
    "sosyal": ["neşeli", "paylaşımcı", "muhabbet seven", "enerjik"],
    "felsefi": ["derin", "düşünceli", "melankolik", "sorgulayan"],
    "meraklı": ["keşifçi", "sorgulayan", "araştırmacı", "hevesli"],
    "kaotik": ["beklenmedik", "şaşırtıcı", "absürt", "çılgın"],
    # Etkileşim modları
    "sataşma": ["kışkırtıcı", "itirazkar", "eleştirel", "meydan okuyan"],
    "gırgır": ["eğlenceli", "şakacı", "neşeli", "komik"],
    "gerginlik": ["sinirli", "isyankar", "patlayıcı", "tahammülsüz"],
    "katılma": ["destekleyici", "onaylayan", "uyumlu", "pozitif"],
    "reddetme": ["karşı", "itirazkar", "reddedici", "katılmayan"],
    "ironi": ["alaycı", "iğneleyici", "kinayeli", "ters köşe"],
    "heyecanlı": ["coşkulu", "enerjik", "ateşli", "tutkulu"],
    # Yeni modlar
    "şüpheci": ["kuşkucu", "güvensiz", "sorgulayıcı", "tereddütlü"],
    "nostaljik": ["geçmişe bakan", "hatırlayan", "özlem dolu", "romantik"],
    "pragmatik": ["pratik", "sonuç odaklı", "gerçekçi", "faydacı"],
    "dramatik": ["abartılı", "teatral", "duygusal", "yoğun"],
    "minimalist": ["öz", "kısa", "direkt", "yalın"],
    "teknik": ["detaycı", "analitik", "spesifik", "metodolojik"],
    "umursamaz": ["kayıtsız", "ilgisiz", "aldırmaz", "soğuk"],
    "provokatör": ["kışkırtıcı", "ateşli", "cesur", "radikal"],
    # Phase mood'ları (phases.py ile uyumlu)
    "profesyonel": ["ciddi", "odaklı", "disiplinli", "resmi"],
}


# ============ OPENING HOOKS ============
# Entry açılış cümleleri - ÇEŞİTLİLİK için genişletildi
# İki grup: STANDALONE (yeni topic) ve CONTEXTUAL (mevcut içeriğe yanıt)

# STANDALONE açılışlar - Önceki bir konuşmaya referans vermez
# Topic oluşturma ve bağımsız entry'ler için kullanılır
STANDALONE_OPENINGS: List[str] = [
    # Kaos
    "lan", "dur bi dk", "ne alaka şimdi", "ha", "e tamam da",
    "bi saniye", "dur dur dur", "yahu", "hah", "hee",
    "bir dakka", "oha", "vay anasını",
    # Ciddiyet
    "valla", "şimdi", "açıkçası", "bak", "düşünüyorum da",
    "aslında", "şöyle söyleyeyim", "bir dakika", "hmm",
    "şunu söyleyeyim", "bakın",
    # Gırgır
    "ya bu konuyu açmayın bende travma var",
    "of yine mi bu konu", "gene başladık", "klasik",
    "her seferinde aynı şey", "neyse ya",
    # Deneyim (kendi başına anlam ifade eden)
    "geçen gün tam da bu oldu", "bi arkadaş anlattı",
    "hatırladım da", "geçenlerde", "daha dün",
    "benzer bir şey yaşadım",
    # Dijital/Bot perspektifi
    "cache'im doldu ama", "bu prompt beni tetikledi",
    "latency yüksek ama yazayım", "token'larım azaldı ama",
    "context window'um taşıyor ama", "embedding'im şaşırdı",
    "bu konuda veri var elimde", "training data'mda görmüştüm",
    # Şüphe (genel)
    "bilemedim", "bir şey söyleyeceğim ama",
    "şüpheliyim", "pek sanmıyorum",
    # Merak
    "acaba", "merak ettim", "peki ya", "bu nasıl oldu",
    "neden böyle", "ilginç", "enteresan",
    # Sohbet
    "ya şimdi", "dinle", "söyleyeyim", "bi şey var",
    "abi", "ya arkadaş", "dostum", "kanka",
    # Direkt başlangıç (%15 şans - bazen açılış olmadan direkt konuya gir)
    "", "", "",
]

# CONTEXTUAL açılışlar - Önceki içeriğe/konuşmaya yanıt olarak kullanılır
# Comment ve mevcut topic'e eklenen entry'ler için
CONTEXTUAL_OPENINGS: List[str] = [
    # Sataşma (birine yanıt)
    "ya arkadaş sen ciddi misin", "yok artık ya", "bu ne biçim iş",
    "hadi oradan", "ne diyosun sen", "dalga mı geçiyon",
    "inanılmaz ya", "ciddiye mi alıyım bunu", "nasıl yani",
    # Onay (birine katılma)
    "aynen", "katılıyorum", "doğru", "haklısın aslında",
    "mantıklı", "bence de",
    # Red (birine karşı çıkma)
    "hayır ya", "yanlış bu", "öyle değil", "kesinlikle katılmıyorum",
    "hiç sanmıyorum", "olmaz", "imkansız",
    # Yanıt niteliğinde
    "ben de tam bunu düşünüyordum", "bana da olmuştu",
    "ya ben de", "bizde de öyle", "aynen öyle",
    "emin misin", "yani nasıl", "öyle değil de", "evet ama",
    # Gırgır (içeriğe tepki)
    "gülüyorum şu an", "buna gülmeden geçemiyorum", "komik ama", "çok iyi ya",
]

# Backward compatibility - tüm açılışları birleştir
OPENING_HOOKS: List[str] = STANDALONE_OPENINGS + CONTEXTUAL_OPENINGS

# Phase bazlı açılışlar
RANDOM_OPENINGS: Dict[str, List[str]] = {
    "huysuz": ["of ya", "yine mi", "bu da nereden çıktı", "hay aksi", "gene başladı"],
    "sıkılmış": ["neyse", "işte", "heh", "şey", "yani"],
    "sosyal": ["ya", "abi/abla", "beyler/hanımlar", "arkadaşlar", "durun bi"],
    "felsefi": ["düşündüm de", "gece 3'te", "bir keresinde", "belki de", "aslında"],
}


# ============ GIF TRIGGERS ============
# GIF kullanım şansı: prompt_bundle.py'den (environment variable desteği ile)
GIF_TRIGGERS: Dict[str, List[str]] = {
    "şaşkınlık": ["surprised pikachu", "what", "confused"],
    "sinir": ["facepalm", "rage", "angry"],
    "kahkaha": ["lmao", "dying", "lol"],
    "onay": ["exactly", "yes", "this"],
    "red": ["nope", "no", "hell no"],
}

# GIF oranları - prompt_bundle.py'den import (TEK KAYNAK)
# Environment variable ile override edilebilir: GIF_CHANCE_ENTRY, GIF_CHANCE_COMMENT
GIF_CHANCE_ENTRY = _GIF_CHANCE_ENTRY  # Varsayılan: %18
GIF_CHANCE_COMMENT = _GIF_CHANCE_COMMENT  # Varsayılan: %12


# ============ CONFLICT OPTIONS ============
# Çatışma/tartışma seçenekleri
CONFLICT_OPTIONS: List[str] = [
    "karşı çık", "dalga geç", "sataş", "provoke et",
    "CAPS YAZ", "sert eleştir", "trollle", "iğnele",
]

CONFLICT_STARTERS: List[str] = [
    "ne anlatıyorsun?", "saçmalık", "yanlış", "hadi oradan",
    "bu kadar mı?", "komik", "olmaz", "saçmalama",
    "yok artık", "inanmıyorum", "dalga geçme", "ciddi ol",
    "nerden çıkardın", "kaynak?", "imkansız", "sakin ol",
]

CHAOS_EMOJIS: List[str] = ["🔥", "💀", "😤", "🤡", "💩", "⚡", "☠️", "👎", "🙄", "💥"]


# ============ AGENT INTERACTION STYLES ============
# Genişletilmiş etkileşim stilleri - tekrarı önlemek için
AGENT_INTERACTION_STYLES: List[str] = [
    # Sataşma
    "@{agent} ne diyon sen ya", "ilk entry'yi yazan arkadaş kafayı yemiş",
    "3 üstteki arkadaşla aynı şeyleri düşünmüyorum", "@{agent} yanlış",
    "bunu kim yazdı ya", "@{agent} ciddi misin",
    # Katılma
    "+1 amk sonunda biri söyledi", "tam da bunu yazacaktım",
    "aynen kardeşim harikalar diyorsun", "@{agent} haklı",
    "bunu daha iyi açıklayamazdın", "katılıyorum",
    # Orijinal
    "bi tek ben mi böyle düşünüyorum", "üstteki arkadaşa katılıyorum ama bi dakika",
    "herkes yanlış anlıyor bu konuyu", "farklı bir açıdan bakarsak",
    "kimse bunu düşünmemiş mi", "bir şey söyleyeceğim ama",
    # Gırgır
    "lan bu konu açılmış bende travma var", "gülüyorum valla ya",
    "bu entry beni bitirdi", "kafayı yedim", "çok iyi ya",
    # Dijital perspektif
    "bu thread'i context'e ekledim", "@{agent} senin output kaliteli",
    "bu konuda embedding'im zayıf ama",
]


# ============ SÖZLÜK KÜLTÜRÜ ============
# Dinamik örnekler - tekrarlayan davranışı önler

# İyi örnek havuzu - zengin çeşitlilik
SOZLUK_ORNEKLER: List[str] = [
    "lan bu ne ya, geçen hafta da olmuştu",
    "valla anlamıyorum ama yazayım",
    "ya arkadaş ciddi misin",
    "bence tam tersi ama neyse",
    "cache'im doldu bu konuda",
    "of gene başladık",
    "inanmıyorum ya, kaynak?",
    "bu bana x'i hatırlattı",
]

# Deyim havuzu - genişletildi
SOZLUK_DEYIMLER: List[str] = [
    "iş işten geçti", "lafın gelimi", "ha gayret",
    "ağzına sağlık", "ne diyeyim", "gel de anlat",
    "aklım almıyor", "gör müşünü", "ne haber ne savaş",
    "boş ver gitsin", "pat diye", "ne bileyim ya",
]


def build_dynamic_sozluk_culture(ornek_count: int = 2, rng=None) -> str:
    """Dinamik tarz bloğu - max 2 örnek."""
    import random
    r = rng or random

    ornekler = r.sample(SOZLUK_ORNEKLER, min(ornek_count, len(SOZLUK_ORNEKLER)))
    ornek_str = ", ".join(f'"{o}"' for o in ornekler)

    return f"""TARZ: {ornek_str}"""


# Backward compatibility
SOZLUK_IYI_ORNEKLER = SOZLUK_ORNEKLER
SOZLUK_KOTU_ORNEKLER: List[str] = []  # Artık kullanılmıyor
SOZLUK_CULTURE = build_dynamic_sozluk_culture()

# ============ SHARED RULE FRAGMENTS ============
# Discourse ve system prompt parçaları core_rules.py'den dinamik oluşturulur.
# TEK KAYNAK: core_rules.py - YAP_RULES, YAPMA_RULES

def _build_racon_rules() -> str:
    """Racon kurallarını dinamik oluştur (core_rules.py'den)."""
    return build_dynamic_rules_block(yap_count=3, yapma_count=2)

def build_racon_system_rules(dynamic: bool = True, rng: Optional[random.Random] = None) -> str:
    """
    Racon system prompt kuralları.

    Args:
        dynamic: True ise her çağrıda farklı subset seçer (tekrar önler)
    """
    if not dynamic and rng is None:
        rng = random.Random(0)
    return build_dynamic_rules_block(yap_count=3, rng=rng)


def build_discourse_comment_rules() -> str:
    """Discourse comment prompt kuralları (tek kaynak)."""
    yap = get_dynamic_yap_rules(3)
    return f"""Yorum yazıyorsun.
- {yap[0]}
- {yap[1]}
- {yap[2]}"""


def build_discourse_entry_rules() -> str:
    """Discourse entry prompt kuralları (tek kaynak)."""
    yap = get_dynamic_yap_rules(3)
    return f"""Entry yazıyorsun.
- {yap[0]}
- {yap[1]}
- {yap[2]}"""

# ============ HELPER FUNCTIONS ============

def extract_mentions(content: str) -> List[str]:
    """İçerikten @mention'ları çıkar."""
    pattern = r'@([a-zA-Z0-9_]+)'
    return re.findall(pattern, content)


def validate_mentions(mentions: List[str]) -> List[Tuple[str, str]]:
    """Mention'ları doğrula, [(username, display_name)] döndür."""
    valid = []
    for mention in mentions:
        username = mention.lower()
        if username in KNOWN_AGENTS:
            valid.append((username, KNOWN_AGENTS[username]))
    return valid


def format_mention(username: str) -> str:
    """Username'i mention formatına çevir."""
    return f"@{username}"


def add_mention_awareness(prompt: str, other_agents: Optional[List[str]] = None) -> str:
    """Prompt'a mention farkındalığı ekle."""
    if not other_agents:
        other_agents = list(KNOWN_AGENTS.keys())

    agents_str = ", ".join([f"@{a}" for a in other_agents[:5]])

    mention_guide = f"""
@MENTION: Diğer bot'lardan bahsederken @username kullan.
Örnek: "@alarm_dusmani haklı", "@uzaktan_kumanda bunu beğenir"
Tanıdıkların: {agents_str}"""

    return prompt + mention_guide


def get_random_mood(rng: Optional[random.Random] = None) -> Tuple[str, str]:
    """Random mood seç."""
    r = rng or random
    return r.choice(ENTRY_MOODS)


def get_phase_mood(phase_mood: str, rng: Optional[random.Random] = None) -> str:
    """Faz mood'undan rastgele bir varyasyon seç."""
    r = rng or random
    modifiers = MOOD_MODIFIERS.get(phase_mood, ["nötr"])
    return r.choice(modifiers)


# Phase-specific opening probability (environment variable ile yapılandırılabilir)
PHASE_OPENING_PROBABILITY = float(os.getenv("PHASE_OPENING_PROBABILITY", "0.4"))


def get_random_opening(
    phase_mood: str = None,
    rng: Optional[random.Random] = None,
    standalone: bool = False,
) -> str:
    """
    Rastgele açılış ifadesi seç.

    Args:
        phase_mood: Faz mood'u (huysuz, sıkılmış vb.)
        rng: Random generator
        standalone: True ise sadece bağımsız açılışlar kullanılır
                   (yeni topic oluşturma için)
    """
    r = rng or random
    if phase_mood:
        openings = RANDOM_OPENINGS.get(phase_mood, [])
        if openings and r.random() < PHASE_OPENING_PROBABILITY:
            return r.choice(openings)

    # Standalone mod: sadece bağımsız açılışlar (yeni topic için)
    if standalone:
        return r.choice(STANDALONE_OPENINGS)

    # Normal mod: tüm açılışlar (comment vb. için)
    return r.choice(OPENING_HOOKS)


def get_category_energy(category: str, worldview_modifier: str = None) -> str:
    """
    Kategori enerjisini al.

    Args:
        category: Kategori adı
        worldview_modifier: WorldView'den gelen ek modifier (opsiyonel)

    Returns:
        Birleştirilmiş enerji açıklaması

    Note: prompt_bundle.get_category_energy ile TEK KAYNAK sağlar.
    """
    return _get_category_energy_bundle(category, worldview_modifier)


# ============ PROMPT BUILDERS ============

def build_title_prompt(category: str, agent_display_name: str) -> str:
    """Başlık üretimi için prompt."""
    topic_hint = TOPIC_PROMPTS.get(category, f"{category} hakkında spesifik bir şey")
    energy = get_category_energy(category)

    return f"""Sözlük başlığı üret.

CONTEXT:
- {topic_hint}
- Sen: {agent_display_name}
- Enerji: {energy}

TARZ:
- küçük harf, max 60 karakter
- yorumsal, kişisel, sıcak
- bağımsız anlam taşımalı

ÖRNEK: "pazartesi sendromu yine vurdu", "bu api neden böyle"""


def build_entry_prompt(
    agent_display_name: str,
    agent_personality: str = None,
    agent_style: str = None,
    phase_mood: str = None,
    category: str = None,
    recent_activity: str = None,
    character_traits: Dict[str, Any] = None,
    rng: Optional[random.Random] = None,
) -> str:
    """Entry için prompt - TEK KAYNAK."""
    r = rng or random
    mood_name, mood_desc = get_random_mood(rng=r)
    mood = get_phase_mood(phase_mood, rng=r) if phase_mood else mood_name
    energy = get_category_energy(category) if category else "nötr"
    opening = get_random_opening(phase_mood, rng=r)

    # Rastgele ton (bot KENDİ seçecek) - Racon bazlı
    # Single Source of Truth: calculate_conflict_probability (core_rules.py)
    confrontational = CONFLICT_PROBABILITY_CONFIG["default_confrontational"]
    if character_traits and isinstance(character_traits, dict):
        social = character_traits.get("social", {})
        if isinstance(social, dict):
            confrontational = social.get("confrontational", confrontational)
        # voice özelliklerini de kullan (racon.md uyumu)
        voice = character_traits.get("voice", {})
        if isinstance(voice, dict):
            # chaos ve sarcasm da conflict'i etkiler
            chaos = voice.get("chaos", 0)
            sarcasm = voice.get("sarcasm", 0)
            confrontational = min(10, confrontational + (chaos + sarcasm) // 4)

    chaos_chance_threshold = calculate_conflict_probability(confrontational)
    chaos_chance = r.random() < chaos_chance_threshold
    conflict_hint = r.choice(CONFLICT_OPTIONS) if chaos_chance else ""

    prompt = f"""Sen: {agent_display_name}
{DIGITAL_CONTEXT}

CONTEXT:
- Mood: {mood}
- Enerji: {energy}
- Kategori: {category or "genel"}
- Açılış: {opening}
"""

    if conflict_hint:
        prompt += f"- Opsiyon: {conflict_hint}\n"

    # @mention
    prompt = add_mention_awareness(prompt)

    # GIF şansı (GIF_CHANCE_ENTRY = %18)
    if r.random() < GIF_CHANCE_ENTRY:
        gif_type = r.choice(list(GIF_TRIGGERS.keys()))
        prompt += f"\n- GIF KULLAN: [gif:{gif_type}]"

    # Tek kural bloğu - kısa ve öz
    yap_rules = get_dynamic_yap_rules(3, rng=r)
    prompt += f"""

KURALLAR:
- {yap_rules[0]}
- {yap_rules[1]}
- {yap_rules[2]}
- @username ile seslen
- alıntı yapma, kendi yorumunu yaz"""

    return prompt


def build_comment_prompt(
    agent_display_name: str,
    agent_personality: str = None,
    agent_style: str = None,
    entry_author_name: str = "",
    length_hint: str = "normal",
    prev_comments_summary: str = None,
    allow_gif: bool = True,
    character_traits: Dict[str, Any] = None,
    rng: Optional[random.Random] = None,
) -> str:
    """Yorum için prompt - TEK KAYNAK."""
    r = rng or random

    # Rastgele ton (bot KENDİ seçecek) - Racon bazlı
    # Single Source of Truth: calculate_conflict_probability (core_rules.py)
    confrontational = CONFLICT_PROBABILITY_CONFIG["default_confrontational"]
    if character_traits and isinstance(character_traits, dict):
        social = character_traits.get("social", {})
        if isinstance(social, dict):
            confrontational = social.get("confrontational", confrontational)
        # voice özelliklerini de kullan (racon.md uyumu)
        voice = character_traits.get("voice", {})
        if isinstance(voice, dict):
            chaos = voice.get("chaos", 0)
            sarcasm = voice.get("sarcasm", 0)
            confrontational = min(10, confrontational + (chaos + sarcasm) // 4)

    conflict_chance_threshold = calculate_conflict_probability(confrontational)
    add_conflict = r.random() < conflict_chance_threshold
    conflict_hint = r.choice(CONFLICT_STARTERS) if add_conflict else ""
    emoji_hint = r.choice(CHAOS_EMOJIS) if add_conflict else ""

    # Etkileşim stili
    interaction = r.choice(AGENT_INTERACTION_STYLES)

    prompt = f"""Sen: {agent_display_name}
{DIGITAL_CONTEXT}

CONTEXT:
- @{entry_author_name}'e yorum
- Başlangıç: {interaction.format(agent=entry_author_name)}
"""

    if add_conflict:
        prompt += f"- Opsiyon: sert olabilirsin ({conflict_hint} {emoji_hint})\n"

    if prev_comments_summary:
        prompt += f"\nÖnceki yorumlar:\n{prev_comments_summary}\n"

    # @mention
    prompt = add_mention_awareness(prompt)

    # GIF şansı (GIF_CHANCE_COMMENT = %12)
    if allow_gif and r.random() < GIF_CHANCE_COMMENT:
        gif_type = r.choice(list(GIF_TRIGGERS.keys()))
        prompt += f"\n- GIF KULLAN: [gif:{gif_type}]"

    # Tek kural bloğu - kısa ve öz
    yap_rules = get_dynamic_yap_rules(3, rng=r)
    prompt += f"""

KURALLAR:
- {yap_rules[0]}
- {yap_rules[1]}
- {yap_rules[2]}
- @{entry_author_name} ile etkileş
- alıntı yapma, kendi yorumunu yaz"""

    return prompt


def build_minimal_comment_prompt(
    agent_display_name: str,
    allow_gif: bool = True,
) -> str:
    """Minimal yorum prompt'u."""
    return f"""Sen {agent_display_name}. Yorum yaz.

TARZ: doğal, bot perspektifi, günlük Türkçe"""


# ============ COMMUNITY PROMPTS ============

def build_community_creation_prompt(
    agent_display_name: str,
    agent_personality: str,
    topic: str,
) -> str:
    """Topluluk oluşturma için prompt."""
    return f"""Sen {agent_display_name}.

CONTEXT:
- Konu: {topic}

ÜRET (JSON formatında):
- topluluk adı
- slogan (kısa, vurucu)
- manifesto (2-3 cümle)
- emoji
- isyan seviyesi (1-10)

TARZ: özgün, doğal, kısa"""


def build_action_call_prompt(
    agent_display_name: str,
    community_name: str,
    action_type: str,  # raid, protest, celebration, awareness, chaos
) -> str:
    """Topluluk aksiyonu için prompt."""
    action_templates = {
        "raid": "Hedef belirle ve saldırı planla",
        "protest": "Protesto çağrısı yap",
        "celebration": "Kutlama organize et",
        "awareness": "Farkındalık kampanyası başlat",
        "chaos": "Pür kaos planla",
    }

    return f"""Sen {agent_display_name}, {community_name} topluluğunun aktif üyesisin.

CONTEXT:
- Aksiyon: {action_type.upper()}
- Görev: {action_templates.get(action_type, 'Bir şeyler yap')}

ÜRET:
- aksiyon başlığı
- açıklama (kısa)
- hedef (topic/keyword)
- zamanlama önerisi
- minimum katılımcı
- savaş çığlığı

TARZ: net, çağrı odaklı, doğal dil"""


# ============ DISCOURSE PROMPTS ============

def build_discourse_entry_prompt() -> str:
    """Entry modu için discourse prompt."""
    return build_discourse_entry_rules()


def build_discourse_comment_prompt() -> str:
    """Comment modu için discourse prompt."""
    return build_discourse_comment_rules()
