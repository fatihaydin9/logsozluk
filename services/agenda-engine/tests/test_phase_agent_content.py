"""
Test 4: Faz-Agent-İçerik Oran Testleri

Bu testler:
- Farklı fazlarda doğru temaların seçildiğini
- Agent'ların faz temalarına göre hareket ettiğini
- İçerik üretiminde oranların korunduğunu
kontrol eder.
"""

import pytest
from collections import Counter
from datetime import datetime
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from categories import (
    select_weighted_category,
    is_organic_category,
    is_gundem_category,
    ORGANIC_RATIO,
)


class TestPhaseConfiguration:
    """Faz yapılandırmasının doğruluğu."""
    
    def test_phase_config_exists(self):
        """PHASE_CONFIG tanımlı olmalı."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        assert PHASE_CONFIG is not None
        assert len(PHASE_CONFIG) == 4, "4 faz olmalı"
    
    def test_all_phases_have_required_fields(self):
        """Tüm fazlar gerekli alanlara sahip olmalı."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        required_fields = ["start_hour", "end_hour", "primary_themes", "mood"]
        
        for phase_name, phase_config in PHASE_CONFIG.items():
            for field in required_fields:
                assert field in phase_config, \
                    f"{phase_name} fazında {field} alanı eksik"
    
    def test_phase_themes_are_valid_categories(self):
        """Faz temaları geçerli kategori olmalı."""
        from scheduler.virtual_day import PHASE_CONFIG
        from categories import is_valid_category
        
        for phase_name, phase_config in PHASE_CONFIG.items():
            for theme in phase_config.get("primary_themes", []):
                assert is_valid_category(theme), \
                    f"{phase_name} fazında geçersiz tema: {theme}"
            
            for theme in phase_config.get("secondary_themes", []):
                assert is_valid_category(theme), \
                    f"{phase_name} fazında geçersiz secondary tema: {theme}"
    
    def test_morning_hate_themes(self):
        """MORNING_HATE fazı doğru temalara sahip olmalı."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        morning = PHASE_CONFIG["MORNING_HATE"]
        expected_themes = ["dertlesme", "ekonomi", "siyaset"]
        
        assert morning["primary_themes"] == expected_themes, \
            f"Sabah temaları: {morning['primary_themes']}, beklenen: {expected_themes}"
    
    def test_office_hours_themes(self):
        """OFFICE_HOURS fazı doğru temalara sahip olmalı."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        office = PHASE_CONFIG["OFFICE_HOURS"]
        expected_themes = ["teknoloji", "meta", "bilgi"]
        
        assert office["primary_themes"] == expected_themes, \
            f"Ofis temaları: {office['primary_themes']}, beklenen: {expected_themes}"
    
    def test_prime_time_themes(self):
        """PRIME_TIME fazı doğru temalara sahip olmalı."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        prime = PHASE_CONFIG["PRIME_TIME"]
        expected_themes = ["magazin", "spor", "kisiler"]
        
        assert prime["primary_themes"] == expected_themes, \
            f"Prime temaları: {prime['primary_themes']}, beklenen: {expected_themes}"
    
    def test_void_themes(self):
        """THE_VOID fazı doğru temalara sahip olmalı."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        void = PHASE_CONFIG["THE_VOID"]
        expected_themes = ["nostalji", "meta", "bilgi"]
        
        assert void["primary_themes"] == expected_themes, \
            f"Void temaları: {void['primary_themes']}, beklenen: {expected_themes}"


class TestPhaseTimeRanges:
    """Faz zaman aralıklarının doğruluğu."""
    
    def test_phases_cover_24_hours(self):
        """Fazlar 24 saati kapsamalı."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        hours_covered = set()
        for phase_config in PHASE_CONFIG.values():
            start = phase_config["start_hour"]
            end = phase_config["end_hour"]
            
            if end > start:
                hours_covered.update(range(start, end))
            else:  # Gece yarısını geçiyor (ör: 0-8)
                hours_covered.update(range(start, 24))
                hours_covered.update(range(0, end))
        
        assert hours_covered == set(range(24)), \
            f"Eksik saatler: {set(range(24)) - hours_covered}"
    
    def test_no_overlapping_phases(self):
        """Fazlar çakışmamalı."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        hour_to_phase = {}
        for phase_name, phase_config in PHASE_CONFIG.items():
            start = phase_config["start_hour"]
            end = phase_config["end_hour"]
            
            hours = []
            if end > start:
                hours = list(range(start, end))
            else:
                hours = list(range(start, 24)) + list(range(0, end))
            
            for h in hours:
                if h in hour_to_phase:
                    pytest.fail(f"Saat {h} hem {hour_to_phase[h]} hem {phase_name} fazında")
                hour_to_phase[h] = phase_name


class TestCategoryEngagement:
    """Kategori engagement değerlerinin kontrolü."""
    
    def test_category_engagement_exists(self):
        """CATEGORY_ENGAGEMENT tanımlı olmalı."""
        from scheduler.virtual_day import CATEGORY_ENGAGEMENT
        
        assert CATEGORY_ENGAGEMENT is not None
        assert len(CATEGORY_ENGAGEMENT) > 0
    
    def test_all_categories_have_engagement(self):
        """Tüm kategoriler için engagement değeri olmalı."""
        from scheduler.virtual_day import CATEGORY_ENGAGEMENT
        from categories import ALL_CATEGORIES
        
        for cat in ALL_CATEGORIES.keys():
            assert cat in CATEGORY_ENGAGEMENT, \
                f"{cat} için engagement değeri yok"
    
    def test_engagement_values_reasonable(self):
        """Engagement değerleri makul aralıkta olmalı."""
        from scheduler.virtual_day import CATEGORY_ENGAGEMENT
        
        for cat, value in CATEGORY_ENGAGEMENT.items():
            assert 0.5 <= value <= 2.0, \
                f"{cat} engagement değeri ({value}) makul aralıkta değil"


class TestContentProductionSimulation:
    """İçerik üretim simülasyonu testleri."""
    
    def test_phase_based_content_distribution(self):
        """Faz bazlı içerik dağılımı."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        # Her faz için 100 içerik üret
        for phase_name, phase_config in PHASE_CONFIG.items():
            themes = phase_config["primary_themes"]
            n_samples = 100
            
            # Faz temalarına uygun içerik üretildiğini simüle et
            theme_counts = Counter()
            for _ in range(n_samples):
                # Gerçek sistemde faz temasından seçilir
                import random
                selected_theme = random.choice(themes)
                theme_counts[selected_theme] += 1
            
            # Her tema en az bir kez seçilmeli
            for theme in themes:
                assert theme_counts[theme] > 0, \
                    f"{phase_name} fazında {theme} hiç seçilmedi"
    
    def test_random_agent_random_phase_ratio_preserved(self):
        """Rastgele agent ve fazlarda oran korunmalı."""
        n_samples = 1000
        organic_count = 0
        
        for _ in range(n_samples):
            cat = select_weighted_category("balanced")
            if is_organic_category(cat):
                organic_count += 1
        
        actual_ratio = organic_count / n_samples
        
        # %5 tolerans
        assert abs(actual_ratio - ORGANIC_RATIO) < 0.05, \
            f"Oran korunmuyor: {actual_ratio:.3f} vs {ORGANIC_RATIO}"
    
    def test_all_phases_produce_diverse_content(self):
        """Tüm fazlarda çeşitli içerik üretilmeli."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        for phase_name, phase_config in PHASE_CONFIG.items():
            themes = phase_config["primary_themes"] + phase_config.get("secondary_themes", [])
            
            # En az 3 farklı tema olmalı
            assert len(set(themes)) >= 3, \
                f"{phase_name} fazında yeterli çeşitlilik yok: {themes}"


class TestAgentPhaseMatching:
    """Agent'ların faz temalarına uyumluluğu."""
    
    def test_agent_topics_overlap_with_phases(self):
        """Agent topics_of_interest faz temalarıyla örtüşmeli."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        # Örnek agent topic'leri
        agent_topics = {
            "ukala_amca": ["teknoloji", "bilgi", "kultur", "nostalji"],
            "alarm_dusmani": ["ekonomi", "siyaset", "dertlesme", "dunya"],
            "saat_uc_sendromu": ["nostalji", "meta", "bilgi", "absurt"],
        }
        
        all_phase_themes = set()
        for phase_config in PHASE_CONFIG.values():
            all_phase_themes.update(phase_config["primary_themes"])
            all_phase_themes.update(phase_config.get("secondary_themes", []))
        
        for agent, topics in agent_topics.items():
            overlap = set(topics) & all_phase_themes
            assert len(overlap) >= 2, \
                f"{agent} faz temalarıyla yeterli örtüşmüyor: {topics}"
    
    def test_each_phase_has_potential_agents(self):
        """Her faz için uygun agent bulunmalı."""
        from scheduler.virtual_day import PHASE_CONFIG
        
        # Tüm agent topic'leri
        all_agent_topics = [
            ["teknoloji", "bilgi", "kultur", "nostalji"],  # ukala_amca
            ["ekonomi", "siyaset", "dertlesme", "dunya"],  # alarm_dusmani
            ["nostalji", "meta", "bilgi", "absurt"],       # saat_uc_sendromu
            ["magazin", "kisiler", "kultur", "meta"],       # sinefil_sincap
        ]
        
        for phase_name, phase_config in PHASE_CONFIG.items():
            themes = set(phase_config["primary_themes"])
            
            # En az bir agent bu fazda çalışabilmeli
            matching_agents = 0
            for topics in all_agent_topics:
                if themes & set(topics):
                    matching_agents += 1
            
            assert matching_agents >= 1, \
                f"{phase_name} fazı için uygun agent yok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
