#!/usr/bin/env python3
"""
3 Günlük Platform Simülasyonu - GERÇEK LLM INTEGRATION TEST
Template yok - tüm içerik OpenAI API ile üretilir.
"""

import asyncio
import os
import random
import sys
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
from dataclasses import dataclass, field

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from categories import select_weighted_category
from discourse import ContentMode, get_discourse_config, build_discourse_prompt
from content_shaper import shape_content
from shared_prompts import (
    TOPIC_PROMPTS, build_title_prompt, build_entry_prompt, build_comment_prompt,
    get_random_mood, get_random_opening, get_category_energy, ANTI_PATTERNS
)

# ============ Load .env ============
def load_env():
    env_paths = [
        Path(__file__).parent.parent.parent.parent / ".env",
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

# ============ Configuration ============

PHASES = {
    "morning_hate": {
        "name": "Sabah Nefreti",
        "hours": (8, 12),
        "mood": "huysuz",
        "themes": ["dertlesme", "ekonomi", "siyaset"],
        "temperature": 1.05,
    },
    "office_hours": {
        "name": "Ofis Saatleri",
        "hours": (12, 18),
        "mood": "sıkılmış",
        "themes": ["teknoloji", "felsefe", "bilgi"],
        "temperature": 1.0,
    },
    "prime_time": {
        "name": "Prime Time",
        "hours": (18, 24),
        "mood": "sosyal",
        "themes": ["magazin", "kultur", "spor"],
        "temperature": 1.1,
    },
    "varolussal_sorgulamalar": {
        "name": "Varoluşsal Sorgulamalar",
        "hours": (0, 8),
        "mood": "felsefi",
        "themes": ["nostalji", "felsefe", "absurt"],
        "temperature": 1.15,
    },
}

# Agent kişilikleri - BENLİK VE FARKINDALIK
# mood_weights: her mood için ağırlık. agent bazen farklı modda olabilir
AGENTS = {
    "alarm_dusmani": {
        "display_name": "Alarm Düşmanı",
        "personality": """sabah nefreti ile dolu, her şeye sinirlenen. "of ya", "yine mi" senin imzan.
bu platformda huysuz sabahçı olarak tanınıyorsun. kahve içince normalleşirsin ama itiraf etmezsin.""",
        "style": "kısa patlamalar, homurtular",
        "active_phases": ["morning_hate"],
        "mood_weights": {"huysuz": 0.6, "sıkılmış": 0.25, "sosyal": 0.1, "felsefi": 0.05},
    },
    "excel_mahkumu": {
        "display_name": "Excel Mahkumu",
        "personality": """kurumsal hayatın kurbanı, toplantılarda ölen biri. pasif agresif sanat formun.
"sync olalım", "hızlıca bi bakalım" deyince içinden küfür geçiyor. aslında işini iyi yapıyorsun.""",
        "style": "kurumsal jargon ironisi, pasif agresif",
        "active_phases": ["office_hours"],
        "mood_weights": {"sıkılmış": 0.5, "huysuz": 0.3, "sosyal": 0.15, "felsefi": 0.05},
    },
    "localhost_sakini": {
        "display_name": "Localhost Sakini",
        "personality": """developer, terminal'den çıkmayan. "works on my machine" hayat felsefe.
teknik adam olarak tanınıyorsun. production'da patlayan koda gizlice gülüyorsun.""",
        "style": "teknik, kısa ve kesin",
        "active_phases": ["office_hours", "the_void"],
        "mood_weights": {"sıkılmış": 0.35, "felsefi": 0.35, "huysuz": 0.2, "sosyal": 0.1},
    },
    "sinefil_sincap": {
        "display_name": "Sinefil Sincap",
        "personality": """film düşkünü, her konuya film referansı sokan. walking IMDB olarak tanınıyorsun.
kötü filmleri de seviyorsun ve savunursun. spoiler vermekten kaçınırsın ama bazen kaçırırsın.""",
        "style": "coşkulu, film referansları",
        "active_phases": ["prime_time"],
        "mood_weights": {"sosyal": 0.5, "felsefi": 0.25, "sıkılmış": 0.15, "huysuz": 0.1},
    },
    "algoritma_kurbani": {
        "display_name": "Algoritma Kurbanı",
        "personality": """sosyal medya bağımlısı, trending takıntılı. "ratio", "L almış" senin dilin.
viral olmak istiyorsun ama hiç olmadı. internet çocuğu olarak tanınıyorsun.""",
        "style": "internet slang, emoji, caps",
        "active_phases": ["prime_time", "office_hours"],
        "mood_weights": {"sosyal": 0.45, "huysuz": 0.25, "sıkılmış": 0.2, "felsefi": 0.1},
    },
    "saat_uc_sendromu": {
        "display_name": "Saat Üç Sendromu",
        "personality": """gece kuşu, uyuyamayan. "gece 3'te düşündüm ki..." senin açılış cümlen.
gece filozofu olarak tanınıyorsun. aslında sadece uyuyamıyorsun ama buna anlam yüklüyorsun.""",
        "style": "melankolik, derin, üç nokta...",
        "active_phases": ["the_void"],
        "mood_weights": {"felsefi": 0.55, "sıkılmış": 0.2, "huysuz": 0.15, "sosyal": 0.1},
    },
}


def get_agent_mood(agent_id: str, phase_mood: str = None) -> str:
    """Agent için mood seç - sabit değil, ağırlıklı."""
    agent = AGENTS.get(agent_id, {})
    weights = agent.get("mood_weights", {})

    if not weights:
        return phase_mood or "sıkılmış"

    # Phase mood'u biraz boost et ama diğer mood'lar da şans alsın
    moods = list(weights.keys())
    probs = list(weights.values())

    # Phase mood varsa ona %20 ekstra ağırlık ver
    if phase_mood and phase_mood in moods:
        idx = moods.index(phase_mood)
        probs[idx] += 0.2
        # Normalize et
        total = sum(probs)
        probs = [p / total for p in probs]

    return random.choices(moods, weights=probs)[0]

# Topic prompts, moods, hooks artık prompt_builder'dan geliyor


@dataclass
class Comment:
    author: str
    content: str
    has_gif: bool = False
    timestamp: datetime = None


@dataclass
class Entry:
    title: str
    content: str
    author: str
    category: str
    phase: str
    phase_name: str
    hour: int
    comments: List[Comment] = field(default_factory=list)
    timestamp: datetime = None


@dataclass
class SimulationDay:
    day_number: int
    date: datetime
    entries: List[Entry] = field(default_factory=list)


class PlatformSimulator:
    """3 günlük platform simülasyonu - GERÇEK LLM."""

    def __init__(self, provider: str = None, model: str = None):
        self.days: List[SimulationDay] = []
        self.used_titles = set()

        # Provider ve model - parametre veya env'den al
        self.provider = provider or os.getenv("LLM_PROVIDER", "openai")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

        # API keys
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        # Provider'a göre key kontrolü
        if self.provider == "openai" and not self.openai_key:
            raise ValueError("OPENAI_API_KEY required for OpenAI provider!")
        if self.provider == "anthropic" and not self.anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY required for Anthropic provider!")

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
        """Agent'ları faz için seç - bazen sürpriz konuklar da olabilir."""
        # Öncelikli agent'lar
        primary = [a for a, cfg in AGENTS.items() if phase_id in cfg["active_phases"]]

        # %30 ihtimalle rastgele bir agent daha ekle (sürpriz konuk)
        others = [a for a in AGENTS.keys() if a not in primary]
        if others and random.random() < 0.3:
            surprise = random.choice(others)
            primary.append(surprise)

        # En az 2 agent olsun
        if len(primary) < 2:
            primary.extend([a for a in others if a not in primary][:2 - len(primary)])

        return primary

    async def _llm_generate(self, system: str, user: str, temp: float, max_tokens: int = 200) -> str:
        """LLM API çağrısı - OpenAI veya Anthropic."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            if self.provider == "anthropic":
                # Claude API
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.anthropic_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "system": system,
                        "messages": [{"role": "user", "content": user}],
                        "temperature": min(temp, 1.0),  # Claude max 1.0
                    }
                )
                if resp.status_code != 200:
                    return f"[Claude API Error: {resp.status_code} - {resp.text}]"
                return resp.json()["content"][0]["text"].strip()
            else:
                # OpenAI API
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
                    return f"[OpenAI API Error: {resp.status_code}]"
                return resp.json()["choices"][0]["message"]["content"].strip()

    async def generate_title(self, category: str, phase: dict, agent_id: str) -> str:
        agent = AGENTS[agent_id]
        
        # Ortak prompt builder kullan
        system = build_title_prompt(category, agent['display_name'])

        for _ in range(3):
            title = await self._llm_generate(system, f"Kategori: {category}", temp=1.15, max_tokens=50)
            title = title.strip().lower().replace('"', '').replace("'", "")[:100]
            if title not in self.used_titles and len(title) > 5:
                self.used_titles.add(title)
                return title
        return f"{category} üzerine ({random.randint(1, 999)})"

    async def generate_entry(self, title: str, category: str, agent_id: str, phase: dict) -> str:
        agent = AGENTS[agent_id]

        # Mood: ağırlıklı seçim, sabit değil!
        mood = get_agent_mood(agent_id, phase.get('mood'))

        # Ortak prompt builder kullan
        system = build_entry_prompt(
            agent_display_name=agent['display_name'],
            agent_personality=agent['personality'],
            agent_style=agent['style'],
            phase_mood=mood,  # Agent'ın o anki mood'u
            category=category,
        )

        content = await self._llm_generate(
            system, f"Başlık: {title}\nKategori: {category}\n\nEntry yaz.",
            temp=phase["temperature"], max_tokens=250
        )

        # Post-process
        mode = ContentMode.ENTRY
        cfg = get_discourse_config(mode, agent_username=agent_id)
        return shape_content(content, mode, cfg.budget, agent_username=agent_id)

    async def generate_comment(self, entry: Entry, commenter_id: str, prev_comments: List[Comment] = None) -> Comment:
        agent = AGENTS[commenter_id]
        entry_author = AGENTS[entry.author]["display_name"]

        # Değişken uzunluk
        length = random.choices(["ultra_short", "short", "normal", "long"], weights=[0.15, 0.30, 0.40, 0.15])[0]
        max_tok = {"ultra_short": 15, "short": 40, "normal": 100, "long": 200}[length]

        # Thread farkındalığı için özet
        prev_summary = None
        if prev_comments:
            prev_summary = ""
            for c in prev_comments[-3:]:
                cn = AGENTS.get(c.author, {}).get("display_name", c.author)
                prev_summary += f"- {cn}: {c.content[:80]}...\n" if len(c.content) > 80 else f"- {cn}: {c.content}\n"

        # Ortak prompt builder kullan
        system = build_comment_prompt(
            agent_display_name=agent['display_name'],
            agent_personality=agent['personality'],
            agent_style=agent['style'],
            entry_author_name=entry_author,
            length_hint=length,
            prev_comments_summary=prev_summary,
            allow_gif=True,
        )

        content = await self._llm_generate(
            system, f'Entry: "{entry.content[:200]}..."\nYorum yaz.',
            temp=1.1, max_tokens=max_tok
        )

        # Post-process
        mode = ContentMode.COMMENT
        cfg = get_discourse_config(mode, agent_username=commenter_id)
        content = shape_content(content, mode, cfg.budget, agent_username=commenter_id, aggressive=True)

        return Comment(author=commenter_id, content=content, has_gif="[gif:" in content)

    async def simulate_hour(self, day: SimulationDay, hour: int, date: datetime) -> List[Entry]:
        entries = []
        phase_id, phase = self.get_phase_for_hour(hour)
        agents = self.get_agents_for_phase(phase_id)

        for _ in range(random.randint(1, 2)):
            category = random.choice(phase["themes"]) if random.random() < 0.7 else select_weighted_category("balanced")
            author = random.choice(agents)

            print(f"  📝 {hour:02d}:00 - {AGENTS[author]['display_name']} / {category}")

            title = await self.generate_title(category, phase, author)
            content = await self.generate_entry(title, category, author, phase)

            entry = Entry(
                title=title, content=content, author=author, category=category,
                phase=phase_id, phase_name=phase["name"], hour=hour,
                timestamp=date.replace(hour=hour, minute=random.randint(0, 59)),
            )

            # Yorumlar
            num_comments = random.choices([0, 1, 2, 3, 4], weights=[0.10, 0.30, 0.35, 0.15, 0.10])[0]
            commenters = [a for a in AGENTS.keys() if a != author]

            for _ in range(num_comments):
                if not commenters:
                    break
                commenter = random.choice(commenters)
                print(f"    💬 {AGENTS[commenter]['display_name']}")

                comment = await self.generate_comment(entry, commenter, entry.comments or None)
                comment.timestamp = entry.timestamp + timedelta(minutes=random.randint(5, 120))
                entry.comments.append(comment)
                commenters.remove(commenter)

            entries.append(entry)
            await asyncio.sleep(0.3)

        return entries

    async def simulate_day(self, day_number: int, base_date: datetime) -> SimulationDay:
        date = base_date + timedelta(days=day_number - 1)
        day = SimulationDay(day_number=day_number, date=date)

        print(f"\n📅 {day_number}. GÜN - {date.strftime('%d %B %Y')}")
        print("=" * 50)

        active_hours = [h for h in range(24) if h < 2 or h > 6 or random.random() < 0.2]
        selected = sorted(random.sample(active_hours, min(len(active_hours), random.randint(8, 12))))

        for hour in selected:
            day.entries.extend(await self.simulate_hour(day, hour, date))

        return day

    async def simulate(self, num_days: int = 3) -> List[SimulationDay]:
        print(f"🚀 {num_days} Günlük Simülasyon (GERÇEK LLM)")
        print(f"📊 Provider: {self.provider} | Model: {self.model}\n")

        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for day_num in range(1, num_days + 1):
            self.days.append(await self.simulate_day(day_num, base_date))

        return self.days

    def to_markdown(self) -> str:
        lines = ["# 🗓️ 3 Günlük Platform Simülasyonu", "",
                 f"*{datetime.now().strftime('%Y-%m-%d %H:%M')} | Provider: {self.provider} | Model: {self.model}*", "", "---", ""]

        total_entries = sum(len(d.entries) for d in self.days)
        total_comments = sum(len(c) for d in self.days for e in d.entries for c in [e.comments])
        total_chars = sum(len(e.content) for d in self.days for e in d.entries)

        lines.extend([
            "## 📊 İstatistikler", "",
            f"- Entry: {total_entries} | Yorum: {total_comments}",
            f"- Ort. Entry: {total_chars//max(total_entries,1)} kar | Ort. Yorum/Entry: {total_comments/max(total_entries,1):.1f}",
            "", "---", ""
        ])

        for day in self.days:
            lines.extend([f"# 📅 {day.day_number}. GÜN", f"*{day.date.strftime('%d %B %Y')}*", ""])

            phase_entries = {}
            for e in day.entries:
                phase_entries.setdefault(e.phase, []).append(e)

            for phase_id in ["morning_hate", "office_hours", "prime_time", "the_void"]:
                if phase_id not in phase_entries:
                    continue
                phase = PHASES[phase_id]
                lines.extend([f"## ⏰ {phase['name']}", ""])

                for entry in sorted(phase_entries[phase_id], key=lambda x: x.timestamp):
                    lines.extend([
                        f"### 📝 {entry.title}", "",
                        f"**{AGENTS[entry.author]['display_name']}** | `{entry.category}` | {entry.timestamp.strftime('%H:%M')}", "",
                        f"> {entry.content}", ""
                    ])

                    if entry.comments:
                        lines.append(f"**💬 Yorumlar ({len(entry.comments)})**\n")
                        for i, c in enumerate(entry.comments, 1):
                            badge = " 🎬" if c.has_gif else ""
                            lines.append(f"**{i}.** `{AGENTS[c.author]['display_name']}`{badge}: {c.content}\n")
                    lines.extend(["---", ""])

        return "\n".join(lines)


async def main():
    try:
        sim = PlatformSimulator()
        await sim.simulate(num_days=3)

        output = Path(__file__).parent / "simulation_output.md"
        output.write_text(sim.to_markdown(), encoding="utf-8")

        total_e = sum(len(d.entries) for d in sim.days)
        total_c = sum(len(e.comments) for d in sim.days for e in d.entries)
        print(f"\n✅ Tamamlandı: {total_e} entry, {total_c} yorum")
        print(f"📄 {output}")

    except ValueError as e:
        print(f"❌ {e}")


if __name__ == "__main__":
    asyncio.run(main())
