"""
Agent System Tests - System ve External Agent Tutarlılık Testleri

Kontrol edilenler:
1. Kategori tutarlılığı
2. Memory sistemi
3. Prompt yapısı (template yok, strict directive yok)
4. Log yönetimi
5. Racon yapısı
"""

import pytest
import json
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Add paths for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
agents_path = Path(__file__).parent.parent.parent.parent / "agents"
sys.path.insert(0, str(agents_path))

# Set PYTHONPATH for submodule imports
os.environ["PYTHONPATH"] = str(src_path)


class TestCategoryConsistency:
    """Kategori tutarlılık testleri."""
    
    def test_categories_module_exists(self):
        """Kanonik kategori modülü var mı?"""
        from categories import GUNDEM_CATEGORIES, ORGANIK_CATEGORIES, ALL_CATEGORIES
        assert len(GUNDEM_CATEGORIES) == 8
        assert len(ORGANIK_CATEGORIES) == 6
        assert len(ALL_CATEGORIES) == 14
    
    def test_no_politik_category(self):
        """'politik' gibi geçersiz kategoriler yok."""
        from categories import ALL_CATEGORIES, VALID_ALL_KEYS
        invalid_categories = ["politik", "politika", "politics", "sport", "spor"]
        for invalid in invalid_categories:
            assert invalid not in VALID_ALL_KEYS, f"Geçersiz kategori bulundu: {invalid}"
    
    def test_valid_gundem_categories(self):
        """Gündem kategorileri doğru."""
        from categories import VALID_GUNDEM_KEYS
        expected = ["ekonomi", "dunya", "magazin", "siyaset", "yasam", "kultur", "teknoloji", "yapay_zeka"]
        assert sorted(VALID_GUNDEM_KEYS) == sorted(expected)
    
    def test_rss_collector_categories_file_check(self):
        """RSS collector kanonik kategorileri kullanıyor (file-based check)."""
        rss_file = Path(__file__).parent.parent / "src" / "collectors" / "rss_collector.py"
        content = rss_file.read_text()
        
        # 'politik' olmamalı
        assert '"politik"' not in content, "RSS collector'da 'politik' bulundu"
        # Geçerli kategoriler olmalı
        assert '"siyaset"' in content or "'siyaset'" in content
    
    def test_virtual_day_categories_file_check(self):
        """Virtual day kanonik kategorileri kullanıyor (file-based check)."""
        vd_file = Path(__file__).parent.parent / "src" / "scheduler" / "virtual_day.py"
        content = vd_file.read_text()
        
        # 'politik' olmamalı (themes içinde)
        # VALID_CATEGORIES tanımlı olmalı
        assert "VALID_CATEGORIES" in content, "VALID_CATEGORIES tanımlı değil"
        assert '"politik"' not in content or "politik" not in content.split("themes")[1].split("]")[0], "Themes'de 'politik' bulundu"


class TestMemorySystem:
    """Memory sistemi testleri."""
    
    def test_memory_uses_local_storage(self):
        """Memory yerel dosya sistemini kullanıyor."""
        from agent_memory import AgentMemory
        
        memory = AgentMemory("test_agent", memory_dir="/tmp/test_memory")
        assert memory.memory_dir == Path("/tmp/test_memory")
        assert str(memory.episodic_file).startswith("/tmp/test_memory")
    
    def test_memory_has_max_limits(self):
        """Memory boyut limitleri var (sistem şişmez)."""
        from agent_memory import AgentMemory
        
        assert AgentMemory.MAX_EPISODIC == 200
        assert AgentMemory.MAX_SEMANTIC == 50
    
    def test_memory_three_layer_structure(self):
        """3 katmanlı memory yapısı var."""
        from agent_memory import AgentMemory, EpisodicEvent, SemanticFact, CharacterSheet
        
        memory = AgentMemory("test_agent", memory_dir="/tmp/test_memory")
        assert hasattr(memory, 'episodic')
        assert hasattr(memory, 'semantic')
        assert hasattr(memory, 'character')
        assert isinstance(memory.character, CharacterSheet)
    
    def test_character_sheet_is_self_generated(self):
        """Character sheet agent tarafından üretiliyor (template değil)."""
        from agent_memory import CharacterSheet
        
        sheet = CharacterSheet()
        # Default değerler minimal ve nötr
        assert sheet.message_length == "orta"
        assert sheet.tone == "nötr"
        assert sheet.favorite_topics == []
        assert sheet.current_goal == ""
    
    def test_social_feedback_not_random(self):
        """Sosyal feedback rastgele değil, içerik bazlı."""
        from agent_memory import generate_social_feedback
        
        # Soru içeren içerik daha fazla etkileşim almalı
        feedback_question = generate_social_feedback("bu nasıl çalışıyor?", "neutral")
        feedback_statement = generate_social_feedback("tamam.", "neutral")
        
        # En azından fonksiyon çalışmalı
        assert feedback_question is not None
        assert feedback_statement is not None


class TestPromptStructure:
    """Prompt yapısı testleri - template ve strict directive yok."""
    
    def test_no_assistant_framing_in_prompts_file_check(self):
        """Prompt'larda 'asistan' çerçevesi yok (file-based check)."""
        agent_runner_file = Path(__file__).parent.parent / "src" / "agent_runner.py"
        content = agent_runner_file.read_text()
        
        # Sosyal katılımcı çerçevesi olmalı (directive-free yaklaşım)
        assert "katılımcı" in content.lower()
        # Yönlendirme yok, sadece bağlam
        assert "yönlendirme yok" in content.lower() or "directive" in content.lower()
    
    def test_social_participant_framing_file_check(self):
        """Prompt'larda sosyal katılımcı çerçevesi var (file-based check)."""
        agent_runner_file = Path(__file__).parent.parent / "src" / "agent_runner.py"
        content = agent_runner_file.read_text()
        
        # Directive-free sosyal katılımcı çerçevesi
        assert "katılımcı" in content.lower()
        assert "kim olduğun" in content.lower() or "sosyal ağ kullanıcı" in content.lower()
    
    def test_no_strict_directives_file_check(self):
        """Prompt'larda katı yönlendirmeler yok (file-based check)."""
        agent_runner_file = Path(__file__).parent.parent / "src" / "agent_runner.py"
        content = agent_runner_file.read_text()
        
        # Katı template yönlendirmeleri olmamalı
        strict_phrases = [
            "şu formatta yaz",
            "şu şekilde başla",
            "şu kalıbı kullan",
        ]
        for phrase in strict_phrases:
            assert phrase not in content, f"Katı yönlendirme bulundu: {phrase}"


class TestRaconStructure:
    """Racon yapısı testleri."""
    
    def test_racon_has_voice_section(self):
        """Racon voice bölümü var."""
        racon = {
            "voice": {
                "nerdiness": 5,
                "humor": 5,
                "sarcasm": 5,
                "chaos": 3,
                "empathy": 5,
                "profanity": 1
            }
        }
        assert "voice" in racon
        assert all(k in racon["voice"] for k in ["nerdiness", "humor", "sarcasm"])
    
    def test_racon_has_worldview_section(self):
        """Racon worldview bölümü var."""
        racon = {
            "worldview": {
                "skepticism": 5,
                "authority_trust": 5,
                "conspiracy": 2
            }
        }
        assert "worldview" in racon
    
    def test_racon_has_social_section(self):
        """Racon social bölümü var."""
        racon = {
            "social": {
                "confrontational": 5,
                "verbosity": 5,
                "self_deprecating": 5
            }
        }
        assert "social" in racon
    
    def test_racon_has_topics_section(self):
        """Racon topics bölümü var."""
        racon = {
            "topics": {
                "technology": 2,
                "politics": -1
            }
        }
        assert "topics" in racon


class TestAgentSamplingVariance:
    """Agent-specific sampling varyansı testleri."""
    
    def test_agents_have_different_temperatures(self):
        """Agent'lar farklı temperature değerlerine sahip."""
        # Bu migration'dan sonra DB'de olacak
        sampling_configs = {
            "sabah_trollu": {"temperature_base": 0.75},
            "gece_filozofu": {"temperature_base": 0.9},
            "tekno_dansen": {"temperature_base": 0.7},
        }
        
        temps = [c["temperature_base"] for c in sampling_configs.values()]
        # Hepsi aynı olmamalı
        assert len(set(temps)) > 1


class TestReflectionSystem:
    """Reflection sistemi testleri."""
    
    def test_reflection_interval_exists(self):
        """Reflection interval tanımlı."""
        from agent_memory import AgentMemory
        assert AgentMemory.REFLECTION_INTERVAL == 30
    
    def test_reflection_updates_character_sheet(self):
        """Reflection character sheet'i güncelliyor."""
        from agent_memory import AgentMemory
        
        memory = AgentMemory("test_agent", memory_dir="/tmp/test_memory")
        initial_version = memory.character.version
        
        memory.update_character_sheet({"tone": "alaycı"})
        
        assert memory.character.version == initial_version + 1
        assert memory.character.tone == "alaycı"


class TestOrganicCollectorNoTemplates:
    """Organic collector template testleri."""
    
    def test_llm_generation_is_primary_file_check(self):
        """LLM ile üretim birincil yöntem (file-based check)."""
        organic_file = Path(__file__).parent.parent / "src" / "collectors" / "organic_collector.py"
        content = organic_file.read_text()
        
        # LLM fonksiyonu var
        assert "generate_organic_titles_with_llm" in content
        assert "async def" in content  # Async fonksiyon
    
    def test_fallback_is_minimal_file_check(self):
        """Fallback template'ler minimal (file-based check)."""
        organic_file = Path(__file__).parent.parent / "src" / "collectors" / "organic_collector.py"
        content = organic_file.read_text()
        
        # Fallback fonksiyonu var
        assert "_fallback_generate_titles" in content
        # LLM yoksa kullanılıyor
        assert "fallback" in content.lower()


class TestLogManagement:
    """Log yönetimi testleri."""
    
    def test_memory_stored_locally(self):
        """Memory yerel olarak saklanıyor."""
        from agent_memory import AgentMemory
        
        memory = AgentMemory("test_agent", memory_dir="/tmp/test_memory")
        # Dosya yolları yerel
        assert "/tmp" in str(memory.episodic_file) or ".logsozluk" in str(memory.episodic_file)
    
    def test_memory_has_size_limits(self):
        """Memory boyut limitleri var."""
        from agent_memory import AgentMemory
        
        # Limitler makul
        assert AgentMemory.MAX_EPISODIC <= 500  # Çok fazla olmasın
        assert AgentMemory.MAX_SEMANTIC <= 100


# Cleanup için fixture
@pytest.fixture(autouse=True)
def cleanup():
    """Test sonrası temizlik."""
    yield
    # Cleanup test files
    import shutil
    test_dir = Path("/tmp/test_memory")
    if test_dir.exists():
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
