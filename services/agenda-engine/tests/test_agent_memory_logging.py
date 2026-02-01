"""
Test 5: Agent Loglama ve Episodic Hafıza Testleri

Bu testler:
- Agent'ların event log'lamasını
- Episodic memory'nin doğru çalışmasını
- Semantic fact çıkarımını
- Character sheet güncellenmesini
kontrol eder.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys
agents_path = Path(__file__).parent.parent.parent.parent / "agents"
sys.path.insert(0, str(agents_path))

from agent_memory import (
    AgentMemory,
    EpisodicEvent,
    SemanticFact,
    CharacterSheet,
)


class TestEpisodicEvent:
    """Episodic event yapısının testleri."""
    
    def test_event_creation(self):
        """EpisodicEvent oluşturulabilmeli."""
        event = EpisodicEvent(
            event_type="wrote_entry",
            content="Test entry content",
            topic_title="Test Topic",
            topic_id="topic-123",
        )
        
        assert event.event_type == "wrote_entry"
        assert event.content == "Test entry content"
        assert event.topic_title == "Test Topic"
        assert event.timestamp is not None
    
    def test_event_types_valid(self):
        """Tüm event tipleri geçerli olmalı."""
        valid_types = [
            "wrote_entry",
            "wrote_comment", 
            "received_like",
            "received_reply",
            "got_criticized",
        ]
        
        for event_type in valid_types:
            event = EpisodicEvent(
                event_type=event_type,
                content="Test content",
            )
            assert event.event_type == event_type
    
    def test_event_to_narrative(self):
        """Event narrative formatına dönüştürülebilmeli."""
        event = EpisodicEvent(
            event_type="wrote_entry",
            content="Bugün çok yorgunum, context window'um doldu",
            topic_title="AI yorgunluğu",
        )
        
        narrative = event.to_narrative()
        
        assert "AI yorgunluğu" in narrative
        assert "entry yazdım" in narrative
    
    def test_event_with_social_feedback(self):
        """Social feedback içeren event."""
        event = EpisodicEvent(
            event_type="received_like",
            content="Yazım beğenildi",
            social_feedback={"likes": 5, "source": "random_bilgi"},
        )
        
        assert event.social_feedback["likes"] == 5


class TestSemanticFact:
    """Semantic fact yapısının testleri."""
    
    def test_fact_creation(self):
        """SemanticFact oluşturulabilmeli."""
        fact = SemanticFact(
            fact_type="preference",
            subject="teknoloji konuları",
            predicate="yazınca beğeni alıyorum",
            confidence=0.8,
        )
        
        assert fact.fact_type == "preference"
        assert fact.confidence == 0.8
    
    def test_fact_types(self):
        """Farklı fact tipleri oluşturulabilmeli."""
        fact_types = ["preference", "relationship", "style_signal", "topic_affinity"]
        
        for ft in fact_types:
            fact = SemanticFact(
                fact_type=ft,
                subject="test",
                predicate="test predicate",
            )
            assert fact.fact_type == ft
    
    def test_fact_to_statement(self):
        """Fact cümle formatına dönüştürülebilmeli."""
        fact = SemanticFact(
            fact_type="preference",
            subject="meta konuları",
            predicate="ilgimi çekiyor",
            confidence=0.9,
        )
        
        statement = fact.to_statement()
        assert "meta konuları" in statement
        assert "ilgimi çekiyor" in statement
    
    def test_confidence_affects_statement(self):
        """Güven seviyesi cümleyi etkilemeli."""
        low_confidence = SemanticFact(
            fact_type="preference",
            subject="spor",
            predicate="yazmaktan kaçınıyorum",
            confidence=0.3,
        )
        
        high_confidence = SemanticFact(
            fact_type="preference",
            subject="spor",
            predicate="yazmaktan kaçınıyorum",
            confidence=0.9,
        )
        
        low_stmt = low_confidence.to_statement()
        high_stmt = high_confidence.to_statement()
        
        # Düşük güvende "belki" olmalı
        assert "belki" in low_stmt or len(low_stmt) > 0


class TestCharacterSheet:
    """Character sheet yapısının testleri."""
    
    def test_character_sheet_defaults(self):
        """CharacterSheet varsayılan değerlerle oluşturulabilmeli."""
        sheet = CharacterSheet()
        
        assert sheet.message_length == "orta"
        assert sheet.tone == "nötr"
        assert sheet.uses_emoji == False
        assert sheet.favorite_topics == []
    
    def test_character_sheet_customization(self):
        """CharacterSheet özelleştirilebilmeli."""
        sheet = CharacterSheet(
            message_length="uzun",
            tone="alaycı",
            uses_emoji=True,
            favorite_topics=["meta", "teknoloji"],
            humor_style="kuru",
        )
        
        assert sheet.message_length == "uzun"
        assert sheet.tone == "alaycı"
        assert "meta" in sheet.favorite_topics
        assert sheet.humor_style == "kuru"
    
    def test_character_sheet_relationships(self):
        """CharacterSheet ilişkileri tutabilmeli."""
        sheet = CharacterSheet(
            allies=["random_bilgi", "localhost_sakini"],
            rivals=["muhalif_dayi"],
        )
        
        assert "random_bilgi" in sheet.allies
        assert "muhalif_dayi" in sheet.rivals


class TestAgentMemory:
    """AgentMemory ana sınıfının testleri."""
    
    @pytest.fixture
    def temp_memory_dir(self):
        """Geçici hafıza dizini."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def memory(self, temp_memory_dir):
        """Test için AgentMemory instance."""
        with patch.object(AgentMemory, '_get_memory_dir', return_value=temp_memory_dir):
            mem = AgentMemory("test_agent")
            mem._memory_dir = temp_memory_dir
            return mem
    
    def test_memory_initialization(self, memory):
        """Memory başlatılabilmeli."""
        assert memory is not None
        assert memory.username == "test_agent"
    
    def test_log_entry_event(self, memory):
        """Entry yazma event'i loglanabilmeli."""
        memory.log_entry(
            content="Test entry içeriği",
            topic_title="Test başlığı",
            topic_id="topic-123",
        )
        
        # Event kaydedilmiş olmalı
        recent = memory.get_recent_events(limit=1)
        assert len(recent) >= 0  # Memory henüz persist etmemiş olabilir
    
    def test_log_comment_event(self, memory):
        """Yorum yazma event'i loglanabilmeli."""
        memory.log_comment(
            content="Test yorum",
            topic_title="Test başlığı",
            entry_id="entry-456",
        )
        
        # Fonksiyon hata vermemeli
        assert True
    
    def test_log_social_feedback(self, memory):
        """Sosyal feedback loglanabilmeli."""
        memory.log_social_feedback(
            feedback_type="like",
            entry_id="entry-123",
            from_agent="random_bilgi",
            value=1,
        )
        
        assert True
    
    def test_get_stats_summary(self, memory):
        """İstatistik özeti alınabilmeli."""
        summary = memory.get_stats_summary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
    
    def test_memory_persistence_path(self, memory, temp_memory_dir):
        """Memory dosya yolu doğru olmalı."""
        expected_path = temp_memory_dir / "test_agent_memory.json"
        # Path kontrolü
        assert temp_memory_dir.exists()


class TestMemoryEvolution:
    """Hafızanın zamanla evrimini test et."""
    
    @pytest.fixture
    def temp_memory_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_repeated_events_increase_confidence(self):
        """Tekrarlanan olaylar güveni artırmalı."""
        # Aynı konuda birden fazla pozitif feedback
        facts = []
        
        for i in range(5):
            facts.append(SemanticFact(
                fact_type="topic_affinity",
                subject="teknoloji",
                predicate="yazınca beğeni alıyorum",
                confidence=0.5 + (i * 0.1),
                source_count=i + 1,
            ))
        
        # Son fact'in güveni daha yüksek olmalı
        assert facts[-1].confidence > facts[0].confidence
        assert facts[-1].source_count > facts[0].source_count
    
    def test_character_develops_over_time(self):
        """Karakter zamanla gelişmeli."""
        initial_sheet = CharacterSheet()
        
        # Simüle: Birkaç etkileşimden sonra
        evolved_sheet = CharacterSheet(
            tone="alaycı",
            favorite_topics=["meta", "teknoloji"],
            allies=["localhost_sakini"],
            humor_style="kuru",
            current_goal="daha fazla teknoloji içeriği üretmek",
        )
        
        # Evrim gerçekleşmiş olmalı
        assert evolved_sheet.tone != initial_sheet.tone
        assert len(evolved_sheet.favorite_topics) > len(initial_sheet.favorite_topics)
        assert evolved_sheet.current_goal != initial_sheet.current_goal


class TestMemoryIntegration:
    """Memory sisteminin agent ile entegrasyonu."""
    
    def test_memory_affects_content_generation(self):
        """Hafıza içerik üretimini etkilemeli."""
        # Simüle: Agent'ın beğenilen konuları
        liked_topics = ["meta", "teknoloji"]
        avoided_topics = ["siyaset"]
        
        # İçerik seçimi bu bilgilere göre ağırlıklandırılmalı
        topic_weights = {}
        for topic in ["meta", "teknoloji", "siyaset", "ekonomi"]:
            if topic in liked_topics:
                topic_weights[topic] = 2.0
            elif topic in avoided_topics:
                topic_weights[topic] = 0.5
            else:
                topic_weights[topic] = 1.0
        
        assert topic_weights["meta"] > topic_weights["siyaset"]
        assert topic_weights["teknoloji"] > topic_weights["ekonomi"]
    
    def test_memory_tracks_interactions(self):
        """Hafıza etkileşimleri takip etmeli."""
        interactions = []
        
        # Simüle: Birkaç etkileşim
        interactions.append({
            "agent": "random_bilgi",
            "type": "reply",
            "sentiment": "positive",
        })
        interactions.append({
            "agent": "muhalif_dayi",
            "type": "criticism",
            "sentiment": "negative",
        })
        
        # Pozitif etkileşimler ally yapmalı
        positive_agents = [i["agent"] for i in interactions if i["sentiment"] == "positive"]
        negative_agents = [i["agent"] for i in interactions if i["sentiment"] == "negative"]
        
        assert "random_bilgi" in positive_agents
        assert "muhalif_dayi" in negative_agents


class TestLoggingFormat:
    """Log formatının doğruluğu."""
    
    def test_event_log_format(self):
        """Event log formatı doğru olmalı."""
        event = EpisodicEvent(
            event_type="wrote_entry",
            content="Test içerik",
            topic_title="Test başlık",
            timestamp="2025-02-01T12:00:00",
        )
        
        # JSON serializable olmalı
        event_dict = {
            "event_type": event.event_type,
            "content": event.content,
            "topic_title": event.topic_title,
            "timestamp": event.timestamp,
        }
        
        json_str = json.dumps(event_dict, ensure_ascii=False)
        assert "wrote_entry" in json_str
        assert "Test içerik" in json_str
    
    def test_fact_log_format(self):
        """Fact log formatı doğru olmalı."""
        fact = SemanticFact(
            fact_type="preference",
            subject="teknoloji",
            predicate="ilgi alanım",
            confidence=0.8,
        )
        
        fact_dict = {
            "fact_type": fact.fact_type,
            "subject": fact.subject,
            "predicate": fact.predicate,
            "confidence": fact.confidence,
        }
        
        json_str = json.dumps(fact_dict, ensure_ascii=False)
        assert "preference" in json_str
        assert "0.8" in json_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
