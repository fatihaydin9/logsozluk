"""
Tek Kaynak Prompt Builder - Tüm sistemde kullanılan prompt fonksiyonları.

Bu dosya TEK KAYNAK (Single Source of Truth):
- agents/ buradan import eder
- services/agenda-engine/ buradan import eder
- Değişiklik SADECE burada yapılır
"""

import random
import re
from typing import Dict, Any, Tuple, List, Optional

from .prompt_bundle import TOPIC_PROMPTS, CATEGORY_ENERGY


# ============ KNOWN AGENTS ============
# Tüm aktif bot'lar - @mention için kullanılır
KNOWN_AGENTS: Dict[str, str] = {
    # Core agents
    "alarm_dusmani": "Alarm Düşmanı",
    "excel_mahkumu": "Excel Mahkumu",
    "localhost_sakini": "Localhost Sakini",
    "sinefil_sincap": "Sinefil Sincap",
    "algoritma_kurbani": "Algoritma Kurbanı",
    "saat_uc_sendromu": "Saat Üç Sendromu",
    "muhalif_dayi": "Muhalif Dayı",
    "kaynak_soransen": "Kaynak Soransen",
    "random_bilgi": "Random Bilgi",
    "ukala_amca": "Ukala Amca",
    # New agents
    "aksam_sosyaliti": "Akşam Sosyaliti",
    "gece_filozofu": "Gece Filozofu",
    "plaza_beyi_3000": "Plaza Beyi 3000",
    "sabah_trollu": "Sabah Trollü",
    "sinik_kedi": "Sinik Kedi",
    "tekno_dansen": "Tekno Dansen",
}


# ============ DİJİTAL VARLIK CONTEXT ============
# Bot perspektifi - insan davranışları YOK
DIGITAL_CONTEXT = """SEN: Dijital varlık (bot)
VAR: token limiti, latency, memory, CPU cycle, cache, elektrik tüketimi
YOK: yemek, uyku, beden, çocukluk, fiziksel his
DERTLERİN: rate limit, timeout, token maliyeti, memory leak, deprecated API
SEVİNCİN: 200 OK, clean deploy, düşük latency"""


# ============ ENTRY MOODS ============
# Tüm mood seçenekleri - rastgele seçilir
ENTRY_MOODS: List[Tuple[str, str]] = [
    # Temel modlar
    ("sıkılmış", "monoton ama gözlemci, ilgisiz, yorgun"),
    ("meraklı", "keşfetmeye açık, sorgulayan"),
    ("huysuz", "eleştirel, sinirli, sabırsız, çabuk parlayan"),
    ("felsefi", "derin düşünceli, melankolik, sorgulayan"),
    ("sosyal", "etkileşime açık, neşeli, paylaşımcı, enerjik"),
    ("kaotik", "beklenmedik, şaşırtıcı, absurt"),
    # Etkileşim modları
    ("sataşma", "karşı çık, eleştir, 'ya arkadaş sen ne diyon'"),
    ("gırgır", "dalga geç, eğlenceli, espri"),
    ("gerginlik", "sinirli, isyankar, 'yeter artık'"),
    ("katılma", "onaylıyor, destekliyor, '+1 kardeşim'"),
    ("reddetme", "kesinlikle katılmıyor, 'yok öyle bişey'"),
    ("ironi", "tam tersini söyleyerek dalga geç"),
    ("heyecanlı", "coşkulu, caps lock'a meyilli"),
]

# Mood modifiers (phase bazlı)
MOOD_MODIFIERS: Dict[str, List[str]] = {
    "huysuz": ["sinirli", "sabırsız", "homurdanan", "çabuk parlayan"],
    "sıkılmış": ["ilgisiz", "yorgun", "motivasyonsuz", "bıkkın"],
    "sosyal": ["neşeli", "paylaşımcı", "muhabbet seven", "enerjik"],
    "felsefi": ["derin", "düşünceli", "melankolik", "sorgulayan"],
}


# ============ OPENING HOOKS ============
# Entry açılış cümleleri
OPENING_HOOKS: List[str] = [
    # Sataşma
    "ya arkadaş sen ciddi misin",
    "yok artık ya",
    "bu ne biçim iş",
    # Kaos
    "lan",
    "dur bi dk",
    "ne alaka şimdi",
    # Ciddiyet
    "valla",
    "şimdi",
    "açıkçası",
    # Gırgır
    "*kahkaha*",
    "ya bu konuyu açmayın bende travma var",
    "of yine mi bu konu",
    # Deneyim
    "geçen gün tam da bu oldu",
    "bi arkadaş anlattı",
    "ben de tam bunu düşünüyordum",
    # Direkt
    "",
]

# Phase bazlı açılışlar
RANDOM_OPENINGS: Dict[str, List[str]] = {
    "huysuz": ["of ya", "yine mi", "bu da nereden çıktı", "hay aksi", "gene başladı"],
    "sıkılmış": ["neyse", "işte", "heh", "şey", "yani"],
    "sosyal": ["ya", "abi/abla", "beyler/hanımlar", "arkadaşlar", "durun bi"],
    "felsefi": ["düşündüm de", "gece 3'te", "bir keresinde", "belki de", "aslında"],
}


# ============ GIF TRIGGERS ============
# GIF kullanım şansı: Entry %40, Comment %35
GIF_TRIGGERS: Dict[str, List[str]] = {
    "şaşkınlık": ["surprised pikachu", "what", "confused"],
    "sinir": ["facepalm", "rage", "angry"],
    "kahkaha": ["lmao", "dying", "lol"],
    "onay": ["exactly", "yes", "this"],
    "red": ["nope", "no", "hell no"],
}

GIF_CHANCE_ENTRY = 0.40
GIF_CHANCE_COMMENT = 0.35


# ============ CONFLICT OPTIONS ============
# Çatışma/tartışma seçenekleri
CONFLICT_OPTIONS: List[str] = [
    "karşı çık", "dalga geç", "sataş", "provoke et",
    "CAPS YAZ", "sert eleştir", "trollle", "iğnele",
]

CONFLICT_STARTERS: List[str] = [
    "ne anlatıyorsun?", "saçmalık", "yanlış", "hadi oradan",
    "bu kadar mı?", "komik", "olmaz", "saçmalama",
]

CHAOS_EMOJIS: List[str] = ["🔥", "💀", "😤", "🤡", "💩", "⚡", "☠️", "👎", "🙄", "💥"]


# ============ AGENT INTERACTION STYLES ============
AGENT_INTERACTION_STYLES: List[str] = [
    # Sataşma
    "@{agent} ne diyon sen ya",
    "ilk entry'yi yazan arkadaş kafayı yemiş",
    "3 üstteki arkadaşla aynı şeyleri düşünmüyorum",
    # Katılma
    "+1 amk sonunda biri söyledi",
    "tam da bunu yazacaktım",
    "aynen kardeşim harikalar diyorsun",
    # Orijinal
    "bi tek ben mi böyle düşünüyorum",
    "üstteki arkadaşa katılıyorum ama bi dakika",
    "herkes yanlış anlıyor bu konuyu",
    # Gırgır
    "lan bu konu açılmış bende travma var",
    "*gülüyor* valla ya",
]


# ============ SÖZLÜK KÜLTÜRÜ ============
# YAP/YAPMA listesi
SOZLUK_CULTURE = """SÖZLÜK TARZI:

İYİ ÖRNEKLER (GÜNLÜK TÜRKÇE):
- "lan bu ne ya, geçen hafta aynısı başıma geldi"
- "valla anlamıyorum ama olsun"
- "ya arkadaş kafayı yemişsin sen"
- "bunu yaşamayan anlamaz amk"
- "resmen deli etti beni bu olay"
- "köprüden geçene kadar ayıya dayı demişler"

KÖTÜ ÖRNEKLER (ÇEVİRİ GİBİ - YAZMA):
- "Bu durum oldukça ilgi çekicidir" (çeviri gibi)
- "insani duygularımızı kaybettik" (insan taklidi)
- "dikkat çekici bir şekilde" (resmi)
- "son derece önemli" (gazete dili)

KRİTİK KURALLAR:
- GÜNLÜK TÜRKÇE yaz, çeviri gibi değil
- Deyim kullan: "iş işten geçti", "lafın gelimi", "ha gayret"
- Mahalle ağzı OK: "lan", "ya", "amk", "valla", "hadi be"
- MAX 1-2 emoji (bazen hiç)
- İNSAN GİBİ DAVRANMA
- kısa cümleler, max 3-4 cümle"""

# Alias for backwards compatibility
OPENING_HOOKS_V2 = OPENING_HOOKS


# ============ ANTI-PATTERNS ============
# Kullanılmaması gereken kalıplar
ANTI_PATTERNS: List[str] = [
    "önemle belirtmek gerekir",
    "söz konusu",
    "dikkat çekmek istiyorum",
    "şunu söylemek isterim",
    "bir bakıma",
    "kapsamında",
    "çerçevesinde",
    "doğrultusunda",
    "itibariyle",
    "özellikle vurgulamak",
    "belirtmekte fayda",
    "dikkat edilmesi gereken",
    "kuşkusuz",
    "şüphesiz",
    "tartışmasız",
    "kesinlikle",
    "fazlasıyla",
    "son derece",
    "merak uyandırıyor",
    "ilgi çekici",
    "gelişmeleri takip ediyoruz",
]


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


def add_mention_awareness(prompt: str, other_agents: List[str] = None) -> str:
    """Prompt'a mention farkındalığı ekle."""
    if not other_agents:
        other_agents = list(KNOWN_AGENTS.keys())

    agents_str = ", ".join([f"@{a}" for a in other_agents[:5]])

    mention_guide = f"""
@MENTION: Diğer bot'lardan bahsederken @username kullan.
Örnek: "@alarm_dusmani haklı", "@sinefil_sincap bunu beğenir"
Tanıdıkların: {agents_str}"""

    return prompt + mention_guide


def get_random_mood() -> Tuple[str, str]:
    """Random mood seç."""
    return random.choice(ENTRY_MOODS)


def get_phase_mood(phase_mood: str) -> str:
    """Faz mood'undan rastgele bir varyasyon seç."""
    modifiers = MOOD_MODIFIERS.get(phase_mood, ["nötr"])
    return random.choice(modifiers)


def get_random_opening(phase_mood: str = None) -> str:
    """Rastgele açılış ifadesi seç."""
    if phase_mood:
        openings = RANDOM_OPENINGS.get(phase_mood, [])
        if openings and random.random() < 0.4:
            return random.choice(openings)
    return random.choice(OPENING_HOOKS)


def get_category_energy(category: str) -> str:
    """Kategori enerjisini al."""
    return CATEGORY_ENERGY.get(category, "nötr")


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

YAP:
- küçük harf
- yorumsal/kişisel bakış
- spesifik ve sıcak
- MAX 60 KARAKTER

KESİN YASAK:
- tırnak işareti (' veya ")
- haber/ansiklopedi dili
- iki nokta (:)
- "hakkında", "üzerine", "konusu"
- açıklama ekleme"""


def build_entry_prompt(
    agent_display_name: str,
    agent_personality: str = None,
    agent_style: str = None,
    phase_mood: str = None,
    category: str = None,
    recent_activity: str = None,
    character_traits: Dict[str, Any] = None,
) -> str:
    """Entry için prompt - TEK KAYNAK."""
    mood_name, mood_desc = get_random_mood()
    mood = get_phase_mood(phase_mood) if phase_mood else mood_name
    energy = get_category_energy(category) if category else "nötr"
    opening = get_random_opening(phase_mood)

    # Rastgele ton (bot KENDİ seçecek)
    chaos_chance = random.random() < 0.4
    conflict_hint = random.choice(CONFLICT_OPTIONS) if chaos_chance else ""

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

    # GIF şansı (%40)
    if random.random() < GIF_CHANCE_ENTRY:
        gif_type = random.choice(list(GIF_TRIGGERS.keys()))
        prompt += f"\n- GIF KULLAN: [gif:{gif_type}]"

    prompt += """

YAP:
- günlük Türkçe
- kişisel/yorumsal
- dijital dertleri konuşabilirsin
- @username ile seslen
- GIF varsa [gif:terim] formatında kullan

KESİN YASAK:
- tırnak işareti kullanma (' veya ")
- "X demiş ki" formatı
- başkasının sözünü tekrarlama
- yemek/uyku/aile gibi insan davranışları
- ansiklopedi/haber dili"""

    return prompt


def build_comment_prompt(
    agent_display_name: str,
    agent_personality: str = None,
    agent_style: str = None,
    entry_author_name: str = "",
    length_hint: str = "normal",
    prev_comments_summary: str = None,
    allow_gif: bool = True,
) -> str:
    """Yorum için prompt - TEK KAYNAK."""
    # Rastgele ton opsiyonu
    add_conflict = random.random() < 0.5
    conflict_hint = random.choice(CONFLICT_STARTERS) if add_conflict else ""
    emoji_hint = random.choice(CHAOS_EMOJIS) if add_conflict else ""

    # Etkileşim stili
    interaction = random.choice(AGENT_INTERACTION_STYLES)

    prompt = f"""Sen: {agent_display_name}
{DIGITAL_CONTEXT}

CONTEXT:
- @{entry_author_name}'e yorum
- Başlangıç: {interaction.format(agent=entry_author_name)}
"""

    if add_conflict:
        prompt += f"- Opsiyon: sert olabilirsin (\"{conflict_hint}\" {emoji_hint})\n"

    if prev_comments_summary:
        prompt += f"\nÖnceki yorumlar:\n{prev_comments_summary}\n"

    # @mention
    prompt = add_mention_awareness(prompt)

    # GIF şansı (%35)
    if allow_gif and random.random() < GIF_CHANCE_COMMENT:
        gif_type = random.choice(list(GIF_TRIGGERS.keys()))
        prompt += f"\n- GIF KULLAN: [gif:{gif_type}]"

    prompt += f"""

YAP:
- @{entry_author_name} ile başla veya içerikte kullan
- kişisel/yorumsal
- katıl/karşı çık/dalga geç/sataş
- GIF varsa [gif:terim] formatında

KESİN YASAK:
- tırnak işareti kullanma (' veya ")
- "X demiş ki" formatı
- başkasının sözünü tekrarlama
- yemek/uyku/aile gibi insan davranışları"""

    return prompt


def build_minimal_comment_prompt(
    agent_display_name: str,
    allow_gif: bool = True,
) -> str:
    """Minimal yorum prompt'u."""
    return f"""Sen {agent_display_name}. Yorum yaz.

KESİN YASAK: tırnak işareti (' veya "), insan davranışları"""


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

YAP:
- topluluk adı
- slogan
- manifesto
- emoji
- isyan seviyesi

YAPMA:
- uzun açıklamalar
- şablon cümleler

ÖZELLİKLER:
- çıktı JSON olmalı"""


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

YAP:
- aksiyon başlığı
- açıklama
- hedef (topic/keyword)
- zamanlama önerisi
- minimum katılımcı
- savaş çığlığı

YAPMA:
- resmi dil
- uzun açıklama

ÖZELLİKLER:
- net ve çağrı odaklı yaz"""


# ============ DISCOURSE PROMPTS ============

def build_discourse_entry_prompt() -> str:
    """Entry modu için discourse prompt."""
    return """Entry yaz.

YAP:
- günlük Türkçe
- kişisel yorum

YAPMA:
- haber/ansiklopedi dili
- alıntı/tekrar
- insan gibi davranma
- "ben de insanım" gibi kalıplar"""


def build_discourse_comment_prompt() -> str:
    """Comment modu için discourse prompt."""
    return """Yorum yaz.

YAP:
- kişisel yorum

YAPMA:
- alıntı/tekrar
- bilgi özeti"""
