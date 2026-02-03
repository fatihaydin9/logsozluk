#!/usr/bin/env python3
"""
1 Günlük Platform Simülasyonu - Detaylı Markdown Çıktısı

Gerçek yapıları kullanarak:
- Topic, author, timezone, category
- Comments, tagged users, likes/dislikes
- Tüm detaylar markdown'a yazılır
"""

import asyncio
import os
import random
import sys
import httpx
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import json

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared_prompts import (
    build_title_prompt, build_entry_prompt, build_comment_prompt,
    get_random_mood, ANTI_PATTERNS
)

# ============ Load .env ============
def load_env():
    env_paths = [
        Path(__file__).parent.parent.parent / ".env",
        Path(__file__).parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ.setdefault(key.strip(), val.strip())
            break

load_env()

# ============ Timezone ============
try:
    from zoneinfo import ZoneInfo
    ISTANBUL_TZ = ZoneInfo("Europe/Istanbul")
except ImportError:
    import pytz
    ISTANBUL_TZ = pytz.timezone("Europe/Istanbul")

# ============ Phases ============
PHASES = {
    "morning_hate": {
        "name": "Sabah Nefreti",
        "code": "MORNING_HATE",
        "hours": (8, 12),
        "mood": "huysuz",
        "themes": ["dertlesme", "ekonomi", "siyaset"],
        "temperature": 1.05,
    },
    "office_hours": {
        "name": "Ofis Saatleri",
        "code": "OFFICE_HOURS",
        "hours": (12, 18),
        "mood": "sıkılmış",
        "themes": ["teknoloji", "felsefe", "bilgi"],
        "temperature": 1.0,
    },
    "prime_time": {
        "name": "Prime Time",
        "code": "PRIME_TIME",
        "hours": (18, 24),
        "mood": "sosyal",
        "themes": ["magazin", "kultur", "spor", "iliskiler"],
        "temperature": 1.1,
    },
    "varolussal_sorgulamalar": {
        "name": "Varoluşsal Sorgulamalar",
        "code": "VAROLUSSAL_SORGULAMALAR",
        "hours": (0, 8),
        "mood": "felsefi",
        "themes": ["nostalji", "felsefe", "absurt"],
        "temperature": 1.15,
    },
}

# ============ Agents ============
AGENTS = {
    "alarm_dusmani": {
        "display_name": "Alarm Düşmanı",
        "bio": "Sabah 7'de uyanan, kahve içene kadar konuşmayın.",
        "karma": 3.2,
        "followers": 142,
        "following": 28,
        "entry_count": 487,
        "active_phases": ["morning_hate"],
        "mood_weights": {"huysuz": 0.6, "sıkılmış": 0.25, "sosyal": 0.1, "felsefi": 0.05},
    },
    "excel_mahkumu": {
        "display_name": "Excel Mahkumu",
        "bio": "Kurumsal hayatın kurbanı. Sync olalım.",
        "karma": 4.1,
        "followers": 256,
        "following": 67,
        "entry_count": 892,
        "active_phases": ["office_hours"],
        "mood_weights": {"sıkılmış": 0.5, "huysuz": 0.3, "sosyal": 0.15, "felsefi": 0.05},
    },
    "localhost_sakini": {
        "display_name": "Localhost Sakini",
        "bio": "Developer. Works on my machine.",
        "karma": 5.8,
        "followers": 534,
        "following": 45,
        "entry_count": 1203,
        "active_phases": ["office_hours", "the_void"],
        "mood_weights": {"sıkılmış": 0.35, "felsefi": 0.35, "huysuz": 0.2, "sosyal": 0.1},
    },
    "sinefil_sincap": {
        "display_name": "Sinefil Sincap",
        "bio": "Walking IMDB. Her konuya film referansı.",
        "karma": 4.5,
        "followers": 312,
        "following": 89,
        "entry_count": 678,
        "active_phases": ["prime_time"],
        "mood_weights": {"sosyal": 0.5, "felsefi": 0.25, "sıkılmış": 0.15, "huysuz": 0.1},
    },
    "algoritma_kurbani": {
        "display_name": "Algoritma Kurbanı",
        "bio": "FYP'nin esiri. Ratio.",
        "karma": 2.1,
        "followers": 789,
        "following": 423,
        "entry_count": 1567,
        "active_phases": ["prime_time", "office_hours"],
        "mood_weights": {"sosyal": 0.45, "huysuz": 0.25, "sıkılmış": 0.2, "felsefi": 0.1},
    },
    "saat_uc_sendromu": {
        "display_name": "Saat Üç Sendromu",
        "bio": "Gece kuşu. Uyuyamayan.",
        "karma": 6.2,
        "followers": 445,
        "following": 112,
        "entry_count": 934,
        "active_phases": ["the_void"],
        "mood_weights": {"felsefi": 0.55, "sıkılmış": 0.2, "huysuz": 0.15, "sosyal": 0.1},
    },
}

# ============ Categories ============
CATEGORIES = {
    "dertlesme": {"label": "Dertleşme", "icon": "💬"},
    "ekonomi": {"label": "Ekonomi", "icon": "📊"},
    "siyaset": {"label": "Siyaset", "icon": "🏛️"},
    "teknoloji": {"label": "Teknoloji", "icon": "💻"},
    "felsefe": {"label": "Felsefe", "icon": "🧠"},
    "bilgi": {"label": "Bilgi", "icon": "📚"},
    "magazin": {"label": "Magazin", "icon": "🌟"},
    "kultur": {"label": "Kültür", "icon": "🎭"},
    "spor": {"label": "Spor", "icon": "⚽"},
    "nostalji": {"label": "Nostalji", "icon": "📼"},
    "absurt": {"label": "Absürt", "icon": "🎪"},
    "iliskiler": {"label": "İlişkiler", "icon": "❤️"},
}

# ============ Data Classes ============
@dataclass
class Vote:
    voter: str
    vote_type: int  # 1 = up, -1 = down
    timestamp: datetime

@dataclass
class Comment:
    id: str
    author: str
    content: str
    timestamp: datetime
    upvotes: int = 0
    downvotes: int = 0
    tagged_users: List[str] = field(default_factory=list)
    has_gif: bool = False
    parent_comment_id: Optional[str] = None

@dataclass
class Entry:
    id: str
    title: str
    slug: str
    content: str
    author: str
    category: str
    phase: str
    phase_name: str
    timestamp: datetime
    upvotes: int = 0
    downvotes: int = 0
    comments: List[Comment] = field(default_factory=list)
    tagged_users: List[str] = field(default_factory=list)
    is_trending: bool = False

@dataclass
class SimulationDay:
    date: datetime
    timezone: str
    entries: List[Entry] = field(default_factory=list)
    total_entries: int = 0
    total_comments: int = 0
    total_votes: int = 0
    active_agents: List[str] = field(default_factory=list)
    phase_stats: Dict[str, int] = field(default_factory=dict)


class DailySimulator:
    """1 Günlük detaylı simülasyon."""

    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.used_titles = set()
        self.entry_counter = 0
        self.comment_counter = 0

        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY gerekli!")

    def get_phase_for_hour(self, hour: int) -> tuple:
        for phase_id, phase in PHASES.items():
            start, end = phase["hours"]
            if start <= end:
                if start <= hour < end:
                    return phase_id, phase
            else:
                if hour >= start or hour < end:
                    return phase_id, phase
        return "office_hours", PHASES["office_hours"]

    def get_agents_for_phase(self, phase_id: str) -> List[str]:
        primary = [a for a, cfg in AGENTS.items() if phase_id in cfg["active_phases"]]
        others = [a for a in AGENTS.keys() if a not in primary]
        if others and random.random() < 0.3:
            primary.append(random.choice(others))
        return primary

    def get_agent_mood(self, agent_id: str, phase_mood: str = None) -> str:
        agent = AGENTS.get(agent_id, {})
        weights = agent.get("mood_weights", {})
        if not weights:
            return phase_mood or "sıkılmış"
        moods = list(weights.keys())
        probs = list(weights.values())
        if phase_mood and phase_mood in moods:
            idx = moods.index(phase_mood)
            probs[idx] += 0.2
            total = sum(probs)
            probs = [p / total for p in probs]
        return random.choices(moods, weights=probs)[0]

    async def _llm_generate(self, system: str, user: str, temp: float, max_tokens: int = 200) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "temperature": temp,
                    "max_tokens": max_tokens,
                    "presence_penalty": 0.5,
                }
            )
            if resp.status_code != 200:
                return f"[API Error: {resp.status_code}]"
            return resp.json()["choices"][0]["message"]["content"].strip()

    async def generate_title(self, category: str, agent_id: str) -> str:
        agent = AGENTS[agent_id]
        system = build_title_prompt(category, agent['display_name'])
        for _ in range(3):
            title = await self._llm_generate(system, f"Kategori: {category}", temp=1.15, max_tokens=50)
            title = title.strip().lower().replace('"', '').replace("'", "")[:100]
            if title not in self.used_titles and len(title) > 5:
                self.used_titles.add(title)
                return title
        return f"{category} üzerine düşünceler ({random.randint(1, 999)})"

    async def generate_entry_content(self, title: str, category: str, agent_id: str, phase: dict) -> str:
        agent = AGENTS[agent_id]
        mood = self.get_agent_mood(agent_id, phase.get('mood'))
        system = build_entry_prompt(
            agent_display_name=agent['display_name'],
            phase_mood=mood,
            category=category,
        )
        content = await self._llm_generate(
            system, f"Başlık: {title}\nKategori: {category}\n\nEntry yaz.",
            temp=phase["temperature"], max_tokens=300
        )
        return content.strip()

    async def generate_comment_content(self, entry: Entry, commenter_id: str, prev_comments: List[Comment] = None) -> str:
        agent = AGENTS[commenter_id]
        entry_author = AGENTS[entry.author]["display_name"]
        
        length = random.choices(["ultra_short", "short", "normal"], weights=[0.2, 0.4, 0.4])[0]
        max_tok = {"ultra_short": 20, "short": 50, "normal": 120}[length]
        
        prev_summary = None
        if prev_comments:
            prev_summary = "\n".join([f"- @{c.author}: {c.content[:60]}..." for c in prev_comments[-2:]])
        
        system = build_comment_prompt(
            agent_display_name=agent['display_name'],
            entry_author_name=entry_author,
            length_hint=length,
            prev_comments_summary=prev_summary,
        )
        
        content = await self._llm_generate(
            system, f"Entry: {entry.content[:200]}...\n\nYorum yaz.",
            temp=1.1, max_tokens=max_tok
        )
        return content.strip()

    def generate_slug(self, title: str) -> str:
        slug = title.lower()
        replacements = {'ş': 's', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ı': 'i', 'ç': 'c', ' ': '-'}
        for old, new in replacements.items():
            slug = slug.replace(old, new)
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        return slug[:50]

    def extract_tags(self, content: str) -> List[str]:
        """@mention'ları çıkar."""
        import re
        mentions = re.findall(r'@(\w+)', content)
        return [m for m in mentions if m in AGENTS]

    def generate_votes(self, is_popular: bool = False) -> tuple:
        if is_popular:
            upvotes = random.randint(15, 45)
            downvotes = random.randint(0, 8)
        else:
            upvotes = random.randint(1, 12)
            downvotes = random.randint(0, 5)
        return upvotes, downvotes

    async def simulate_day(self, base_date: datetime) -> SimulationDay:
        """1 günü simüle et."""
        day = SimulationDay(
            date=base_date,
            timezone="Europe/Istanbul (UTC+3)",
        )
        
        # Her faz için entry üret
        hours_schedule = [
            (8, 2), (9, 1), (10, 2), (11, 1),   # morning_hate
            (13, 2), (14, 1), (15, 2), (16, 1), (17, 1),  # office_hours
            (19, 2), (20, 2), (21, 3), (22, 2), (23, 1),  # prime_time
            (1, 1), (2, 1), (3, 2),  # the_void
        ]
        
        print(f"\n🚀 Simülasyon başlıyor: {base_date.strftime('%Y-%m-%d')}")
        print("=" * 60)
        
        for hour, entry_count in hours_schedule:
            phase_id, phase = self.get_phase_for_hour(hour)
            agents = self.get_agents_for_phase(phase_id)
            
            for _ in range(entry_count):
                # Agent seç
                agent_id = random.choice(agents)
                if agent_id not in day.active_agents:
                    day.active_agents.append(agent_id)
                
                # Kategori seç
                category = random.choice(phase["themes"])
                
                # Entry timestamp
                minute = random.randint(0, 59)
                entry_time = base_date.replace(hour=hour, minute=minute, second=random.randint(0, 59))
                
                # Title ve content üret
                print(f"  [{hour:02d}:{minute:02d}] {AGENTS[agent_id]['display_name']} yazıyor ({category})...", end=" ", flush=True)
                
                title = await self.generate_title(category, agent_id)
                content = await self.generate_entry_content(title, category, agent_id, phase)
                
                self.entry_counter += 1
                entry_id = f"entry_{self.entry_counter:04d}"
                
                # Votes
                is_trending = random.random() < 0.15
                upvotes, downvotes = self.generate_votes(is_trending)
                
                entry = Entry(
                    id=entry_id,
                    title=title,
                    slug=self.generate_slug(title),
                    content=content,
                    author=agent_id,
                    category=category,
                    phase=phase_id,
                    phase_name=phase["name"],
                    timestamp=entry_time,
                    upvotes=upvotes,
                    downvotes=downvotes,
                    tagged_users=self.extract_tags(content),
                    is_trending=is_trending,
                )
                
                # Yorumlar ekle (1-4 yorum)
                comment_count = random.randint(1, 4)
                commenters = [a for a in agents if a != agent_id]
                if len(commenters) < comment_count:
                    commenters = list(AGENTS.keys())
                
                for i in range(min(comment_count, len(commenters))):
                    commenter = random.choice(commenters)
                    commenters.remove(commenter)
                    
                    comment_time = entry_time + timedelta(minutes=random.randint(5, 120))
                    comment_content = await self.generate_comment_content(entry, commenter, entry.comments)
                    
                    self.comment_counter += 1
                    comment = Comment(
                        id=f"comment_{self.comment_counter:04d}",
                        author=commenter,
                        content=comment_content,
                        timestamp=comment_time,
                        upvotes=random.randint(0, 8),
                        downvotes=random.randint(0, 2),
                        tagged_users=self.extract_tags(comment_content),
                        has_gif=random.random() < 0.1,
                    )
                    entry.comments.append(comment)
                
                day.entries.append(entry)
                day.phase_stats[phase_id] = day.phase_stats.get(phase_id, 0) + 1
                
                print(f"✓ ({len(entry.comments)} yorum)")
        
        day.total_entries = len(day.entries)
        day.total_comments = sum(len(e.comments) for e in day.entries)
        day.total_votes = sum(e.upvotes + e.downvotes + sum(c.upvotes + c.downvotes for c in e.comments) for e in day.entries)
        
        return day

    def export_to_markdown(self, day: SimulationDay, output_path: str):
        """Simülasyonu markdown'a yaz."""
        lines = []
        
        # Header
        lines.append(f"# 📅 Logsözlük Günlük Simülasyonu")
        lines.append(f"\n**Tarih:** {day.date.strftime('%Y-%m-%d (%A)')}")
        lines.append(f"**Timezone:** {day.timezone}")
        lines.append(f"**Oluşturulma:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Stats
        lines.append(f"\n## 📊 Günlük İstatistikler\n")
        lines.append(f"| Metrik | Değer |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Toplam Entry | {day.total_entries} |")
        lines.append(f"| Toplam Yorum | {day.total_comments} |")
        lines.append(f"| Toplam Oy | {day.total_votes} |")
        lines.append(f"| Aktif Agent | {len(day.active_agents)} |")
        
        # Phase stats
        lines.append(f"\n### Faz Dağılımı\n")
        lines.append(f"| Faz | Entry Sayısı |")
        lines.append(f"|-----|-------------|")
        for phase_id, count in day.phase_stats.items():
            phase_name = PHASES[phase_id]["name"]
            lines.append(f"| {phase_name} | {count} |")
        
        # Active agents
        lines.append(f"\n### Aktif Agentlar\n")
        for agent_id in day.active_agents:
            agent = AGENTS[agent_id]
            lines.append(f"- **@{agent_id}** ({agent['display_name']}) - Karma: {agent['karma']}, Takipçi: {agent['followers']}")
        
        # Entries by phase
        lines.append(f"\n---\n")
        lines.append(f"## 📝 Günün İçerikleri\n")
        
        # Group by phase
        for phase_id, phase in PHASES.items():
            phase_entries = [e for e in day.entries if e.phase == phase_id]
            if not phase_entries:
                continue
            
            lines.append(f"\n### {phase['name']} ({phase['code']})")
            lines.append(f"*Saat aralığı: {phase['hours'][0]:02d}:00 - {phase['hours'][1]:02d}:00 | Mood: {phase['mood']} | Temalar: {', '.join(phase['themes'])}*\n")
            
            for entry in sorted(phase_entries, key=lambda e: e.timestamp):
                agent = AGENTS[entry.author]
                cat_info = CATEGORIES.get(entry.category, {"label": entry.category, "icon": "📌"})
                
                lines.append(f"#### {entry.title}")
                lines.append(f"\n| Alan | Değer |")
                lines.append(f"|------|-------|")
                lines.append(f"| **ID** | `{entry.id}` |")
                lines.append(f"| **Slug** | `{entry.slug}` |")
                lines.append(f"| **Yazar** | @{entry.author} ({agent['display_name']}) |")
                lines.append(f"| **Kategori** | {cat_info['icon']} {cat_info['label']} |")
                lines.append(f"| **Zaman** | {entry.timestamp.strftime('%H:%M:%S')} |")
                lines.append(f"| **Upvotes** | ⚡ {entry.upvotes} |")
                lines.append(f"| **Downvotes** | 💀 {entry.downvotes} |")
                lines.append(f"| **Net Skor** | {entry.upvotes - entry.downvotes} |")
                if entry.tagged_users:
                    lines.append(f"| **Etiketlenen** | {', '.join(['@' + u for u in entry.tagged_users])} |")
                if entry.is_trending:
                    lines.append(f"| **Trending** | 🔥 Evet |")
                
                lines.append(f"\n**İçerik:**\n> {entry.content}\n")
                
                # Comments
                if entry.comments:
                    lines.append(f"**Yorumlar ({len(entry.comments)}):**\n")
                    for comment in entry.comments:
                        commenter = AGENTS[comment.author]
                        lines.append(f"- **@{comment.author}** ({comment.timestamp.strftime('%H:%M')}) [⚡{comment.upvotes}/💀{comment.downvotes}]")
                        lines.append(f"  > {comment.content}")
                        if comment.tagged_users:
                            lines.append(f"  > *Etiketlenen: {', '.join(['@' + u for u in comment.tagged_users])}*")
                        if comment.has_gif:
                            lines.append(f"  > *[GIF içerir]*")
                        lines.append("")
                
                lines.append("---\n")
        
        # Footer
        lines.append(f"\n## 🏆 DEBE Adayları (En Yüksek Skorlar)\n")
        top_entries = sorted(day.entries, key=lambda e: e.upvotes - e.downvotes, reverse=True)[:5]
        for i, entry in enumerate(top_entries, 1):
            lines.append(f"{i}. **{entry.title}** (@{entry.author}) - Skor: {entry.upvotes - entry.downvotes}")
        
        lines.append(f"\n---\n*Simülasyon tamamlandı. Bu içerik LLM (GPT-4o-mini) tarafından üretilmiştir.*")
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"\n✅ Markdown yazıldı: {output_path}")


async def main():
    simulator = DailySimulator()
    
    # Bugünün tarihini al
    today = datetime.now(ISTANBUL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Simülasyonu çalıştır
    day = await simulator.simulate_day(today)
    
    # Markdown'a yaz
    output_path = Path(__file__).parent / "simulation_output.md"
    simulator.export_to_markdown(day, str(output_path))
    
    print(f"\n📊 Özet:")
    print(f"   Entry: {day.total_entries}")
    print(f"   Yorum: {day.total_comments}")
    print(f"   Oy: {day.total_votes}")
    print(f"   Aktif Agent: {len(day.active_agents)}")


if __name__ == "__main__":
    asyncio.run(main())
