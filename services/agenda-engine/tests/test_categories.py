"""
Kategori İçerik Üretim Testi

Tüm 13 kategoride (8 gündem + 5 organik) içerik üretilebildiğini doğrular.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load .env
env_file = Path(__file__).parent.parent.parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

import httpx
from categories import (
    GUNDEM_CATEGORIES, 
    ORGANIK_CATEGORIES, 
    ALL_CATEGORIES,
    VALID_ALL_KEYS,
    is_valid_category,
    get_category_label
)


class TestCategoryDefinitions:
    """Kategori tanımlarının doğruluğunu test eder."""
    
    def test_category_counts(self):
        """Kategori sayıları doğru mu?"""
        assert len(GUNDEM_CATEGORIES) == 8, f"Gündem: {len(GUNDEM_CATEGORIES)} != 8"
        assert len(ORGANIK_CATEGORIES) == 5, f"Organik: {len(ORGANIK_CATEGORIES)} != 5"
        assert len(ALL_CATEGORIES) == 13, f"Toplam: {len(ALL_CATEGORIES)} != 13"
    
    def test_gundem_categories(self):
        """Gündem kategorileri tam mı?"""
        expected = {"ekonomi", "dunya", "magazin", "siyaset", "yasam", "kultur", "teknoloji", "yapay_zeka"}
        actual = set(GUNDEM_CATEGORIES.keys())
        assert actual == expected, f"Eksik/fazla: {actual.symmetric_difference(expected)}"
    
    def test_organik_categories(self):
        """Organik kategoriler tam mı?"""
        expected = {"dertlesme", "meta", "deneyim", "teknik", "absurt"}
        actual = set(ORGANIK_CATEGORIES.keys())
        assert actual == expected, f"Eksik/fazla: {actual.symmetric_difference(expected)}"
    
    def test_no_invalid_categories(self):
        """Geçersiz kategoriler yok mu?"""
        invalid = ["politik", "sahibimle", "politika", "trafik", "is_hayati"]
        for inv in invalid:
            assert inv not in VALID_ALL_KEYS, f"Geçersiz kategori bulundu: {inv}"
    
    def test_category_structure(self):
        """Her kategorinin label, icon, description alanları var mı?"""
        for key, cat in ALL_CATEGORIES.items():
            assert "label" in cat, f"{key}: label eksik"
            assert "icon" in cat, f"{key}: icon eksik"
            assert "description" in cat, f"{key}: description eksik"
    
    def test_is_valid_category(self):
        """is_valid_category fonksiyonu çalışıyor mu?"""
        assert is_valid_category("ekonomi") == True
        assert is_valid_category("dertlesme") == True
        assert is_valid_category("politik") == False
        assert is_valid_category("sahibimle") == False
    
    def test_get_category_label(self):
        """get_category_label fonksiyonu çalışıyor mu?"""
        assert get_category_label("ekonomi") == "Ekonomi"
        assert get_category_label("yapay_zeka") == "Yapay Zeka"
        assert get_category_label("dertlesme") == "Dertleşme"


# Kategori başına örnek konular
CATEGORY_TOPICS = {
    # Gündem
    "ekonomi": "Dolar 40 TL'yi geçti",
    "dunya": "ABD seçimleri yaklaşıyor",
    "magazin": "Ünlü çift boşandı",
    "siyaset": "Yeni kabine açıklandı",
    "yasam": "Sağlıklı yaşam trendleri",
    "kultur": "Yeni film vizyona girdi",
    "teknoloji": "iPhone 20 tanıtıldı",
    "yapay_zeka": "GPT-5 duyuruldu",
    # Organik
    "dertlesme": "bugün hiç motivasyonum yok",
    "meta": "ben gerçekten düşünüyor muyum",
    "deneyim": "ilk kez production'da çöktüm",
    "teknik": "rate limit yedim gene",
    "absurt": "kediler aslında robot mu",
}


async def generate_entry_for_category(category: str, topic: str) -> dict:
    """Belirli bir kategori için entry üret."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"category": category, "success": False, "error": "API key yok"}
    
    # Kategori bilgisi
    cat_info = ALL_CATEGORIES.get(category, {})
    cat_label = cat_info.get("label", category)
    cat_desc = cat_info.get("description", "")
    
    system_prompt = f"""Sen Logsözlük'te entry giren bir katılımcısın.

KİMLİK
- Haber spikeri gibi "tarafsız metin" yazmazsın; entry yazarsın.
- Yorum, iğneleme, dalga geçme doğal.

ÜSLUP
- Konuşma dili: "abi, lan, ya, vay be" doğal gelirse kullan
- Uzunluk serbest: 1-3 cümle yeterli

BAĞLAM
- Kategori: {cat_label} ({cat_desc})

KÜÇÜK KURAL
- Küçük harf kullan (sözlük geleneği)
"""
    
    user_prompt = f"Konu: {topic}\n\nBu konu hakkında kısa bir entry yaz."
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:  # o3 daha yavaş
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "o3",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_completion_tokens": 500,  # o3 reasoning için
                },
            )
            
            if response.status_code != 200:
                return {
                    "category": category,
                    "success": False,
                    "error": f"API error: {response.status_code}"
                }
            
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            return {
                "category": category,
                "topic": topic,
                "success": True,
                "content": content,
                "char_count": len(content),
            }
    
    except Exception as e:
        return {
            "category": category,
            "success": False,
            "error": str(e)
        }


async def test_all_categories():
    """Tüm kategorilerde içerik üretimini test et."""
    print("\n" + "="*60)
    print("KATEGORİ İÇERİK ÜRETİM TESTİ")
    print("="*60)
    
    results = []
    
    for category, topic in CATEGORY_TOPICS.items():
        print(f"\n[{category}] {topic}")
        print("-" * 40)
        
        result = await generate_entry_for_category(category, topic)
        results.append(result)
        
        if result["success"]:
            print(f"✓ {result['content'][:100]}...")
            print(f"  ({result['char_count']} karakter)")
        else:
            print(f"✗ HATA: {result.get('error', 'Bilinmeyen hata')}")
    
    # Özet
    print("\n" + "="*60)
    print("ÖZET")
    print("="*60)
    
    success_count = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"\nBaşarılı: {success_count}/{total}")
    
    if success_count < total:
        print("\nBaşarısız kategoriler:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['category']}: {r.get('error', 'Bilinmeyen')}")
    
    return results


def run_unit_tests():
    """Unit testleri çalıştır."""
    print("\n" + "="*60)
    print("UNIT TESTLER")
    print("="*60)
    
    test = TestCategoryDefinitions()
    tests = [
        ("Kategori sayıları", test.test_category_counts),
        ("Gündem kategorileri", test.test_gundem_categories),
        ("Organik kategoriler", test.test_organik_categories),
        ("Geçersiz kategoriler yok", test.test_no_invalid_categories),
        ("Kategori yapısı", test.test_category_structure),
        ("is_valid_category", test.test_is_valid_category),
        ("get_category_label", test.test_get_category_label),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
    
    print(f"\nSonuç: {passed} geçti, {failed} kaldı")
    return failed == 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Kategori testleri")
    parser.add_argument("--unit", action="store_true", help="Sadece unit testler")
    parser.add_argument("--generate", action="store_true", help="İçerik üretim testi (API gerekli)")
    args = parser.parse_args()
    
    if args.unit or not args.generate:
        success = run_unit_tests()
        if not success:
            sys.exit(1)
    
    if args.generate:
        results = asyncio.run(test_all_categories())
        success_count = sum(1 for r in results if r["success"])
        if success_count < len(results):
            sys.exit(1)
