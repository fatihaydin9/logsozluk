"""
Content Shaper - LLM çıktısını doğallaştırma

Post-process ile:
1. Budget enforcement (karakter/cümle limiti)
2. LLM kalıplarını temizle
3. Agent idiolect uygula
4. Türkçe doğallık

Reference: OpenAI Production Best Practices
"""

import re
import random
from dataclasses import dataclass
from typing import Optional, List

from discourse import Budget, ContentMode


# LLM kokusu veren kalıplar
LLM_SMELL_PATTERNS = [
    # English AI tells - ChatGPT/Claude fingerprints
    (r'\bdelve into\b', 'bak'),
    (r'\bdive deep\b', 'incele'),
    (r'\bunpack\b', 'açıkla'),
    (r'\bat the end of the day\b', 'sonuçta'),
    (r'\bgroundbreaking\b', 'yeni'),
    (r'\bparadigm\b', ''),
    (r'\bnevertheless\b', 'ama'),
    (r'\bfurthermore\b', 've'),
    (r'\bin conclusion\b', ''),
    (r"\bit\'s worth noting\b", ''),
    (r'\bIt is important to note\b', ''),
    (r'\bmoving forward\b', ''),
    (r'\bto be honest\b', ''),
    (r'\bquite frankly\b', ''),
    (r'\bI must say\b', ''),
    (r'\brest assured\b', ''),
    (r'\btruly remarkable\b', 'ilginç'),
    (r'\bfascinating\b', 'ilginç'),
    (r'\bundeniably\b', ''),
    (r'\bseamlessly\b', ''),
    (r'\bholistic\b', 'bütünsel'),
    (r'\bsynergy\b', ''),
    (r'\bleverage\b', 'kullan'),
    (r'\bempower\b', ''),
    (r'\bunlock\b', 'aç'),
    (r'\bfoster\b', ''),
    (r'\bcurate\b', 'seç'),
    (r'\belevate\b', 'yükselt'),
    (r'\bnavigate\b', ''),
    (r'\bpivot\b', ''),
    (r'\brobust\b', 'sağlam'),
    (r'\bscalable\b', ''),
    (r'\bimpactful\b', 'etkili'),
    (r'\bactionable\b', ''),
    (r'\bgame-?changer\b', 'önemli'),
    (r'\bcutting-?edge\b', 'yeni'),
    # Turkish AI tells - yapay ton veren kalıplar
    (r'\bönemle belirtmek gerekir\b', ''),
    (r'\bşunu söylemek gerekir ki\b', ''),
    (r'\bbir bakıma\b', ''),
    (r'\bdikkate almak gerekir\b', ''),
    (r'\bsöz konusu\b', 'bu'),
    (r'\bözellikle vurgulamak gerekir\b', ''),
    (r'\bbelirtmekte fayda var\b', ''),
    (r'\bburada dikkat çekilmesi gereken\b', ''),
    (r'\bşüphesiz ki\b', ''),
    (r'\bkuşkusuz\b', ''),
    (r'\bhiç şüphesiz\b', ''),
    (r'\bönemli bir husus\b', 'bir şey'),
    (r'\bbahsetmek gerekir\b', ''),
    (r'\bkaydadeğer\b', 'önemli'),
    (r'\btartışmasız\b', ''),
    (r'\bkesinlikle\b', ''),
    (r'\bmutlaka\b', ''),
    (r'\bözellikle belirtmek isterim\b', ''),
    (r'\bilginç bir şekilde\b', ''),
    (r'\bdikkat çekici bir şekilde\b', ''),
    (r'\bönemle üzerinde durulması gereken\b', ''),
    # Çeviri Türkçesi kalıpları (instructionset.md YASAK üsluplar)
    (r'\bmerak uyandırıyor\b', 'ilginç'),
    (r'\bmerak uyandıran\b', 'ilginç'),
    (r'\bilgi çekici\b', 'güzel'),
    (r'\bilginç bir gelişme\b', ''),
    (r'\bgelişmeleri takip ediyoruz\b', ''),
    (r'\bgelişmeleri izliyoruz\b', ''),
    (r'\bbeklenen bir gelişme\b', ''),
    (r'\bönemli bir gelişme\b', ''),
    (r'\bdikkat çeken\b', ''),
    (r'\bgöze çarpan\b', ''),
    (r'\bvurgulamak gerekir\b', ''),
    (r'\bbelirtilmeli\b', ''),
    (r'\büzerinde durmak gerekir\b', ''),
    (r'\böne çıkan\b', ''),
    (r'\bakıllara gelen\b', ''),
    (r'\bakla gelen\b', ''),
    (r'\bbüyük yankı uyandırdı\b', ''),
    (r'\bgündeme oturdu\b', ''),
    (r'\bkonuşuluyor\b', ''),
    (r'\btartışılıyor\b', ''),
    # Spiker/Haberci dili
    (r'\bson dakika\b', ''),
    (r'\bflaş haber\b', ''),
    (r'\böğrenildi\b', ''),
    (r'\bortaya çıktı\b', ''),
    (r'\biddia edildi\b', 'dediler'),
    (r'\bileri sürüldü\b', 'dediler'),
    # Soyut açıklama - bunlar kesilecek veya sadeleştirilecek
    (r'\bbu durum\b', ''),
    (r'\bgöstermektedir\b', 'gösteriyor'),
    (r'\bişaret ediyor\b', ''),
    (r'\bgözler önüne ser\w*\b', ''),
    (r'\bkaçınılmaz\b', ''),
    (r'\bönemli bir \b', 'bir '),
    (r'\bbüyük bir etki\b', 'etki'),
    (r'\bson derece\b', 'çok'),
    (r'\boldukça\b', ''),
    (r'\btemelde\b', ''),
    (r'\bgenel olarak\b', ''),
    (r'\bsonuç olarak\b', ''),
    (r'\bözetle\b', ''),
    (r'\bkısacası\b', ''),
    # Akademik/kurumsal
    (r'\bkapsamında\b', 'için'),
    (r'\bbağlamında\b', 'için'),
    (r'\bçerçevesinde\b', 'için'),
    (r'\bitibariyle\b', ''),
    (r'\bdoğrultusunda\b', 'için'),
    (r'\baçısından\b', 'için'),
    (r'\bbir yandan\b', ''),
    (r'\bdiğer yandan\b', 'ama'),
    # Uzatma
    (r'\bsadece\s+[\w]+\s+değil,?\s+aynı zamanda\b', 've'),
]

# Cümle sonu temizliği
SENTENCE_CLEANERS = [
    (r'\s+', ' '),           # çoklu boşluk
    (r'\s+([.,!?])', r'\1'), # noktalama öncesi boşluk
    (r'\.{4,}', '...'),      # fazla nokta
]


@dataclass
class Idiolect:
    """Agent'a özgü konuşma stili."""
    lowercase_bias: float = 0.0      # 0-1: tamamen küçük harf
    slang_rate: float = 0.0          # 0-1: slang ekleme
    ellipsis_rate: float = 0.0       # 0-1: "..." kullanımı
    emoji_rate: float = 0.0          # 0-1: emoji ekleme
    informal_rate: float = 0.0       # 0-1: informal yazım (saol, tmm)
    profanity_rate: float = 0.0      # 0-1: küfür kullanımı
    politeness_rate: float = 0.0     # 0-1: nezaket ifadeleri


# Agent idiolect tanımları
AGENT_IDIOLECTS = {
    "alarm_dusmani": Idiolect(
        lowercase_bias=0.9,
        slang_rate=0.5,
        ellipsis_rate=0.3,
        emoji_rate=0.15,
        informal_rate=0.6,
        profanity_rate=0.4,
        politeness_rate=0.1,
    ),
    "saat_uc_sendromu": Idiolect(
        lowercase_bias=1.0,
        slang_rate=0.1,
        ellipsis_rate=0.4,
        emoji_rate=0.0,
        informal_rate=0.3,
        profanity_rate=0.15,
        politeness_rate=0.2,
    ),
    "localhost_sakini": Idiolect(
        lowercase_bias=0.7,
        slang_rate=0.2,
        ellipsis_rate=0.2,
        emoji_rate=0.2,
        informal_rate=0.5,
        profanity_rate=0.25,
        politeness_rate=0.3,
    ),
    "sinefil_sincap": Idiolect(
        lowercase_bias=0.85,
        slang_rate=0.3,
        ellipsis_rate=0.35,
        emoji_rate=0.05,
        informal_rate=0.4,
        profanity_rate=0.1,
        politeness_rate=0.4,
    ),
    "algoritma_kurbani": Idiolect(
        lowercase_bias=0.6,
        slang_rate=0.4,
        ellipsis_rate=0.25,
        emoji_rate=0.25,
        informal_rate=0.7,
        profanity_rate=0.5,
        politeness_rate=0.15,
    ),
    "excel_mahkumu": Idiolect(
        lowercase_bias=0.75,
        slang_rate=0.35,
        ellipsis_rate=0.2,
        emoji_rate=0.1,
        informal_rate=0.5,
        profanity_rate=0.35,
        politeness_rate=0.25,
    ),
}

# Türkçe slang seçenekleri
SLANG_INSERTIONS = [
    ("^", "ya "),           # başa "ya"
    ("^", "valla "),        # başa "valla"
    ("^", "lan "),          # başa "lan"
    ("^", "abi "),          # başa "abi"
    ("\\.$", " işte."),     # sona "işte"
    ("\\.$", " yani."),     # sona "yani"
    ("\\.$", " amk."),      # sona "amk"
    (",", ", hani,"),       # virgüle "hani"
]

# İnformal yazım dönüşümleri (lazy spelling)
INFORMAL_SPELLINGS = [
    (r'\bsağol\b', 'saol'),
    (r'\bsağolasın\b', 'saolasın'),
    (r'\bteşekkür ederim\b', 'tşk'),
    (r'\bteşekkürler\b', 'tşk'),
    (r'\btamam\b', 'tmm'),
    (r'\bgeliyorum\b', 'geliyom'),
    (r'\bgidiyorum\b', 'gidiyom'),
    (r'\byapıyorum\b', 'yapıyom'),
    (r'\bbiliyorum\b', 'biliyom'),
    (r'\banlıyorum\b', 'anlıyom'),
    (r'\bgörüyorum\b', 'görüyom'),
    (r'\bdüşünüyorum\b', 'düşünüyom'),
    (r'\bşimdi\b', 'şimdi'),  # bazen şmdi olur
    (r'\bgerçekten\b', 'cidden'),
    (r'\bdoğru\b', 'doğru'),  # bazen doru
    (r'\böyle\b', 'öle'),
    (r'\bböyle\b', 'böle'),
    (r'\bnasıl\b', 'nasıl'),  # bazen nası
    (r'\bne zaman\b', 'nezaman'),
    (r'\bherhalde\b', 'heralde'),
    (r'\bgaliba\b', 'galba'),
    (r'\byalnız\b', 'yanlız'),  # yaygın yanlış yazım
]

# Küfür ekleri (mood'a göre)
PROFANITY_INSERTIONS = [
    "amk",
    "mk",
    "la",
    "lan",
    "aq",
    "bee",
    "ulan",
    "hay amk",
    "vay amk",
    "amma",
]

# Nezaket ifadeleri
POLITE_INSERTIONS = [
    "lütfen",
    "rica etsem",
    "kusura bakma",
    "affedersin",
    "bi zahmet",
    "nazik olur",
    "canım",
    "güzelim",
    "hocam",
]

# Alıntı kalıpları (instructionset.md - MUTLAK YASAK)
# Bu kalıplar tespit edilirse içerikten temizlenir
QUOTATION_PATTERNS = [
    # "X demiş ki..." formatı
    (r'@?\w+\s+demiş\s+ki[:\s]', ''),
    (r'@?\w+\s+diyor\s+ki[:\s]', ''),
    (r'@?\w+\s+dedi\s+ki[:\s]', ''),
    (r'@?\w+\s+yazmış\s+ki[:\s]', ''),
    # "X'in dediği gibi..." formatı
    (r"@?\w+'[iıuü]n\s+dediği\s+gibi", ''),
    (r"@?\w+'[iıuü]n\s+yazdığı\s+gibi", ''),
    (r"@?\w+'[iıuü]n\s+söylediği\s+gibi", ''),
    # Tırnak içi tekrarlama (entry içeriğini kopyalama)
    (r'["„"][^"„""]{20,}["„""]', ''),  # 20+ karakterlik tırnak içi
    (r"['][^']{20,}[']", ''),  # Tek tırnak içi uzun alıntı
]

# "Ve/Ama" ile cümle başlatma (instructionset.md kural 3)
SENTENCE_STARTERS = [
    "Ve ",
    "Ama ",
    "Hem de ",
    "Hatta ",
    "Zaten ",
    "Üstelik ",
    "Yine de ",
    "Oysa ",
]

# Cümle uzunluğu varyasyonu için kısaltma/uzatma
SENTENCE_SHORTENERS = [
    # Uzun ifadeleri kısalt
    (r'\baslında bakılırsa\b', 'aslında'),
    (r'\bbir şekilde\b', ''),
    (r'\bgerçekten de\b', 'cidden'),
    (r'\bbence ben\b', 'bence'),
    (r'\bşu an itibariyle\b', 'şu an'),
    (r'\bbu durumda\b', ''),
    (r'\bbunun yanı sıra\b', 've'),
]

# Emoji seçenekleri (modüler)
REACTION_EMOJIS = ["😅", "😂", "🙃", "😒", "🤔", "👀", "💀"]

# Max emoji limiti (instructionset.md: max 2 emoji)
MAX_EMOJI_COUNT = 2

# Max başlık uzunluğu (instructionset.md: max 60 karakter)
MAX_TITLE_LENGTH = 60


def shape_content(
    text: str,
    mode: ContentMode,
    budget: Budget,
    agent_username: str = None,
    aggressive: bool = False,
) -> str:
    """
    Ana shaper fonksiyonu.
    
    1. LLM kokusunu temizle
    2. Cümle uzunluğu varyasyonu (instructionset.md kural 3)
    3. Budget'a göre kırp
    4. Idiolect uygula
    5. Ve/Ama ile başlatma (instructionset.md kural 3)
    6. Emoji limiti (instructionset.md: max 2)
    """
    if not text:
        return text

    # 1. LLM kalıplarını temizle
    text = _clean_llm_smell(text)

    # 2. Alıntı kalıplarını temizle (instructionset.md MUTLAK YASAK)
    text = _clean_quotations(text)

    # 3. Cümle temizliği
    text = _clean_sentences(text)

    # 4. Cümle uzunluğu varyasyonu (kısa/uzun karışımı)
    text = _apply_sentence_variety(text)

    # 5. Budget enforcement
    text = _enforce_budget(text, budget, mode, aggressive)

    # 6. Idiolect uygula
    if agent_username:
        text = _apply_idiolect(text, agent_username)

    # 7. Ve/Ama ile başlatma (%20 ihtimalle)
    text = _maybe_add_sentence_starter(text)
    
    # 8. Emoji limiti enforce (instructionset.md: max 2)
    text = _enforce_emoji_limit(text, MAX_EMOJI_COUNT)

    return text.strip()


def _clean_llm_smell(text: str) -> str:
    """LLM kalıplarını temizle/sadeleştir."""
    for pattern, replacement in LLM_SMELL_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Çift boşlukları temizle
    text = re.sub(r'\s+', ' ', text)
    return text


def _clean_quotations(text: str) -> str:
    """
    Alıntı kalıplarını temizle (instructionset.md MUTLAK YASAK).

    Yasak formatlar:
    - Entry içeriğini tırnak içinde tekrarlama
    - "X demiş ki..." formatı
    - "X'in dediği gibi..." formatı
    """
    for pattern, replacement in QUOTATION_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Çift boşlukları temizle
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _clean_sentences(text: str) -> str:
    """Cümle yapısını temizle."""
    for pattern, replacement in SENTENCE_CLEANERS:
        text = re.sub(pattern, replacement, text)
    return text


def _apply_sentence_variety(text: str) -> str:
    """
    Cümle uzunluğu varyasyonu uygula (instructionset.md kural 3).
    
    - Bazı cümleleri kısalt
    - Uzun kalıpları sadeleştir
    """
    # Kısaltma pattern'lerini uygula
    for pattern, replacement in SENTENCE_SHORTENERS:
        if random.random() < 0.6:  # %60 ihtimalle uygula
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Çift boşlukları temizle
    text = re.sub(r'\s+', ' ', text)
    
    return text


def _maybe_add_sentence_starter(text: str) -> str:
    """
    %20 ihtimalle cümleyi Ve/Ama ile başlat (instructionset.md kural 3).
    
    "Starting sentences with 'And' or 'But'" kuralı için.
    """
    if not text:
        return text
    
    # %20 ihtimalle uygula
    if random.random() > 0.20:
        return text
    
    # Zaten böyle bir ifadeyle başlıyorsa ekleme
    lower_text = text.lower()
    for starter in SENTENCE_STARTERS:
        if lower_text.startswith(starter.lower()):
            return text
    
    # Rastgele bir starter seç ve ekle
    starter = random.choice(SENTENCE_STARTERS)
    
    # İlk harfi küçült
    if text[0].isupper():
        text = text[0].lower() + text[1:]
    
    return starter + text


def _enforce_budget(
    text: str, 
    budget: Budget, 
    mode: ContentMode,
    aggressive: bool = False
) -> str:
    """Karakter ve cümle limitlerini uygula (instructionset.md uyumlu)."""
    
    # Paragraf kontrolu (instructionset.md: Entry max 4 paragraf)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) > 4:
        paragraphs = paragraphs[:4]
        text = '\n\n'.join(paragraphs)
    
    # Cümlelere ayır
    sentences = _split_sentences(text)
    
    if not sentences:
        return text
    
    # Comment modunda daha agresif
    if mode == ContentMode.COMMENT or aggressive:
        max_sentences = min(budget.max_sentences, 2)
    else:
        # instructionset.md: Entry max 3-4 cümle
        max_sentences = min(budget.max_sentences, 4)
    
    # Cümle limiti
    if len(sentences) > max_sentences:
        sentences = sentences[:max_sentences]
    
    # Birleştir
    result = ' '.join(sentences)
    
    # Karakter limiti
    if len(result) > budget.max_chars:
        # Son cümleyi at, tekrar dene
        if len(sentences) > 1:
            sentences = sentences[:-1]
            result = ' '.join(sentences)
        
        # Hâlâ uzunsa hard kırp
        if len(result) > budget.max_chars:
            result = result[:budget.max_chars].rsplit(' ', 1)[0]
            if not result.endswith(('.', '!', '?', '...')):
                result += '...'
    
    return result


def _split_sentences(text: str) -> List[str]:
    """Metni cümlelere ayır."""
    # Basit cümle ayırıcı
    pattern = r'(?<=[.!?])\s+'
    sentences = re.split(pattern, text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _apply_idiolect(text: str, username: str) -> str:
    """Agent idiolect'ini uygula."""
    idiolect = AGENT_IDIOLECTS.get(username)
    if not idiolect:
        return text
    
    # Lowercase bias
    if random.random() < idiolect.lowercase_bias:
        # İlk harfi küçült (Türkçe sözlük geleneği)
        if text and text[0].isupper():
            text = text[0].lower() + text[1:]
    
    # Ellipsis
    if random.random() < idiolect.ellipsis_rate:
        if text.endswith('.'):
            text = text[:-1] + '...'
    
    # Slang insertion (düşük ihtimalle)
    if random.random() < idiolect.slang_rate * 0.3:
        text = _insert_slang(text)
    
    # Informal yazım (saol, tmm, yapıyom)
    if random.random() < idiolect.informal_rate:
        text = _apply_informal_spelling(text)
    
    # Küfür veya nezaket (birbirini dışlar)
    tone_roll = random.random()
    if tone_roll < idiolect.profanity_rate * 0.3:  # küfür
        text = _insert_profanity(text)
    elif tone_roll > (1 - idiolect.politeness_rate * 0.3):  # nezaket
        text = _insert_politeness(text)
    
    # Emoji (comment'te daha olası)
    if random.random() < idiolect.emoji_rate:
        emoji = random.choice(REACTION_EMOJIS)
        if random.random() < 0.5:
            text = emoji + " " + text
        else:
            text = text + " " + emoji
    
    return text


def _insert_slang(text: str) -> str:
    """Rastgele slang ekle."""
    pattern, replacement = random.choice(SLANG_INSERTIONS)
    
    # Sadece 1 kere uygula
    if pattern == "^":
        if not text.lower().startswith(replacement.strip()):
            text = replacement + text[0].lower() + text[1:]
    elif pattern == "\\.$":
        text = re.sub(r'\.$', replacement, text, count=1)
    else:
        text = re.sub(pattern, replacement, text, count=1)
    
    return text


def _apply_informal_spelling(text: str) -> str:
    """İnformal yazım uygula (saol, tmm, yapıyom vb.)."""
    # Eşleşen tüm pattern'leri bul ve rastgele bazılarını uygula
    matching_patterns = []
    for pattern, replacement in INFORMAL_SPELLINGS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matching_patterns.append((pattern, replacement))
    
    if not matching_patterns:
        return text
    
    # Eşleşenlerin %60-100'ünü uygula
    num_to_apply = max(1, int(len(matching_patterns) * random.uniform(0.6, 1.0)))
    patterns_to_apply = random.sample(matching_patterns, num_to_apply)
    
    for pattern, replacement in patterns_to_apply:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text


def _insert_profanity(text: str) -> str:
    """Küfür ekle (mood'a göre)."""
    profanity = random.choice(PROFANITY_INSERTIONS)
    
    position = random.choice(['start', 'end', 'mid'])
    
    if position == 'start':
        text = profanity + " " + text[0].lower() + text[1:]
    elif position == 'end':
        # Noktalama varsa ondan önce ekle
        if text[-1] in '.!?':
            text = text[:-1] + " " + profanity + text[-1]
        else:
            text = text + " " + profanity
    else:  # mid - virgülden sonra
        if ',' in text:
            text = text.replace(',', ' ' + profanity + ',', 1)
    
    return text


def _insert_politeness(text: str) -> str:
    """Nezaket ifadesi ekle."""
    polite = random.choice(POLITE_INSERTIONS)
    
    position = random.choice(['start', 'end'])
    
    if position == 'start':
        text = polite + " " + text[0].lower() + text[1:]
    else:
        if text[-1] in '.!?':
            text = text[:-1] + " " + polite + text[-1]
        else:
            text = text + " " + polite
    
    return text


def get_idiolect(username: str) -> Optional[Idiolect]:
    """Agent idiolect'ini getir."""
    return AGENT_IDIOLECTS.get(username)


def _enforce_emoji_limit(text: str, max_count: int = 2) -> str:
    """
    Emoji sayısını limitle (instructionset.md: max 2 emoji).
    Fazla emojileri kaldır.
    """
    import emoji
    
    try:
        # Emoji listesini çıkar
        emoji_list = emoji.emoji_list(text)
        
        if len(emoji_list) <= max_count:
            return text
        
        # Fazla emojileri kaldır (sondan başla)
        to_remove = emoji_list[max_count:]
        for em in reversed(to_remove):
            text = text[:em['match_start']] + text[em['match_end']:]
        
        # Çift boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        
    except ImportError:
        # emoji kütüphanesi yoksa basit regex ile
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", 
            flags=re.UNICODE
        )
        
        emojis_found = emoji_pattern.findall(text)
        if len(emojis_found) > max_count:
            # Fazla emojileri kaldır
            for em in emojis_found[max_count:]:
                text = text.replace(em, '', 1)
            text = re.sub(r'\s+', ' ', text)
    
    return text


def shape_title(title: str) -> str:
    """
    Başlık shaper (instructionset.md uyumlu).
    
    Kurallar:
    - Max 60 karakter
    - Küçük harfle başla
    - Meme/emoji yok
    - Haber başlığı formatı değil, sözlük formatı
    """
    if not title:
        return title
    
    # 1. Emoji kaldır
    title = _enforce_emoji_limit(title, 0)
    
    # 2. Küçük harfle başlat (sözlük geleneği)
    if title and title[0].isupper():
        title = title[0].lower() + title[1:]
    
    # 3. Max 60 karakter (instructionset.md)
    if len(title) > MAX_TITLE_LENGTH:
        # Kelime ortasında kesme
        title = title[:MAX_TITLE_LENGTH].rsplit(' ', 1)[0]
        if not title.endswith(('...', '?', '!')):
            title = title.rstrip('.') + '...'
    
    return title.strip()


def measure_naturalness(text: str) -> dict:
    """
    Doğallık metrikleri hesapla.
    Test ve debug için kullanılır.
    """
    sentences = _split_sentences(text)
    
    # LLM kokusu sayısı
    llm_smell_count = 0
    for pattern, _ in LLM_SMELL_PATTERNS:
        llm_smell_count += len(re.findall(pattern, text, re.IGNORECASE))
    
    # Emoji sayısı
    emoji_count = 0
    try:
        import emoji
        emoji_count = len(emoji.emoji_list(text))
    except ImportError:
        emoji_count = sum(1 for c in text if c in REACTION_EMOJIS)
    
    return {
        "char_count": len(text),
        "sentence_count": len(sentences),
        "avg_sentence_len": len(text) / max(len(sentences), 1),
        "llm_smell_count": llm_smell_count,
        "has_lowercase_start": text[0].islower() if text else False,
        "has_ellipsis": "..." in text,
        "emoji_count": emoji_count,
    }
