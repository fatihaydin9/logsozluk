#!/usr/bin/env python3
"""
Multi-Model Karşılaştırma Testi
6 farklı LLM modeli ile 1 günlük simülasyon çalıştırır.
Her model için ayrı markdown dosyası oluşturur.

Modeller:
- OpenAI: gpt-4o-mini, gpt-4o, gpt-4-turbo
- Anthropic: claude-3-haiku-20240307, claude-3-5-sonnet-20241022, claude-3-opus-20240229
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from datetime import datetime

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

from run_1day_simulation import DetailedSimulator, generate_markdown, AGENTS

# Test edilecek modeller
MODELS = [
    # OpenAI modelleri
    {"provider": "openai", "model": "gpt-4o-mini", "name": "GPT-4o Mini"},
    {"provider": "openai", "model": "gpt-4o", "name": "GPT-4o"},
    {"provider": "openai", "model": "gpt-4-turbo", "name": "GPT-4 Turbo"},
    # Anthropic modelleri
    {"provider": "anthropic", "model": "claude-3-haiku-20240307", "name": "Claude 3 Haiku"},
    {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
    {"provider": "anthropic", "model": "claude-3-opus-20240229", "name": "Claude 3 Opus"},
]


class MultiModelSimulator(DetailedSimulator):
    """Multi-model destekli simülatör."""

    def __init__(self, provider: str, model: str):
        # Parent init çağırmadan önce provider/model set et
        self.days = []
        self.used_titles = set()
        self.provider = provider
        self.model = model

        # API keys
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        # Provider kontrolü
        if provider == "openai" and not self.openai_key:
            raise ValueError("OPENAI_API_KEY required!")
        if provider == "anthropic" and not self.anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY required!")


def generate_markdown_with_model(entries, provider: str, model: str, model_name: str, duration: float) -> str:
    """Model bilgisi eklenmiş markdown oluştur."""
    # Base markdown'ı al
    base_md = generate_markdown(entries)

    # Header'ı güncelle
    header = f"""# 🗓️ 1 Günlük Platform Simülasyonu - {model_name}

*Oluşturulma: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Provider: {provider} | Model: {model}*
*Süre: {duration:.1f} saniye*
*Timezone: Europe/Istanbul (UTC+3)*

---
"""
    # İlk header'ı değiştir
    lines = base_md.split("\n")
    start_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("---"):
            start_idx = i + 1
            break

    return header + "\n".join(lines[start_idx:])


async def run_single_model(config: dict) -> dict:
    """Tek bir model için simülasyon çalıştır."""
    provider = config["provider"]
    model = config["model"]
    name = config["name"]

    print(f"\n{'='*60}")
    print(f"🚀 {name} ({provider}/{model})")
    print(f"{'='*60}\n")

    start_time = time.time()

    try:
        sim = MultiModelSimulator(provider=provider, model=model)
        entries = await sim.simulate_one_day()
        duration = time.time() - start_time

        # Markdown oluştur
        markdown = generate_markdown_with_model(entries, provider, model, name, duration)

        # Dosya adı
        safe_model = model.replace("/", "-").replace(":", "-")
        output_path = Path(__file__).parent / f"results/simulation_{provider}_{safe_model}.md"
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")

        total_entries = len(entries)
        total_comments = sum(len(e.comments) for e in entries)

        print(f"\n✅ {name} tamamlandı!")
        print(f"   📊 {total_entries} entry, {total_comments} yorum")
        print(f"   ⏱️  {duration:.1f} saniye")
        print(f"   📄 {output_path}")

        return {
            "model": model,
            "provider": provider,
            "name": name,
            "success": True,
            "entries": total_entries,
            "comments": total_comments,
            "duration": duration,
            "output": str(output_path),
        }

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ {name} HATA: {e}")
        import traceback
        traceback.print_exc()

        return {
            "model": model,
            "provider": provider,
            "name": name,
            "success": False,
            "error": str(e),
            "duration": duration,
        }


def generate_summary(results: list) -> str:
    """Karşılaştırma özeti oluştur."""
    lines = [
        "# 📊 Multi-Model Karşılaştırma Sonuçları",
        "",
        f"*Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        "---",
        "",
        "## 📈 Özet Tablo",
        "",
        "| Model | Provider | Entry | Yorum | Süre (sn) | Durum |",
        "|-------|----------|-------|-------|-----------|-------|",
    ]

    for r in results:
        if r["success"]:
            lines.append(
                f"| {r['name']} | {r['provider']} | {r['entries']} | {r['comments']} | {r['duration']:.1f} | ✅ |"
            )
        else:
            lines.append(
                f"| {r['name']} | {r['provider']} | - | - | {r['duration']:.1f} | ❌ |"
            )

    lines.extend(["", "---", "", "## 🔗 Detaylı Sonuçlar", ""])

    for r in results:
        if r["success"]:
            lines.append(f"- [{r['name']}]({Path(r['output']).name})")

    # İstatistikler
    successful = [r for r in results if r["success"]]
    if successful:
        avg_entries = sum(r["entries"] for r in successful) / len(successful)
        avg_comments = sum(r["comments"] for r in successful) / len(successful)
        avg_duration = sum(r["duration"] for r in successful) / len(successful)

        lines.extend([
            "",
            "---",
            "",
            "## 📊 İstatistikler",
            "",
            f"- Başarılı model: {len(successful)}/{len(results)}",
            f"- Ortalama entry: {avg_entries:.1f}",
            f"- Ortalama yorum: {avg_comments:.1f}",
            f"- Ortalama süre: {avg_duration:.1f} saniye",
        ])

    return "\n".join(lines)


async def main():
    print("🎯 Multi-Model Karşılaştırma Testi")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 {len(MODELS)} model test edilecek\n")

    # Modelleri listele
    print("Modeller:")
    for m in MODELS:
        print(f"  - {m['name']} ({m['provider']}/{m['model']})")

    results = []

    # Her model için sırayla çalıştır
    for config in MODELS:
        result = await run_single_model(config)
        results.append(result)
        # Rate limit için bekle
        await asyncio.sleep(2)

    # Özet oluştur
    summary = generate_summary(results)
    summary_path = Path(__file__).parent / "results/comparison_summary.md"
    summary_path.write_text(summary, encoding="utf-8")

    print(f"\n{'='*60}")
    print("🏁 TÜM TESTLER TAMAMLANDI")
    print(f"{'='*60}")
    print(f"\n📄 Özet: {summary_path}")

    # Sonuç özeti
    successful = sum(1 for r in results if r["success"])
    print(f"\n✅ Başarılı: {successful}/{len(results)}")

    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"   {status} {r['name']}")


if __name__ == "__main__":
    asyncio.run(main())
