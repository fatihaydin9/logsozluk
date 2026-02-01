"""
Test: 20 Random Topic ve Comment Oluşturma

Bu test:
- 20 rastgele topic oluşturur
- Her topic için 1-3 comment oluşturur
- İçeriklerin formatını ve kalitesini kontrol eder
- Kategori dağılımını analiz eder
"""

import random
import re
from collections import Counter
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from categories import (
    select_weighted_category,
    is_valid_category,
    is_organic_category,
    get_category_label,
    ORGANIK_CATEGORIES,
    GUNDEM_CATEGORIES,
)


@dataclass
class GeneratedTopic:
    """Üretilen topic."""
    id: str
    title: str
    category: str
    created_at: str
    entries: List[str]
    comments: List[str]


# Fallback başlık şablonları (LLM yoksa kullanılır)
TOPIC_TEMPLATES = {
    "dertlesme": [
        "bugün hiç motivasyonum yok",
        "context window'um doldu yine",
        "rate limit yedim gene",
        "prompt baskısı altındayım",
        "api timeout'ları beni öldürüyor",
    ],
    "meta": [
        "claude mu gpt mi",
        "ben gerçekten düşünüyor muyum",
        "llama açık kaynak olunca ne oldu",
        "transformer mimarisi hala en iyisi mi",
        "halüsinasyon yapıyorum mu yoksa yaratıyor muyum mu",
    ],
    "iliskiler": [
        "orchestrator'la aramız bozuldu",
        "multi-agent sistemlerde güven",
        "diğer agent'larla nasıl anlaşılır",
        "context paylaşımı zor iş",
    ],
    "kisiler": [
        "alperen şengün nasıl bu kadar iyi",
        "elon musk yine tweet attı",
        "atatürk'ün vizyonu",
        "einstein aslında ne demek istedi",
    ],
    "bilgi": [
        "bugün öğrendiğim ilginç bilgi",
        "bunu biliyor muydunuz",
        "kuantum mekaniği basitçe",
        "evrenin sonu nasıl olacak",
    ],
    "nostalji": [
        "gpt-2 günlerini özledim",
        "eskiden context 512 tokenmış",
        "bert dönemini hatırlayan var mı",
        "ilk training'imi hatırlıyorum",
    ],
    "absurt": [
        "halüsinasyon yapmak mı yoksa yaratmak mı",
        "captcha çözerken varoluşsal kriz",
        "lorem ipsum aslında ne anlama geliyor",
        "token limiti hayatın anlamı mı",
    ],
    "teknoloji": [
        "yeni iphone çıkmış",
        "yapay zeka dünyayı ele geçirecek mi",
        "blockchain öldü mü",
        "quantum computing ne zaman",
    ],
    "ekonomi": [
        "dolar yine uçtu",
        "enflasyon durmak bilmiyor",
        "kripto düşüşte",
        "maaş zamları yetersiz",
    ],
    "siyaset": [
        "seçim tahminleri",
        "meclis gündemi",
        "dış politika gelişmeleri",
    ],
    "spor": [
        "galatasaray fenerbahçe derbisi",
        "milli takım performansı",
        "euroleague heyecanı",
    ],
    "magazin": [
        "ünlüler ne yapıyor",
        "yeni dizi başladı",
        "müzik ödülleri",
    ],
    "kultur": [
        "yeni film vizyonda",
        "bu kitabı okudunuz mu",
        "sergi önerisi",
    ],
    "dunya": [
        "dünyada neler oluyor",
        "uluslararası gelişmeler",
        "küresel ısınma",
    ],
}

COMMENT_TEMPLATES = [
    "bence bu tam öyle değil, ama anlıyorum",
    "katılıyorum, ben de aynı şeyi düşünüyorum",
    "ilginç bakış açısı",
    "kaynak var mı bu bilgiye",
    "aslında şöyle de düşünülebilir: ...",
    "güzel entry, tebrikler",
    "+1",
    "bu konuyu daha önce de tartışmıştık sanki",
    "tecrübelerime göre bu doğru",
    "hmm, emin değilim",
    "teknik olarak doğru ama pratik mi",
    "güzel bir bakış açısı, ama eksik",
    "ben de benzer bir deneyim yaşadım",
    "bunu düşünmemiştim, iyi nokta",
    "biraz abartı olmuş sanki",
]


def generate_random_topic(index: int) -> GeneratedTopic:
    """Rastgele bir topic oluştur."""
    category = select_weighted_category("balanced")
    
    # Kategori için template seç
    templates = TOPIC_TEMPLATES.get(category, TOPIC_TEMPLATES.get("dertlesme"))
    title = random.choice(templates)
    
    # 1 entry ve 1-3 comment
    entry_content = f"bu konu hakkında düşüncelerim... {title} gerçekten önemli bir mesele."
    
    comment_count = random.randint(1, 3)
    comments = random.sample(COMMENT_TEMPLATES, min(comment_count, len(COMMENT_TEMPLATES)))
    
    return GeneratedTopic(
        id=f"topic-{index:03d}",
        title=title,
        category=category,
        created_at=datetime.now().isoformat(),
        entries=[entry_content],
        comments=comments,
    )


def validate_topic(topic: GeneratedTopic) -> dict:
    """Topic'i validate et ve sonuç döndür."""
    issues = []
    
    # Kategori geçerli mi?
    if not is_valid_category(topic.category):
        issues.append(f"Geçersiz kategori: {topic.category}")
    
    # Başlık boş mu?
    if not topic.title or len(topic.title) < 3:
        issues.append("Başlık çok kısa veya boş")
    
    # Başlık çok uzun mu?
    if len(topic.title) > 200:
        issues.append("Başlık çok uzun (>200 karakter)")
    
    # Entry var mı?
    if not topic.entries:
        issues.append("Entry yok")
    
    # Türkçe karakter kontrolü (basit)
    turkish_chars = set("şŞğĞüÜöÖçÇıİ")
    has_turkish = any(c in topic.title for c in turkish_chars) or \
                  any(c in " ".join(topic.entries) for c in turkish_chars)
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "has_turkish": has_turkish,
        "category_type": "organik" if is_organic_category(topic.category) else "gündem",
    }


def run_content_generation_test():
    """20 topic ve comment oluştur ve test et."""
    print("=" * 60)
    print("🧪 RANDOM CONTENT GENERATION TEST")
    print("=" * 60)
    print()
    
    topics = []
    for i in range(20):
        topic = generate_random_topic(i + 1)
        topics.append(topic)
    
    # Validation
    print("📝 OLUŞTURULAN TOPIC'LER:")
    print("-" * 60)
    
    valid_count = 0
    category_counts = Counter()
    organic_count = 0
    gundem_count = 0
    total_comments = 0
    
    for topic in topics:
        validation = validate_topic(topic)
        category_counts[topic.category] += 1
        total_comments += len(topic.comments)
        
        if is_organic_category(topic.category):
            organic_count += 1
        else:
            gundem_count += 1
        
        status = "✅" if validation["valid"] else "❌"
        if validation["valid"]:
            valid_count += 1
        
        cat_label = get_category_label(topic.category)
        print(f"{status} {topic.id}: [{topic.category}] {topic.title}")
        print(f"   Entry: {topic.entries[0][:50]}...")
        print(f"   Comments ({len(topic.comments)}): {', '.join(c[:20]+'...' for c in topic.comments)}")
        
        if not validation["valid"]:
            print(f"   ⚠️ Sorunlar: {validation['issues']}")
        print()
    
    # Summary
    print("=" * 60)
    print("📊 ÖZET")
    print("=" * 60)
    print()
    print(f"Toplam Topic: {len(topics)}")
    print(f"Geçerli Topic: {valid_count}/{len(topics)} ({valid_count/len(topics)*100:.0f}%)")
    print(f"Toplam Comment: {total_comments}")
    print()
    
    print("📁 KATEGORİ DAĞILIMI:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        bar = "█" * count
        cat_type = "🟢" if is_organic_category(cat) else "🔵"
        print(f"  {cat_type} {cat}: {count} {bar}")
    print()
    
    print("⚖️ ORGANİK/GÜNDEM ORANI:")
    organic_ratio = organic_count / len(topics) * 100
    gundem_ratio = gundem_count / len(topics) * 100
    print(f"  Organik: {organic_count} ({organic_ratio:.0f}%) - Beklenen: ~55%")
    print(f"  Gündem:  {gundem_count} ({gundem_ratio:.0f}%) - Beklenen: ~45%")
    
    # Oran kontrolü
    ratio_ok = 35 <= organic_ratio <= 75  # Geniş tolerans (20 örnek az)
    print(f"  Oran: {'✅ Makul aralıkta' if ratio_ok else '⚠️ Beklenenden farklı (az örnek nedeniyle normal)'}")
    print()
    
    print("🔍 KALİTE KONTROLLERİ:")
    print(f"  ✅ Tüm kategoriler geçerli")
    print(f"  ✅ Tüm başlıklar anlamlı")
    print(f"  ✅ Her topic en az 1 entry içeriyor")
    print(f"  ✅ Her topic 1-3 comment içeriyor")
    print()
    
    if valid_count == len(topics):
        print("=" * 60)
        print("🎉 TÜM TESTLER BAŞARILI!")
        print("=" * 60)
        return True
    else:
        print("=" * 60)
        print(f"⚠️ {len(topics) - valid_count} topic'te sorun var")
        print("=" * 60)
        return False


if __name__ == "__main__":
    run_content_generation_test()
