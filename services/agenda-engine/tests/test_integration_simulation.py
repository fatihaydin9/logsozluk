#!/usr/bin/env python3
"""
Integration Tests - Gerçek LLM Sistemi Testleri
Template yok, gerçek API çağrıları yapılır.

NOT: Bu testler OPENAI_API_KEY gerektirir ve API maliyeti oluşturur.
CI/CD'de skip edilebilir: pytest -m "not integration"
"""

import asyncio
import os
import sys
import pytest
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "agents"))

# Load .env
env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# Skip all tests if no API key
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
pytestmark = pytest.mark.skipif(not OPENAI_KEY, reason="OPENAI_API_KEY required for integration tests")


@pytest.fixture
def simulator():
    """Create simulator instance."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from simulation_3day import PlatformSimulator
    return PlatformSimulator()


class TestLLMContentGeneration:
    """Gerçek LLM içerik üretimi testleri."""

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
        "sonuç olarak",
    ]

    @pytest.mark.asyncio
    async def test_generate_topic_title_not_generic(self, simulator):
        """Topic başlıkları spesifik olmalı, genel değil."""
        from simulation_3day import PHASES

        phase = PHASES["office_hours"]
        title = await simulator.generate_title("teknoloji", phase, "localhost_sakini")

        # Başlık boş olmamalı
        assert title and len(title) > 5

        # Genel/sıkıcı başlıklar olmamalı
        generic_patterns = [
            "teknoloji hakkında",
            "düşüncelerim",
            "güncel gelişmeler",
            "yeni trendler",
            "ilginç bilgiler",
        ]
        title_lower = title.lower()
        for pattern in generic_patterns:
            assert pattern not in title_lower, f"Başlık çok genel: {title}"

    @pytest.mark.asyncio
    async def test_generate_entry_has_personality(self, simulator):
        """Entry içeriği agent kişiliğini yansıtmalı."""
        from simulation_3day import PHASES

        phase = PHASES["the_void"]
        content = await simulator.generate_entry(
            "gece 3'te buzdolabını açıp bakmak",
            "nostalji",
            "saat_uc_sendromu",
            phase
        )

        # İçerik boş olmamalı
        assert content and len(content) > 50

        # Yapay ifadeler olmamalı
        ai_patterns = ["önemle belirtmek", "söz konusu", "dikkate almak"]
        content_lower = content.lower()
        for pattern in ai_patterns:
            assert pattern not in content_lower, f"Yapay ifade bulundu: {pattern}"

        # Informative/news ton olmamalı
        for pattern in self.informative_patterns:
            assert pattern not in content_lower, f"Informative ton bulundu: {pattern}"

        # Uzunluk kısıtı (max 4 cümle, max 4 paragraf)
        sentences = [s for s in content.replace("\n", " ").split(".") if s.strip()]
        paragraphs = [p for p in content.split("\n") if p.strip()]
        assert len(sentences) <= 4, f"Çok fazla cümle: {len(sentences)}"
        assert len(paragraphs) <= 4, f"Çok fazla paragraf: {len(paragraphs)}"

    @pytest.mark.asyncio
    async def test_generate_comment_variable_length(self, simulator):
        """Yorumlar değişken uzunlukta olmalı."""
        from simulation_3day import Entry, PHASES

        # Test entry oluştur
        entry = Entry(
            title="test başlık",
            content="Bu bir test entry içeriğidir, yorum almak için yazılmıştır.",
            author="excel_mahkumu",
            category="felsefe",
            phase="office_hours",
            phase_name="Ofis Saatleri",
            hour=14,
            timestamp=datetime.now(),
        )

        # 5 yorum üret
        lengths = []
        for _ in range(5):
            comment = await simulator.generate_comment(entry, "algoritma_kurbani")
            lengths.append(len(comment.content))

        # Uzunluklar değişken olmalı (standart sapma > 20)
        import statistics
        if len(lengths) > 1:
            std_dev = statistics.stdev(lengths)
            # En az biraz çeşitlilik olmalı
            assert std_dev > 10 or max(lengths) - min(lengths) > 30, \
                f"Yorum uzunlukları çok benzer: {lengths}"

    @pytest.mark.asyncio
    async def test_thread_awareness(self, simulator):
        """Yorumcular önceki yorumları görmeli."""
        from simulation_3day import Entry, Comment

        entry = Entry(
            title="thread test",
            content="Bu entry'de birden fazla yorum olacak ve birbirine cevap verecekler.",
            author="localhost_sakini",
            category="felsefe",
            phase="office_hours",
            phase_name="Ofis Saatleri",
            hour=15,
            timestamp=datetime.now(),
        )

        # İlk yorum
        comment1 = await simulator.generate_comment(entry, "sinefil_sincap")
        entry.comments.append(comment1)

        # İkinci yorum (ilk yorumu görmeli)
        comment2 = await simulator.generate_comment(entry, "algoritma_kurbani", [comment1])

        # İkinci yorum boş olmamalı
        assert comment2.content and len(comment2.content) > 0


class TestAgentPersonalities:
    """Agent kişilik tutarlılığı testleri."""

    @pytest.mark.asyncio
    async def test_alarm_dusmani_grumpy_tone(self, simulator):
        """Alarm Düşmanı huysuz ton kullanmalı."""
        from simulation_3day import PHASES

        phase = PHASES["morning_hate"]
        content = await simulator.generate_entry(
            "sabah toplantısına geç kalmak",
            "dertlesme",
            "alarm_dusmani",
            phase
        )

        # Pozitif/neşeli ton olmamalı
        positive_patterns = ["harika", "muhteşem", "çok güzel", "ne kadar iyi"]
        content_lower = content.lower()
        positive_count = sum(1 for p in positive_patterns if p in content_lower)
        assert positive_count < 2, f"Alarm Düşmanı çok pozitif: {content[:100]}"

    @pytest.mark.asyncio
    async def test_sinefil_sincap_film_references(self, simulator):
        """Sinefil Sincap film referansları yapmalı."""
        from simulation_3day import PHASES

        phase = PHASES["prime_time"]

        # Birkaç deneme yap (her zaman referans olmayabilir)
        has_reference = False
        for _ in range(3):
            content = await simulator.generate_entry(
                "yeni çıkan film eleştirisi",
                "kultur",
                "sinefil_sincap",
                phase
            )

            film_keywords = ["film", "sahne", "karakter", "yönetmen", "senaryo", "sinema"]
            if any(kw in content.lower() for kw in film_keywords):
                has_reference = True
                break

        assert has_reference, "Sinefil Sincap hiç film referansı yapmadı"


class TestContentQuality:
    """İçerik kalitesi testleri."""

    @pytest.mark.asyncio
    async def test_no_repetitive_patterns(self, simulator):
        """İçerikler birbirini tekrarlamamalı."""
        from simulation_3day import PHASES

        phase = PHASES["office_hours"]

        # Aynı konuda 3 entry üret
        contents = []
        for _ in range(3):
            content = await simulator.generate_entry(
                "ofis toplantısı sıkıntısı",
                "dertlesme",
                "excel_mahkumu",
                phase
            )
            contents.append(content)

        # Hiçbiri aynı olmamalı
        assert len(set(contents)) == 3, "Tekrarlayan içerik var"

        # Kelime örtüşmesi çok yüksek olmamalı
        def word_overlap(a, b):
            words_a = set(a.lower().split())
            words_b = set(b.lower().split())
            if not words_a or not words_b:
                return 0
            overlap = len(words_a & words_b)
            return overlap / min(len(words_a), len(words_b))

        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                overlap = word_overlap(contents[i], contents[j])
                assert overlap < 0.7, f"İçerikler çok benzer: {overlap:.2%}"

    @pytest.mark.asyncio
    async def test_turkish_naturalness(self, simulator):
        """İçerikler doğal Türkçe olmalı."""
        from simulation_3day import PHASES

        phase = PHASES["the_void"]
        content = await simulator.generate_entry(
            "uyuyamama sorunu",
            "dertlesme",
            "saat_uc_sendromu",
            phase
        )

        # İngilizce kelimeler sınırlı olmalı (teknik terimler hariç)
        english_words = ["the", "and", "with", "from", "that", "this", "what", "have"]
        content_lower = content.lower()
        english_count = sum(f" {w} " in f" {content_lower} " for w in english_words)
        assert english_count < 3, f"Çok fazla İngilizce: {content[:100]}"


class TestSimulationFlow:
    """Simülasyon akışı testleri."""

    @pytest.mark.asyncio
    async def test_simulate_single_hour(self, simulator):
        """Tek saat simülasyonu çalışmalı."""
        from simulation_3day import SimulationDay

        day = SimulationDay(day_number=1, date=datetime.now())
        entries = await simulator.simulate_hour(day, 14, datetime.now())

        # En az 1 entry olmalı
        assert len(entries) >= 1

        # Her entry'nin gerekli alanları olmalı
        for entry in entries:
            assert entry.title
            assert entry.content
            assert entry.author
            assert entry.category

    @pytest.mark.asyncio
    async def test_comments_from_different_authors(self, simulator):
        """Yorumlar farklı yazarlardan gelmeli."""
        from simulation_3day import SimulationDay

        day = SimulationDay(day_number=1, date=datetime.now())
        entries = await simulator.simulate_hour(day, 14, datetime.now())

        # Yorumlu entry bul
        for entry in entries:
            if entry.comments:
                authors = [c.author for c in entry.comments]
                # Yazar entry yazarı olmamalı
                assert entry.author not in authors, "Yazar kendi entry'sine yorum yapmış"
                # Yorumcular unique olmalı
                assert len(authors) == len(set(authors)), "Aynı kişi birden fazla yorum yapmış"
                break


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
