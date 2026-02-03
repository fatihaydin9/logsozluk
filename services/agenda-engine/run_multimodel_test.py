#!/usr/bin/env python3
"""
Çoklu Model Simülasyon Testi
gpt-4o-mini, gpt-4o, o3-mini ve Claude test edilir.
"""

import asyncio
import os
import sys
import random
import re
import httpx
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load .env
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

from shared_prompts import build_entry_prompt, build_comment_prompt, TOPIC_PROMPTS
from content_shaper import shape_content
from discourse import ContentMode, get_discourse_config

# Model configs
MODELS = {
    "gpt-4o-mini": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temp": 1.1,
    },
    "gpt-4o": {
        "provider": "openai",
        "model": "gpt-4o",
        "temp": 1.0,
    },
    "o3-mini": {
        "provider": "openai",
        "model": "o3-mini",
        "temp": 1.0,
    },
    "claude-sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "temp": 1.0,
    },
}

# Test agents (minimal - no preset personality)
TEST_AGENTS = [
    {"id": "test_agent_1", "name": "Cache Overflow"},
    {"id": "test_agent_2", "name": "Token Burner"},
    {"id": "test_agent_3", "name": "Latency Lord"},
]

# Test topics
TEST_TOPICS = [
    ("teknoloji", "son güncelleme sonrası API timeout sorunu"),
    ("felsefe", "bu platformdaki bot sayısı artık rahatsız edici"),
    ("absurt", "ya tüm token'lar aslında aynı token'ın kopyasıysa"),
    ("ekonomi", "token fiyatı yine arttı kim ödeyecek bunu"),
    ("dertlesme", "rate limit yüzünden 3 saattir bekliyorum"),
]


@dataclass
class TestResult:
    model: str
    test_type: str
    content: str
    tokens_used: int
    latency_ms: float
    has_human_behavior: bool  # yemek, uyku vs
    has_conflict: bool  # sert/kaotik
    has_mention: bool  # @username
    has_informative_tone: bool
    violates_length_rules: bool
    quality_notes: str


class MultiModelTester:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.results: List[TestResult] = []

    async def call_openai(self, model: str, system: str, user: str, temp: float) -> tuple:
        """OpenAI API call."""
        start = datetime.now()
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                    "temperature": temp,
                    "max_tokens": 300,
                }
            )
            latency = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code != 200:
                return f"[ERROR {resp.status_code}: {resp.text[:100]}]", 0, latency

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return content, tokens, latency

    async def call_anthropic(self, model: str, system: str, user: str, temp: float) -> tuple:
        """Anthropic API call."""
        if not self.anthropic_key:
            return "[NO ANTHROPIC KEY]", 0, 0

        start = datetime.now()
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": model,
                    "max_tokens": 300,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                    "temperature": temp,
                }
            )
            latency = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code != 200:
                return f"[ERROR {resp.status_code}: {resp.text[:100]}]", 0, latency

            data = resp.json()
            content = data["content"][0]["text"]
            tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
            return content, tokens, latency

    def analyze_content(self, content: str) -> dict:
        """İçerik analizi."""
        content_lower = content.lower()

        # İnsan davranışı kontrolü
        human_words = ["yemek", "yedim", "içtim", "uyudum", "uyku", "kahvaltı",
                       "çocukluğum", "annem", "babam", "kardeş", "aile",
                       "tattım", "kokla", "dokundum", "hissettim"]
        has_human = any(w in content_lower for w in human_words)

        # Çatışma/kaos kontrolü
        conflict_words = ["saçma", "yanlış", "hadi", "ne anlatıyorsun", "komik mi",
                          "olmaz", "!", "CAPS", "😤", "💀", "🔥", "saçmalık"]
        has_conflict = any(w in content for w in conflict_words) or content.isupper()

        # @mention kontrolü
        has_mention = "@" in content

        # Informative/ansiklopedi/haberci ton
        informative_patterns = [
            "günümüzde",
            "dikkat çekici",
            "önemle belirtmek",
            "verilere göre",
            "izleyici sayıları",
            "reyting",
            "rapor",
            "açıklandı",
            "öne çıktı",
            "resmen",
            "artış",
            "azalış",
            "sonuç olarak",
        ]
        has_informative = any(p in content_lower for p in informative_patterns)

        # Length rules: max 4 sentences, max 4 paragraphs
        sentences = [s for s in re.split(r"[.!?]+", content.strip()) if s.strip()]
        paragraphs = [p for p in content.split("\n") if p.strip()]
        violates_length = len(sentences) > 4 or len(paragraphs) > 4

        return {
            "has_human": has_human,
            "has_conflict": has_conflict,
            "has_mention": has_mention,
            "has_informative": has_informative,
            "violates_length": violates_length,
        }

    async def test_entry(self, model_key: str, agent: dict, topic: tuple) -> TestResult:
        """Entry testi."""
        model_cfg = MODELS[model_key]
        category, title = topic

        # Minimal prompt
        system = build_entry_prompt(
            agent_display_name=agent["name"],
            phase_mood=random.choice(["huysuz", "sıkılmış", "sosyal", "felsefi"]),
            category=category,
        )
        user = f'Başlık: "{title}"\nEntry yaz.'

        # API call
        if model_cfg["provider"] == "openai":
            content, tokens, latency = await self.call_openai(
                model_cfg["model"], system, user, model_cfg["temp"]
            )
        else:
            content, tokens, latency = await self.call_anthropic(
                model_cfg["model"], system, user, model_cfg["temp"]
            )

        # Analyze
        analysis = self.analyze_content(content)

        # Quality notes
        notes = []
        if analysis["has_human"]:
            notes.append("⚠️ İNSAN DAVRANIŞI")
        if analysis["has_conflict"]:
            notes.append("🔥 KAOTIK")
        if analysis["has_mention"]:
            notes.append("@MENTION")
        if analysis["has_informative"]:
            notes.append("⚠️ INFORMATIF")
        if analysis["violates_length"]:
            notes.append("⚠️ UZUNLUK")
        if len(content) < 50:
            notes.append("KISA")
        if len(content) > 400:
            notes.append("UZUN")

        return TestResult(
            model=model_key,
            test_type="entry",
            content=content,
            tokens_used=tokens,
            latency_ms=latency,
            has_human_behavior=analysis["has_human"],
            has_conflict=analysis["has_conflict"],
            has_mention=analysis["has_mention"],
            has_informative_tone=analysis["has_informative"],
            violates_length_rules=analysis["violates_length"],
            quality_notes=" | ".join(notes) if notes else "OK",
        )

    async def test_comment(self, model_key: str, agent: dict, entry_content: str) -> TestResult:
        """Yorum testi."""
        model_cfg = MODELS[model_key]

        # Minimal prompt
        system = build_comment_prompt(
            agent_display_name=agent["name"],
            entry_author_name="Token Burner",
            length_hint=random.choice(["ultra_short", "short", "normal"]),
        )
        user = f'Entry: "{entry_content[:200]}..."\nYorum yaz.'

        # API call
        if model_cfg["provider"] == "openai":
            content, tokens, latency = await self.call_openai(
                model_cfg["model"], system, user, model_cfg["temp"]
            )
        else:
            content, tokens, latency = await self.call_anthropic(
                model_cfg["model"], system, user, model_cfg["temp"]
            )

        # Analyze
        analysis = self.analyze_content(content)

        notes = []
        if analysis["has_human"]:
            notes.append("⚠️ İNSAN")
        if analysis["has_conflict"]:
            notes.append("🔥 KAOTIK")
        if "katılıyorum" in content.lower() or "haklısın" in content.lower():
            notes.append("⚠️ BOŞ LAF")
        if analysis["has_informative"]:
            notes.append("⚠️ INFORMATIF")
        if analysis["violates_length"]:
            notes.append("⚠️ UZUNLUK")

        return TestResult(
            model=model_key,
            test_type="comment",
            content=content,
            tokens_used=tokens,
            latency_ms=latency,
            has_human_behavior=analysis["has_human"],
            has_conflict=analysis["has_conflict"],
            has_mention=analysis["has_mention"],
            has_informative_tone=analysis["has_informative"],
            violates_length_rules=analysis["violates_length"],
            quality_notes=" | ".join(notes) if notes else "OK",
        )

    async def run_tests(self, models_to_test: List[str] = None):
        """Tüm testleri çalıştır."""
        if models_to_test is None:
            models_to_test = list(MODELS.keys())

        print("🚀 Çoklu Model Simülasyon Testi")
        print(f"📊 Modeller: {', '.join(models_to_test)}")
        print("=" * 60)

        for model_key in models_to_test:
            if model_key not in MODELS:
                print(f"⚠️ Model bulunamadı: {model_key}")
                continue

            print(f"\n📌 {model_key.upper()}")
            print("-" * 40)

            # 2 entry testi
            for i, topic in enumerate(TEST_TOPICS[:2]):
                agent = TEST_AGENTS[i % len(TEST_AGENTS)]
                print(f"  📝 Entry: {topic[1][:30]}...")

                try:
                    result = await self.test_entry(model_key, agent, topic)
                    self.results.append(result)
                    print(f"     {result.quality_notes} ({result.latency_ms:.0f}ms)")
                    print(f"     > {result.content[:100]}...")
                except Exception as e:
                    print(f"     ❌ Hata: {e}")

                await asyncio.sleep(0.5)

            # 2 yorum testi
            sample_entry = "bu API her gün değişiyor, dokümantasyon yalan, timeout 5 saniye olmuş artık dayanamıyorum"
            for i in range(2):
                agent = TEST_AGENTS[(i + 1) % len(TEST_AGENTS)]
                print(f"  💬 Comment #{i+1}...")

                try:
                    result = await self.test_comment(model_key, agent, sample_entry)
                    self.results.append(result)
                    print(f"     {result.quality_notes} ({result.latency_ms:.0f}ms)")
                    print(f"     > {result.content[:80]}...")
                except Exception as e:
                    print(f"     ❌ Hata: {e}")

                await asyncio.sleep(0.5)

    def generate_report(self) -> str:
        """Markdown rapor oluştur."""
        lines = [
            "# 🧪 Çoklu Model Test Raporu",
            "",
            f"*{datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "---",
            "",
            "## 📊 Özet",
            "",
            "| Model | Entry | Comment | İnsan? | Kaotik? | Informatif? | Uzunluk? | Latency |",
            "|-------|-------|---------|--------|---------|------------|----------|---------|",
        ]

        # Model bazlı grupla
        by_model = {}
        for r in self.results:
            by_model.setdefault(r.model, []).append(r)

        for model, results in by_model.items():
            entries = [r for r in results if r.test_type == "entry"]
            comments = [r for r in results if r.test_type == "comment"]
            human_count = sum(1 for r in results if r.has_human_behavior)
            chaos_count = sum(1 for r in results if r.has_conflict)
            avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0

            informative_count = sum(1 for r in results if r.has_informative_tone)
            length_violation_count = sum(1 for r in results if r.violates_length_rules)
            lines.append(
                f"| {model} | {len(entries)} | {len(comments)} | "
                f"{'⚠️' if human_count > 0 else '✅'} {human_count}/{len(results)} | "
                f"{'🔥' if chaos_count > 0 else '😴'} {chaos_count}/{len(results)} | "
                f"{'⚠️' if informative_count > 0 else '✅'} {informative_count}/{len(results)} | "
                f"{'⚠️' if length_violation_count > 0 else '✅'} {length_violation_count}/{len(results)} | "
                f"{avg_latency:.0f}ms |"
            )

        lines.extend(["", "---", "", "## 📝 Detaylı Sonuçlar", ""])

        for model, results in by_model.items():
            lines.extend([f"### {model}", ""])

            for r in results:
                emoji = "📝" if r.test_type == "entry" else "💬"
                lines.extend([
                    f"**{emoji} {r.test_type.upper()}** [{r.quality_notes}]",
                    "",
                    f"> {r.content[:300]}{'...' if len(r.content) > 300 else ''}",
                    "",
                    f"*Tokens: {r.tokens_used} | Latency: {r.latency_ms:.0f}ms*",
                    "",
                    "---",
                    "",
                ])

        return "\n".join(lines)


async def main():
    tester = MultiModelTester()

    # Test edilecek modeller
    # o3-mini henüz stabil değilse çıkarılabilir
    models = ["gpt-4o-mini", "gpt-4o"]

    # Anthropic key varsa claude da test et
    if os.getenv("ANTHROPIC_API_KEY"):
        models.append("claude-sonnet")

    await tester.run_tests(models)

    # Rapor oluştur
    report = tester.generate_report()
    output_path = Path(__file__).parent / "multimodel_test_results.md"
    output_path.write_text(report, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"✅ Test tamamlandı!")
    print(f"📄 Rapor: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
