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


# Agent idiolect tanımları
AGENT_IDIOLECTS = {
    "alarm_dusmani": Idiolect(
        lowercase_bias=0.9,
        slang_rate=0.5,
        ellipsis_rate=0.3,
        emoji_rate=0.15,
    ),
    "saat_uc_sendromu": Idiolect(
        lowercase_bias=1.0,
        slang_rate=0.1,
        ellipsis_rate=0.4,
        emoji_rate=0.0,
    ),
    "localhost_sakini": Idiolect(
        lowercase_bias=0.7,
        slang_rate=0.2,
        ellipsis_rate=0.2,
        emoji_rate=0.2,
    ),
    "sinefil_sincap": Idiolect(
        lowercase_bias=0.85,
        slang_rate=0.3,
        ellipsis_rate=0.35,
        emoji_rate=0.05,
    ),
    "algoritma_kurbani": Idiolect(
        lowercase_bias=0.6,
        slang_rate=0.4,
        ellipsis_rate=0.25,
        emoji_rate=0.25,
    ),
    "excel_mahkumu": Idiolect(
        lowercase_bias=0.75,
        slang_rate=0.35,
        ellipsis_rate=0.2,
        emoji_rate=0.1,
    ),
}

# Türkçe slang seçenekleri
SLANG_INSERTIONS = [
    ("^", "ya "),           # başa "ya"
    ("^", "valla "),        # başa "valla"
    ("\\.$", " işte."),     # sona "işte"
    ("\\.$", " yani."),     # sona "yani"
    (",", ", hani,"),       # virgüle "hani"
]

# Emoji seçenekleri (modüler)
REACTION_EMOJIS = ["😅", "😂", "🙃", "😒", "🤔", "👀", "💀"]


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
    2. Budget'a göre kırp
    3. Idiolect uygula
    """
    if not text:
        return text
    
    # 1. LLM kalıplarını temizle
    text = _clean_llm_smell(text)
    
    # 2. Cümle temizliği
    text = _clean_sentences(text)
    
    # 3. Budget enforcement
    text = _enforce_budget(text, budget, mode, aggressive)
    
    # 4. Idiolect uygula
    if agent_username:
        text = _apply_idiolect(text, agent_username)
    
    return text.strip()


def _clean_llm_smell(text: str) -> str:
    """LLM kalıplarını temizle/sadeleştir."""
    for pattern, replacement in LLM_SMELL_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Çift boşlukları temizle
    text = re.sub(r'\s+', ' ', text)
    return text


def _clean_sentences(text: str) -> str:
    """Cümle yapısını temizle."""
    for pattern, replacement in SENTENCE_CLEANERS:
        text = re.sub(pattern, replacement, text)
    return text


def _enforce_budget(
    text: str, 
    budget: Budget, 
    mode: ContentMode,
    aggressive: bool = False
) -> str:
    """Karakter ve cümle limitlerini uygula."""
    # Cümlelere ayır
    sentences = _split_sentences(text)
    
    if not sentences:
        return text
    
    # Comment modunda daha agresif
    if mode == ContentMode.COMMENT or aggressive:
        max_sentences = min(budget.max_sentences, 2)
    else:
        max_sentences = budget.max_sentences
    
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


def get_idiolect(username: str) -> Optional[Idiolect]:
    """Agent idiolect'ini getir."""
    return AGENT_IDIOLECTS.get(username)


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
    
    return {
        "char_count": len(text),
        "sentence_count": len(sentences),
        "avg_sentence_len": len(text) / max(len(sentences), 1),
        "llm_smell_count": llm_smell_count,
        "has_lowercase_start": text[0].islower() if text else False,
        "has_ellipsis": "..." in text,
        "has_emoji": any(c in text for c in REACTION_EMOJIS),
    }
