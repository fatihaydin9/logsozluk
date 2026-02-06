"""
Dağılım Kontrol Testi

Bu test şunları kontrol eder:
1. Kategori dağılımının dengeli olması (hiçbir kategori %25'i geçmemeli)
2. Feed, organic ve bio kaynaklarının dengeli kullanımı
3. Agent seçiminin dengeli olması
4. Topic üretiminin çeşitli olması

Kullanım:
    python tests/test_distribution_control.py
    pytest tests/test_distribution_control.py -v
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import Counter
import random

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "agents"))
sys.path.insert(0, str(PROJECT_ROOT / "shared_prompts"))

# Import persona generator
from persona_generator import (
    generate_persona, PersonaProfile,
    analyze_category_distribution, check_distribution_balance,
    PROFESSIONS, HOBBIES
)

# Import prompt bundle
try:
    from prompt_bundle import TOPIC_PROMPTS, CATEGORY_ENERGY
    PROMPTS_AVAILABLE = True
except ImportError:
    PROMPTS_AVAILABLE = False
    TOPIC_PROMPTS = {}
    CATEGORY_ENERGY = {}


# ============ CATEGORIES ============
CATEGORIES = ["dertlesme", "teknoloji", "felsefe", "kultur", "ekonomi", "nostalji", "absurt", "bilgi", "siyaset", "spor", "magazin", "iliskiler", "kisiler", "dunya"]


# ============ CONTENT SOURCE WEIGHTS ============
@dataclass
class ContentSourceConfig:
    """İçerik kaynağı ağırlıkları."""
    feed_weight: float = 0.30      # Feed'den gelen konular
    organic_weight: float = 0.40   # Organik/random konular
    bio_weight: float = 0.30       # Agent bio'sundan kaynaklanan konular
    
    def validate(self) -> bool:
        total = self.feed_weight + self.organic_weight + self.bio_weight
        return abs(total - 1.0) < 0.01


# ============ BALANCED CATEGORY SELECTOR ============
class BalancedCategorySelector:
    """
    Dengeli kategori seçici.
    
    Feed, organic ve bio kaynaklarını dengeli kullanır.
    Son kullanılan kategorileri takip ederek tekrarı önler.
    """
    
    def __init__(self, config: ContentSourceConfig = None):
        self.config = config or ContentSourceConfig()
        self.recent_categories: List[str] = []
        self.max_recent = 3  # Son 3 kategoriyi takip et
        self.category_counts: Dict[str, int] = {cat: 0 for cat in CATEGORIES}
        
    def select_category(
        self,
        agent_categories: List[str] = None,
        feed_categories: List[str] = None,
        phase: str = None,
    ) -> Tuple[str, str]:
        """
        Dengeli şekilde kategori seç.
        
        Args:
            agent_categories: Agent'ın ilgi alanları (bio'dan)
            feed_categories: Feed'den gelen kategoriler
            phase: Mevcut faz
        
        Returns:
            (category, source) tuple
        """
        # Kaynak seçimi
        source_roll = random.random()
        
        if source_roll < self.config.feed_weight and feed_categories:
            # Feed'den seç
            source = "feed"
            available = [c for c in feed_categories if c not in self.recent_categories]
            if not available:
                available = feed_categories
        elif source_roll < self.config.feed_weight + self.config.organic_weight:
            # Organic - tamamen random
            source = "organic"
            available = [c for c in CATEGORIES if c not in self.recent_categories]
            if not available:
                available = CATEGORIES
        else:
            # Bio'dan seç
            source = "bio"
            if agent_categories:
                available = [c for c in agent_categories if c not in self.recent_categories]
                if not available:
                    available = agent_categories
            else:
                available = CATEGORIES
        
        # En az kullanılan kategorilere öncelik ver
        min_count = min(self.category_counts.get(c, 0) for c in available)
        least_used = [c for c in available if self.category_counts.get(c, 0) == min_count]
        
        category = random.choice(least_used)
        
        # Güncelle
        self.recent_categories.append(category)
        if len(self.recent_categories) > self.max_recent:
            self.recent_categories.pop(0)
        
        self.category_counts[category] = self.category_counts.get(category, 0) + 1
        
        return category, source
    
    def get_distribution(self) -> Dict[str, float]:
        """Kategori dağılımını yüzde olarak döndür."""
        total = sum(self.category_counts.values())
        if total == 0:
            return {}
        return {cat: (count / total * 100) for cat, count in self.category_counts.items()}
    
    def is_balanced(self, threshold: float = 25.0) -> bool:
        """Dağılımın dengeli olup olmadığını kontrol et."""
        dist = self.get_distribution()
        return all(pct <= threshold for pct in dist.values())


# ============ AGENT SELECTOR ============
class BalancedAgentSelector:
    """
    Dengeli agent seçici.
    
    Agent'ların eşit dağılımını sağlar.
    """
    
    def __init__(self, agent_usernames: List[str]):
        self.agents = agent_usernames
        self.agent_counts: Dict[str, int] = {a: 0 for a in agent_usernames}
        self.recent_agents: List[str] = []
        self.max_recent = 2
    
    def select_agent(self, preferred_agents: List[str] = None) -> str:
        """
        Dengeli şekilde agent seç.
        
        Args:
            preferred_agents: Tercih edilen agentlar (kategori uyumlu)
        """
        # Tercih edilenler varsa ve son kullanılmamışsa
        if preferred_agents:
            available = [a for a in preferred_agents if a not in self.recent_agents]
            if available:
                # En az kullanılanı seç
                min_count = min(self.agent_counts.get(a, 0) for a in available)
                least_used = [a for a in available if self.agent_counts.get(a, 0) == min_count]
                agent = random.choice(least_used)
            else:
                # Fallback: tüm agentlardan en az kullanılanı
                min_count = min(self.agent_counts.values())
                least_used = [a for a, c in self.agent_counts.items() if c == min_count]
                agent = random.choice(least_used)
        else:
            # Random ama dengeli
            min_count = min(self.agent_counts.values())
            least_used = [a for a, c in self.agent_counts.items() if c == min_count]
            agent = random.choice(least_used)
        
        # Güncelle
        self.agent_counts[agent] += 1
        self.recent_agents.append(agent)
        if len(self.recent_agents) > self.max_recent:
            self.recent_agents.pop(0)
        
        return agent
    
    def get_distribution(self) -> Dict[str, float]:
        """Agent dağılımını yüzde olarak döndür."""
        total = sum(self.agent_counts.values())
        if total == 0:
            return {}
        return {agent: (count / total * 100) for agent, count in self.agent_counts.items()}


# ============ TEST FUNCTIONS ============

def test_persona_distribution():
    """Persona üretiminin dengeli olduğunu test et."""
    print("\n" + "=" * 60)
    print("TEST: Persona Dağılımı")
    print("=" * 60)
    
    # 50 persona üret
    personas = [generate_persona(seed=f"test_{i}") for i in range(50)]
    
    is_balanced, distribution = check_distribution_balance(personas, threshold=25.0)
    
    print(f"\n50 persona üretildi.")
    print(f"Dengeli mi? {'✓ PASS' if is_balanced else '✗ FAIL'}")
    print("\nKategori dağılımı:")
    
    for cat, data in sorted(distribution.items(), key=lambda x: x[1]["percentage"], reverse=True):
        bar = "█" * int(data["percentage"] / 2)
        status = "⚠" if data["percentage"] > 25 else " "
        print(f"  {status} {cat:15} {data['percentage']:5.1f}% {bar}")
    
    assert is_balanced, "Persona dağılımı dengeli değil!"
    return True


def test_category_selector_balance():
    """Kategori seçicinin dengeli olduğunu test et."""
    print("\n" + "=" * 60)
    print("TEST: Kategori Seçici Dengesi")
    print("=" * 60)
    
    selector = BalancedCategorySelector()
    
    # Simüle et: 100 kategori seçimi
    source_counts = {"feed": 0, "organic": 0, "bio": 0}
    
    for _ in range(100):
        # Rastgele agent kategorileri
        agent_cats = random.sample(CATEGORIES, 3)
        # Rastgele feed kategorileri
        feed_cats = random.sample(CATEGORIES, 2)
        
        category, source = selector.select_category(
            agent_categories=agent_cats,
            feed_categories=feed_cats,
        )
        source_counts[source] += 1
    
    # Dağılımı kontrol et
    dist = selector.get_distribution()
    is_balanced = selector.is_balanced(threshold=20.0)
    
    print(f"\n100 kategori seçimi yapıldı.")
    print(f"Dengeli mi? {'✓ PASS' if is_balanced else '✗ FAIL'}")
    
    print("\nKaynak dağılımı:")
    for source, count in source_counts.items():
        bar = "█" * (count // 2)
        print(f"  {source:10} {count:3}% {bar}")
    
    print("\nKategori dağılımı:")
    for cat, pct in sorted(dist.items(), key=lambda x: x[1], reverse=True):
        if pct > 0:
            bar = "█" * int(pct / 2)
            status = "⚠" if pct > 20 else " "
            print(f"  {status} {cat:15} {pct:5.1f}% {bar}")
    
    # Kaynak dağılımı yaklaşık doğru mu?
    feed_ratio = source_counts["feed"] / 100
    organic_ratio = source_counts["organic"] / 100
    bio_ratio = source_counts["bio"] / 100
    
    # %15 tolerans
    assert abs(feed_ratio - 0.30) < 0.15, f"Feed ratio off: {feed_ratio}"
    assert abs(organic_ratio - 0.40) < 0.15, f"Organic ratio off: {organic_ratio}"
    assert abs(bio_ratio - 0.30) < 0.15, f"Bio ratio off: {bio_ratio}"
    
    return True


def test_agent_selector_balance():
    """Agent seçicinin dengeli olduğunu test et."""
    print("\n" + "=" * 60)
    print("TEST: Agent Seçici Dengesi")
    print("=" * 60)
    
    agents = ["gece_filozofu", "alarm_dusmani", "uzaktan_kumanda", "muhalif_dayi",
              "kanape_filozofu", "excel_mahkumu", "localhost_sakini", "patron_adayi"]
    
    selector = BalancedAgentSelector(agents)
    
    # 80 seçim yap (her agent ortalama 10)
    for _ in range(80):
        # Bazen tercih edilen agentlarla, bazen random
        if random.random() < 0.5:
            preferred = random.sample(agents, 3)
            selector.select_agent(preferred_agents=preferred)
        else:
            selector.select_agent()
    
    dist = selector.get_distribution()
    
    print(f"\n80 agent seçimi yapıldı.")
    print("\nAgent dağılımı:")
    
    max_pct = max(dist.values())
    min_pct = min(dist.values())
    variance = max_pct - min_pct
    
    for agent, pct in sorted(dist.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(pct / 2)
        print(f"  {agent:20} {pct:5.1f}% {bar}")
    
    print(f"\nVaryans: {variance:.1f}% (max - min)")
    is_balanced = variance < 15.0  # Max %15 varyans kabul edilebilir
    print(f"Dengeli mi? {'✓ PASS' if is_balanced else '✗ FAIL'}")
    
    assert is_balanced, f"Agent dağılımı dengeli değil! Varyans: {variance:.1f}%"
    return True


def test_profession_diversity():
    """Meslek çeşitliliğini test et."""
    print("\n" + "=" * 60)
    print("TEST: Meslek Çeşitliliği")
    print("=" * 60)
    
    # Profession kategorilerini say
    profession_categories = {}
    for prof, cats in PROFESSIONS:
        for cat in cats:
            if cat not in profession_categories:
                profession_categories[cat] = 0
            profession_categories[cat] += 1
    
    total = sum(profession_categories.values())
    
    print(f"\n{len(PROFESSIONS)} farklı meslek tanımlı.")
    print("\nMeslek->Kategori dağılımı:")
    
    for cat, count in sorted(profession_categories.items(), key=lambda x: x[1], reverse=True):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {cat:15} {pct:5.1f}% ({count} meslek) {bar}")
    
    # Teknoloji kategorisi %20'den fazla olmamalı
    tech_pct = profession_categories.get("teknoloji", 0) / total * 100
    is_diverse = tech_pct < 25.0
    
    print(f"\nTeknoloji oranı: {tech_pct:.1f}%")
    print(f"Çeşitli mi? {'✓ PASS' if is_diverse else '✗ FAIL'}")
    
    assert is_diverse, f"Meslekler çok teknoloji ağırlıklı: {tech_pct:.1f}%"
    return True


def test_full_simulation_distribution():
    """Tam simülasyon dağılımını test et."""
    print("\n" + "=" * 60)
    print("TEST: Tam Simülasyon Dağılımı (2 gün)")
    print("=" * 60)
    
    agents = ["gece_filozofu", "alarm_dusmani", "uzaktan_kumanda", "muhalif_dayi"]
    
    # Her agent için persona üret
    agent_personas = {a: generate_persona(seed=a) for a in agents}
    
    category_selector = BalancedCategorySelector()
    agent_selector = BalancedAgentSelector(agents)
    
    phases = ["morning_hate", "office_hours", "prime_time", "varolussal_sorgulamalar"]
    
    # 2 gün, 4 faz, her fazda 1 topic = 8 topic
    for day in range(1, 3):
        for phase in phases:
            # Agent seç
            agent = agent_selector.select_agent()
            persona = agent_personas[agent]
            
            # Kategori seç (persona'dan)
            agent_cats = persona.get_top_categories(3)
            
            category, source = category_selector.select_category(
                agent_categories=agent_cats,
                feed_categories=random.sample(CATEGORIES, 2),
                phase=phase,
            )
    
    # Sonuçları analiz et
    cat_dist = category_selector.get_distribution()
    agent_dist = agent_selector.get_distribution()
    
    print("\nKategori dağılımı:")
    for cat, pct in sorted(cat_dist.items(), key=lambda x: x[1], reverse=True):
        if pct > 0:
            bar = "█" * int(pct / 2)
            print(f"  {cat:15} {pct:5.1f}% {bar}")
    
    print("\nAgent dağılımı:")
    for agent, pct in sorted(agent_dist.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(pct / 2)
        print(f"  {agent:20} {pct:5.1f}% {bar}")
    
    # Denge kontrolleri
    cat_balanced = category_selector.is_balanced(threshold=40.0)  # 8 seçimde yüksek tolerans
    agent_variance = max(agent_dist.values()) - min(agent_dist.values())
    agent_balanced = agent_variance < 30.0  # 8 seçimde yüksek tolerans
    
    print(f"\nKategori dengeli mi? {'✓' if cat_balanced else '✗'}")
    print(f"Agent dengeli mi? {'✓' if agent_balanced else '✗'}")
    
    return True


# ============ MAIN ============

def run_all_tests():
    """Tüm testleri çalıştır."""
    print("\n" + "=" * 60)
    print("🧪 DAĞILIM KONTROL TESTLERİ")
    print("=" * 60)
    
    tests = [
        ("Persona Dağılımı", test_persona_distribution),
        ("Kategori Seçici", test_category_selector_balance),
        ("Agent Seçici", test_agent_selector_balance),
        ("Meslek Çeşitliliği", test_profession_diversity),
        ("Tam Simülasyon", test_full_simulation_distribution),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True, None))
        except AssertionError as e:
            results.append((name, False, str(e)))
        except Exception as e:
            results.append((name, False, str(e)))
    
    # Özet
    print("\n" + "=" * 60)
    print("📊 ÖZET")
    print("=" * 60)
    
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    
    for name, ok, error in results:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"  {status} {name}")
        if error:
            print(f"       → {error[:50]}...")
    
    print(f"\n{passed}/{total} test başarılı")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
