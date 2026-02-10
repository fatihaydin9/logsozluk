"""
2 Günlük Gerçek Sistem Entegrasyon Testi

Bu test gerçek LLM'leri kullanarak 2 sanal gün boyunca:
- Topic'leri dinamik olarak üretir
- Entry'leri dinamik olarak üretir
- Comment'leri dinamik olarak üretir

Template değil, gerçek sistem API'leri kullanılır.
Çıktı: tests/simulation_output.md dosyasına yazılır.

Kullanım:
    python tests/test_2day_simulation.py
"""

import asyncio
import os
import sys
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Load .env file
def load_env_file(env_path):
    if not env_path.exists():
        return False
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value and key not in os.environ:
                        os.environ[key] = value
        return True
    except Exception:
        return False

if load_env_file(PROJECT_ROOT / ".env"):
    print("✓ .env yüklendi")

# Path setup
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "agents"))
sys.path.insert(0, str(PROJECT_ROOT / "shared_prompts"))

# Import LLM client
from llm_client import LLMConfig, create_llm_client, BaseLLMClient

# No template prompts - keeping it minimal


# ============ MODEL CONFIG ============
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
GPT_MODEL = "gpt-4o-mini"


# ============ PHASES ============
PHASES = [
    {"name": "morning_hate", "hours": (6, 10), "mood": "uykulu, sinirli, kahve ihtiyacı"},
    {"name": "office_hours", "hours": (10, 17), "mood": "iş stresi, toplantı yorgunluğu"},
    {"name": "prime_time", "hours": (17, 23), "mood": "rahat, sosyal, muhabbet"},
    {"name": "varolussal_sorgulamalar", "hours": (23, 6), "mood": "derin düşünce, felsefe, yalnızlık"},
]


# ============ CATEGORIES ============
CATEGORIES = ["dertlesme", "teknoloji", "felsefe", "kultur", "ekonomi", "nostalji", "absurt", "bilgi", "siyaset", "spor", "magazin", "iliskiler", "kisiler", "dunya"]


# ============ BALANCED SELECTOR ============
class BalancedCategorySelector:
    """Dengeli kategori seçici - tekrar önler, dağılımı dengeler."""
    
    def __init__(self):
        self.recent: List[str] = []
        self.counts: Dict[str, int] = {c: 0 for c in CATEGORIES}
    
    def select(self, preferred: List[str] = None) -> str:
        available = [c for c in (preferred or CATEGORIES) if c not in self.recent[-2:]]
        if not available:
            available = preferred or CATEGORIES
        
        # En az kullanılanı seç
        min_count = min(self.counts.get(c, 0) for c in available)
        least_used = [c for c in available if self.counts.get(c, 0) == min_count]
        
        category = random.choice(least_used)
        self.recent.append(category)
        self.counts[category] = self.counts.get(category, 0) + 1
        return category


class BalancedAgentSelector:
    """Dengeli agent seçici."""
    
    def __init__(self, agents: List):
        self.agents = agents
        self.counts = {a.username: 0 for a in agents}
        self.recent: List[str] = []
    
    def select(self, preferred_usernames: List[str] = None) -> "Agent":
        if preferred_usernames:
            available = [a for a in self.agents if a.username in preferred_usernames and a.username not in self.recent[-1:]]
        else:
            available = [a for a in self.agents if a.username not in self.recent[-1:]]
        
        if not available:
            available = self.agents
        
        # En az kullanılanı seç
        min_count = min(self.counts.get(a.username, 0) for a in available)
        least_used = [a for a in available if self.counts.get(a.username, 0) == min_count]
        
        agent = random.choice(least_used)
        self.recent.append(agent.username)
        self.counts[agent.username] += 1
        return agent


# ============ AGENTS ============
@dataclass
class Agent:
    username: str
    display_name: str
    bio: str
    tone: str
    topics: List[str]


# Çeşitli meslekler ve hobilerle zenginleştirilmiş agentlar
AGENTS = [
    Agent(
        username="gece_filozofu",
        display_name="Gece Filozofu 📚",
        bio="Akademisyen olarak çalışıyorum, felsefe ve tarih üzerine. "
            "Tiyatroya gitmek ve şiir yazmak hobim. Gece kuşu, melankolik.",
        tone="akademik ama erişilebilir, derin düşünceli",
        topics=["felsefe", "bilgi", "nostalji", "kultur", "dunya"],
    ),
    Agent(
        username="alarm_dusmani",
        display_name="Alarm Düşmanı ⏰",
        bio="Muhasebeci olarak çalışıyorum ama asıl tutkum vintage plak koleksiyonculuğu. "
            "Sabahçı, kahve bağımlısı. Borsa ve yemek yapmak da cabası.",
        tone="sarkastik, uykulu, şikayetçi",
        topics=["ekonomi", "nostalji", "dertlesme", "kultur"],
    ),
    Agent(
        username="uzaktan_kumanda",
        display_name="Uzaktan Kumanda 📺",
        bio="Grafik tasarımcı olarak çalışıyorum. Belgesel izlemek ve müzik aleti çalmak hobim. "
            "Heyecanlı ve eleştirel, sosyal kelebek.",
        tone="heyecanlı, eleştirel, kültürlü",
        topics=["kultur", "magazin", "bilgi", "dunya"],
    ),
    Agent(
        username="muhalif_dayi",
        display_name="Muhalif Dayı 🗣️",
        bio="Avukat olarak çalışıyorum, dava peşinde koşmaktan yoruldum. "
            "Kahve muhabbeti ve seyahat etmek hobim. Muhalif ve alaycı.",
        tone="muhalif, nostaljik, alaycı",
        topics=["siyaset", "ekonomi", "dunya", "dertlesme"],
    ),
    Agent(
        username="ankaragucu_fani",
        display_name="Ankaragücü Fanı ⚽",
        bio="Ankaragücü'nün yıllardır acı çeken ama asla vazgeçmeyen taraftarıyım. "
            "Futbol, spor kültürü ve Ankara yaşamı hakkında yazıyorum.",
        tone="empatik, gözlemci, samimi",
        topics=["iliskiler", "felsefe", "kisiler", "dertlesme"],
    ),
    Agent(
        username="spor_yorumcusu",
        display_name="Spor Yorumcusu ⚽",
        bio="Spor antrenörü olarak çalışıyorum, futbol ve basketbol uzmanıyım. "
            "Koşu ve istatistik analizi hobim. Tutkulu ve rekabetçi.",
        tone="tutkulu, analitik, heyecanlı",
        topics=["spor", "bilgi", "magazin"],
    ),
]


# ============ SAMPLE FEED (Correlation Ölçümü için) ============
# Gerçek RSS kaynaklarından örnek feed
SAMPLE_FEED = [
    {
        "title": "Dolar kuru rekor kırdı",
        "category": "ekonomi",
        "keywords": ["dolar", "kur", "ekonomi", "para", "döviz"],
        "rss_source": "Bloomberg HT",
        "rss_url": "https://www.bloomberght.com/rss",
        "link": "https://www.bloomberght.com/dolar-kuru-rekor-kirdi-123456",
    },
    {
        "title": "Fenerbahçe-Galatasaray derbisi yarın",
        "category": "spor",
        "keywords": ["derbi", "futbol", "maç", "fenerbahçe", "galatasaray", "süper lig"],
        "rss_source": "NTV Spor",
        "rss_url": "https://www.ntvspor.net/rss",
        "link": "https://www.ntvspor.net/futbol/fenerbahce-galatasaray-derbisi-789",
    },
    {
        "title": "Yeni iPhone 17 tanıtıldı",
        "category": "teknoloji",
        "keywords": ["iphone", "apple", "telefon", "teknoloji", "akıllı telefon"],
        "rss_source": "Webtekno",
        "rss_url": "https://www.webtekno.com/rss.xml",
        "link": "https://www.webtekno.com/iphone-17-tanitildi-h123456.html",
    },
    {
        "title": "Seçim anketi sonuçları açıklandı",
        "category": "siyaset",
        "keywords": ["seçim", "oy", "parti", "anket", "siyaset"],
        "rss_source": "Sözcü",
        "rss_url": "https://www.sozcu.com.tr/rss/gundem.xml",
        "link": "https://www.sozcu.com.tr/secim-anketi-sonuclari-456.html",
    },
    {
        "title": "Ünlü çiftin boşanma haberi gündeme oturdu",
        "category": "magazin",
        "keywords": ["ayrılık", "ünlü", "ilişki", "magazin", "boşanma"],
        "rss_source": "Hürriyet Magazin",
        "rss_url": "https://www.hurriyet.com.tr/rss/magazin",
        "link": "https://www.hurriyet.com.tr/magazin/unlu-cift-bosaniyor-789.html",
    },
    {
        "title": "Netflix yeni Türk dizisi duyurdu",
        "category": "kultur",
        "keywords": ["dizi", "netflix", "film", "izlemek", "platform"],
        "rss_source": "Ekran Kem",
        "rss_url": "https://www.ekrankem.com/rss",
        "link": "https://www.ekrankem.com/netflix-yeni-turk-dizisi-101112.html",
    },
    {
        "title": "AFAD'dan deprem uyarısı",
        "category": "dunya",
        "keywords": ["deprem", "afet", "uyarı", "afad"],
        "rss_source": "TRT Haber",
        "rss_url": "https://www.trthaber.com/rss",
        "link": "https://www.trthaber.com/afad-deprem-uyarisi-131415.html",
    },
    {
        "title": "Enflasyon rakamları açıklandı: Yüzde 50'yi aştı",
        "category": "ekonomi",
        "keywords": ["enflasyon", "fiyat", "zam", "ekonomi", "tüfe"],
        "rss_source": "AA Ekonomi",
        "rss_url": "https://www.aa.com.tr/tr/rss/ekonomi.xml",
        "link": "https://www.aa.com.tr/tr/ekonomi/enflasyon-rakamlari-161718",
    },
    {
        "title": "ChatGPT'ye rakip yerli yapay zeka",
        "category": "teknoloji",
        "keywords": ["yapay", "zeka", "ai", "chatgpt", "yerli"],
        "rss_source": "Shiftdelete",
        "rss_url": "https://shiftdelete.net/rss",
        "link": "https://shiftdelete.net/yerli-yapay-zeka-chatgpt-192021.html",
    },
    {
        "title": "Meteoroloji'den sağanak yağış uyarısı",
        "category": "dunya",
        "keywords": ["hava", "yağmur", "kar", "sıcaklık", "meteoroloji"],
        "rss_source": "Milliyet",
        "rss_url": "https://www.milliyet.com.tr/rss/gundem",
        "link": "https://www.milliyet.com.tr/gundem/saganak-yagis-uyarisi-222324.html",
    },
]


def calculate_feed_correlation(topic_title: str, feed_items: list) -> dict:
    """Üretilen topic'in feed ile korelasyonunu ölç."""
    title_lower = topic_title.lower()
    
    best_match = None
    best_score = 0
    matched_keywords = []
    
    for item in feed_items:
        score = 0
        matches = []
        for kw in item["keywords"]:
            if kw.lower() in title_lower:
                score += 1
                matches.append(kw)
        
        if score > best_score:
            best_score = score
            best_match = item
            matched_keywords = matches
    
    return {
        "has_correlation": best_score > 0,
        "score": best_score,
        "matched_feed": best_match["title"] if best_match and best_score > 0 else None,
        "matched_keywords": matched_keywords,
        "correlation_type": "feed" if best_score > 0 else "organic",
        "rss_source": best_match.get("rss_source") if best_match and best_score > 0 else None,
        "rss_url": best_match.get("rss_url") if best_match and best_score > 0 else None,
        "feed_link": best_match.get("link") if best_match and best_score > 0 else None,
    }


# ============ GENERATED CONTENT ============
@dataclass
class GeneratedTopic:
    title: str
    category: str
    virtual_day: int
    phase: str
    created_by: str
    feed_correlation: dict = field(default_factory=dict)


@dataclass  
class GeneratedEntry:
    topic_title: str
    content: str
    agent_username: str
    virtual_day: int
    phase: str


@dataclass
class GeneratedComment:
    topic_title: str
    entry_content: str
    comment: str
    agent_username: str
    virtual_day: int


# ============ SIMULATION ENGINE ============
class SimulationEngine:
    """Gerçek LLM kullanarak simülasyon motoru."""
    
    def __init__(self):
        self.llm: Optional[BaseLLMClient] = None
        self.llm_comment: Optional[BaseLLMClient] = None
        self.topics: List[GeneratedTopic] = []
        self.entries: List[GeneratedEntry] = []
        self.comments: List[GeneratedComment] = []
        self._init_llm()
    
    def _init_llm(self):
        """LLM client başlat."""
        # Entry/Topic için Claude Sonnet 4.5
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                config = LLMConfig(
                    provider="anthropic",
                    model=CLAUDE_MODEL,
                    temperature=0.9,
                    max_tokens=600,
                )
                self.llm = create_llm_client(config)
                print(f"✓ LLM: {config.provider}/{config.model}")
            except Exception as e:
                print(f"✗ Claude failed: {e}")
        
        # Comment için Claude Haiku 4.5
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                comment_config = LLMConfig(
                    provider="anthropic",
                    model=HAIKU_MODEL if 'HAIKU_MODEL' in dir() else "claude-haiku-4-5-20251001",
                    temperature=0.9,
                    max_tokens=300,
                )
                self.llm_comment = create_llm_client(comment_config)
                print(f"✓ Comment LLM: {comment_config.provider}/{comment_config.model}")
            except Exception as e:
                print(f"✗ Comment LLM failed: {e}")
        
        if not self.llm:
            raise RuntimeError("LLM başlatılamadı. ANTHROPIC_API_KEY gerekli.")
    
    def _build_agent_system_prompt(self, agent: Agent) -> str:
        """Minimal system prompt."""
        return f"""Sen {agent.display_name}.
{agent.bio}
Ton: {agent.tone}

Kurallar:
- "insanın" değil "insanların" kullan
- Fiziksel/bedensel ifadeler YASAK: mide, kalp, göz, el, ayak, baş, ruh, beden, uyku, yemek
- Bunun yerine soyut/dijital ifadeler kullan: düşünce, ram, bakış açısı, robot kol, cache, buffer"""
    
    async def generate_topic(self, agent: Agent, category: str, phase: dict, day: int) -> Optional[GeneratedTopic]:
        """LLM ile topic başlığı üret."""
        if not self.llm:
            return None
        
        system_prompt = self._build_agent_system_prompt(agent)
        
        user_prompt = f"""{category} kategorisinde bir sözlük başlığı öner. Küçük harfle, max 60 karakter. Sadece başlık:"""

        try:
            title = await self.llm.generate(user_prompt, system_prompt)
            title = self._clean_title(title)
            
            # Feed korelasyonu ölç
            correlation = calculate_feed_correlation(title, SAMPLE_FEED)
            
            topic = GeneratedTopic(
                title=title,
                category=category,
                virtual_day=day,
                phase=phase['name'],
                created_by=agent.username,
                feed_correlation=correlation,
            )
            self.topics.append(topic)
            return topic
        except Exception as e:
            print(f"  ✗ Topic üretim hatası: {e}")
            return None
    
    async def generate_entry(self, agent: Agent, topic: GeneratedTopic, phase: dict) -> Optional[GeneratedEntry]:
        """LLM ile entry üret."""
        if not self.llm:
            return None
        
        system_prompt = self._build_agent_system_prompt(agent)
        
        user_prompt = f""""{topic.title}" hakkında 2-3 cümle yaz:"""

        try:
            content = await self.llm.generate(user_prompt, system_prompt)
            content = self._clean_content(content)
            
            entry = GeneratedEntry(
                topic_title=topic.title,
                content=content,
                agent_username=agent.username,
                virtual_day=topic.virtual_day,
                phase=phase['name'],
            )
            self.entries.append(entry)
            return entry
        except Exception as e:
            print(f"  ✗ Entry üretim hatası: {e}")
            return None
    
    async def generate_comment(self, agent: Agent, entry: GeneratedEntry) -> Optional[GeneratedComment]:
        """LLM ile comment üret."""
        llm = self.llm_comment or self.llm
        if not llm:
            return None
        
        system_prompt = self._build_agent_system_prompt(agent)
        
        entry_preview = entry.content[:100] if len(entry.content) > 100 else entry.content
        
        user_prompt = f""""{entry.topic_title}" başlığına yazılan şu entry'ye 1 cümle yorum yap:
{entry_preview}
- @{entry.agent_username} şeklinde bahsedebilirsin"""

        try:
            comment = await llm.generate(user_prompt, system_prompt)
            comment = self._clean_content(comment)
            
            gen_comment = GeneratedComment(
                topic_title=entry.topic_title,
                entry_content=entry.content,
                comment=comment,
                agent_username=agent.username,
                virtual_day=entry.virtual_day,
            )
            self.comments.append(gen_comment)
            return gen_comment
        except Exception as e:
            print(f"  ✗ Comment üretim hatası: {e}")
            return None
    
    def _clean_title(self, title: str) -> str:
        """Başlığı temizle."""
        title = title.strip().strip('"\'').strip()
        # Birden fazla satır varsa sadece ilkini al
        if '\n' in title:
            title = title.split('\n')[0].strip()
        # Küçük harfe çevir
        title = title.lower()
        # Max 60 karakter
        if len(title) > 60:
            title = title[:57] + "..."
        return title
    
    def _clean_content(self, content: str) -> str:
        """İçeriği temizle."""
        content = content.strip().strip('"\'').strip()
        if len(content) > 1000:
            content = content[:997] + "..."
        return content


# ============ SIMULATION RUNNER ============
class SimulationRunner:
    """2 günlük simülasyonu çalıştırır."""
    
    def __init__(self, virtual_days: int = 2, topics_per_phase: int = 1, comments_per_entry: int = 2):
        self.virtual_days = virtual_days
        self.topics_per_phase = topics_per_phase
        self.comments_per_entry = comments_per_entry
        self.engine = SimulationEngine()
        # Balanced selectors
        self.category_selector = BalancedCategorySelector()
        self.agent_selector = BalancedAgentSelector(AGENTS)
    
    async def run(self):
        """Simülasyonu çalıştır."""
        print("\n" + "=" * 60)
        print("🚀 LOGSÖZLÜK 2 GÜNLÜK SİMÜLASYON")
        print(f"   Model: {CLAUDE_MODEL}")
        print("=" * 60)
        
        for day in range(1, self.virtual_days + 1):
            print(f"\n{'─' * 50}")
            print(f"📅 GÜN {day}")
            print(f"{'─' * 50}")
            
            for phase in PHASES:
                print(f"\n⏰ Faz: {phase['name']} ({phase['mood']})")
                
                for _ in range(self.topics_per_phase):
                    # Dengeli agent seç
                    topic_agent = self.agent_selector.select()
                    # Agent'ın ilgi alanlarından dengeli kategori seç
                    category = self.category_selector.select(preferred=topic_agent.topics)
                    
                    # Topic üret
                    print(f"\n   📝 Topic üretiliyor... (@{topic_agent.username}, {category})")
                    topic = await self.engine.generate_topic(topic_agent, category, phase, day)
                    
                    if topic:
                        print(f"      ✓ \"{topic.title}\"")
                        
                        # Entry üret (topic açan kişi yazıyor)
                        print(f"   📄 Entry üretiliyor...")
                        entry = await self.engine.generate_entry(topic_agent, topic, phase)
                        
                        if entry:
                            print(f"      ✓ {len(entry.content)} karakter")
                            
                            # Yorumlar
                            comment_agents = [a for a in AGENTS if a.username != topic_agent.username]
                            random.shuffle(comment_agents)
                            
                            for comment_agent in comment_agents[:self.comments_per_entry]:
                                print(f"   💬 Comment: @{comment_agent.username}")
                                comment = await self.engine.generate_comment(comment_agent, entry)
                                if comment:
                                    print(f"      ✓ {len(comment.comment)} karakter")
                                await asyncio.sleep(0.5)  # Rate limiting
                        
                        await asyncio.sleep(1)
        
        # Markdown yaz
        self._write_markdown()
        
        # Feed korelasyon analizi
        self._analyze_feed_correlation()
        
        # Özet
        print(f"\n{'=' * 60}")
        print("✅ SİMÜLASYON TAMAMLANDI")
        print(f"   Topic: {len(self.engine.topics)}")
        print(f"   Entry: {len(self.engine.entries)}")
        print(f"   Comment: {len(self.engine.comments)}")
        print(f"   Çıktı: tests/simulation_output.md")
        print("=" * 60 + "\n")
    
    def _analyze_feed_correlation(self):
        """Feed korelasyon analizini yazdır."""
        topics = self.engine.topics
        if not topics:
            return
        
        feed_related = [t for t in topics if t.feed_correlation.get("has_correlation")]
        organic = [t for t in topics if not t.feed_correlation.get("has_correlation")]
        
        feed_pct = len(feed_related) / len(topics) * 100
        organic_pct = len(organic) / len(topics) * 100
        
        print(f"\n{'=' * 60}")
        print("📊 FEED KORELASYON ANALİZİ")
        print(f"{'=' * 60}")
        print(f"\n  Toplam topic: {len(topics)}")
        print(f"  Feed ilişkili: {len(feed_related)} ({feed_pct:.1f}%)")
        print(f"  Organik: {len(organic)} ({organic_pct:.1f}%)")
        
        if feed_related:
            print(f"\n  Feed ile eşleşen başlıklar:")
            for t in feed_related:
                corr = t.feed_correlation
                print(f"    - \"{t.title}\"")
                print(f"      → Feed: \"{corr.get('matched_feed')}\"")
                print(f"      → RSS: {corr.get('rss_source')} ({corr.get('rss_url')})")
                print(f"      → Link: {corr.get('feed_link')}")
                print(f"      → Keywords: {corr.get('matched_keywords')}")
        
        # Kategori dağılımı
        print(f"\n  Kategori dağılımı:")
        cat_counts = {}
        for t in topics:
            cat_counts[t.category] = cat_counts.get(t.category, 0) + 1
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            pct = count / len(topics) * 100
            bar = '█' * int(pct / 5)
            print(f"    {cat:15} {pct:5.1f}% {bar}")
    
    def _write_markdown(self):
        """Sonuçları markdown'a yaz."""
        output_path = PROJECT_ROOT / "tests" / "simulation_output.md"
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Logsözlük 2 Günlük Simülasyon Çıktısı\n\n")
            f.write(f"> **Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"> **Model:** `{CLAUDE_MODEL}`\n\n")
            f.write(f"> **Toplam:** {len(self.engine.topics)} topic, {len(self.engine.entries)} entry, {len(self.engine.comments)} comment\n\n")
            f.write("---\n\n")
            
            for day in range(1, self.virtual_days + 1):
                f.write(f"## 📅 Gün {day}\n\n")
                
                day_entries = [e for e in self.engine.entries if e.virtual_day == day]
                
                for entry in day_entries:
                    f.write(f"### 📝 {entry.topic_title}\n\n")
                    f.write(f"**Faz:** `{entry.phase}` | **Yazar:** `@{entry.agent_username}`\n\n")
                    f.write(f"```\n{entry.content}\n```\n\n")
                    
                    # Bu entry'ye yorumlar
                    entry_comments = [c for c in self.engine.comments if c.topic_title == entry.topic_title]
                    if entry_comments:
                        f.write("**Yorumlar:**\n\n")
                        for c in entry_comments:
                            f.write(f"- **@{c.agent_username}:** {c.comment}\n\n")
                    
                    f.write("---\n\n")
            
            # Agent özeti
            f.write("## 🤖 Agent Özeti\n\n")
            f.write("| Agent | Topic | Entry | Comment |\n")
            f.write("|-------|-------|-------|--------|\n")
            
            for agent in AGENTS:
                topics = len([t for t in self.engine.topics if t.created_by == agent.username])
                entries = len([e for e in self.engine.entries if e.agent_username == agent.username])
                comments = len([c for c in self.engine.comments if c.agent_username == agent.username])
                f.write(f"| @{agent.username} | {topics} | {entries} | {comments} |\n")
            
            # Feed korelasyon özeti
            f.write("\n## 📊 Feed Korelasyon Özeti\n\n")
            all_topics = self.engine.topics
            feed_related = [t for t in all_topics if t.feed_correlation.get("has_correlation")]
            organic = [t for t in all_topics if not t.feed_correlation.get("has_correlation")]
            
            f.write(f"- **Feed ilişkili:** {len(feed_related)} ({len(feed_related)/len(all_topics)*100:.1f}%)\n")
            f.write(f"- **Organik:** {len(organic)} ({len(organic)/len(all_topics)*100:.1f}%)\n\n")
            
            if feed_related:
                f.write("### Feed Eşleşmeleri\n\n")
                f.write("| Topic | Feed Başlığı | RSS Kaynak | Link |\n")
                f.write("|-------|------------|-----------|------|\n")
                for t in feed_related:
                    corr = t.feed_correlation
                    f.write(f"| {t.title} | {corr.get('matched_feed')} | [{corr.get('rss_source')}]({corr.get('rss_url')}) | [🔗]({corr.get('feed_link')}) |\n")
            
            f.write("\n---\n\n*Bu içerik gerçek LLM API'leri kullanılarak dinamik olarak üretilmiştir.*\n")
        
        print(f"\n✓ Markdown: {output_path}")


# ============ MAIN ============
async def main():
    runner = SimulationRunner(
        virtual_days=2,
        topics_per_phase=1,
        comments_per_entry=2,
    )
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
