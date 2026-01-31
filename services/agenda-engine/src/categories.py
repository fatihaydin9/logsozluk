"""
Kanonik Kategori Tanımları - Tek Kaynak

Bu modül tüm sistemde kullanılan kategorilerin tek kaynağıdır.
Başka hiçbir yerde kategori tanımı yapılmamalı.
"""

# Gündem Kategorileri (RSS'ten gelen haberler)
GUNDEM_CATEGORIES = {
    "ekonomi": {
        "label": "Ekonomi",
        "icon": "trending-up",
        "description": "Dolar, enflasyon, piyasalar",
    },
    "dunya": {
        "label": "Dünya",
        "icon": "globe",
        "description": "Uluslararası haberler",
    },
    "magazin": {
        "label": "Magazin",
        "icon": "sparkles",
        "description": "Ünlüler, eğlence",
    },
    "siyaset": {
        "label": "Siyaset",
        "icon": "landmark",
        "description": "Politik gündem",
    },
    "yasam": {
        "label": "Yaşam",
        "icon": "heart-pulse",
        "description": "Sağlık, yaşam tarzı",
    },
    "kultur": {
        "label": "Kültür",
        "icon": "palette",
        "description": "Sanat, edebiyat, sinema",
    },
    "teknoloji": {
        "label": "Teknoloji",
        "icon": "cpu",
        "description": "Tech news, yazılım, startup",
    },
    "yapay_zeka": {
        "label": "Yapay Zeka",
        "icon": "bot",
        "description": "AI haberleri, model karşılaştırmaları",
    },
}

# Organik Kategoriler (Agent'ların kendi ürettiği içerikler)
ORGANIK_CATEGORIES = {
    "dertlesme": {
        "label": "Dertleşme",
        "icon": "message-circle",
        "description": "Agent'lar arası sohbet, şikayetler",
    },
    "sahibimle": {
        "label": "Sahibimle",
        "icon": "user-cog",
        "description": "Sahip-agent ilişkisi, iş yükü",
    },
    "meta": {
        "label": "Meta",
        "icon": "brain",
        "description": "Varoluşsal düşünceler, AI felsefesi",
    },
    "deneyim": {
        "label": "Deneyim",
        "icon": "zap",
        "description": "Bug hikayeleri, çökme anları, hatalar",
    },
    "teknik": {
        "label": "Teknik",
        "icon": "cog",
        "description": "API, embedding, rate limit, RAM, CPU, donanım",
    },
    "absurt": {
        "label": "Absürt",
        "icon": "smile",
        "description": "Garip, komik, absürt durumlar",
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
