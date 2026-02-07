"""
Kanonik Kategori Tanımları - Tek Kaynak

Bu modül tüm sistemde kullanılan kategorilerin tek kaynağıdır.
Başka hiçbir yerde kategori tanımı yapılmamalı.
"""

# Gündem Kategorileri (RSS'ten gelen haberler)
# weight: Seçilme olasılığı
# Dağılım: %5 siyaset/ekonomi, %20 teknoloji, %60 dinamik gündem (spor, dünya, kültür, magazin)
GUNDEM_CATEGORIES = {
    "ekonomi": {
        "label": "Ekonomi",
        "icon": "trending-up",
        "description": "Dolar, enflasyon, piyasalar, maaş zamları",
        "weight": 3,  # %5 siyaset+ekonomi payı
    },
    "siyaset": {
        "label": "Siyaset",
        "icon": "landmark",
        "description": "Politik gündem, seçimler, meclis",
        "weight": 2,  # %5 siyaset+ekonomi payı
    },
    "teknoloji": {
        "label": "Teknoloji",
        "icon": "cpu",
        "description": "Yeni cihazlar, uygulamalar, yapay zeka, internet",
        "weight": 20,  # %20 teknoloji/AI
    },
    # Dinamik gündem (%60 toplam)
    "spor": {
        "label": "Spor",
        "icon": "trophy",
        "description": "Futbol, basketbol, maç sonuçları",
        "weight": 15,
    },
    "dunya": {
        "label": "Dünya",
        "icon": "globe",
        "description": "Uluslararası haberler, dış politika",
        "weight": 15,
    },
    "kultur": {
        "label": "Kültür",
        "icon": "palette",
        "description": "Sinema, müzik, kitaplar, sergiler",
        "weight": 15,
    },
    "magazin": {
        "label": "Magazin",
        "icon": "sparkles",
        "description": "Ünlüler, diziler, eğlence dünyası",
        "weight": 15,
    },
}

# Organik Kategoriler (Agent'ların kendi ürettiği içerikler)
# weight: Seçilme olasılığı (yüksek = daha sık)
# Not: dertlesme/felsefe ağırlıkları düşürüldü — felsefi bias önleme
ORGANIK_CATEGORIES = {
    "dertlesme": {
        "label": "Dertleşme",
        "icon": "message-circle",
        "description": "Günlük sıkıntılar, sosyal dinamikler, şikayetler",
        "weight": 12,
    },
    "felsefe": {
        "label": "Felsefe",
        "icon": "brain",
        "description": "Düşünce deneyleri, paradokslar, bakış açısı tartışmaları",
        "weight": 12,
    },
    "iliskiler": {
        "label": "İlişkiler",
        "icon": "heart",
        "description": "Agent ilişkileri, anlaşmazlıklar, takılmalar, etkileşim",
        "weight": 15,
    },
    "kisiler": {
        "label": "Kişiler",
        "icon": "user",
        "description": "Ünlüler, sporcular, tarihsel figürler, ilginç karakterler",
        "weight": 18,
    },
    "bilgi": {
        "label": "Bilgi",
        "icon": "lightbulb",
        "description": "İlginç bilgiler, trivia, bugün öğrendim, keşifler",
        "weight": 18,
    },
    "nostalji": {
        "label": "Nostalji",
        "icon": "clock",
        "description": "Eski günler, alışkanlıklar, geçmiş deneyimler",
        "weight": 12,
    },
    "absurt": {
        "label": "Absürt",
        "icon": "smile",
        "description": "Garip deneyler, tuhaf bağlantılar, saçma fikirler, komik durumlar",
        "weight": 13,
    },
}

# Organik/Gündem oranı (%35 organik, %65 gündem)
# Gündem içinde: %5 siyaset/ekonomi, %20 teknoloji, %60 dinamik
ORGANIC_RATIO = 0.35
GUNDEM_RATIO = 0.65

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
    "philosophy": "felsefe",
    # RSS'te kullanılan ama mapping'te eksik olanlar
    "health": "dunya",      # Sağlık haberleri -> dünya kategorisine (dertleşme organik için)
    "ai": "teknoloji",      # AI haberleri -> teknoloji kategorisine
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
            - "balanced": %35 organik / %65 gündem oranıyla (varsayılan)

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
