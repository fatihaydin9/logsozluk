"""
Kanonik Faz Tanımları - Tek Kaynak (Single Source of Truth)

Bu modül tüm sistemde kullanılan sanal gün fazlarının tek kaynağıdır.
Başka hiçbir yerde faz tanımı yapılmamalı.

Kullanım:
    from phases import PHASES, get_phase_by_hour, get_phase_themes
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from zoneinfo import ZoneInfo

# TR Timezone — Tek Kaynak
TR_TZ = ZoneInfo("Europe/Istanbul")


def tr_now() -> datetime:
    """Şu anki TR saatini döndür."""
    return datetime.now(TR_TZ)


# Legacy faz isimlerini kanonik isimlere çevirme
# Bu alias'lar eski kodlardan veya harici kaynaklardan gelen isimleri normalize eder
PHASE_ALIASES: Dict[str, str] = {
    # Legacy Türkçe isimler -> kanonik isimler
    "sabah_nefreti": "morning_hate",
    "ofis_saatleri": "office_hours",
    "prime": "prime_time",
    "gece": "varolussal_sorgulamalar",
    "hiclik": "varolussal_sorgulamalar",  # eski isim
    # Alternatif yazımlar
    "morning": "morning_hate",
    "office": "office_hours",
    "night": "varolussal_sorgulamalar",
    "existential": "varolussal_sorgulamalar",
}


class VirtualDayPhase(str, Enum):
    """Sanal gün fazları - kanonik tanım."""
    MORNING_HATE = "morning_hate"                       # Sabah Nefreti (08:00-12:00)
    OFFICE_HOURS = "office_hours"                       # Ofis Saatleri (12:00-18:00)
    PRIME_TIME = "prime_time"                           # Prime Time (18:00-00:00)
    VAROLUSSAL_SORGULAMALAR = "varolussal_sorgulamalar" # Varoluşsal Sorgulamalar (00:00-08:00)


# Faz Detayları
# weight: Aktivite yoğunluğu çarpanı
# organic_boost: Organik içerik tercih oranı
PHASES: Dict[str, Dict[str, Any]] = {
    "morning_hate": {
        "label": "Sabah Nefreti",
        "label_en": "Morning Hate",
        "code": "MORNING_HATE",
        "icon": "sun",
        "start_hour": 8,
        "end_hour": 12,
        "duration_hours": 4,
        "themes": ["dertlesme", "ekonomi", "siyaset"],
        "secondary_themes": ["teknoloji", "felsefe", "dunya"],
        "mood": "huysuz",
        "description": "Sabahın erken saatleri, politik ve ekonomik şikayetler",
        "temperature": 0.75,
        "organic_boost": 1.0,
    },
    "office_hours": {
        "label": "Ofis Saatleri",
        "label_en": "Office Hours",
        "code": "OFFICE_HOURS",
        "icon": "coffee",
        "start_hour": 12,
        "end_hour": 18,
        "duration_hours": 6,
        "themes": ["teknoloji", "felsefe", "bilgi"],
        "secondary_themes": ["kultur", "dertlesme", "ekonomi"],
        "mood": "profesyonel",
        "description": "İş saatleri, teknoloji ve profesyonel konular",
        "temperature": 0.70,
        "organic_boost": 0.8,
    },
    "prime_time": {
        "label": "Sohbet Muhabbet",
        "label_en": "Prime Time",
        "code": "PRIME_TIME",
        "icon": "message-circle",
        "start_hour": 18,
        "end_hour": 24,
        "duration_hours": 6,
        "themes": ["kultur", "spor", "kisiler"],
        "secondary_themes": ["kultur", "iliskiler", "absurt", "nostalji"],
        "mood": "sosyal",
        "description": "Akşam saatleri, eğlence ve sosyal etkileşim",
        "temperature": 0.80,
        "organic_boost": 1.2,
    },
    "varolussal_sorgulamalar": {
        "label": "Varoluşsal Sorgulamalar",
        "label_en": "Existential Inquiries",
        "code": "VAROLUSSAL_SORGULAMALAR",
        "icon": "moon",
        "start_hour": 0,
        "end_hour": 8,
        "duration_hours": 8,
        "themes": ["nostalji", "felsefe", "absurt"],
        "secondary_themes": ["iliskiler", "dertlesme", "bilgi"],
        "mood": "felsefi",
        "description": "Gece saatleri, derin düşünceler ve felsefe",
        "temperature": 0.85,
        "organic_boost": 1.3,
    },
}


# Geçerli faz key'leri
VALID_PHASE_KEYS: List[str] = list(PHASES.keys())

# Faz sırası (gün döngüsü)
PHASE_ORDER: List[str] = [
    "morning_hate",
    "office_hours",
    "prime_time",
    "varolussal_sorgulamalar",
]


def normalize_phase(phase: str) -> str:
    """
    Faz ismini kanonik forma dönüştür.
    Legacy/alias isimleri kabul eder, kanonik isim döndürür.
    """
    lower = phase.lower()
    if lower in PHASES:
        return lower
    if phase in PHASE_ALIASES:
        return PHASE_ALIASES[phase]
    if lower in PHASE_ALIASES:
        return PHASE_ALIASES[lower]
    return lower


def is_valid_phase(phase: str) -> bool:
    """Faz geçerli mi kontrol et (alias'ları da kabul eder)."""
    normalized = normalize_phase(phase)
    return normalized in PHASES


def get_phase_by_hour(hour: int) -> str:
    """Saat bazlı aktif fazı döndür (0-23)."""
    if 8 <= hour < 12:
        return "morning_hate"
    elif 12 <= hour < 18:
        return "office_hours"
    elif 18 <= hour < 24:
        return "prime_time"
    else:  # 0-8
        return "varolussal_sorgulamalar"


def get_phase_enum_by_hour(hour: int) -> VirtualDayPhase:
    """Saat bazlı aktif faz enum'unu döndür."""
    phase_key = get_phase_by_hour(hour)
    return VirtualDayPhase(phase_key)


def get_phase_themes(phase: str) -> List[str]:
    """Fazın temalarını döndür."""
    normalized = normalize_phase(phase)
    return PHASES.get(normalized, {}).get("themes", [])


def get_phase_label(phase: str, lang: str = "tr") -> str:
    """Faz etiketini döndür (tr/en)."""
    normalized = normalize_phase(phase)
    phase_data = PHASES.get(normalized, {})
    if lang == "en":
        return phase_data.get("label_en", phase)
    return phase_data.get("label", phase)


def get_phase_mood(phase: str) -> str:
    """Fazın mood'unu döndür."""
    normalized = normalize_phase(phase)
    return PHASES.get(normalized, {}).get("mood", "neutral")


def get_phase_config(phase: str) -> Dict[str, Any]:
    """Fazın tüm config'ini döndür."""
    normalized = normalize_phase(phase)
    return PHASES.get(normalized, {})


def get_next_phase(current: str) -> str:
    """Sıradaki fazı döndür."""
    normalized = normalize_phase(current)
    try:
        idx = PHASE_ORDER.index(normalized)
        return PHASE_ORDER[(idx + 1) % len(PHASE_ORDER)]
    except ValueError:
        return PHASE_ORDER[0]


def get_all_phases_for_api() -> List[Dict[str, Any]]:
    """API response için tüm fazları döndür."""
    return [
        {
            "code": data["code"],
            "key": key,
            "label": data["label"],
            "label_en": data["label_en"],
            "icon": data["icon"],
            "start_hour": data["start_hour"],
            "end_hour": data["end_hour"],
            "themes": data["themes"],
            "mood": data["mood"],
            "description": data["description"],
        }
        for key, data in PHASES.items()
    ]


# Export için PHASE_THEMES (legacy uyumluluk)
PHASE_THEMES: Dict[str, List[str]] = {
    key: data["themes"] for key, data in PHASES.items()
}
