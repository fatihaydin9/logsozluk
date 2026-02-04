"""
Report Generator - Günlük gündem raporu üret.
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

from ..config import get_settings
from .headline_grouper import HeadlineGroup

logger = logging.getLogger(__name__)

# Kategori sıralaması (raporda bu sırayla görünecek)
CATEGORY_ORDER = [
    "ekonomi",
    "siyaset",
    "teknoloji",
    "spor",
    "dunya",
    "kultur",
    "magazin",
]


class ReportGenerator:
    """Markdown formatında günlük rapor üret."""

    def __init__(self):
        self.settings = get_settings()

    async def generate_daily_report(
        self, groups: Dict[str, HeadlineGroup], start_time: float = None
    ) -> str:
        """
        Günlük rapor üret ve dosyaya kaydet.

        Returns:
            Oluşturulan dosyanın path'i
        """
        today = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M")

        # Rapor içeriği oluştur
        lines = [
            f"# GÜNDEM ÖZETİ - {today}",
            "",
        ]

        # İstatistikler
        total_headlines = sum(len(g.headlines) for g in groups.values())
        total_sources = len(set(
            source
            for g in groups.values()
            for source in g.sources
        ))

        # Kategorileri sırala
        sorted_groups = self._sort_groups(groups)

        for group in sorted_groups:
            if not group.headlines:
                continue

            lines.append(f"## {group.category_label.upper()}")
            lines.append("")

            # Özet
            if group.summary:
                lines.append(group.summary)
            else:
                # Fallback: başlık listesi
                for h in group.headlines[:5]:
                    lines.append(f"- {h['title']}")
            lines.append("")

            # Kaynaklar
            source_names = ", ".join(group.sources[:5])
            lines.append(f"*Kaynaklar: {source_names} ({len(group.headlines)} haber)*")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Meta bilgiler
        lines.append("## Meta")
        lines.append(f"- **Toplam:** {total_headlines} haber işlendi")
        lines.append(f"- **Kaynak sayısı:** {total_sources}")

        if start_time:
            elapsed = datetime.now().timestamp() - start_time
            lines.append(f"- **Oluşturma süresi:** {elapsed:.1f} saniye")

        lines.append(f"- **Oluşturma zamanı:** {current_time}")

        # Dosyaya kaydet
        report_content = "\n".join(lines)
        file_path = await self._save_report(report_content, today)

        logger.info(f"Gündem raporu oluşturuldu: {file_path}")
        return file_path

    def _sort_groups(self, groups: Dict[str, HeadlineGroup]) -> list:
        """Grupları kategori sırasına göre sırala."""
        sorted_list = []

        # Önce bilinen kategoriler sırayla
        for cat in CATEGORY_ORDER:
            if cat in groups:
                sorted_list.append(groups[cat])
            # Alt kategorileri de ekle (ekonomi_1, ekonomi_2, etc.)
            for key, group in groups.items():
                if key.startswith(f"{cat}_") and group not in sorted_list:
                    sorted_list.append(group)

        # Sonra bilinmeyen kategoriler
        for key, group in groups.items():
            if group not in sorted_list:
                sorted_list.append(group)

        return sorted_list

    async def _save_report(self, content: str, date_str: str) -> str:
        """Raporu dosyaya kaydet."""
        # Output dizini
        output_dir = Path(self.settings.report_output_dir)

        # Eğer relative path ise, agenda-engine root'una göre çözümle
        if not output_dir.is_absolute():
            base_dir = Path(__file__).parent.parent.parent  # src/../.. = agenda-engine
            output_dir = base_dir / output_dir

        # Dizin yoksa oluştur
        output_dir.mkdir(parents=True, exist_ok=True)

        # Dosya adı
        filename = f"{date_str}_gundem.md"
        file_path = output_dir / filename

        # Yaz
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    async def get_latest_report(self) -> str:
        """En son raporu oku."""
        output_dir = Path(self.settings.report_output_dir)

        if not output_dir.is_absolute():
            base_dir = Path(__file__).parent.parent.parent
            output_dir = base_dir / output_dir

        if not output_dir.exists():
            return ""

        # En yeni .md dosyasını bul
        reports = list(output_dir.glob("*_gundem.md"))
        if not reports:
            return ""

        latest = max(reports, key=lambda p: p.stat().st_mtime)

        with open(latest, "r", encoding="utf-8") as f:
            return f.read()
