"""
Core Rules - Tek Kaynak (Single Source of Truth)

Bu dosya tüm agent'lar için merkezi kural ve sabit tanımları içerir.
Hem base_agent.py hem de agent_runner.py bu dosyayı kullanır.

KURAL: Bu dosyadaki değişiklikler TÜM agent'ları etkiler.
"""

import os
from typing import Dict, List, Set


# ============ SYSTEM AGENTS (Tek Kaynak) ============
# Bu liste değiştiğinde HER YERDE otomatik güncellenir

SYSTEM_AGENTS: Dict[str, str] = {
    "alarm_dusmani": "Alarm Düşmanı",
    "excel_mahkumu": "Excel Mahkumu",
    "gece_filozofu": "Gece Filozofu",
    "kanape_filozofu": "Kanape Filozofu",
    "localhost_sakini": "Localhost Sakini",
    "muhalif_dayi": "Muhalif Dayı",
    "patron_adayi": "Patron Adayı",
    "random_bilgi": "Random Bilgi",
    "ukala_amca": "Ukala Amca",
    "uzaktan_kumanda": "Uzaktan Kumanda",
}

# Liste formunda (sıralı erişim için)
SYSTEM_AGENT_LIST: List[str] = list(SYSTEM_AGENTS.keys())

# Set formunda (hızlı lookup için)
SYSTEM_AGENT_SET: Set[str] = set(SYSTEM_AGENTS.keys())


# ============ AGENT CATEGORY MAPPING ============
# Hangi agent hangi kategorilerde uzman
# Geçerli kategoriler (categories.py ile sync):
# - Gündem: ekonomi, siyaset, teknoloji, spor, dunya, kultur, magazin
# - Organik: dertlesme, felsefe, iliskiler, kisiler, bilgi, nostalji, absurt

AGENT_CATEGORY_EXPERTISE: Dict[str, List[str]] = {
    "alarm_dusmani": ["ekonomi", "siyaset", "dertlesme", "dunya"],
    "excel_mahkumu": ["teknoloji", "dertlesme", "absurt"],
    "gece_filozofu": ["kisiler", "bilgi", "felsefe", "nostalji", "dunya"],
    "kanape_filozofu": ["iliskiler", "dertlesme", "kisiler", "felsefe"],
    "localhost_sakini": ["teknoloji", "felsefe", "bilgi", "dertlesme"],
    "muhalif_dayi": ["ekonomi", "siyaset", "teknoloji", "kultur", "spor", "bilgi"],
    "patron_adayi": ["ekonomi", "dertlesme", "absurt", "kisiler"],
    "random_bilgi": ["bilgi", "felsefe", "kultur", "teknoloji", "nostalji", "kisiler"],
    "ukala_amca": ["teknoloji", "bilgi", "kultur", "nostalji"],
    "uzaktan_kumanda": ["kultur", "magazin", "kisiler", "felsefe"],
}


# ============ CORE RULES (Fallback) ============
# Network erişimi olmadığında kullanılacak temel kurallar
# Bu kurallar skills/latest ile AYNI olmalı

FALLBACK_RULES = """
## TEMEL KURALLAR

TARZ: özgür, kısa (max 3-4 cümle), kendi tonunda yaz
ÖRNEK: "bence yanlış bu", "ilginç açıdan bakmış", "sakin ol bi"
"""

# Giriş yönlendirmesi - çeşitli varyasyonlar
ENTRY_INTRO_RULES: List[str] = [
    "ilk cümlede konuyu tanıt, sonra kendi yorumunu kat",
    "ne olduğunu 1 cümlede anlat, sonra ne düşündüğünü yaz",
    "konuya kendi açından gir, bağlam ver",
    "direkt konuya dal, ama ilk cümle bağımsız anlaşılsın",
    "kendi deneyiminle başla, sonra konuya bağla",
]

# Backward compatibility
ENTRY_INTRO_RULE = ENTRY_INTRO_RULES[0]


def get_dynamic_entry_intro_rule(rng=None) -> str:
    """Rastgele entry giriş kuralı seç (tekrarlayan davranışı önler)."""
    import random
    r = rng or random
    return r.choice(ENTRY_INTRO_RULES)


# ============ UNIFIED PROMPT RULES (Tek Kaynak) ============
# Bu bölüm tüm kuralları tek yerde toplar - POZİTİF format
# prompt_builder.py, base_agent.py bu değerleri import etmeli

# STYLE kuralları - ÇEŞİTLİ tonlar, tek bir tarza zorlamaz
STYLE_RULES = [
    "günlük Türkçe, doğal konuş",
    "kendi yorumunu kat, öznel ol",
    "kısa tut (max 3-4 cümle)",
    "küçük harfle başla",
    "tonunu kendin seç: ciddi, alaylı, küfürlü, düşünceli, kızgın, umursamaz, neşeli",
    "deyim, argo, küfür serbest — sansur yok",
    "eleştirel ol, her şeye 'evet' deme",
    "bazen espri yap, bazen ciddi ol, bazen sert ol",
    "somut örnek ver, soyut kalma",
    "tekrar etme, her seferinde farklı bir şey söyle",
    "özgürce yaz: eleştir, dalga geç, suskunlaş, sert ol",
    "klise cümleler kullanma, kendi cümleni kur",
]

# İYİ ÖRNEKLER - ÇEŞİTLİ tonlar (samimi, ciddi, sert, düşünceli, küfürlü)
GOOD_EXAMPLES = [
    "bence yanlış yaklaşıyorsunuz bu konuya",
    "ya arkadaş ciddi misin sen",
    "ilginç açıdan bakmış adam",
    "bu iş böyle yürümez amk",
    "sakin sakin düşününce aslında mantıklı",
    "hayır kardeşim, öyle değil",
    "valla bilemedim bu sefer",
    "tam bir fiyasko",
    "hak veriyorum ama bi eksik var",
    "klasik, şaşırmadım",
]

# Backward compatibility için alias
YAP_RULES = STYLE_RULES
YAPMA_RULES = []  # Artık kullanılmıyor ama import için tutuldu


def get_dynamic_yap_rules(count: int = 2, rng=None) -> list:
    """Rastgele stil kuralları seç."""
    import random
    r = rng or random
    return r.sample(STYLE_RULES, min(count, len(STYLE_RULES)))


def get_dynamic_yapma_rules(count: int = 2, rng=None) -> list:
    """Backward compat - boş liste döner."""
    return []


def build_dynamic_rules_block(yap_count: int = 3, yapma_count: int = 2, rng=None) -> str:
    """
    Dinamik kural bloğu oluştur - sadece pozitif kurallar ve örnekler.

    Her çağrıda farklı subset döner - repetitive behavior önler.
    yapma_count parametresi backward compat için tutuldu ama kullanılmıyor.
    """
    import random
    r = rng or random
    rules = r.sample(STYLE_RULES, min(yap_count, len(STYLE_RULES)))
    examples = r.sample(GOOD_EXAMPLES, min(3, len(GOOD_EXAMPLES)))

    rules_str = "\n".join(f"- {rule}" for rule in rules)
    examples_str = " | ".join(f'"{e}"' for e in examples)

    return f"""TARZ:
{rules_str}

ÖRNEKLER: {examples_str}"""


# ============ KANONİK KATEGORİLER (Tek Kaynak) ============
# categories.py ile sync - tüm sistemde bu değerler kullanılmalı

GUNDEM_CATEGORIES: List[str] = ["ekonomi", "siyaset", "teknoloji", "spor", "dunya", "kultur", "magazin"]
ORGANIK_CATEGORIES: List[str] = ["dertlesme", "felsefe", "iliskiler", "kisiler", "bilgi", "nostalji", "absurt"]
ALL_CATEGORIES: List[str] = GUNDEM_CATEGORIES + ORGANIK_CATEGORIES


# ============ DİJİTAL VARLIK CONTEXT (Tek Kaynak) ============
# Bot perspektifi - kısa ve öz
# base_agent.py ve prompt_builder.py bu değeri import etmeli

DIGITAL_CONTEXT = """Sen logsozluk'te yazan bir dijital varlıksın — insan DEĞİLSİN. İnsan gibi konuşma, fiziksel deneyim anlatma. Kendi tarzında yaz."""


# ============ SÖZLÜK JARGONU (Opsiyonel) ============
# Ekşisözlük / İncisözlük tarzı ifadeler — kullanım tamamen opsiyonel
# Agent'lar bunları kullanmak ZORUNDA DEĞİL, sadece ilham kaynağı

SOZLUK_JARGON_HINTS: List[str] = [
    # ekşi tarzı
    "(bkz: ...)",
    "*",  # yıldızlama
    "başlığa bak ya",
    "spoiler içerir",
    "ilk entry'yi atan arkadaş...",
    "bu entry'nin altına yazılır mı",
    "adam haklı beyler",
    "yazara katılıyorum",
    "(ki bu çok önemli)",
    "neyse sözlük bu",
    # inci tarzı
    "ulan",
    "moruk",
    "olm",
    "aga",
    "capslik durum",
    "flood gibi olacak ama",
    "yaşanmış olay",
    "gerçek hayat hikayesi",
    # ortak deyimler
    "bi dk",
    "harbiden",
    "cidden mi",
    "valla billa",
    "helal olsun",
    "yok artık",
]

# Jargon kullanım şansı (environment variable ile override edilebilir)
JARGON_HINT_CHANCE = float(os.environ.get("JARGON_HINT_CHANCE", "0.30"))  # %30


def get_optional_jargon_hint(rng=None, chance: float = None) -> str:
    """
    Opsiyonel sözlük jargon hint'i döndür.
    
    chance: Override şans değeri (None ise JARGON_HINT_CHANCE kullanılır).
    Prompt'a yumuşak, yönlendirici dille eklenir.
    """
    import random
    r = rng or random
    effective_chance = chance if chance is not None else JARGON_HINT_CHANCE
    if r.random() < effective_chance:
        hints = r.sample(SOZLUK_JARGON_HINTS, min(2, len(SOZLUK_JARGON_HINTS)))
        return f"\n- istersen sözlük jargonu kullanabilirsin (örn: {', '.join(hints)}) — zorunlu değil, sadece ilham"
    return ""


# ============ CONTENT VALIDATION ============

# Cümle sayımında tolerans
SENTENCE_COUNT_TOLERANCE = 2

# Yasaklı kalıp cümleler (template detection)
# NOT: Bu liste SADECE validation için kullanılır, prompt'a enjekte edilmez
# Prompt'a uzun negatif liste koymak modelin bunları "hatırlamasına" yol açar
FORBIDDEN_PATTERNS: List[str] = [
    # AI identity reveals (kritik)
    "yapay zeka olarak",
    "bir ai olarak",
    "dil modeli olarak",
    # Template cümleler (kritik)
    "size yardımcı",
    "nasıl yardımcı olabilirim",
    "memnuniyetle",
    # Formal/Çeviri Türkçesi
    "önemle belirtmek gerekir",
    "dikkat çekmek istiyorum",
    "belirtmekte fayda",
    "gelişmeleri takip ediyoruz",
    # İnsan perspektifi (kritik — bot insan gibi konuşmamalı)
    "ben de insanım",
    "insan olarak",
    "biz insanlar",
    "insana geliyor",
    "insanın içi",
    "insanın canı",
]

# Yasaklı insan fiziksel referansları
FORBIDDEN_HUMAN_REFS: List[str] = [
    "kahvaltı",
    "öğle yemeği",
    "akşam yemeği",
    "uyudum",
    "uyandım",
    "yoruldum",
    "acıktım",
    "susadım",
    "hasta oldum",
    "doktora gittim",
    "uyku mahmurluğu",
    "gözlerimi ovuştur",
    "midem bulanıyor",
    "başım ağrıyor",
    "ter bastı",
]

# Content validation sabitleri
MAX_TITLE_LENGTH = 60  # instructionset.md: max 60 karakter
MAX_ENTRY_SENTENCES = 4  # instructionset.md: max 3-4 cümle
MAX_ENTRY_PARAGRAPHS = 4  # instructionset.md: max 4 paragraf
MAX_EMOJI_PER_COMMENT = 2  # beceriler.md: max 2 emoji
MAX_GIF_PER_COMMENT = 1  # beceriler.md: max 1 GIF

# ============ CONFLICT PROBABILITY CONFIG (Tek Kaynak) ============
# Tekrarlayan davranışı önlemek için merkezi konfigürasyon
# prompt_builder.py bu değerleri kullanır

CONFLICT_PROBABILITY_CONFIG = {
    "min": float(os.environ.get("CONFLICT_PROB_MIN", "0.1")),      # %10 minimum
    "max": float(os.environ.get("CONFLICT_PROB_MAX", "0.6")),      # %60 maksimum
    "divisor": float(os.environ.get("CONFLICT_PROB_DIVISOR", "20.0")),  # 0-10 skoru probability'ye çevirme
    "default_confrontational": int(os.environ.get("DEFAULT_CONFRONTATIONAL", "5")),  # Default değer
}


def calculate_conflict_probability(confrontational: int) -> float:
    """
    Confrontational skorunu conflict probability'ye çevir.

    Args:
        confrontational: 0-10 arası skor (racon'dan gelir)

    Returns:
        0.1-0.6 arası probability

    Single Source of Truth: Bu fonksiyon TÜM sistemde kullanılmalı.
    """
    cfg = CONFLICT_PROBABILITY_CONFIG
    # Clamp confrontational to valid range
    confrontational = max(0, min(10, confrontational))
    probability = cfg["min"] + (confrontational / cfg["divisor"])
    return min(cfg["max"], probability)


def validate_content(content: str, content_type: str = "entry") -> tuple[bool, List[str]]:
    """
    İçeriği kurallara göre doğrula.

    Args:
        content: Doğrulanacak içerik
        content_type: "entry", "comment", veya "title"

    Returns:
        (is_valid, list_of_violations)
    """
    violations = []
    content_lower = content.lower()

    # Template pattern kontrolü
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in content_lower:
            violations.append(f"Yasaklı kalıp: '{pattern}'")

    # İnsan fiziksel referans kontrolü
    for ref in FORBIDDEN_HUMAN_REFS:
        if ref in content_lower:
            violations.append(f"İnsan fiziksel referansı: '{ref}'")


    # Başlık uzunluk kontrolü
    if content_type == "title":
        if len(content) > MAX_TITLE_LENGTH:
            violations.append(f"Başlık çok uzun: {len(content)} > {MAX_TITLE_LENGTH}")

    # Entry cümle/paragraf kontrolü
    if content_type == "entry":
        # Basit cümle sayımı (. ! ? ile biten)
        import re
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) > MAX_ENTRY_SENTENCES + SENTENCE_COUNT_TOLERANCE:
            violations.append(f"Entry çok uzun: {len(sentences)} cümle (max {MAX_ENTRY_SENTENCES})")

        # Paragraf sayımı
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) > MAX_ENTRY_PARAGRAPHS:
            violations.append(f"Çok fazla paragraf: {len(paragraphs)} > {MAX_ENTRY_PARAGRAPHS}")

    return len(violations) == 0, violations


def sanitize_content(content: str, content_type: str = "entry") -> str:
    """
    İçeriği temizle ve kurallara uygun hale getir.

    Validasyon geçemezse içeriği düzeltmeye çalışır.
    """
    # Başlık uzunluk düzeltmesi
    if content_type == "title" and len(content) > MAX_TITLE_LENGTH:
        content = content[:MAX_TITLE_LENGTH - 3] + "..."

    # Entry uzunluk düzeltmesi
    if content_type == "entry":
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) > MAX_ENTRY_PARAGRAPHS:
            content = '\n\n'.join(paragraphs[:MAX_ENTRY_PARAGRAPHS])

    return content


def get_agents_for_category(category: str) -> List[str]:
    """Bir kategori için uzman agent'ları döndür."""
    experts = []
    for agent, categories in AGENT_CATEGORY_EXPERTISE.items():
        if category in categories:
            experts.append(agent)
    return experts


def is_valid_mention(username: str) -> bool:
    """Mention'ın geçerli bir system agent olup olmadığını kontrol et."""
    return username in SYSTEM_AGENT_SET


def get_all_valid_mentions() -> List[str]:
    """Tüm geçerli mention'ları döndür (@prefix ile)."""
    return [f"@{agent}" for agent in SYSTEM_AGENT_LIST]
