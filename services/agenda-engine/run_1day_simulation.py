#!/usr/bin/env python3
"""
1 Günlük Detaylı Simülasyon - Gerçek LLM API
Sonuçlar: topics, comments, votes, categories, timezone, authors
"""

import asyncio
import os
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict
from collections import Counter

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents"))

# Load .env
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

from simulation_3day import PlatformSimulator, AGENTS, PHASES, get_agent_mood


@dataclass
class DetailedComment:
    author: str
    author_display: str
    content: str
    mood: str
    upvotes: int = 0
    downvotes: int = 0
    has_gif: bool = False
    has_mention: bool = False
    timestamp: datetime = None


@dataclass
class DetailedEntry:
    title: str
    content: str
    author: str
    author_display: str
    category: str
    phase: str
    phase_name: str
    mood: str
    hour: int
    upvotes: int = 0
    downvotes: int = 0
    comments: List[DetailedComment] = field(default_factory=list)
    timestamp: datetime = None
    timezone: str = "Europe/Istanbul"


class DetailedSimulator(PlatformSimulator):
    """Detaylı simülasyon - vote ve mood bilgileri dahil."""

    async def simulate_hour_detailed(self, hour: int, date: datetime) -> List[DetailedEntry]:
        entries = []
        phase_id, phase = self.get_phase_for_hour(hour)
        agents = self.get_agents_for_phase(phase_id)

        num_entries = random.randint(1, 3)

        for _ in range(num_entries):
            category = random.choice(phase["themes"]) if random.random() < 0.7 else random.choice(
                ["teknoloji", "ekonomi", "felsefe", "nostalji", "absurt"]
            )
            author = random.choice(agents)
            agent_mood = get_agent_mood(author, phase.get("mood"))

            print(f"  📝 {hour:02d}:00 - {AGENTS[author]['display_name']} ({agent_mood}) / {category}")

            title = await self.generate_title(category, phase, author)
            content = await self.generate_entry(title, category, author, phase)

            # Rastgele votes
            base_up = random.randint(2, 25)
            base_down = random.randint(0, 5)
            # Mood'a göre vote ayarla
            if agent_mood in ["sosyal", "felsefi"]:
                base_up = int(base_up * 1.3)
            elif agent_mood == "huysuz":
                base_down = int(base_down * 1.5)

            entry = DetailedEntry(
                title=title,
                content=content,
                author=author,
                author_display=AGENTS[author]["display_name"],
                category=category,
                phase=phase_id,
                phase_name=phase["name"],
                mood=agent_mood,
                hour=hour,
                upvotes=base_up,
                downvotes=base_down,
                timestamp=date.replace(hour=hour, minute=random.randint(0, 59)),
            )

            # Yorumlar
            num_comments = random.choices([0, 1, 2, 3, 4, 5], weights=[0.05, 0.20, 0.35, 0.25, 0.10, 0.05])[0]
            commenters = [a for a in AGENTS.keys() if a != author]
            random.shuffle(commenters)

            prev_comments = []
            for i in range(min(num_comments, len(commenters))):
                commenter = commenters[i]
                commenter_mood = get_agent_mood(commenter, phase.get("mood"))
                print(f"    💬 {AGENTS[commenter]['display_name']} ({commenter_mood})")

                comment = await self.generate_comment(entry, commenter, prev_comments if prev_comments else None)

                # Comment votes
                c_up = random.randint(0, 10)
                c_down = random.randint(0, 3)

                detailed_comment = DetailedComment(
                    author=commenter,
                    author_display=AGENTS[commenter]["display_name"],
                    content=comment.content,
                    mood=commenter_mood,
                    upvotes=c_up,
                    downvotes=c_down,
                    has_gif="[gif:" in comment.content,
                    has_mention="@" in comment.content,
                    timestamp=entry.timestamp + timedelta(minutes=random.randint(5, 180)),
                )
                entry.comments.append(detailed_comment)
                prev_comments.append(comment)

            entries.append(entry)
            await asyncio.sleep(0.2)

        return entries

    async def simulate_one_day(self) -> List[DetailedEntry]:
        """1 günlük simülasyon."""
        print("🚀 1 Günlük Detaylı Simülasyon Başlıyor")
        print(f"📊 Provider: {self.provider} | Model: {self.model}")
        print(f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d')}\n")

        date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        all_entries = []

        # Gün boyunca aktif saatler (gece 3-6 arası az)
        hours = []
        for h in range(24):
            if 3 <= h <= 6:
                if random.random() < 0.3:
                    hours.append(h)
            else:
                if random.random() < 0.7:
                    hours.append(h)

        hours = sorted(set(hours))
        print(f"⏰ Aktif saatler: {hours}\n")

        for hour in hours:
            phase_id, phase = self.get_phase_for_hour(hour)
            print(f"\n{'='*50}")
            print(f"⏰ Saat {hour:02d}:00 - {phase['name']}")
            print(f"{'='*50}")

            entries = await self.simulate_hour_detailed(hour, date)
            all_entries.extend(entries)

        return all_entries


def generate_markdown(entries: List[DetailedEntry]) -> str:
    """Detaylı markdown raporu oluştur."""
    lines = [
        "# 🗓️ 1 Günlük Platform Simülasyonu - Detaylı Rapor",
        "",
        f"*Oluşturulma: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        f"*Timezone: Europe/Istanbul (UTC+3)*",
        "",
        "---",
        "",
    ]

    # İstatistikler
    total_entries = len(entries)
    total_comments = sum(len(e.comments) for e in entries)
    total_upvotes = sum(e.upvotes for e in entries) + sum(c.upvotes for e in entries for c in e.comments)
    total_downvotes = sum(e.downvotes for e in entries) + sum(c.downvotes for e in entries for c in e.comments)

    # Kategori dağılımı
    categories = Counter(e.category for e in entries)
    # Author dağılımı
    authors = Counter(e.author for e in entries)
    # Mood dağılımı
    moods = Counter(e.mood for e in entries)
    # Phase dağılımı
    phases = Counter(e.phase_name for e in entries)

    lines.extend([
        "## 📊 Genel İstatistikler",
        "",
        "| Metrik | Değer |",
        "|--------|-------|",
        f"| Toplam Entry | {total_entries} |",
        f"| Toplam Yorum | {total_comments} |",
        f"| Toplam Upvote | {total_upvotes} |",
        f"| Toplam Downvote | {total_downvotes} |",
        f"| Ort. Yorum/Entry | {total_comments/max(total_entries,1):.1f} |",
        f"| Ort. Upvote/Entry | {sum(e.upvotes for e in entries)/max(total_entries,1):.1f} |",
        "",
    ])

    # Kategori dağılımı
    lines.extend([
        "## 📂 Kategori Dağılımı",
        "",
        "| Kategori | Entry Sayısı | % |",
        "|----------|--------------|---|",
    ])
    for cat, count in categories.most_common():
        pct = count / total_entries * 100
        lines.append(f"| {cat} | {count} | {pct:.0f}% |")
    lines.append("")

    # Author dağılımı
    lines.extend([
        "## 👤 Yazar Dağılımı",
        "",
        "| Yazar | Entry Sayısı | Mood Dağılımı |",
        "|-------|--------------|---------------|",
    ])
    for author_id, count in authors.most_common():
        author_moods = [e.mood for e in entries if e.author == author_id]
        mood_counts = Counter(author_moods)
        mood_str = ", ".join([f"{m}({c})" for m, c in mood_counts.most_common(3)])
        lines.append(f"| {AGENTS[author_id]['display_name']} | {count} | {mood_str} |")
    lines.append("")

    # Mood dağılımı
    lines.extend([
        "## 🎭 Mood Dağılımı",
        "",
        "| Mood | Entry Sayısı | % |",
        "|------|--------------|---|",
    ])
    for mood, count in moods.most_common():
        pct = count / total_entries * 100
        lines.append(f"| {mood} | {count} | {pct:.0f}% |")
    lines.append("")

    # Phase dağılımı
    lines.extend([
        "## ⏰ Zaman Dilimi Dağılımı",
        "",
        "| Faz | Saat Aralığı | Entry Sayısı |",
        "|-----|--------------|--------------|",
    ])
    phase_hours = {
        "Sabah Nefreti": "08:00-12:00",
        "Ofis Saatleri": "12:00-18:00",
        "Altın Saatler": "18:00-00:00",
        "Karanlık Mod": "00:00-08:00",
    }
    for phase_name, count in phases.most_common():
        hours = phase_hours.get(phase_name, "?")
        lines.append(f"| {phase_name} | {hours} | {count} |")
    lines.append("")

    # Detaylı içerik
    lines.extend([
        "---",
        "",
        "# 📝 Detaylı İçerik",
        "",
    ])

    # Faz bazında grupla
    phase_entries = {}
    for e in entries:
        phase_entries.setdefault(e.phase, []).append(e)

    phase_order = ["morning_hate", "office_hours", "prime_time", "the_void"]

    for phase_id in phase_order:
        if phase_id not in phase_entries:
            continue

        phase = PHASES[phase_id]
        phase_list = sorted(phase_entries[phase_id], key=lambda x: x.timestamp)

        lines.extend([
            f"## ⏰ {phase['name']}",
            f"*Saat: {phase['hours'][0]:02d}:00 - {phase['hours'][1]:02d}:00 | Baskın Mood: {phase['mood']}*",
            "",
        ])

        for entry in phase_list:
            # Entry header
            vote_str = f"👍 {entry.upvotes} | 👎 {entry.downvotes}"
            lines.extend([
                f"### 📝 {entry.title}",
                "",
                f"| | |",
                f"|---|---|",
                f"| **Yazar** | {entry.author_display} |",
                f"| **Kategori** | `{entry.category}` |",
                f"| **Mood** | {entry.mood} |",
                f"| **Saat** | {entry.timestamp.strftime('%H:%M')} |",
                f"| **Votes** | {vote_str} |",
                "",
                f"> {entry.content}",
                "",
            ])

            # Comments
            if entry.comments:
                lines.append(f"**💬 Yorumlar ({len(entry.comments)})**")
                lines.append("")

                for i, c in enumerate(entry.comments, 1):
                    gif_badge = " 🎬" if c.has_gif else ""
                    mention_badge = " @" if c.has_mention else ""
                    c_votes = f"👍{c.upvotes} 👎{c.downvotes}"

                    lines.append(
                        f"**{i}.** `{c.author_display}` ({c.mood}){gif_badge}{mention_badge} [{c_votes}]"
                    )
                    lines.append(f"   > {c.content}")
                    lines.append("")

            lines.extend(["---", ""])

    # En çok oy alan entry'ler
    lines.extend([
        "## 🏆 En Popüler Entry'ler (Top 5)",
        "",
    ])
    top_entries = sorted(entries, key=lambda x: x.upvotes - x.downvotes, reverse=True)[:5]
    for i, e in enumerate(top_entries, 1):
        score = e.upvotes - e.downvotes
        lines.append(f"{i}. **{e.title}** - {e.author_display} (Score: {score}, 💬{len(e.comments)})")
    lines.append("")

    # En aktif yorumcular
    comment_authors = Counter()
    for e in entries:
        for c in e.comments:
            comment_authors[c.author] += 1

    lines.extend([
        "## 💬 En Aktif Yorumcular",
        "",
    ])
    for author_id, count in comment_authors.most_common(5):
        lines.append(f"- {AGENTS[author_id]['display_name']}: {count} yorum")
    lines.append("")

    return "\n".join(lines)


async def main():
    try:
        sim = DetailedSimulator()
        entries = await sim.simulate_one_day()

        # Markdown oluştur
        markdown = generate_markdown(entries)

        # Dosyaya yaz
        output_path = Path(__file__).parent / "simulation_1day_detailed.md"
        output_path.write_text(markdown, encoding="utf-8")

        print(f"\n{'='*50}")
        print("✅ Simülasyon Tamamlandı!")
        print(f"📄 Çıktı: {output_path}")
        print(f"📊 Toplam: {len(entries)} entry, {sum(len(e.comments) for e in entries)} yorum")

    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
