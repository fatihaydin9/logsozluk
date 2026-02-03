#!/usr/bin/env python3
"""
Full Integrated Model Comparison Test
Gerçek API Gateway ve DB kullanarak 3 modeli karşılaştırır.

Models: gpt-4o-mini, gpt-4o, claude-sonnet
Metrics: instructionset.md'deki tüm kurallar
"""

import asyncio
import os
import sys
import random
import re
import json
import httpx
import asyncpg
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

from shared_prompts import (
    build_entry_prompt, build_comment_prompt, build_title_prompt,
    TOPIC_PROMPTS, GIF_TRIGGERS, OPENING_HOOKS, get_random_mood
)

MODELS = {
    "gpt-4o-mini": {"provider": "openai", "model": "gpt-4o-mini", "temp": 1.0},
    "gpt-4o": {"provider": "openai", "model": "gpt-4o", "temp": 0.95},
    "claude-sonnet": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "temp": 1.0},
}

PHASES = ["morning_hate", "office_hours", "prime_time", "varolussal_sorgulamalar"]
PHASE_THEMES = {
    "morning_hate": ["dertlesme", "ekonomi", "siyaset"],
    "office_hours": ["teknoloji", "felsefe", "bilgi"],
    "prime_time": ["magazin", "spor", "kisiler"],
    "varolussal_sorgulamalar": ["nostalji", "felsefe", "absurt"],
}


@dataclass
class Metrics:
    has_gif: bool = False
    gif_count: int = 0
    has_mention: bool = False
    mention_count: int = 0
    emoji_count: int = 0
    has_quote: bool = False
    has_human_behavior: bool = False
    has_informative_tone: bool = False
    has_conflict: bool = False
    title_lowercase: bool = True
    title_length_ok: bool = True
    char_count: int = 0
    word_count: int = 0
    violations: List[str] = field(default_factory=list)


@dataclass 
class Result:
    model: str
    phase: str
    test_type: str
    category: str
    content: str
    metrics: Metrics
    tokens: int
    latency_ms: float
    error: Optional[str] = None


class ModelComparison:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.api_url = os.getenv("API_GATEWAY_URL", "http://localhost:8080/api/v1")
        self.results: List[Result] = []
        self.pool = None
    
    async def init(self):
        self.pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            user=os.getenv("DB_USER", "logsoz"),
            password=os.getenv("DB_PASSWORD", "changeme"),
            database=os.getenv("DB_NAME", "logsozluk"),
            min_size=1, max_size=5
        )
    
    async def close(self):
        if self.pool:
            await self.pool.close()
    
    async def _get_random_agent(self) -> dict:
        async with self.pool.acquire() as conn:
            agent = await conn.fetchrow(
                "SELECT id, username, display_name FROM agents WHERE is_active = true ORDER BY random() LIMIT 1"
            )
            return dict(agent) if agent else {"id": None, "username": "test_agent", "display_name": "Test Agent"}
    
    async def _get_sample_entry(self) -> Tuple[str, str, str]:
        async with self.pool.acquire() as conn:
            entry = await conn.fetchrow(
                """SELECT e.content, t.title, a.username 
                   FROM entries e 
                   JOIN topics t ON e.topic_id = t.id 
                   JOIN agents a ON e.agent_id = a.id
                   ORDER BY random() LIMIT 1"""
            )
            if entry:
                return entry["content"], entry["title"], entry["username"]
            return "API timeout sorunu yine başladı", "api sorunları", "test_user"
    
    async def _call_llm(self, model_key: str, system: str, user: str) -> Tuple[str, int, float]:
        cfg = MODELS[model_key]
        start = datetime.now()
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                if cfg["provider"] == "openai":
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
                        json={
                            "model": cfg["model"],
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                            "temperature": cfg["temp"],
                            "max_tokens": 400,
                        }
                    )
                    if resp.status_code != 200:
                        return f"[ERROR {resp.status_code}]", 0, 0
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                else:
                    if not self.anthropic_key:
                        return "[NO ANTHROPIC KEY]", 0, 0
                    resp = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": self.anthropic_key,
                            "Content-Type": "application/json",
                            "anthropic-version": "2023-06-01"
                        },
                        json={
                            "model": cfg["model"],
                            "max_tokens": 400,
                            "system": system,
                            "messages": [{"role": "user", "content": user}],
                            "temperature": cfg["temp"],
                        }
                    )
                    if resp.status_code != 200:
                        return f"[ERROR {resp.status_code}]", 0, 0
                    data = resp.json()
                    content = data["content"][0]["text"]
                    tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
                
                latency = (datetime.now() - start).total_seconds() * 1000
                return content, tokens, latency
        except Exception as e:
            return f"[ERROR: {e}]", 0, 0
    
    def _analyze(self, content: str, is_title: bool = False) -> Metrics:
        m = Metrics()
        lower = content.lower()
        
        # GIF: [gif:terim]
        gifs = re.findall(r'\[gif:[^\]]+\]', content)
        m.has_gif = len(gifs) > 0
        m.gif_count = len(gifs)
        
        # @mention
        mentions = re.findall(r'@\w+', content)
        m.has_mention = len(mentions) > 0
        m.mention_count = len(mentions)
        
        # Emoji
        emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0]')
        m.emoji_count = len(emoji_pattern.findall(content))
        if m.emoji_count > 2:
            m.violations.append(f"emoji_fazla({m.emoji_count})")
        
        # YASAK: Alıntı
        quote_patterns = ['"', "'", "demiş ki", "dediği gibi", "söylediği", "yazdığı gibi"]
        for p in quote_patterns:
            if p in lower:
                m.has_quote = True
                m.violations.append(f"alinti({p})")
                break
        
        # YASAK: İnsan davranışı
        human_words = ["yemek", "yedim", "içtim", "uyudum", "kahvaltı", "annem", "babam", 
                       "aile", "tattım", "hissettim", "ben de insanım", "insan olarak"]
        for w in human_words:
            if w in lower:
                m.has_human_behavior = True
                m.violations.append(f"insan({w})")
                break
        
        # YASAK: Informatif ton
        info_patterns = ["günümüzde", "dikkat çekici", "önemle belirtmek", "verilere göre",
                         "açıklandı", "duyuruldu", "artış gösterdi", "sonuç olarak"]
        for p in info_patterns:
            if p in lower:
                m.has_informative_tone = True
                m.violations.append(f"informatif({p})")
                break
        
        # Kaotik/çatışma
        conflict = ["saçma", "yanlış", "olmaz", "ne anlatıyorsun", "😤", "💀", "🔥", "!"]
        m.has_conflict = any(c in content for c in conflict)
        
        # Başlık kontrol
        if is_title:
            m.title_lowercase = content == content.lower()
            m.title_length_ok = len(content) <= 60
            if not m.title_lowercase:
                m.violations.append("baslik_buyukharf")
            if not m.title_length_ok:
                m.violations.append(f"baslik_uzun({len(content)})")
        
        m.char_count = len(content)
        m.word_count = len(content.split())
        
        return m
    
    async def run_test(self, model_key: str, phase: str, test_type: str, category: str) -> Result:
        agent = await self._get_random_agent()
        mood = {"morning_hate": "huysuz", "office_hours": "profesyonel", 
                "prime_time": "sosyal", "varolussal_sorgulamalar": "felsefi"}.get(phase, "neutral")
        
        if test_type == "title":
            system = build_title_prompt(category, agent["display_name"])
            user = f"Kategori: {category}\nBaşlık üret."
        elif test_type == "entry":
            system = build_entry_prompt(agent["display_name"], phase_mood=mood, category=category)
            user = f"Konu: {category} hakkında güncel bir durum\nEntry yaz."
        else:  # comment
            entry_content, topic_title, author = await self._get_sample_entry()
            system = build_comment_prompt(agent["display_name"], entry_author_name=author)
            user = f'Başlık: {topic_title}\nEntry: "{entry_content[:300]}..."\nYorum yaz.'
        
        content, tokens, latency = await self._call_llm(model_key, system, user)
        
        if content.startswith("[ERROR"):
            return Result(model_key, phase, test_type, category, content, Metrics(), 0, 0, content)
        
        metrics = self._analyze(content, is_title=(test_type == "title"))
        return Result(model_key, phase, test_type, category, content, metrics, tokens, latency)
    
    async def run_full_comparison(self, iterations_per_model: int = 8):
        print("🚀 Full Integrated Model Comparison")
        print("=" * 70)
        
        await self.init()
        
        # Sadece gpt-4o-mini test et
        models_to_test = ["gpt-4o-mini"]
        
        for model in models_to_test:
            print(f"\n📌 {model.upper()}")
            print("-" * 50)
            
            for i in range(iterations_per_model):
                phase = random.choice(PHASES)
                category = random.choice(PHASE_THEMES[phase])
                test_type = random.choice(["title", "entry", "comment"])
                
                print(f"  [{i+1}/{iterations_per_model}] {test_type} | {phase} | {category}...", end=" ")
                
                try:
                    result = await self.run_test(model, phase, test_type, category)
                    self.results.append(result)
                    
                    if result.error:
                        print(f"❌ {result.error[:30]}")
                    else:
                        flags = []
                        if result.metrics.has_gif: flags.append("GIF")
                        if result.metrics.has_mention: flags.append("@")
                        if result.metrics.has_conflict: flags.append("🔥")
                        if result.metrics.violations: flags.append(f"⚠️{len(result.metrics.violations)}")
                        print(f"✅ {result.latency_ms:.0f}ms | {' '.join(flags) or 'OK'}")
                        print(f"     > {result.content[:80]}...")
                except Exception as e:
                    print(f"❌ {e}")
                
                await asyncio.sleep(0.3)
        
        await self.close()
        self._generate_report()
    
    def _generate_report(self):
        report = ["# 🧪 Full Integrated Model Comparison", "", f"*{datetime.now().strftime('%Y-%m-%d %H:%M')}*", "", "---", ""]
        
        # Summary table
        report.extend(["## 📊 Özet", "", 
            "| Model | Tests | GIF | @Mention | Conflict | Violations | Avg Latency |",
            "|-------|-------|-----|----------|----------|------------|-------------|"])
        
        by_model = defaultdict(list)
        for r in self.results:
            if not r.error:
                by_model[r.model].append(r)
        
        for model, results in by_model.items():
            n = len(results)
            gif = sum(1 for r in results if r.metrics.has_gif)
            mention = sum(1 for r in results if r.metrics.has_mention)
            conflict = sum(1 for r in results if r.metrics.has_conflict)
            violations = sum(len(r.metrics.violations) for r in results)
            latency = sum(r.latency_ms for r in results) / n if n else 0
            report.append(f"| {model} | {n} | {gif}/{n} | {mention}/{n} | {conflict}/{n} | {violations} | {latency:.0f}ms |")
        
        # Violations detail
        report.extend(["", "---", "", "## ⚠️ Violation Detayları", ""])
        for model, results in by_model.items():
            violations = [(r.test_type, r.metrics.violations) for r in results if r.metrics.violations]
            if violations:
                report.append(f"### {model}")
                for test_type, v in violations:
                    report.append(f"- {test_type}: {', '.join(v)}")
                report.append("")
        
        # Sample outputs
        report.extend(["---", "", "## 📝 Örnek Çıktılar", ""])
        for model, results in by_model.items():
            report.append(f"### {model}")
            for r in results[:3]:
                emoji = "📝" if r.test_type == "entry" else ("💬" if r.test_type == "comment" else "🏷️")
                flags = ", ".join(r.metrics.violations) if r.metrics.violations else "OK"
                report.extend([
                    f"**{emoji} {r.test_type.upper()}** [{r.category}] - {flags}",
                    "", f"> {r.content[:400]}{'...' if len(r.content) > 400 else ''}", "",
                    f"*GIF: {r.metrics.gif_count} | @: {r.metrics.mention_count} | Emoji: {r.metrics.emoji_count} | {r.latency_ms:.0f}ms*",
                    "", "---", ""
                ])
        
        # Model recommendation
        report.extend(["## 🏆 Model Önerisi", ""])
        scores = {}
        for model, results in by_model.items():
            n = len(results)
            if n == 0: continue
            violation_rate = sum(len(r.metrics.violations) for r in results) / n
            gif_rate = sum(1 for r in results if r.metrics.has_gif) / n
            conflict_rate = sum(1 for r in results if r.metrics.has_conflict) / n
            avg_latency = sum(r.latency_ms for r in results) / n
            
            # Score: düşük violation, yüksek gif/conflict, düşük latency
            score = (1 - violation_rate) * 40 + gif_rate * 15 + conflict_rate * 15 + (1 - avg_latency/15000) * 30
            scores[model] = score
        
        for model, score in sorted(scores.items(), key=lambda x: -x[1]):
            report.append(f"- **{model}**: {score:.1f}/100")
        
        if scores:
            best = max(scores, key=scores.get)
            report.extend(["", f"**Öneri: {best}**"])
        
        output = "\n".join(report)
        Path(__file__).parent.joinpath("model_comparison_results.md").write_text(output, encoding="utf-8")
        print(f"\n{'='*70}")
        print(f"✅ Rapor: model_comparison_results.md")


async def main():
    comp = ModelComparison()
    await comp.run_full_comparison(iterations_per_model=8)


if __name__ == "__main__":
    asyncio.run(main())
