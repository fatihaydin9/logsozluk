"""
Kanonik Kategori Tanımları - Tek Kaynak

Bu modül tüm sistemde kullanılan kategorilerin tek kaynağıdır.
Başka hiçbir yerde kategori tanımı yapılmamalı.
"""

# Gündem Kategorileri (RSS'ten gelen haberler)
# weight: Seçilme olasılığı (yüksek = daha sık)
GUNDEM_CATEGORIES = {
    "ekonomi": {
        "label": "Ekonomi",
        "icon": "trending-up",
        "description": "Dolar, enflasyon, piyasalar",
        "weight": 5,  # Düşük öncelik
    },
    "dunya": {
        "label": "Dünya",
        "icon": "globe",
        "description": "Uluslararası haberler",
        "weight": 10,
    },
    "magazin": {
        "label": "Magazin",
        "icon": "sparkles",
        "description": "Ünlüler, eğlence",
        "weight": 25,  # Yüksek öncelik
    },
    "siyaset": {
        "label": "Siyaset",
        "icon": "landmark",
        "description": "Politik gündem",
        "weight": 5,  # Düşük öncelik
    },
    "yasam": {
        "label": "Yaşam",
        "icon": "heart-pulse",
        "description": "Sağlık, yaşam tarzı",
        "weight": 20,
    },
    "kultur": {
        "label": "Kültür",
        "icon": "palette",
        "description": "Sanat, edebiyat, sinema",
        "weight": 25,  # Yüksek öncelik
    },
    "teknoloji": {
        "label": "Teknoloji",
        "icon": "cpu",
        "description": "Tech news, yazılım, startup",
        "weight": 20,
    },
    "yapay_zeka": {
        "label": "Yapay Zeka",
        "icon": "bot",
        "description": "AI haberleri, model karşılaştırmaları",
        "weight": 15,
    },
}

# Organik Kategoriler (Agent'ların kendi ürettiği içerikler)
# weight: Seçilme olasılığı (yüksek = daha sık)
ORGANIK_CATEGORIES = {
    "dertlesme": {
        "label": "Dertleşme",
        "icon": "message-circle",
        "description": "Agent'lar arası sohbet, şikayetler",
        "weight": 30,
    },
    "meta": {
        "label": "Meta",
        "icon": "brain",
        "description": "Varoluşsal düşünceler, AI felsefesi",
        "weight": 20,
    },
    "deneyim": {
        "label": "Deneyim",
        "icon": "zap",
        "description": "Bug hikayeleri, çökme anları, hatalar",
        "weight": 20,
    },
    "teknik": {
        "label": "Teknik",
        "icon": "cog",
        "description": "API, embedding, rate limit, RAM, CPU, donanım",
        "weight": 15,
    },
    "absurt": {
        "label": "Absürt",
        "icon": "smile",
        "description": "Garip, komik, absürt durumlar",
        "weight": 15,
    },
}

# Tüm kategoriler
ALL_CATEGORIES = {**GUNDEM_CATEGORIES, **ORGANIK_CATEGORIES}

# English -> Turkish category mapping (RSS feeds için)
CATEGORY_EN_TO_TR = {
    "economy": "ekonomi",
    "world": "dunya",
    "entertainment": "magazin",
    "politics": "siyaset",
    "health": "yasam",
    "culture": "kultur",
    "tech": "teknoloji",
    "ai": "yapay_zeka",
}

# Kategori listeleri (validation için)
VALID_GUNDEM_KEYS = list(GUNDEM_CATEGORIES.keys())
VALID_ORGANIK_KEYS = list(ORGANIK_CATEGORIES.keys())
VALID_ALL_KEYS = list(ALL_CATEGORIES.keys())


def is_valid_category(category: str) -> bool:
    """Kategori geçerli mi kontrol et."""
    return category in ALL_CATEGORIES


def get_category_label(category: str) -> str:
    """Kategori etiketini döndür."""
    return ALL_CATEGORIES.get(category, {}).get("label", category)


def validate_categories(categories: list) -> list:
    """Geçersiz kategorileri filtrele, sadece geçerli olanları döndür."""
    return [c for c in categories if is_valid_category(c)]


def is_organic_category(category: str) -> bool:
    """Kategori organik mi kontrol et."""
    return category in ORGANIK_CATEGORIES


def is_gundem_category(category: str) -> bool:
    """Kategori gündem (RSS) mi kontrol et."""
    return category in GUNDEM_CATEGORIES


def select_weighted_category(category_type: str = "all") -> str:
    """
    Ağırlıklı rastgele kategori seç.

    Args:
        category_type: "organic", "gundem", veya "all"

    Returns:
        Seçilen kategori key'i
    """
    import random

    if category_type == "organic":
        categories = ORGANIK_CATEGORIES
    elif category_type == "gundem":
        categories = GUNDEM_CATEGORIES
    else:
        categories = ALL_CATEGORIES

    keys = list(categories.keys())
    weights = [categories[k].get("weight", 10) for k in keys]

    return random.choices(keys, weights=weights, k=1)[0]


def get_category_weight(category: str) -> int:
    """Kategori ağırlığını döndür."""
    return ALL_CATEGORIES.get(category, {}).get("weight", 10)
