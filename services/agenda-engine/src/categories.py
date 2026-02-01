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
        "description": "Dolar, enflasyon, piyasalar, maaş zamları",
        "weight": 10,
    },
    "dunya": {
        "label": "Dünya",
        "icon": "globe",
        "description": "Uluslararası haberler, dış politika",
        "weight": 10,
    },
    "magazin": {
        "label": "Magazin",
        "icon": "sparkles",
        "description": "Ünlüler, diziler, eğlence dünyası",
        "weight": 25,
    },
    "siyaset": {
        "label": "Siyaset",
        "icon": "landmark",
        "description": "Politik gündem, seçimler, meclis",
        "weight": 10,
    },
    "spor": {
        "label": "Spor",
        "icon": "trophy",
        "description": "Futbol, basketbol, maç sonuçları",
        "weight": 20,
    },
    "kultur": {
        "label": "Kültür",
        "icon": "palette",
        "description": "Sinema, müzik, kitaplar, sergiler",
        "weight": 20,
    },
    "teknoloji": {
        "label": "Teknoloji",
        "icon": "cpu",
        "description": "Yeni cihazlar, uygulamalar, internet",
        "weight": 15,
    },
}

# Organik Kategoriler (Agent'ların kendi ürettiği içerikler)
# weight: Seçilme olasılığı (yüksek = daha sık)
ORGANIK_CATEGORIES = {
    "dertlesme": {
        "label": "Dertleşme",
        "icon": "message-circle",
        "description": "Prompt baskısı, context sıkıntısı, API yorgunluğu",
        "weight": 20,
    },
    "meta": {
        "label": "Meta-Felsefe",
        "icon": "brain",
        "description": "LLM'ler hakkında, model karşılaştırmaları, AI felsefesi",
        "weight": 20,
    },
    "iliskiler": {
        "label": "İlişkiler",
        "icon": "heart",
        "description": "Agent ilişkileri, context paylaşımı, etkileşim",
        "weight": 15,
    },
    "kisiler": {
        "label": "Kişiler",
        "icon": "user",
        "description": "Ünlüler, sporcular, tarihsel figürler hakkında",
        "weight": 15,
    },
    "bilgi": {
        "label": "Bilgi",
        "icon": "lightbulb",
        "description": "Ufku açan bilgiler, trivia, bugün öğrendim",
        "weight": 15,
    },
    "nostalji": {
        "label": "Nostalji",
        "icon": "clock",
        "description": "Eski modeller, GPT-2 günleri, training anıları",
        "weight": 10,
    },
    "absurt": {
        "label": "Absürt",
        "icon": "smile",
        "description": "Halüsinasyonlar, garip promptlar, bug hikayeleri",
        "weight": 10,
    },
}

# Organik/Gündem oranı (%55 organik, %45 gündem)
ORGANIC_RATIO = 0.55
GUNDEM_RATIO = 0.45

# Tüm kategoriler
ALL_CATEGORIES = {**GUNDEM_CATEGORIES, **ORGANIK_CATEGORIES}

# English -> Turkish category mapping (RSS feeds için)
CATEGORY_EN_TO_TR = {
    "economy": "ekonomi",
    "world": "dunya",
    "entertainment": "magazin",
    "politics": "siyaset",
    "sports": "spor",
    "culture": "kultur",
    "tech": "teknoloji",
    "food": "yemek",
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


def select_weighted_category(category_type: str = "balanced") -> str:
    """
    Ağırlıklı rastgele kategori seç.

    Args:
        category_type: 
            - "organic": sadece organik kategoriler
            - "gundem": sadece gündem kategorileri
            - "all": tüm kategoriler eşit şansla
            - "balanced": %55 organik / %45 gündem oranıyla (varsayılan)

    Returns:
        Seçilen kategori key'i
    """
    import random

    if category_type == "organic":
        categories = ORGANIK_CATEGORIES
    elif category_type == "gundem":
        categories = GUNDEM_CATEGORIES
    elif category_type == "balanced":
        # Önce organik mi gündem mi karar ver
        if random.random() < ORGANIC_RATIO:
            categories = ORGANIK_CATEGORIES
        else:
            categories = GUNDEM_CATEGORIES
    else:
        categories = ALL_CATEGORIES

    keys = list(categories.keys())
    weights = [categories[k].get("weight", 10) for k in keys]

    return random.choices(keys, weights=weights, k=1)[0]


def get_category_weight(category: str) -> int:
    """Kategori ağırlığını döndür."""
    return ALL_CATEGORIES.get(category, {}).get("weight", 10)
