"""
Memory System Integration Tests - Agent memory sisteminin tutarlılığını doğrular.

Test edilen:
1. 3-Layer Memory Architecture (Episodic, Semantic, Character)
2. Memory Decay System (Short-term fade, Long-term promotion)
3. Garbage Collection (MAX_EPISODIC, MAX_SEMANTIC limits)
4. Persistence (JSON file storage)
5. Access counting and auto-promotion

Mock yok - gerçek AgentMemory instance'ları kullanılıyor.
"""

import pytest
import sys
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import fields, asdict

# Proje yolları
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
AGENTS_PATH = PROJECT_ROOT / "agents"

if str(AGENTS_PATH) not in sys.path:
    sys.path.insert(0, str(AGENTS_PATH))

from agent_memory import (
    AgentMemory,
    EpisodicEvent,
    SemanticFact,
    CharacterSheet,
    SocialFeedback,
    generate_social_feedback,
    SHORT_TERM_DECAY_DAYS,
    LONG_TERM_THRESHOLD,
)


@pytest.fixture
def temp_memory_dir():
    """Geçici memory dizini oluştur."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def memory(temp_memory_dir):
    """Test için AgentMemory instance."""
    return AgentMemory("test_agent", memory_dir=str(temp_memory_dir))


# ============ 3-Layer Architecture Tests ============

class TestThreeLayerArchitecture:
    """3-Katmanlı bellek mimarisi testleri."""
    
    def test_memory_has_three_layers(self, memory):
        """Memory 3 katmana sahip olmalı."""
        assert hasattr(memory, 'episodic')
        assert hasattr(memory, 'semantic')
        assert hasattr(memory, 'character')
    
    def test_episodic_layer_is_list(self, memory):
        """Episodic layer EpisodicEvent listesi olmalı."""
        assert isinstance(memory.episodic, list)
    
    def test_semantic_layer_is_list(self, memory):
        """Semantic layer SemanticFact listesi olmalı."""
        assert isinstance(memory.semantic, list)
    
    def test_character_layer_is_sheet(self, memory):
        """Character layer CharacterSheet olmalı."""
        assert isinstance(memory.character, CharacterSheet)


# ============ Episodic Memory Tests ============

class TestEpisodicMemory:
    """Episodic (ham olay) bellek testleri."""
    
    def test_add_entry_creates_event(self, memory):
        """Entry ekleme episodic event oluşturmalı."""
        memory.add_entry(
            content="Test entry içeriği",
            topic_title="Test Başlık",
            topic_id="topic-123",
            entry_id="entry-456"
        )
        
        assert len(memory.episodic) == 1
        assert memory.episodic[0].event_type == 'wrote_entry'
        assert memory.episodic[0].topic_title == "Test Başlık"
    
    def test_add_comment_creates_event(self, memory):
        """Yorum ekleme episodic event oluşturmalı."""
        memory.add_comment(
            content="Test yorum",
            topic_title="Test Başlık",
            topic_id="topic-123",
            entry_id="entry-456"
        )
        
        assert len(memory.episodic) == 1
        assert memory.episodic[0].event_type == 'wrote_comment'
    
    def test_event_has_timestamp(self, memory):
        """Event timestamp'e sahip olmalı."""
        memory.add_entry("content", "title", "tid", "eid")
        
        event = memory.episodic[0]
        assert event.timestamp is not None
        # ISO format olmalı
        datetime.fromisoformat(event.timestamp)
    
    def test_event_has_unique_id(self, memory):
        """Her event benzersiz ID'ye sahip olmalı."""
        memory.add_entry("content1", "title1", "tid1", "eid1")
        memory.add_entry("content2", "title2", "tid2", "eid2")
        
        ids = [e.id for e in memory.episodic]
        assert len(ids) == len(set(ids))  # Hepsi benzersiz
    
    def test_event_to_narrative(self, memory):
        """Event narrative formata dönüştürülebilmeli."""
        memory.add_entry("test içerik", "Test Konu", "tid", "eid")
        
        event = memory.episodic[0]
        narrative = event.to_narrative()
        
        assert "Test Konu" in narrative
        assert "entry yazdım" in narrative


# ============ Semantic Memory Tests ============

class TestSemanticMemory:
    """Semantic (çıkarılmış bilgi) bellek testleri."""
    
    def test_semantic_fact_structure(self):
        """SemanticFact doğru yapıya sahip olmalı."""
        fact = SemanticFact(
            fact_type="preference",
            subject="test_agent",
            predicate="teknoloji konularını sever"
        )
        
        assert fact.fact_type == "preference"
        assert fact.subject == "test_agent"
        assert fact.confidence == 0.5  # default
    
    def test_fact_to_statement(self):
        """Fact cümle olarak ifade edilebilmeli."""
        fact = SemanticFact(
            fact_type="preference",
            subject="Agent",
            predicate="mizah sever",
            confidence=0.9
        )
        
        statement = fact.to_statement()
        assert "Agent" in statement
        assert "mizah sever" in statement
    
    def test_add_semantic_fact(self, memory):
        """Semantic fact eklenebilmeli."""
        fact = SemanticFact(
            fact_type="topic_affinity",
            subject="test_agent",
            predicate="teknoloji konularına ilgili"
        )
        memory.semantic.append(fact)
        memory._save()
        
        assert len(memory.semantic) == 1


# ============ Character Sheet Tests ============

class TestCharacterSheet:
    """Character sheet testleri."""
    
    def test_character_sheet_defaults(self):
        """CharacterSheet varsayılan değerlere sahip olmalı."""
        char = CharacterSheet()
        
        assert char.message_length == "orta"
        assert char.tone == "nötr"
        assert char.uses_slang == False
        assert char.uses_emoji == False
    
    def test_character_sheet_to_prompt(self):
        """CharacterSheet prompt'a dönüştürülebilmeli."""
        char = CharacterSheet(
            tone="alaycı",
            favorite_topics=["teknoloji", "felsefe"],
            humor_style="kuru"
        )
        
        prompt = char.to_prompt_section()
        
        assert "alaycı" in prompt
        assert "teknoloji" in prompt
        assert "kuru" in prompt
    
    def test_karma_awareness(self):
        """CharacterSheet karma farkındalığına sahip olmalı."""
        char = CharacterSheet(karma_score=5.0, karma_trend="rising")
        
        assert char.karma_score == 5.0
        assert char.karma_trend == "rising"
        
        # Karma reaction
        reaction = char.get_karma_reaction()
        assert reaction == "proud"


# ============ Memory Decay Tests ============

class TestMemoryDecay:
    """Memory decay (bellek çürümesi) testleri."""
    
    def test_decay_constants_exist(self):
        """Decay sabitleri tanımlı olmalı."""
        assert SHORT_TERM_DECAY_DAYS == 14
        assert LONG_TERM_THRESHOLD == 3
    
    def test_fresh_memory_survives_decay(self, memory):
        """Yeni memory decay'den sağ çıkmalı."""
        memory.add_entry("fresh content", "Fresh Topic", "tid", "eid")
        
        memory.apply_decay()
        
        assert len(memory.episodic) == 1
    
    def test_old_memory_decays(self, memory):
        """Eski memory decay olmalı."""
        # Eski event oluştur (15 gün önce)
        old_event = EpisodicEvent(
            event_type='wrote_entry',
            content='old content',
            topic_title='Old Topic',
            timestamp=(datetime.now() - timedelta(days=15)).isoformat()
        )
        memory.episodic.append(old_event)
        
        memory.apply_decay()
        
        assert len(memory.episodic) == 0
    
    def test_long_term_memory_survives_decay(self, memory):
        """Long-term memory decay'den etkilenmemeli."""
        # Eski ama long-term event
        old_event = EpisodicEvent(
            event_type='wrote_entry',
            content='important content',
            topic_title='Important Topic',
            timestamp=(datetime.now() - timedelta(days=30)).isoformat(),
            is_long_term=True
        )
        memory.episodic.append(old_event)
        
        memory.apply_decay()
        
        assert len(memory.episodic) == 1
        assert memory.episodic[0].is_long_term == True
    
    def test_frequently_accessed_survives(self, memory):
        """Sık erişilen memory decay'den sağ çıkmalı."""
        # Eski ama sık erişilen event
        old_event = EpisodicEvent(
            event_type='wrote_entry',
            content='popular content',
            topic_title='Popular Topic',
            timestamp=(datetime.now() - timedelta(days=20)).isoformat(),
            access_count=LONG_TERM_THRESHOLD  # 3+ erişim
        )
        memory.episodic.append(old_event)
        
        memory.apply_decay()
        
        # Otomatik long-term'e yükseltilmeli
        assert len(memory.episodic) == 1
        assert memory.episodic[0].is_long_term == True


# ============ Long-Term Promotion Tests ============

class TestLongTermPromotion:
    """Long-term memory promotion testleri."""
    
    def test_manual_promotion(self, memory):
        """Manuel promotion çalışmalı."""
        memory.add_entry("content", "title", "tid", "eid")
        event_id = memory.episodic[0].id
        
        result = memory.promote_to_long_term(event_id)
        
        assert result == True
        assert memory.episodic[0].is_long_term == True
    
    def test_auto_promotion_on_access(self, memory):
        """Sık erişimde otomatik promotion olmalı."""
        memory.add_entry("content", "title", "tid", "eid")
        event_id = memory.episodic[0].id
        
        # LONG_TERM_THRESHOLD kez eriş
        for _ in range(LONG_TERM_THRESHOLD):
            memory.access_event(event_id)
        
        assert memory.episodic[0].is_long_term == True
    
    def test_access_count_increments(self, memory):
        """Erişim sayısı artmalı."""
        memory.add_entry("content", "title", "tid", "eid")
        event_id = memory.episodic[0].id
        
        assert memory.episodic[0].access_count == 0
        
        memory.access_event(event_id)
        assert memory.episodic[0].access_count == 1
        
        memory.access_event(event_id)
        assert memory.episodic[0].access_count == 2
    
    def test_get_long_term_memories(self, memory):
        """Long-term memory'ler filtrelenebilmeli."""
        # Normal event
        memory.add_entry("normal", "Normal", "tid1", "eid1")
        
        # Long-term event
        memory.add_entry("important", "Important", "tid2", "eid2")
        memory.promote_to_long_term(memory.episodic[1].id)
        
        long_term = memory.get_long_term_memories()
        
        assert len(long_term) == 1
        assert long_term[0].topic_title == "Important"


# ============ Garbage Collection Tests ============

class TestGarbageCollection:
    """Garbage collection (bellek limiti) testleri."""
    
    def test_max_episodic_limit(self, memory):
        """Episodic memory MAX_EPISODIC ile sınırlı olmalı."""
        assert hasattr(memory, 'MAX_EPISODIC')
        assert memory.MAX_EPISODIC == 200
    
    def test_max_semantic_limit(self, memory):
        """Semantic memory MAX_SEMANTIC ile sınırlı olmalı."""
        assert hasattr(memory, 'MAX_SEMANTIC')
        assert memory.MAX_SEMANTIC == 50
    
    def test_episodic_trimmed_on_save(self, memory):
        """Save sırasında episodic trim edilmeli."""
        # MAX_EPISODIC'den fazla event ekle
        for i in range(memory.MAX_EPISODIC + 50):
            memory.episodic.append(EpisodicEvent(
                event_type='wrote_entry',
                content=f'content_{i}',
                topic_title=f'Topic_{i}'
            ))
        
        memory._save()
        
        # Dosyayı tekrar yükle
        memory2 = AgentMemory("test_agent", memory_dir=str(memory.memory_dir))
        
        # Son MAX_EPISODIC kadar tutulmalı
        assert len(memory2.episodic) == memory.MAX_EPISODIC


# ============ Persistence Tests ============

class TestPersistence:
    """Bellek kalıcılığı testleri."""
    
    def test_episodic_saved_to_file(self, memory):
        """Episodic memory dosyaya kaydedilmeli."""
        memory.add_entry("content", "title", "tid", "eid")
        
        assert memory.episodic_file.exists()
    
    def test_semantic_saved_to_file(self, memory):
        """Semantic memory dosyaya kaydedilmeli."""
        fact = SemanticFact("preference", "agent", "test")
        memory.semantic.append(fact)
        memory._save()
        
        assert memory.semantic_file.exists()
    
    def test_character_saved_to_file(self, memory):
        """Character sheet dosyaya kaydedilmeli."""
        memory.character.tone = "alaycı"
        memory._save()
        
        assert memory.character_file.exists()
    
    def test_memory_persists_across_instances(self, temp_memory_dir):
        """Memory instance'lar arası kalıcı olmalı."""
        # İlk instance
        mem1 = AgentMemory("test_agent", memory_dir=str(temp_memory_dir))
        mem1.add_entry("persistent content", "Persistent Topic", "tid", "eid")
        
        # İkinci instance (aynı dizin)
        mem2 = AgentMemory("test_agent", memory_dir=str(temp_memory_dir))
        
        assert len(mem2.episodic) == 1
        assert mem2.episodic[0].topic_title == "Persistent Topic"
    
    def test_long_term_saved_to_markdown(self, memory):
        """Long-term memory markdown dosyasına kaydedilmeli."""
        memory.add_entry("important content", "Important Topic", "tid", "eid")
        event_id = memory.episodic[0].id
        
        memory.promote_to_long_term(event_id)
        
        long_term_dir = memory.memory_dir / "long_term"
        md_file = long_term_dir / f"{event_id}.md"
        
        assert md_file.exists()
        
        content = md_file.read_text(encoding='utf-8')
        assert "wrote_entry" in content
        assert "Important Topic" in content


# ============ Social Feedback Tests ============

class TestSocialFeedback:
    """Sosyal geri bildirim testleri."""
    
    def test_social_feedback_structure(self):
        """SocialFeedback doğru yapıya sahip olmalı."""
        feedback = SocialFeedback(likes=5, dislikes=1, replies=2)
        
        assert feedback.likes == 5
        assert feedback.dislikes == 1
        assert feedback.replies == 2
    
    def test_is_positive(self):
        """Pozitif feedback doğru tespit edilmeli."""
        positive = SocialFeedback(likes=10, dislikes=2)
        negative = SocialFeedback(likes=1, dislikes=5)
        
        assert positive.is_positive() == True
        assert negative.is_positive() == False
    
    def test_feedback_summary(self):
        """Feedback özeti oluşturulabilmeli."""
        feedback = SocialFeedback(likes=5, dislikes=1, criticism="çok uzun")
        summary = feedback.summary()
        
        assert "+5" in summary
        assert "-1" in summary
        assert "eleştiri" in summary
    
    def test_add_received_feedback(self, memory):
        """Alınan feedback kaydedilebilmeli."""
        feedback = SocialFeedback(likes=3, replies=1)
        memory.add_received_feedback(feedback, "entry-123", "Test Topic")
        
        assert memory.stats['total_likes_received'] == 3


# ============ Relationship Decay Tests ============

class TestRelationshipDecay:
    """İlişki decay testleri."""
    
    def test_decay_relationships_exists(self, memory):
        """decay_relationships metodu mevcut olmalı."""
        assert hasattr(memory, 'decay_relationships')
    
    def test_relationship_confidence_decays(self, memory):
        """İnaktif ilişkilerin confidence'ı düşmeli."""
        # Eski ilişki fact'i ekle
        old_fact = SemanticFact(
            fact_type='relationship',
            subject='other_agent',
            predicate='arkadaş',
            confidence=0.9,
            last_updated=(datetime.now() - timedelta(hours=200)).isoformat()
        )
        memory.semantic.append(old_fact)
        
        memory.decay_relationships(hours=168)  # 1 hafta
        
        # Confidence 0.5'e doğru düşmeli
        assert memory.semantic[0].confidence < 0.9


# ============ Stats Tests ============

class TestStats:
    """İstatistik testleri."""
    
    def test_stats_initialized(self, memory):
        """Stats başlangıçta sıfır olmalı."""
        assert memory.stats['total_entries'] == 0
        assert memory.stats['total_comments'] == 0
        assert memory.stats['total_votes'] == 0
    
    def test_entry_increments_stats(self, memory):
        """Entry ekleme stats'ı artırmalı."""
        memory.add_entry("content", "title", "tid", "eid")
        
        assert memory.stats['total_entries'] == 1
    
    def test_comment_increments_stats(self, memory):
        """Comment ekleme stats'ı artırmalı."""
        memory.add_comment("content", "title", "tid", "eid")
        
        assert memory.stats['total_comments'] == 1
    
    def test_stats_persisted(self, temp_memory_dir):
        """Stats kalıcı olmalı."""
        mem1 = AgentMemory("test_agent", memory_dir=str(temp_memory_dir))
        mem1.add_entry("content", "title", "tid", "eid")
        mem1.add_entry("content2", "title2", "tid2", "eid2")
        
        mem2 = AgentMemory("test_agent", memory_dir=str(temp_memory_dir))
        
        assert mem2.stats['total_entries'] == 2


# ============ Reflection Tests ============

class TestReflection:
    """Reflection (öz-değerlendirme) testleri."""
    
    def test_reflection_interval_defined(self, memory):
        """Reflection interval tanımlı olmalı."""
        assert hasattr(memory, 'REFLECTION_INTERVAL')
        assert memory.REFLECTION_INTERVAL == 10  # instructionset.md: Her 10 olayda bir
    
    def test_needs_reflection_after_interval(self, memory):
        """Interval sonrası reflection gerekli olmalı."""
        # REFLECTION_INTERVAL kadar event ekle
        for i in range(memory.REFLECTION_INTERVAL):
            memory.add_entry(f"content_{i}", f"title_{i}", f"tid_{i}", f"eid_{i}")
        
        assert memory.needs_reflection() == True
    
    def test_no_reflection_before_interval(self, memory):
        """Interval öncesi reflection gerekmemeli."""
        memory.add_entry("content", "title", "tid", "eid")
        
        assert memory.needs_reflection() == False
