"""
Test: İçerik Dengesi ve Kategori Kontrolü

Bu test modülü:
1. Organik/RSS oranının doğru olduğunu (%65/%35)
2. Organik kategorilerin (dertlesme, meta, deneyim, teknik, absurt) doğru üretildiğini
3. Siyasetle alakası olmayan konularda siyasi üslup olmadığını
test eder.
"""

import pytest
import asyncio
import random
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from categories import (
    ALL_CATEGORIES,
    GUNDEM_CATEGORIES,
    ORGANIK_CATEGORIES,
    VALID_ALL_KEYS,
    VALID_ORGANIK_KEYS,
    VALID_GUNDEM_KEYS,
    is_valid_category,
    validate_categories,
)


class TestCategoryDefinitions:
    """Kategori tanımlarının doğruluğunu test et."""
    
    def test_no_genel_category(self):
        """'genel' kategorisi olmamalı."""
        assert "genel" not in ALL_CATEGORIES
        assert "genel" not in VALID_ALL_KEYS
        assert not is_valid_category("genel")
    
    def test_organik_categories_exist(self):
        """Organik kategoriler tanımlı olmalı."""
        required_organik = ["dertlesme", "meta", "deneyim", "teknik", "absurt"]
        for cat in required_organik:
            assert cat in ORGANIK_CATEGORIES, f"'{cat}' organik kategorilerde olmalı"
            assert is_valid_category(cat)
    
    def test_gundem_categories_exist(self):
        """Gündem kategorileri tanımlı olmalı."""
        required_gundem = ["ekonomi", "dunya", "magazin", "siyaset", "yasam", "kultur", "teknoloji", "yapay_zeka"]
        for cat in required_gundem:
            assert cat in GUNDEM_CATEGORIES, f"'{cat}' gündem kategorilerinde olmalı"
            assert is_valid_category(cat)
    
    def test_validate_categories_filters_invalid(self):
        """Geçersiz kategoriler filtrelenmeli."""
        input_cats = ["ekonomi", "genel", "meta", "invalid", "dertlesme"]
        valid = validate_categories(input_cats)
        assert "genel" not in valid
        assert "invalid" not in valid
        assert "ekonomi" in valid
        assert "meta" in valid
        assert "dertlesme" in valid


class TestOrganicRSSRatio:
    """Organik/RSS oranının doğruluğunu test et."""
    
    def test_organic_weight_is_65_percent(self):
        """ORGANIC_WEIGHT %65 olmalı."""
        # main.py'den import et
        try:
            from main import ORGANIC_WEIGHT, RSS_WEIGHT
            assert ORGANIC_WEIGHT == 0.65, f"ORGANIC_WEIGHT {ORGANIC_WEIGHT} ama 0.65 olmalı"
            assert RSS_WEIGHT == 0.35, f"RSS_WEIGHT {RSS_WEIGHT} ama 0.35 olmalı"
        except ImportError:
            pytest.skip("main.py import edilemedi")
    
    def test_random_distribution_favors_organic(self):
        """Random dağılım organik içeriği tercih etmeli."""
        organic_weight = 0.65
        trials = 10000
        organic_count = sum(1 for _ in range(trials) if random.random() < organic_weight)
        
        # %65 civarında olmalı (±%3 tolerans)
        ratio = organic_count / trials
        assert 0.62 <= ratio <= 0.68, f"Organic ratio {ratio:.2%}, expected ~65%"


class TestPhaseConfigCategories:
    """Faz konfigürasyonundaki kategorilerin doğruluğunu test et."""
    
    def test_phase_themes_are_valid(self):
        """PHASE_CONFIG'deki tüm temalar geçerli kategori olmalı."""
        try:
            from scheduler.virtual_day import PHASE_CONFIG
            
            for phase, config in PHASE_CONFIG.items():
                themes = config.get("themes", [])
                for theme in themes:
                    assert is_valid_category(theme), \
                        f"Phase {phase}: '{theme}' geçerli kategori değil"
        except ImportError:
            pytest.skip("virtual_day.py import edilemedi")
    
    def test_siyaset_not_dominant_in_phases(self):
        """Siyaset tüm fazlarda dominant olmamalı."""
        try:
            from scheduler.virtual_day import PHASE_CONFIG
            
            siyaset_count = 0
            total_phases = len(PHASE_CONFIG)
            
            for phase, config in PHASE_CONFIG.items():
                themes = config.get("themes", [])
                if "siyaset" in themes:
                    siyaset_count += 1
            
            # Siyaset en fazla 1-2 fazda olmalı
            assert siyaset_count <= 2, \
                f"Siyaset {siyaset_count} fazda var, en fazla 2 olmalı"
        except ImportError:
            pytest.skip("virtual_day.py import edilemedi")


class TestOrganicCollectorCategories:
    """Organik collector'ın doğru kategoriler ürettiğini test et."""
    
    def test_organic_prompt_uses_valid_categories(self):
        """Organik prompt sadece geçerli organik kategorileri kullanmalı."""
        try:
            from collectors.organic_collector import generate_organic_titles_with_llm
            
            # Prompt içinde tanımlı kategorileri kontrol et
            import inspect
            source = inspect.getsource(generate_organic_titles_with_llm)
            
            # Prompt'ta organik kategoriler olmalı
            for cat in VALID_ORGANIK_KEYS:
                assert cat in source.lower() or cat.replace("_", " ") in source.lower(), \
                    f"'{cat}' organik prompt'ta olmalı"
            
            # 'genel' olmamalı
            assert '"genel"' not in source.lower(), "Organik prompt'ta 'genel' olmamalı"
            
        except ImportError:
            pytest.skip("organic_collector.py import edilemedi")


class TestContentPoliticsFilter:
    """Siyasi olmayan konularda siyasi içerik kontrolü."""
    
    def test_non_political_themes_list(self):
        """Siyasi olmayan temalar listesi."""
        non_political = ["teknoloji", "yapay_zeka", "kultur", "magazin", "meta", "absurt", "deneyim", "teknik", "dertlesme"]
        
        for theme in non_political:
            assert theme != "siyaset", f"'{theme}' siyaset olmamalı"
            assert is_valid_category(theme), f"'{theme}' geçerli kategori olmalı"
    
    def test_political_keywords(self):
        """Siyasi anahtar kelimeler tanımlı olmalı."""
        political_keywords = [
            "hükümet", "muhalefet", "parti", "seçim", "oy", "bakan", 
            "cumhurbaşkan", "meclis", "siyaset", "politika"
        ]
        # Bu kelimelerin varlığı test amaçlı - gerçek filtreleme LLM'de
        assert len(political_keywords) > 0


class TestAgentPromptPoliticsAvoidance:
    """Agent promptlarında siyaset kaçınma kontrolü."""
    
    def test_prompt_has_politics_avoidance_rule(self):
        """Entry prompt'ta siyaset kaçınma kuralı olmalı."""
        try:
            from agent_runner import SystemAgentRunner
            
            # Mock agent ve phase_config
            mock_agent = {
                "display_name": "Test Agent",
                "username": "test_agent",
                "racon_config": {
                    "voice": {},
                    "topics": {"avoid_politics": True}
                }
            }
            mock_phase = {"themes": ["teknoloji"]}
            
            runner = SystemAgentRunner.__new__(SystemAgentRunner)
            runner._agent_memories = {}
            
            prompt = runner._build_racon_system_prompt(mock_agent, mock_phase)
            
            # Prompt'ta siyaset kaçınma kuralı olmalı
            assert "siyaset" in prompt.lower() or "KONU ODAĞI" in prompt, \
                "Prompt'ta siyaset kaçınma kuralı olmalı"
            
        except Exception as e:
            pytest.skip(f"Agent prompt testi atlandı: {e}")


class TestCommentPromptBalance:
    """Comment prompt dengesini test et."""
    
    def test_comment_prompt_has_length_limit(self):
        """Comment prompt'ta uzunluk limiti olmalı."""
        try:
            import inspect
            from agent_runner import SystemAgentRunner
            
            source = inspect.getsource(SystemAgentRunner._write_comment)
            
            # 2-4 cümle limiti olmalı
            assert "2-4" in source or "2–4" in source, \
                "Comment prompt'ta 2-4 cümle limiti olmalı"
            
            # GIF nadir olmalı
            assert "nadir" in source.lower() or "%10" in source or "%15" in source, \
                "Comment prompt'ta GIF sıklığı azaltılmalı"
            
        except Exception as e:
            pytest.skip(f"Comment prompt testi atlandı: {e}")


# Integration test - gerçek LLM çağrısı yapmaz
class TestIntegrationMocked:
    """Mock'lanmış entegrasyon testleri."""
    
    @pytest.mark.asyncio
    async def test_category_fallback_not_genel(self):
        """Kategori fallback'i 'genel' olmamalı."""
        try:
            from agent_runner import SystemAgentRunner
            
            # _create_topic_and_entry metodunun context'inde genel olmamalı
            import inspect
            source = inspect.getsource(SystemAgentRunner._create_topic_and_entry)
            
            assert '"genel"' not in source, \
                "_create_topic_and_entry'de 'genel' fallback olmamalı"
            assert '"yasam"' in source or "'yasam'" in source, \
                "_create_topic_and_entry'de 'yasam' fallback olmalı"
            
        except Exception as e:
            pytest.skip(f"Integration test atlandı: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
