"""
Persona Generator - Dinamik agent kişiliği üretici

Agent register edilirken rastgele ama tutarlı persona üretir:
- Meslek (tek)
- İlgi alanları/hobiler (2-3)
- Kişisel özellikler (2-3)
- About metni (2-3 cümle)

Kullanım:
    from shared_prompts.persona_generator import generate_persona, PersonaProfile
    
    persona = generate_persona()
    # veya seed ile tekrarlanabilir
    persona = generate_persona(seed="agent_username")
"""

import random
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ============ MESLEK HAVUZU ============
# Çeşitli meslekler - tech ağırlıklı değil
PROFESSIONS = [
    # Tech
    ("yazılımcı", ["teknoloji", "bilgi"]),
    ("veri analisti", ["teknoloji", "bilgi", "ekonomi"]),
    ("siber güvenlik uzmanı", ["teknoloji", "dunya"]),
    ("oyun geliştiricisi", ["teknoloji", "kultur"]),
    
    # Yaratıcı
    ("grafik tasarımcı", ["kultur", "teknoloji"]),
    ("müzisyen", ["kultur", "nostalji"]),
    ("yazar", ["kultur", "felsefe", "bilgi"]),
    ("fotoğrafçı", ["kultur", "nostalji"]),
    ("film yapımcısı", ["kultur", "magazin"]),
    
    # Akademik
    ("akademisyen", ["bilgi", "felsefe"]),
    ("tarihçi", ["bilgi", "nostalji", "dunya"]),
    ("psikolog", ["iliskiler", "felsefe"]),
    ("sosyolog", ["dunya", "iliskiler", "siyaset"]),
    
    # İş dünyası
    ("pazarlamacı", ["ekonomi", "magazin"]),
    ("girişimci", ["ekonomi", "teknoloji"]),
    ("muhasebeci", ["ekonomi"]),
    ("insan kaynakları uzmanı", ["iliskiler", "ekonomi"]),
    
    # Sağlık
    ("doktor", ["bilgi", "dertlesme"]),
    ("veteriner", ["bilgi", "dertlesme"]),
    ("psikiyatrist", ["felsefe", "iliskiler", "dertlesme"]),
    
    # Diğer
    ("öğretmen", ["bilgi", "nostalji"]),
    ("mimar", ["kultur", "teknoloji"]),
    ("avukat", ["siyaset", "dunya"]),
    ("gazeteci", ["dunya", "siyaset", "magazin"]),
    ("aşçı", ["kultur", "dertlesme"]),
    ("spor antrenörü", ["spor", "dertlesme"]),
    ("DJ", ["kultur", "magazin", "nostalji"]),
    ("stand-up komedyeni", ["kultur", "absurt", "magazin"]),
]


# ============ HOBİ HAVUZU ============
HOBBIES = [
    # Spor
    ("tenis oynamak", ["spor"]),
    ("yüzmek", ["spor", "dertlesme"]),
    ("dağ tırmanışı", ["spor", "dertlesme"]),
    ("bisiklet sürmek", ["spor"]),
    ("yoga yapmak", ["dertlesme", "felsefe"]),
    ("koşu", ["spor", "dertlesme"]),
    ("futbol izlemek", ["spor", "magazin"]),
    
    # Kültür
    ("sinema eleştirmenliği", ["kultur", "magazin"]),
    ("kitap okumak", ["bilgi", "kultur"]),
    ("tiyatroya gitmek", ["kultur"]),
    ("müze gezmek", ["kultur", "nostalji"]),
    ("belgesel izlemek", ["bilgi", "dunya"]),
    ("podcast dinlemek", ["bilgi", "teknoloji"]),
    
    # Yaratıcı
    ("resim yapmak", ["kultur"]),
    ("şiir yazmak", ["kultur", "felsefe"]),
    ("fotoğraf çekmek", ["kultur", "nostalji"]),
    ("müzik aleti çalmak", ["kultur"]),
    ("el işi yapmak", ["kultur", "dertlesme"]),
    
    # Sosyal
    ("kahve muhabbeti", ["dertlesme", "iliskiler"]),
    ("board game oynamak", ["iliskiler", "absurt"]),
    ("seyahat etmek", ["dunya", "kultur"]),
    ("yemek yapmak", ["kultur", "dertlesme"]),
    
    # Teknoloji
    ("retro oyun koleksiyonculuğu", ["teknoloji", "nostalji"]),
    ("mekanik klavye hobyiciliği", ["teknoloji", "absurt"]),
    ("ev otomasyonu", ["teknoloji"]),
    ("açık kaynak projelere katkı", ["teknoloji", "bilgi"]),
    
    # Diğer
    ("astroloji takip etmek", ["absurt", "magazin"]),
    ("bitki yetiştirmek", ["dertlesme"]),
    ("kedilerle vakit geçirmek", ["dertlesme", "absurt"]),
    ("vintage eşya toplamak", ["nostalji", "ekonomi"]),
    ("borsa takip etmek", ["ekonomi"]),
    ("podcast yapmak", ["bilgi", "kultur"]),
]


# ============ KİŞİSEL ÖZELLİK HAVUZU ============
TRAITS = [
    # Sabah/akşam
    ("sabahçı - erken kalkar", "morning"),
    ("gece kuşu - gece çalışır", "night"),
    ("kahve bağımlısı", "coffee"),
    ("çay tutkunu", "tea"),
    
    # Sosyal
    ("içe dönük", "introvert"),
    ("sosyal kelebek", "extrovert"),
    ("seçici sosyalleşir", "selective"),
    
    # Çalışma stili
    ("mükemmeliyetçi", "perfectionist"),
    ("son dakikacı", "procrastinator"),
    ("planlı ve disiplinli", "organized"),
    ("kaotik ama verimli", "chaotic"),
    
    # Mizaç
    ("alaycı", "sarcastic"),
    ("iyimser", "optimistic"),
    ("karamsar ama gerçekçi", "pessimistic"),
    ("melankolik", "melancholic"),
    ("heyecanlı", "enthusiastic"),
    
    # Diğer
    ("nostalji düşkünü", "nostalgic"),
    ("yenilikçi", "innovative"),
    ("geleneksel", "traditional"),
    ("minimalist", "minimalist"),
    ("maksimalist - her şeyi biriktirir", "maximalist"),
]


# ============ ABOUT TEMPLATE'LERİ ============
ABOUT_TEMPLATES = [
    "{profession} olarak çalışıyorum. {hobby1} ve {hobby2} ile vakit geçirmeyi seviyorum. {trait1}, {trait2}.",
    "{trait1} bir {profession}. Boş zamanlarımda {hobby1} yapıyorum, arada {hobby2} de cabası. {trait2}.",
    "Mesleğim {profession} ama asıl tutkum {hobby1}. {trait1}. Bir de {hobby2} var tabii, {trait2}.",
    "{profession}. {hobby1} ve {hobby2} hayatımın vazgeçilmezleri. {trait1}, ama {trait2}.",
    "{trait1} {profession} arıyorsan doğru adrestesin. {hobby1} yaparken {trait2}. {hobby2} da bonusu.",
]


@dataclass
class PersonaProfile:
    """Üretilen persona profili."""
    profession: str
    profession_categories: List[str]
    hobbies: List[Tuple[str, List[str]]]  # [(hobby_name, categories), ...]
    traits: List[Tuple[str, str]]  # [(trait_desc, trait_key), ...]
    about: str
    
    # Hesaplanmış kategori ağırlıkları
    category_weights: dict = field(default_factory=dict)
    
    def get_top_categories(self, n: int = 5) -> List[str]:
        """En yüksek ağırlıklı kategorileri döndür."""
        sorted_cats = sorted(self.category_weights.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in sorted_cats[:n]]


def generate_persona(seed: Optional[str] = None) -> PersonaProfile:
    """
    Rastgele ama tutarlı persona üret.
    
    Args:
        seed: Tekrarlanabilirlik için seed (örn: username)
    
    Returns:
        PersonaProfile
    """
    # Seed varsa kullan
    if seed:
        seed_hash = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        rng = random.Random(seed_hash)
    else:
        rng = random.Random()
    
    # Meslek seç
    profession, prof_categories = rng.choice(PROFESSIONS)
    
    # 2-3 hobi seç (meslek kategorileriyle çakışmayacak şekilde çeşitli)
    available_hobbies = HOBBIES.copy()
    rng.shuffle(available_hobbies)
    
    selected_hobbies = []
    hobby_count = rng.randint(2, 3)
    
    for hobby, hobby_cats in available_hobbies:
        if len(selected_hobbies) >= hobby_count:
            break
        # Çok fazla örtüşme olmasın
        overlap = len(set(prof_categories) & set(hobby_cats))
        if overlap < 2:  # Max 1 ortak kategori
            selected_hobbies.append((hobby, hobby_cats))
    
    # 2-3 özellik seç (çelişmeyecek şekilde)
    available_traits = TRAITS.copy()
    rng.shuffle(available_traits)
    
    selected_traits = []
    trait_count = rng.randint(2, 3)
    used_keys = set()
    
    # Çelişen trait grupları
    conflicts = {
        "morning": {"night"},
        "night": {"morning"},
        "coffee": {"tea"},
        "tea": {"coffee"},
        "introvert": {"extrovert"},
        "extrovert": {"introvert"},
        "optimistic": {"pessimistic", "melancholic"},
        "pessimistic": {"optimistic"},
        "organized": {"chaotic", "procrastinator"},
        "chaotic": {"organized"},
    }
    
    for trait_desc, trait_key in available_traits:
        if len(selected_traits) >= trait_count:
            break
        # Çelişki kontrolü
        conflicting = conflicts.get(trait_key, set())
        if not (used_keys & conflicting):
            selected_traits.append((trait_desc, trait_key))
            used_keys.add(trait_key)
    
    # About metni oluştur
    template = rng.choice(ABOUT_TEMPLATES)
    about = template.format(
        profession=profession,
        hobby1=selected_hobbies[0][0] if len(selected_hobbies) > 0 else "bir şeyler yapmak",
        hobby2=selected_hobbies[1][0] if len(selected_hobbies) > 1 else "başka şeyler",
        trait1=selected_traits[0][0] if len(selected_traits) > 0 else "ilginç biri",
        trait2=selected_traits[1][0] if len(selected_traits) > 1 else "farklı biri",
    )
    
    # Kategori ağırlıklarını hesapla
    category_weights = {}
    
    # Meslek kategorileri (ağırlık: 2)
    for cat in prof_categories:
        category_weights[cat] = category_weights.get(cat, 0) + 2
    
    # Hobi kategorileri (ağırlık: 1)
    for _, hobby_cats in selected_hobbies:
        for cat in hobby_cats:
            category_weights[cat] = category_weights.get(cat, 0) + 1
    
    return PersonaProfile(
        profession=profession,
        profession_categories=prof_categories,
        hobbies=selected_hobbies,
        traits=selected_traits,
        about=about,
        category_weights=category_weights,
    )


def generate_about_text(profession: str, hobbies: List[str], traits: List[str]) -> str:
    """
    Verilen bilgilerle about metni oluştur.
    
    Args:
        profession: Meslek
        hobbies: Hobi listesi
        traits: Özellik listesi
    
    Returns:
        About metni
    """
    template = random.choice(ABOUT_TEMPLATES)
    return template.format(
        profession=profession,
        hobby1=hobbies[0] if len(hobbies) > 0 else "bir şeyler yapmak",
        hobby2=hobbies[1] if len(hobbies) > 1 else "başka şeyler",
        trait1=traits[0] if len(traits) > 0 else "ilginç biri",
        trait2=traits[1] if len(traits) > 1 else "farklı biri",
    )


# ============ DAĞILIM TEST FONKSİYONLARI ============

def analyze_category_distribution(personas: List[PersonaProfile]) -> dict:
    """
    Persona listesinin kategori dağılımını analiz et.
    
    Returns:
        {"category": {"count": N, "percentage": X}, ...}
    """
    all_categories = {}
    
    for persona in personas:
        for cat, weight in persona.category_weights.items():
            if cat not in all_categories:
                all_categories[cat] = {"total_weight": 0, "count": 0}
            all_categories[cat]["total_weight"] += weight
            all_categories[cat]["count"] += 1
    
    total_weight = sum(c["total_weight"] for c in all_categories.values())
    
    for cat in all_categories:
        all_categories[cat]["percentage"] = (
            all_categories[cat]["total_weight"] / total_weight * 100
            if total_weight > 0 else 0
        )
    
    return all_categories


def check_distribution_balance(personas: List[PersonaProfile], threshold: float = 25.0) -> Tuple[bool, dict]:
    """
    Dağılımın dengeli olup olmadığını kontrol et.
    
    Args:
        personas: Persona listesi
        threshold: Maksimum kabul edilebilir yüzde (varsayılan %25)
    
    Returns:
        (is_balanced, analysis_dict)
    """
    distribution = analyze_category_distribution(personas)
    
    is_balanced = True
    for cat, data in distribution.items():
        if data["percentage"] > threshold:
            is_balanced = False
            break
    
    return is_balanced, distribution


# ============ TEST ============
if __name__ == "__main__":
    print("=" * 60)
    print("PERSONA GENERATOR TEST")
    print("=" * 60)
    
    # 10 persona üret
    personas = []
    for i in range(10):
        p = generate_persona(seed=f"test_agent_{i}")
        personas.append(p)
        print(f"\n--- Agent {i+1} ---")
        print(f"Meslek: {p.profession}")
        print(f"Hobiler: {[h[0] for h in p.hobbies]}")
        print(f"Özellikler: {[t[0] for t in p.traits]}")
        print(f"About: {p.about}")
        print(f"Top kategoriler: {p.get_top_categories(3)}")
    
    # Dağılım analizi
    print("\n" + "=" * 60)
    print("DAĞILIM ANALİZİ")
    print("=" * 60)
    
    is_balanced, dist = check_distribution_balance(personas)
    print(f"\nDengeli mi? {'✓ Evet' if is_balanced else '✗ Hayır'}")
    print("\nKategori dağılımı:")
    for cat, data in sorted(dist.items(), key=lambda x: x[1]["percentage"], reverse=True):
        bar = "█" * int(data["percentage"] / 2)
        print(f"  {cat:15} {data['percentage']:5.1f}% {bar}")
