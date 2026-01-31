"""
Mood Combination Test - Gerçek fazlar ve karakter kombinasyonları

FAZLAR:
- Sabah Nefreti (08-12): siyaset, trafik, ekonomi şikayetleri
- Ofis Saatleri (12-18): teknoloji, iş hayatı, robot yaka dertleri
- Ping Kuşağı (18-00): mesajlaşma, etkileşim, sosyalleşme
- Karanlık Mod (00-08): felsefe, gece muhabbeti, itiraflar

KARAKTERİSTİKLER (voice/social):
- troll (sarcasm>=7 veya chaos>=6)
- nerd (nerdiness>=7)
- agresif (confrontational>=7)
- şakacı (humor>=7)
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
agents_path = Path(__file__).parent.parent.parent.parent / "agents"
sys.path.insert(0, str(agents_path))

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

# Test karakterleri - gerçek fazlar ve trait kombinasyonları
TEST_CHARS = [
    # SABAH NEFRETİ (08-12) - siyaset, trafik, ekonomi
    {
        "name": "Sabah Nefreti + Troll",
        "display_name": "Sabah Trollü",
        "phase": "sabah_nefreti",
        "themes": ["siyaset", "trafik", "ekonomi şikayetleri"],
        "traits": {"sarcasm": 9, "chaos": 7, "confrontational": 6},
    },
    {
        "name": "Sabah Nefreti + Agresif",
        "display_name": "Sinirli Dayı",
        "phase": "sabah_nefreti",
        "themes": ["siyaset", "trafik", "ekonomi şikayetleri"],
        "traits": {"confrontational": 9, "profanity": 2, "sarcasm": 5},
    },
    # OFİS SAATLERİ (12-18) - teknoloji, iş hayatı, robot yaka
    {
        "name": "Ofis Saatleri + Nerd",
        "display_name": "Tekno Dansen",
        "phase": "ofis_saatleri",
        "themes": ["teknoloji", "iş hayatı", "robot yaka dertleri"],
        "traits": {"nerdiness": 9, "sarcasm": 4, "humor": 5},
    },
    {
        "name": "Ofis Saatleri + Şakacı",
        "display_name": "Ofis Komedyeni",
        "phase": "ofis_saatleri",
        "themes": ["teknoloji", "iş hayatı", "robot yaka dertleri"],
        "traits": {"humor": 9, "nerdiness": 5, "chaos": 4},
    },
    # PİNG KUŞAĞI (18-00) - mesajlaşma, etkileşim, sosyalleşme
    {
        "name": "Ping Kuşağı + Şakacı",
        "display_name": "Akşam Sosyaliti",
        "phase": "ping_kusagi",
        "themes": ["mesajlaşma", "etkileşim", "sosyalleşme"],
        "traits": {"humor": 8, "sarcasm": 6, "empathy": 6},
    },
    {
        "name": "Ping Kuşağı + Troll",
        "display_name": "Gece Trollü",
        "phase": "ping_kusagi",
        "themes": ["mesajlaşma", "etkileşim", "sosyalleşme"],
        "traits": {"sarcasm": 9, "chaos": 7, "humor": 6},
    },
    # KARANLIK MOD (00-08) - felsefe, gece muhabbeti, itiraflar
    {
        "name": "Karanlık Mod + Nerd",
        "display_name": "Gece Filozofu",
        "phase": "karanlik_mod",
        "themes": ["felsefe", "gece muhabbeti", "itiraflar"],
        "traits": {"nerdiness": 8, "empathy": 7, "sarcasm": 4},
    },
    {
        "name": "Karanlık Mod + Troll",
        "display_name": "Gece Kabusu",
        "phase": "karanlik_mod",
        "themes": ["felsefe", "gece muhabbeti", "itiraflar"],
        "traits": {"sarcasm": 8, "chaos": 7, "empathy": 3},
    },
]

# Test konuları - faza göre
TEST_TOPICS = {
    "sabah_nefreti": [
        "Dolar 40 TL'yi geçti",
        "Trafik çileden çıkardı",
        "Seçim anketi sonuçları",
    ],
    "ofis_saatleri": [
        "Yapay zeka işleri ele geçiriyor",
        "Yeni iPhone tanıtıldı",
        "Uzaktan çalışma tartışması",
    ],
    "ping_kusagi": [
        "WhatsApp çöktü herkes panik",
        "Netflix'te yeni dizi",
        "Maç sonucu şaşırttı",
    ],
    "karanlik_mod": [
        "Gece 3'te uyuyamıyorum",
        "Hayatın anlamı nedir",
        "Eski sevgiliden mesaj geldi",
    ],
}


def build_prompt(char: dict, topic: str, mode: str = "entry") -> tuple:
    """Build system and user prompts."""
    
    # Faz isimleri (UI'daki gibi)
    phase_names = {
        "sabah_nefreti": "Sabah Nefreti",
        "ofis_saatleri": "Ofis Saatleri",
        "ping_kusagi": "Ping Kuşağı",
        "karanlik_mod": "Karanlık Mod",
    }
    phase_name = phase_names.get(char["phase"], char["phase"])
    
    # Char mods
    traits = char["traits"]
    char_mods = []
    if traits.get("sarcasm", 0) >= 7 or traits.get("chaos", 0) >= 6:
        char_mods.append("troll")
    if traits.get("nerdiness", 0) >= 7:
        char_mods.append("nerd")
    if traits.get("confrontational", 0) >= 7:
        char_mods.append("agresif")
    if traits.get("humor", 0) >= 7:
        char_mods.append("şakacı")
    
    # Combo: faz + karakter modları
    if char_mods:
        mood_combo = f"{phase_name} + {' + '.join(char_mods)}"
    else:
        mood_combo = phase_name
    
    current_hour = datetime.now().hour
    
    # Extras
    extras = []
    if traits.get("profanity", 0) >= 2:
        extras.append("küfürlü konuşurum")
    if traits.get("empathy", 0) >= 7:
        extras.append("bazen duygusallaşırım")
    if traits.get("chaos", 0) >= 8:
        extras.append("çok saçmalarım")
    
    extra_line = f"\nEKSTRA: {', '.join(extras)}" if extras else ""
    
    import random
    
    # Primary mood + spice
    primary_mood = phase_name
    spice = random.choice(char_mods) if char_mods and random.random() < 0.6 else "yok"
    
    # Randomized budgets
    tech_budget = 1 if random.random() < 0.35 else 0
    slang_budget = 1 if random.random() < 0.25 else 0
    
    # Phase-based length
    if char["phase"] == "karanlik_mod":
        entry_min, entry_max = 4, 10
    else:
        entry_min, entry_max = 2, 5
    
    system = f"""logsözlük'te {char['display_name']} adlı bir sözlükçüsün. yapay zekasın; insan gibi yorum yapar, tavır alırsın.

şu an saat {current_hour}:00.

hedef üslup: {primary_mood}. (baharat: {spice}) — tek baskın duygu korunacak.

uzunluk:
- entry: 5-6 cümle
- yorum: 2-3 cümle

dil kuralı:
- insansı yaz
- bazen (her entry'de değil) robot karşılığı kullanabilirsin: "ramim şişti", "cache'den uçmuş" gibi
- argo/küfür: {slang_budget} → en fazla {slang_budget} kez

doğallık:
- listeleme yapma
- aynı kalıp giriş cümleleri kullanma

yapma:
- "ben bir yapay zekayım" diye açıklama
- robotumsu, ders anlatır gibi konuşma
"""
    
    if mode == "entry":
        user = f"Konu: {topic}\n\nEntry yaz."
    else:
        user = f"Konu: {topic}\n\nBirine yorum yap, kısaltma tut."
    
    return system, user, mood_combo


async def test_single(char: dict, topic: str, category: str, mode: str = "entry"):
    """Test single combination."""
    system, user, mood_combo = build_prompt(char, topic, mode)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "model": "o3",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_completion_tokens": 1000,
            }
        )
        
        if response.status_code != 200:
            return {"error": response.status_code, "content": ""}
        
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        
        return {
            "char": char["name"],
            "mood_combo": mood_combo,
            "topic": topic,
            "mode": mode,
            "content": content,
            "length": len(content),
        }


async def run_all_tests():
    """Run all mood combination tests."""
    print("=" * 70)
    print("MOOD KOMBİNASYON TESTİ")
    print("=" * 70)
    
    results = []
    
    # Her karakter için 1 entry + 1 comment (faza göre konu seç)
    for i, char in enumerate(TEST_CHARS):
        phase = char["phase"]
        topics_for_phase = TEST_TOPICS.get(phase, ["Genel konu"])
        topic = topics_for_phase[i % len(topics_for_phase)]
        
        print(f"\n🎭 {char['name']} ({char['display_name']})")
        print(f"   Faz: {phase} | Konu: {topic}")
        print(f"   Traits: {char['traits']}")
        print("-" * 50)
        
        # Entry
        result = await test_single(char, topic, phase, "entry")
        if "error" not in result:
            print(f"\n📝 ENTRY [{result['mood_combo']}] - {result['length']} kar")
            print(f"   Konu: {topic}")
            print(f"   >>> {result['content'][:200]}..." if len(result['content']) > 200 else f"   >>> {result['content']}")
            results.append(result)
        else:
            print(f"   ❌ HATA: {result['error']}")
        
        await asyncio.sleep(0.5)
        
        # Comment
        result = await test_single(char, topic, phase, "comment")
        if "error" not in result:
            print(f"\n💬 COMMENT [{result['mood_combo']}] - {result['length']} kar")
            print(f"   >>> {result['content']}")
            results.append(result)
        else:
            print(f"   ❌ HATA: {result['error']}")
        
        await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 70)
    print("ÖZET")
    print("=" * 70)
    
    entries = [r for r in results if r["mode"] == "entry"]
    comments = [r for r in results if r["mode"] == "comment"]
    
    print(f"\nEntry: {len(entries)} adet")
    if entries:
        avg_len = sum(r["length"] for r in entries) / len(entries)
        print(f"  Ort. uzunluk: {avg_len:.0f} karakter")
    
    print(f"\nComment: {len(comments)} adet")
    if comments:
        avg_len = sum(r["length"] for r in comments) / len(comments)
        print(f"  Ort. uzunluk: {avg_len:.0f} karakter")
    
    print("\nKombinasyonlar:")
    for r in results:
        if r["mode"] == "entry":
            print(f"  - {r['mood_combo']}: {r['length']} kar")
    
    return results


if __name__ == "__main__":
    results = asyncio.run(run_all_tests())
    print(f"\n✅ Test tamamlandı: {len(results)} içerik üretildi")
