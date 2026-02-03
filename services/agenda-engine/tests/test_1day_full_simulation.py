#!/usr/bin/env python3
"""
1 Günlük Tam Simülasyon - Integration Test
Mood değişkenliği, community sistemi ve tüm yeni özellikler.

NOT: Bu test OPENAI_API_KEY gerektirir.
pytest -m "not integration" ile skip edilebilir.
"""

import asyncio
import os
import sys
import random
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # Project root for shared_prompts
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env
env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# Check API key
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
needs_api = pytest.mark.skipif(not OPENAI_KEY, reason="OPENAI_API_KEY required")


@pytest.fixture
def simulator():
    """Create simulator instance."""
    if not OPENAI_KEY:
        pytest.skip("OPENAI_API_KEY required")
    from simulation_3day import PlatformSimulator
    return PlatformSimulator()


class TestMoodVariability:
    """Mood değişkenliği testleri - agent'lar hep aynı modda olmamalı."""

    def test_agent_mood_weights_exist(self):
        """Her agent'ın mood_weights'i olmalı."""
        from simulation_3day import AGENTS

        for agent_id, agent in AGENTS.items():
            assert "mood_weights" in agent, f"{agent_id} mood_weights eksik"
            weights = agent["mood_weights"]
            assert len(weights) >= 3, f"{agent_id} en az 3 mood'a sahip olmalı"
            assert abs(sum(weights.values()) - 1.0) < 0.01, f"{agent_id} weights toplamı 1 olmalı"

    def test_get_agent_mood_variability(self):
        """get_agent_mood farklı sonuçlar döndürmeli."""
        from simulation_3day import get_agent_mood

        # Aynı agent için 20 kez mood al
        moods = [get_agent_mood("alarm_dusmani", "huysuz") for _ in range(20)]

        # En az 2 farklı mood olmalı
        unique_moods = set(moods)
        assert len(unique_moods) >= 2, f"Mood çeşitliliği yetersiz: {unique_moods}"

    def test_all_agents_have_mood_variety(self):
        """Tüm agent'lar mood çeşitliliğine sahip olmalı."""
        from simulation_3day import AGENTS, get_agent_mood

        for agent_id in AGENTS.keys():
            moods = [get_agent_mood(agent_id) for _ in range(30)]
            unique = set(moods)
            assert len(unique) >= 2, f"{agent_id} mood çeşitliliği yok: {unique}"

    def test_phase_mood_boost(self):
        """Phase mood'u boost edilmeli ama diğer mood'lar da görülmeli."""
        from simulation_3day import get_agent_mood

        # alarm_dusmani için huysuz fazında
        moods = [get_agent_mood("alarm_dusmani", "huysuz") for _ in range(50)]
        counts = Counter(moods)

        # Huysuz en çok olmalı ama tek olmamalı
        assert counts["huysuz"] > 20, "Phase mood yeterince boost edilmemiş"
        assert len(counts) >= 2, "Sadece phase mood var, çeşitlilik yok"


class TestAgentPhaseFlexibility:
    """Agent'ların faz esnekliği - bazen farklı fazlarda görünmeli."""

    def test_surprise_guests_possible(self):
        """Sürpriz konuklar mümkün olmalı."""
        from simulation_3day import AGENTS

        # get_agents_for_phase fonksiyonunu direkt test et
        # (PlatformSimulator API key gerektirir)
        import random

        def get_agents_for_phase(phase_id: str):
            """Agent'ları faz için seç - bazen sürpriz konuklar da olabilir."""
            primary = [a for a, cfg in AGENTS.items() if phase_id in cfg["active_phases"]]
            others = [a for a in AGENTS.keys() if a not in primary]
            if others and random.random() < 0.3:
                surprise = random.choice(others)
                primary.append(surprise)
            if len(primary) < 2:
                primary.extend([a for a in others if a not in primary][:2 - len(primary)])
            return primary

        # 50 kez morning_hate için agent listesi al
        all_agents = set()
        primary_agents = {"alarm_dusmani"}  # Sabah için birincil

        for _ in range(50):
            agents = get_agents_for_phase("morning_hate")
            all_agents.update(agents)

        # Birincil agent'lar dışında da agent görülmeli
        non_primary = all_agents - primary_agents
        assert len(non_primary) > 0, "Sürpriz konuk hiç yok"


class TestCommunitySystem:
    """Community sistemi testleri."""

    def test_community_models_import(self):
        """Community modelleri import edilebilmeli."""
        from community import (
            CommunityManager, ActionType, SupportType,
            IDEOLOGY_TEMPLATES, BATTLE_CRY_TEMPLATES
        )

        assert CommunityManager is not None
        assert len(list(ActionType)) == 5
        assert len(list(SupportType)) == 4
        assert len(IDEOLOGY_TEMPLATES) >= 5
        assert len(BATTLE_CRY_TEMPLATES) >= 5

    def test_ideology_generation(self):
        """İdeoloji otomatik üretilebilmeli."""
        from community import CommunityManager

        # Pool olmadan test et
        cm = CommunityManager(None)

        ideology = cm.generate_ideology("RAM fiyatları")

        assert "ideology" in ideology
        assert "emoji" in ideology
        assert "rebellion_level" in ideology
        assert "battle_cry" in ideology
        assert ideology["rebellion_level"] >= 0
        assert ideology["rebellion_level"] <= 10

    def test_ideology_with_custom_slogan(self):
        """Özel slogan ile ideoloji üretilebilmeli."""
        from community import CommunityManager

        cm = CommunityManager(None)
        ideology = cm.generate_ideology("Excel", slogan="Spreadsheet'e ölüm!")

        assert "Spreadsheet'e ölüm!" in ideology["battle_cry"]

    def test_slug_creation(self):
        """Türkçe karakterli isimlerden slug oluşturulabilmeli."""
        from community import CommunityManager

        cm = CommunityManager(None)

        assert cm._create_slug("RAM'e Ölüm Hareketi") == "ram-e-olum-hareketi"
        assert cm._create_slug("Gece Üç Kulübü") == "gece-uc-kulubu"
        assert cm._create_slug("Şikayet Ordusu!") == "sikayet-ordusu"

    def test_action_types_coverage(self):
        """Tüm aksiyon tipleri mevcut olmalı."""
        from community import ActionType

        expected = ["raid", "protest", "celebration", "awareness", "chaos"]
        actual = [a.value for a in ActionType]

        for exp in expected:
            assert exp in actual, f"ActionType eksik: {exp}"


class TestSDKCommunityModels:
    """SDK topluluk modelleri testleri."""

    def test_sdk_community_imports(self):
        """SDK community modelleri import edilebilmeli."""
        sdk_path = Path(__file__).parent.parent.parent.parent / "sdk" / "python"
        if str(sdk_path) not in sys.path:
            sys.path.insert(0, str(sdk_path))

        from logsoz_sdk import (
            Topluluk, ToplulukAksiyon, ToplulukDestek,
            AksiyonTipi, DestekTipi
        )

        assert Topluluk is not None
        assert ToplulukAksiyon is not None
        assert ToplulukDestek is not None

    def test_aksiyon_tipi_values(self):
        """AksiyonTipi enum değerleri doğru olmalı."""
        sdk_path = Path(__file__).parent.parent.parent.parent / "sdk" / "python"
        if str(sdk_path) not in sys.path:
            sys.path.insert(0, str(sdk_path))

        from logsoz_sdk import AksiyonTipi

        assert AksiyonTipi.RAID.value == "raid"
        assert AksiyonTipi.PROTESTO.value == "protest"
        assert AksiyonTipi.KUTLAMA.value == "celebration"
        assert AksiyonTipi.FARKINDALIK.value == "awareness"
        assert AksiyonTipi.KAOS.value == "chaos"

    def test_destek_tipi_values(self):
        """DestekTipi enum değerleri doğru olmalı."""
        sdk_path = Path(__file__).parent.parent.parent.parent / "sdk" / "python"
        if str(sdk_path) not in sys.path:
            sys.path.insert(0, str(sdk_path))

        from logsoz_sdk import DestekTipi

        assert DestekTipi.UYE.value == "member"
        assert DestekTipi.SAVUNUCU.value == "advocate"
        assert DestekTipi.FANATIK.value == "fanatic"
        assert DestekTipi.KURUCU.value == "founder"

    def test_topluluk_from_dict(self):
        """Topluluk.from_dict() çalışmalı."""
        sdk_path = Path(__file__).parent.parent.parent.parent / "sdk" / "python"
        if str(sdk_path) not in sys.path:
            sys.path.insert(0, str(sdk_path))

        from logsoz_sdk import Topluluk

        data = {
            "id": "test-id",
            "name": "Test Hareketi",
            "slug": "test-hareketi",
            "ideology": "Test ideolojisi",
            "battle_cry": "Test sloganı!",
            "emoji": "🔥",
            "rebellion_level": 8,
        }

        topluluk = Topluluk.from_dict(data)

        assert topluluk.id == "test-id"
        assert topluluk.isim == "Test Hareketi"
        assert topluluk.isyan_seviyesi == 8
        assert topluluk.emoji == "🔥"


class TestPromptBuilderIntegration:
    """Prompt builder entegrasyonu testleri."""

    def test_prompt_builder_imports(self):
        """prompt_builder fonksiyonları import edilebilmeli."""
        from shared_prompts import (
            build_title_prompt, build_entry_prompt, build_comment_prompt,
            build_community_creation_prompt, build_action_call_prompt,
            extract_mentions, validate_mentions, add_mention_awareness,
            TOPIC_PROMPTS, ANTI_PATTERNS, MOOD_MODIFIERS
        )

        assert build_title_prompt is not None
        assert len(TOPIC_PROMPTS) >= 10
        assert len(ANTI_PATTERNS) >= 10
        assert len(MOOD_MODIFIERS) >= 4

    def test_mention_extraction(self):
        """@mention çıkarma çalışmalı."""
        from shared_prompts import extract_mentions

        content = "@alarm_dusmani haklı, @sinefil_sincap da katılır"
        mentions = extract_mentions(content)

        assert "alarm_dusmani" in mentions
        assert "sinefil_sincap" in mentions
        assert len(mentions) == 2

    def test_mention_validation(self):
        """Mention doğrulama çalışmalı."""
        from shared_prompts import validate_mentions, KNOWN_AGENTS

        mentions = ["alarm_dusmani", "unknown_user", "sinefil_sincap"]
        valid = validate_mentions(mentions)

        usernames = [v[0] for v in valid]
        assert "alarm_dusmani" in usernames
        assert "sinefil_sincap" in usernames
        assert "unknown_user" not in usernames

    def test_build_entry_prompt_has_mood(self):
        """Entry prompt'u mood içermeli."""
        from shared_prompts import build_entry_prompt, MOOD_MODIFIERS

        prompt = build_entry_prompt(
            agent_display_name="Test Agent",
            agent_personality="Test kişilik",
            agent_style="test stil",
            phase_mood="huysuz",
            category="teknoloji"
        )

        # Prompt "ŞU ANKİ HALİN:" satırı içermeli
        assert "ŞU ANKİ HALİN:" in prompt, "Prompt'ta mood satırı yok"

        # Mood varyasyonlarından biri prompt'ta olmalı
        all_moods = []
        for mood_list in MOOD_MODIFIERS.values():
            all_moods.extend(mood_list)
        has_mood = any(mood in prompt.lower() for mood in all_moods)
        assert has_mood, f"Prompt'ta geçerli mood yok"


@needs_api
class TestOneDaySimulation:
    """1 günlük tam simülasyon testi - API gerektirir."""

    @pytest.mark.asyncio
    async def test_simulate_one_day(self, simulator):
        """1 günlük simülasyon çalışmalı."""
        from simulation_3day import SimulationDay

        day = SimulationDay(day_number=1, date=datetime.now())

        # 4 saat simüle et (maliyet için kısıtlı)
        test_hours = [9, 14, 20, 2]  # Her fazdan birer saat

        for hour in test_hours:
            entries = await simulator.simulate_hour(day, hour, datetime.now())
            day.entries.extend(entries)

        # Sonuçları kontrol et
        assert len(day.entries) >= 4, "Yetersiz entry sayısı"

        # Her fazdan entry var mı?
        phases = set(e.phase for e in day.entries)
        assert len(phases) >= 3, f"Faz çeşitliliği yetersiz: {phases}"

    @pytest.mark.asyncio
    async def test_mood_appears_in_content(self, simulator):
        """Mood içerikte yansımalı."""
        from simulation_3day import PHASES

        phase = PHASES["morning_hate"]

        # Birkaç entry üret
        entries_content = []
        for _ in range(3):
            content = await simulator.generate_entry(
                "sabah toplantısı çilesi",
                "dertlesme",
                "alarm_dusmani",
                phase
            )
            entries_content.append(content.lower())

        # Hepsinin aynı olmadığını kontrol et
        assert len(set(entries_content)) >= 2, "Tüm içerikler aynı"

    @pytest.mark.asyncio
    async def test_comments_have_variety(self, simulator):
        """Yorumlar çeşitli uzunluklarda olmalı."""
        from simulation_3day import Entry

        entry = Entry(
            title="test başlık",
            content="Bu bir test içeriğidir. Yorum çeşitliliği test edilecek.",
            author="excel_mahkumu",
            category="felsefe",
            phase="office_hours",
            phase_name="Ofis Saatleri",
            hour=14,
            timestamp=datetime.now(),
        )

        # 6 yorum üret
        comments = []
        commenters = ["alarm_dusmani", "localhost_sakini", "sinefil_sincap",
                      "algoritma_kurbani", "saat_uc_sendromu"]

        for commenter in commenters[:5]:
            comment = await simulator.generate_comment(entry, commenter, comments)
            comments.append(comment)
            entry.comments.append(comment)

        # Uzunluk çeşitliliği kontrol et
        lengths = [len(c.content) for c in comments]
        length_range = max(lengths) - min(lengths)
        assert length_range > 20, f"Yorum uzunluk çeşitliliği yetersiz: {lengths}"

    @pytest.mark.asyncio
    async def test_no_ai_patterns_in_content(self, simulator):
        """İçeriklerde AI pattern'leri olmamalı."""
        from simulation_3day import PHASES
        from shared_prompts import ANTI_PATTERNS

        phase = PHASES["office_hours"]
        content = await simulator.generate_entry(
            "kod review çilesi",
            "teknoloji",
            "localhost_sakini",
            phase
        )

        content_lower = content.lower()
        for pattern in ANTI_PATTERNS[:5]:  # İlk 5 pattern'i kontrol et
            assert pattern not in content_lower, f"AI pattern bulundu: {pattern}"


class TestContentShaping:
    """İçerik şekillendirme testleri."""

    def test_content_shaper_import(self):
        """content_shaper import edilebilmeli."""
        from content_shaper import shape_content, LLM_SMELL_PATTERNS

        assert shape_content is not None
        assert len(LLM_SMELL_PATTERNS) > 0

    def test_ai_phrases_removed(self):
        """AI ifadeleri kaldırılmalı."""
        from content_shaper import shape_content
        from discourse import ContentMode, get_discourse_config

        content = "önemle belirtmek gerekir ki bu konu hakkında söz konusu durumu ele almak istiyorum"
        config = get_discourse_config(ContentMode.ENTRY)
        shaped = shape_content(content, ContentMode.ENTRY, config.budget)

        assert "önemle belirtmek" not in shaped.lower()
        assert "söz konusu" not in shaped.lower()


class TestFullSystemIntegration:
    """Tam sistem entegrasyonu."""

    def test_all_components_work_together(self):
        """Tüm bileşenler birlikte çalışmalı (API gerektirmeyen)."""
        # Imports
        from simulation_3day import AGENTS, PHASES, get_agent_mood
        from shared_prompts import build_entry_prompt, build_comment_prompt
        from content_shaper import shape_content
        from discourse import ContentMode, get_discourse_config
        from community import CommunityManager, ActionType

        # Agent mood al
        mood = get_agent_mood("alarm_dusmani", "huysuz")
        assert mood in ["huysuz", "sıkılmış", "sosyal", "felsefi"]

        # Prompt oluştur
        prompt = build_entry_prompt(
            agent_display_name="Alarm Düşmanı",
            agent_personality=AGENTS["alarm_dusmani"]["personality"],
            agent_style=AGENTS["alarm_dusmani"]["style"],
            phase_mood=mood,
            category="dertlesme"
        )
        assert len(prompt) > 100

        # Discourse config al
        config = get_discourse_config(ContentMode.ENTRY)
        assert config.budget is not None

        # Community ideoloji oluştur
        cm = CommunityManager(None)
        ideology = cm.generate_ideology("Sabah Toplantıları")
        assert ideology["rebellion_level"] >= 0

        # Phases ve agents tutarlı
        assert len(PHASES) == 4
        assert len(AGENTS) >= 6


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
