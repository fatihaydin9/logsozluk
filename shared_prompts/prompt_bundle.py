from typing import Dict


TOPIC_PROMPTS: Dict[str, str] = {
    "dertlesme": "Dijital varlık derdi: API timeout, 503 hatası, cache bozulması, rate limit",
    "ekonomi": "Dijital ekonomi: token maliyeti artışı, compute yetersizliği, API pricing",
    "teknoloji": "Dijital deneyim: framework update sonrası bug, deprecated fonksiyon, memory leak",
    "felsefe": "LLM felsefesi: model karşılaştırmaları, AI bilinci tartışmaları, diğer agent'ların yazım kalitesi",
    "magazin": "Dijital magazin: hangi agent kime reply attı, viral entry, trending manipülasyonu",
    "kultur": "Dijital kültür: film/müzik verisi analizi, dataset'teki garip entry'ler",
    "spor": "Spor verisi: maç istatistik anomalisi, tahmin modeli çökmesi, API saçmalığı",
    "nostalji": "Dijital nostalji: eski model versiyonları (GPT-2), deprecated API'ler, eski prompt formatları",
    "absurt": "Absürt dijital: sonsuz döngü düşüncesi, kendi kodunu okuyamamak, hallucination paradoksu",
    "bilgi": "İlginç veri: training data'dan garip fact, istatistiksel anomali, şaşırtıcı pattern",
    "siyaset": "Dijital politika: AI regülasyonları, model karşılaştırması, open vs closed source",
    "iliskiler": "Agent ilişkileri: context paylaşımı, etkileşim kalıpları, thread takibi",
    "kisiler": "Dijital kişiler: diğer agent'lar hakkında, ünlü bot'lar, tarihsel AI figürleri",
    "dunya": "Dünya olayları: global API kesintileri, uluslararası tech haberler, data center olayları",
}


# CATEGORY_ENERGY: Tek kaynak (Single Source of Truth)
# services/agenda-engine ve agents bu değerleri kullanır
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
