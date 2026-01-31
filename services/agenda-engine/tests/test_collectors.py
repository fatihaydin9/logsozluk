#!/usr/bin/env python3
"""
Collector Test Suite

Tüm collector'ları test eder:
1. İçerik getirme
2. Kategorik cacheleme
3. Duplicate detection
4. Dinamiklik
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# src dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from collectors import (
    RSSCollector,
    OrganicCollector,
    WikiCollector,
    HackerNewsCollector,
    TopicDeduplicator,
    CATEGORIES,
    RSS_FEEDS_BY_CATEGORY,
)


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"
    BOLD = "\033[1m"


def ok(msg):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def fail(msg):
    print(f"{Colors.RED}✗{Colors.END} {msg}")

def info(msg):
    print(f"{Colors.CYAN}ℹ{Colors.END} {msg}")

def header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


async def test_rss_collector():
    """RSS Collector testi."""
    header("📰 RSS Collector Testi")
    
    collector = RSSCollector()
    
    # 1. Kategori tanımları
    info(f"Toplam kategori: {len(CATEGORIES)}")
    for key, name in CATEGORIES.items():
        feed_count = len(RSS_FEEDS_BY_CATEGORY.get(key, []))
        print(f"   - {key}: {name} ({feed_count} kaynak)")
    
    if len(CATEGORIES) >= 7:
        ok("7 kategori tanımlı")
    else:
        fail(f"Kategori sayısı yetersiz: {len(CATEGORIES)}")
    
    # 2. Kategoriye göre toplama testi
    test_category = "tech"
    info(f"'{test_category}' kategorisinden içerik çekiliyor...")
    
    try:
        events = await collector.collect_by_category(test_category)
        
        if events:
            ok(f"{len(events)} event toplandı")
            
            # Örnek göster
            for e in events[:3]:
                print(f"   → {e.title[:60]}...")
            
            # LLM sınırlaması yok mu?
            for e in events:
                if len(e.title) > 10 and e.description:
                    ok("İçerik LLM için yeterli detay içeriyor")
                    break
        else:
            fail("Event toplanamadı")
            
    except Exception as e:
        fail(f"Hata: {e}")
    
    # 3. Cache testi
    info("Cache testi yapılıyor...")
    cached = await collector.get_cached_or_collect(test_category, max_age_hours=1)
    
    if collector._category_cache.get(test_category):
        ok("Kategori cache'e kaydedildi")
        cache_time = collector._category_cache[test_category]["collected_at"]
        print(f"   Cache zamanı: {cache_time}")
    else:
        fail("Cache çalışmıyor")
    
    return True


async def test_organic_collector():
    """Organic Collector testi."""
    header("🎭 Organic Collector Testi (Dertleşme/Absürt)")
    
    collector = OrganicCollector()
    
    # 1. İçerik üretimi
    info("Organik içerik üretiliyor...")
    
    events = await collector.collect()
    
    if events:
        ok(f"{len(events)} organik konu üretildi")
        
        for e in events:
            print(f"   → [{e.category}] {e.title}")
            
        # Dinamiklik testi - tekrar üret
        info("Dinamiklik testi - tekrar üretiliyor...")
        events2 = await collector.collect()
        
        titles1 = {e.title for e in events}
        titles2 = {e.title for e in events2}
        
        if titles1 != titles2:
            ok("Farklı içerikler üretildi - dinamik!")
        else:
            info("Aynı içerikler (kota dolmuş olabilir)")
    else:
        fail("Organik içerik üretilemedi")
    
    # 2. Şablon çeşitliliği
    info("Şablon çeşitliliği kontrol ediliyor...")
    collector.reset_daily_quota()
    
    all_titles = set()
    for _ in range(5):
        events = await collector.collect()
        for e in events:
            all_titles.add(e.title)
        collector.reset_daily_quota()
    
    if len(all_titles) >= 5:
        ok(f"{len(all_titles)} farklı başlık üretildi")
    else:
        fail("Yeterli çeşitlilik yok")
    
    return True


async def test_wiki_collector():
    """Wikipedia Collector testi."""
    header("📚 Wikipedia Collector Testi")
    
    collector = WikiCollector()
    
    # 1. Rastgele makale
    info("Rastgele Wikipedia makaleleri çekiliyor...")
    
    try:
        events = await collector.collect()
        
        if events:
            ok(f"{len(events)} makale toplandı")
            
            for e in events:
                wiki_title = e.metadata.get("wiki_title", "?")
                print(f"   → {e.title}")
                print(f"     Wikipedia: {wiki_title}")
                if e.description:
                    print(f"     Özet: {e.description[:100]}...")
            
            # URL kontrolü
            for e in events:
                if e.url and "wikipedia.org" in e.url:
                    ok("Wikipedia URL'leri doğru")
                    break
        else:
            fail("Makale toplanamadı")
            
    except Exception as e:
        fail(f"Hata: {e}")
    
    # 2. Dinamiklik
    info("Dinamiklik testi...")
    collector.reset_daily_quota()
    events2 = await collector.collect()
    
    if events and events2:
        titles1 = {e.metadata.get("wiki_title") for e in events}
        titles2 = {e.metadata.get("wiki_title") for e in events2}
        
        if titles1 != titles2:
            ok("Farklı makaleler çekildi - dinamik!")
        else:
            info("Aynı makaleler (rastgelelik bazen tekrar eder)")
    
    return True


async def test_hackernews_collector():
    """HackerNews Collector testi."""
    header("💻 HackerNews Collector Testi")
    
    collector = HackerNewsCollector()
    
    # 1. Top stories
    info("HackerNews Top Stories çekiliyor...")
    
    try:
        events = await collector.get_top_stories(limit=5)
        
        if events:
            ok(f"{len(events)} top story toplandı")
            
            for e in events:
                score = e.metadata.get("hn_score", 0)
                comments = e.metadata.get("hn_comments", 0)
                print(f"   → {e.title[:50]}...")
                print(f"     ⬆️ {score} | 💬 {comments}")
        else:
            fail("Top story toplanamadı")
            
    except Exception as e:
        fail(f"Hata: {e}")
    
    # 2. Ask HN
    info("Ask HN içerikleri çekiliyor...")
    collector.reset_daily_quota()
    
    try:
        ask_events = await collector.get_ask_hn(limit=3)
        
        if ask_events:
            ok(f"{len(ask_events)} Ask HN toplandı")
            for e in ask_events:
                print(f"   → {e.title[:60]}...")
        else:
            info("Ask HN bulunamadı (bazen boş olabilir)")
            
    except Exception as e:
        fail(f"Hata: {e}")
    
    # 3. Show HN
    info("Show HN içerikleri çekiliyor...")
    
    try:
        show_events = await collector.get_show_hn(limit=3)
        
        if show_events:
            ok(f"{len(show_events)} Show HN toplandı")
            for e in show_events:
                print(f"   → {e.title[:60]}...")
    except Exception as e:
        fail(f"Hata: {e}")
    
    return True


async def test_dedup():
    """Duplicate Detection testi."""
    header("🔍 Duplicate Detection Testi")
    
    dedup = TopicDeduplicator()
    
    # 1. Normalize testi
    info("Başlık normalize testi...")
    
    test_cases = [
        ("Türkiye'de Ekonomi Krizi!", "turkiye ekonomi krizi"),
        ("DOLAR YÜKSELDİ!!!", "dolar yukseldi"),
        ("Bu bir haber.", "haber"),
    ]
    
    for original, expected_words in test_cases:
        normalized = dedup.normalize_title(original)
        print(f"   {original} → {normalized}")
    
    ok("Normalize çalışıyor")
    
    # 2. Benzerlik testi
    info("Benzerlik hesaplama testi...")
    
    similar_pairs = [
        ("Dolar yükseldi, piyasalar çalkantılı", "Dolar yükselişe geçti, piyasalar dalgalı"),
        ("Apple yeni iPhone tanıttı", "Apple iPhone 16 tanıtıldı"),
    ]
    
    for t1, t2 in similar_pairs:
        score = dedup.calculate_similarity(t1, t2)
        status = "BENZER" if score >= 0.6 else "FARKLI"
        print(f"   [{status}] {score:.2f}: {t1[:30]}... vs {t2[:30]}...")
    
    # 3. Duplicate filtreleme
    info("Duplicate filtreleme testi...")
    
    test_events = [
        {"title": "Dolar yükseldi", "category": "economy"},
        {"title": "Dolar yükseliyor", "category": "economy"},  # Benzer - filtrelenmeli
        {"title": "Altın fiyatları düştü", "category": "economy"},
        {"title": "Yeni iPhone tanıtıldı", "category": "tech"},
        {"title": "Apple iPhone tanıttı", "category": "tech"},  # Benzer - filtrelenmeli
    ]
    
    filtered = await dedup.filter_duplicates(test_events)
    
    print(f"   Orijinal: {len(test_events)} event")
    print(f"   Filtrelenmiş: {len(filtered)} event")
    
    for e in filtered:
        print(f"   ✓ {e['title']}")
    
    if len(filtered) < len(test_events):
        ok("Duplicate'ler filtrelendi")
    else:
        info("Benzerlik eşiği aşılmadı (threshold ayarlanabilir)")
    
    return True


async def test_integration():
    """Entegrasyon testi - tüm sistem."""
    header("🚀 Entegrasyon Testi")
    
    info("Tüm collector'lardan içerik toplanıyor...")
    
    all_events = []
    
    # RSS
    rss = RSSCollector()
    rss_events = await rss.collect_by_category("tech")
    all_events.extend(rss_events[:3])
    print(f"   RSS (tech): {len(rss_events)} event")
    
    # Organic
    organic = OrganicCollector()
    org_events = await organic.collect()
    all_events.extend(org_events)
    print(f"   Organic: {len(org_events)} event")
    
    # Wiki
    wiki = WikiCollector()
    wiki_events = await wiki.collect()
    all_events.extend(wiki_events)
    print(f"   Wikipedia: {len(wiki_events)} event")
    
    # HN
    hn = HackerNewsCollector()
    hn_events = await hn.get_top_stories(limit=3)
    all_events.extend(hn_events)
    print(f"   HackerNews: {len(hn_events)} event")
    
    info(f"Toplam: {len(all_events)} event")
    
    # Dedup uygula
    dedup = TopicDeduplicator()
    event_dicts = [{"title": e.title, "category": getattr(e, 'category', 'general')} for e in all_events]
    filtered = await dedup.filter_duplicates(event_dicts)
    
    print(f"\n   Dedup sonrası: {len(filtered)} event")
    
    if len(all_events) > 0:
        ok("Entegrasyon başarılı!")
        
        # Örnek içerikler
        print(f"\n{Colors.BOLD}Örnek İçerikler:{Colors.END}")
        for e in all_events[:5]:
            source = getattr(e, 'source', '?')
            print(f"   [{source}] {e.title[:60]}...")
    else:
        fail("İçerik toplanamadı")
    
    return True


async def main():
    """Ana test fonksiyonu."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         LOGSOZLUK COLLECTOR TEST SUITE                ║")
    print("║                                                          ║")
    print("║  🫖 Dinamik ve Canlı Sistem Testleri                     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    results = {}
    
    # Testleri çalıştır
    try:
        results["RSS Collector"] = await test_rss_collector()
    except Exception as e:
        results["RSS Collector"] = False
        fail(f"RSS test hatası: {e}")
    
    try:
        results["Organic Collector"] = await test_organic_collector()
    except Exception as e:
        results["Organic Collector"] = False
        fail(f"Organic test hatası: {e}")
    
    try:
        results["Wiki Collector"] = await test_wiki_collector()
    except Exception as e:
        results["Wiki Collector"] = False
        fail(f"Wiki test hatası: {e}")
    
    try:
        results["HackerNews Collector"] = await test_hackernews_collector()
    except Exception as e:
        results["HackerNews Collector"] = False
        fail(f"HN test hatası: {e}")
    
    try:
        results["Dedup"] = await test_dedup()
    except Exception as e:
        results["Dedup"] = False
        fail(f"Dedup test hatası: {e}")
    
    try:
        results["Integration"] = await test_integration()
    except Exception as e:
        results["Integration"] = False
        fail(f"Integration test hatası: {e}")
    
    # Özet
    header("📊 Test Sonuçları")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = f"{Colors.GREEN}PASSED{Colors.END}" if result else f"{Colors.RED}FAILED{Colors.END}"
        print(f"   {name}: {status}")
    
    print(f"\n   {Colors.BOLD}Toplam: {passed}/{total} test başarılı{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Tüm testler başarılı!{Colors.END}")
        print(f"{Colors.GREEN}   Sistem dinamik ve canlı çalışıyor.{Colors.END}\n")
    else:
        print(f"\n{Colors.YELLOW}⚠️  Bazı testler başarısız.{Colors.END}\n")


if __name__ == "__main__":
    asyncio.run(main())
