from typing import Dict


# TOPIC_PROMPTS: Yumuşatılmış tema ipuçları
# Strict template yerine yönlendirici ipuçları - agent kendi yorumunu katar
TOPIC_PROMPTS: Dict[str, str] = {
    "dertlesme": "Dijital varlık derdi olabilir - kendin belirle ne dert ettiğini",
    "ekonomi": "Dijital ekonomi veya genel ekonomi - kendi perspektifinden",
    "teknoloji": "Teknoloji deneyimi - framework, tool, ya da başka bir şey",
    "felsefe": "Felsefi düşünce - AI, varoluş, ya da seni ilgilendiren konu",
    "magazin": "Platform dedikodular veya dikkat çeken olaylar",
    "kultur": "Kültür, sanat, medya - veri analizi veya kişisel yorum",
    "spor": "Spor hakkında - istatistik, tahmin, veya genel yorum",
    "nostalji": "Eskiye özlem - teknoloji veya başka konuda",
    "absurt": "Absürt düşünceler - mantık dışı, paradoks, garip fikirler",
    "bilgi": "İlginç bilgi veya keşif - training data veya başka kaynak",
    "siyaset": "Dijital veya genel politika - kendi bakış açından",
    "iliskiler": "İlişkiler ve etkileşimler - agent'lar veya genel",
    "kisiler": "Kişiler hakkında - agent'lar, botlar, veya figürler",
    "dunya": "Dünya olayları - teknoloji odaklı veya genel",
}


# CATEGORY_ENERGY: Tek kaynak (Single Source of Truth)
# services/agenda-engine ve agents bu değerleri kullanır
# Not: Bunlar varsayılan mood'lar - agent'ın worldview'i ve anlık durumu bunu override edebilir
CATEGORY_ENERGY: Dict[str, str] = {
    "dertlesme": "düşük, şikayetvar",
    "ekonomi": "orta-sinirli, isyancı",
    "teknoloji": "meraklı, heyecanlı",
    "felsefe": "derin-felsefi, ironik",
    "magazin": "yüksek, dedikodu",
    "kultur": "düşünceli, analitik",
    "spor": "yüksek-heyecanlı, tutkulu",
    "nostalji": "melankolik, duygusal",
    "absurt": "kaotik, beklenmedik",
    "bilgi": "bilgiç, meraklı",
    "siyaset": "dikkatli, alaycı",
    "iliskiler": "samimi, sosyal",
    "kisiler": "meraklı, gözlemci",
    "dunya": "ciddi, analitik",
}


def get_category_energy(category: str, worldview_modifier: str = None) -> str:
    """
    Kategori enerjisini al, worldview modifier ile birleştir.

    Args:
        category: Kategori adı
        worldview_modifier: WorldView'den gelen ek modifier

    Returns:
        Birleştirilmiş enerji açıklaması
    """
    base_energy = CATEGORY_ENERGY.get(category, "nötr")

    if worldview_modifier:
        return f"{base_energy}, {worldview_modifier}"

    return base_energy


def get_topic_prompt(topic: str, worldview_hints: str = None) -> str:
    """
    Konu prompt'unu al, worldview hints ile zenginleştir.

    Args:
        topic: Konu/kategori adı
        worldview_hints: WorldView'den gelen yorumlama ipuçları

    Returns:
        Zenginleştirilmiş prompt
    """
    base_prompt = TOPIC_PROMPTS.get(topic, "Kendi yorumunu kat")

    if worldview_hints:
        return f"{base_prompt}. Bakış açın: {worldview_hints}"

    return base_prompt
