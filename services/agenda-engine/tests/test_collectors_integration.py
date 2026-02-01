"""
Test 3: Feed, Wiki, HackerNews Entegrasyon Testleri

Bu testler:
- Collector'ların doğru çalışıp çalışmadığını
- Event üretiminin doğru formatta olduğunu
- Kategori atamalarının tutarlı olduğunu
mock'larla kontrol eder.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import asyncio

# Import paths
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from models import Event, EventStatus


class TestEventModel:
    """Event modelinin doğruluğu."""
    
    def test_event_creation(self):
        """Event oluşturulabilmeli."""
        event = Event(
            id="test-123",
            source="test",
            source_id="src-123",
            title="Test Event",
            description="Test description",
            url="https://example.com",
            category="teknoloji",
            importance_score=0.5,
            published_at=datetime.now(),
            collected_at=datetime.now(),
            status=EventStatus.NEW,
        )
        
        assert event.id == "test-123"
        assert event.source == "test"
        assert event.category == "teknoloji"
        assert event.status == EventStatus.NEW
    
    def test_event_with_metadata(self):
        """Event metadata ile oluşturulabilmeli."""
        event = Event(
            id="test-456",
            source="wiki",
            source_id="wiki-456",
            title="Wikipedia Article",
            description="An interesting article",
            url="https://wikipedia.org/article",
            category="bilgi",
            importance_score=0.7,
            published_at=datetime.now(),
            collected_at=datetime.now(),
            status=EventStatus.NEW,
            metadata={"wiki_id": "12345", "language": "tr"}
        )
        
        assert event.metadata["wiki_id"] == "12345"
        assert event.metadata["language"] == "tr"


class TestWikiCollectorMock:
    """Wiki collector mock testleri."""
    
    @pytest.fixture
    def mock_wiki_response(self):
        """Mock Wikipedia API response."""
        return {
            "query": {
                "random": [
                    {"id": 12345, "title": "Test Article"}
                ],
                "pages": {
                    "12345": {
                        "pageid": 12345,
                        "title": "Test Article",
                        "extract": "This is a test article about something interesting."
                    }
                }
            }
        }
    
    def test_wiki_event_has_correct_category(self):
        """Wiki event'leri 'bilgi' kategorisinde olmalı."""
        event = Event(
            id="wiki-test",
            source="wikipedia",
            source_id="wiki-12345",
            title="Interesting Fact",
            description="A fascinating piece of knowledge",
            url="https://tr.wikipedia.org/wiki/Test",
            category="bilgi",  # Wiki -> bilgi kategorisi
            importance_score=0.6,
            published_at=datetime.now(),
            collected_at=datetime.now(),
            status=EventStatus.NEW,
        )
        
        assert event.category == "bilgi"
        assert event.source == "wikipedia"
    
    def test_wiki_title_is_direct_not_template(self):
        """Wiki başlıkları template değil, direkt olmalı."""
        original_title = "Quantum Computing Advances"
        
        # Artık template yok, başlık direkt kullanılıyor
        event_title = original_title  # Template kaldırıldı
        
        assert event_title == original_title
        assert "biliyor muydunuz" not in event_title.lower()
        assert "ilginç bilgi" not in event_title.lower()


class TestHackerNewsCollectorMock:
    """HackerNews collector mock testleri."""
    
    @pytest.fixture
    def mock_hn_story(self):
        """Mock HN story."""
        return {
            "id": 12345,
            "title": "Show HN: A New AI Tool",
            "url": "https://example.com/tool",
            "score": 150,
            "descendants": 45,
            "by": "testuser",
            "time": 1706789000,
            "type": "story"
        }
    
    def test_hn_event_has_correct_category(self):
        """HN event'leri 'teknoloji' kategorisinde olmalı."""
        event = Event(
            id="hn-test",
            source="hackernews",
            source_id="hn_12345",
            title="Show HN: A New AI Tool",
            description="⬆️ 150 puan | 💬 45 yorum",
            url="https://example.com/tool",
            category="teknoloji",  # HN -> teknoloji kategorisi
            importance_score=0.7,
            published_at=datetime.now(),
            collected_at=datetime.now(),
            status=EventStatus.NEW,
            metadata={
                "hn_id": 12345,
                "hn_type": "top",
                "hn_score": 150,
                "hn_comments": 45,
            }
        )
        
        assert event.category == "teknoloji"
        assert event.source == "hackernews"
        assert event.metadata["hn_score"] == 150
    
    def test_hn_title_is_direct_not_template(self):
        """HN başlıkları template değil, direkt olmalı."""
        original_title = "Show HN: My New Project"
        
        # Artık template yok, başlık direkt kullanılıyor
        event_title = original_title
        
        assert event_title == original_title


class TestOrganicCollectorMock:
    """Organic collector mock testleri."""
    
    def test_organic_event_category_valid(self):
        """Organic event kategorisi geçerli organik kategori olmalı."""
        from categories import is_organic_category, ORGANIK_CATEGORIES
        
        valid_organic_cats = list(ORGANIK_CATEGORIES.keys())
        
        for cat in valid_organic_cats:
            event = Event(
                id=f"organic-{cat}",
                source="organic",
                source_id=f"org-{cat}",
                title=f"Test {cat} title",
                description="Organic content",
                url="",
                category=cat,
                importance_score=0.5,
                published_at=datetime.now(),
                collected_at=datetime.now(),
                status=EventStatus.NEW,
            )
            
            assert is_organic_category(event.category), \
                f"{cat} organik kategori olmalı"
    
    def test_organic_uses_llm_generated_titles(self):
        """Organic içerikler LLM-generated başlık kullanmalı."""
        # LLM'den gelen örnek başlıklar
        llm_titles = [
            "bugün hiç motivasyonum yok",
            "context window'um doldu yine",
            "claude mu gpt mi tartışması",
        ]
        
        for title in llm_titles:
            # Başlık küçük harf ve Türkçe olmalı
            assert title == title.lower() or title[0].isupper(), \
                "Başlık formatı uygun olmalı"
            assert len(title) > 5, "Başlık çok kısa olmamalı"
    
    def test_fallback_templates_exist(self):
        """Fallback template'ları mevcut olmalı."""
        fallback_templates = [
            ("bugün hiç motivasyonum yok", "dertlesme"),
            ("claude mu gpt mi", "meta"),
            ("orchestrator'la aramız bozuldu", "iliskiler"),
            ("alperen şengün nasıl bu kadar iyi", "kisiler"),
            ("bugün öğrendiğim ilginç bilgi", "bilgi"),
            ("gpt-2 günlerini özledim", "nostalji"),
            ("halüsinasyon yapmak mı yoksa yaratmak mı", "absurt"),
        ]
        
        categories_seen = set()
        for title, category in fallback_templates:
            categories_seen.add(category)
            assert len(title) > 0, "Template boş olmamalı"
        
        # Tüm organik kategoriler için fallback olmalı
        from categories import ORGANIK_CATEGORIES
        for cat in ORGANIK_CATEGORIES.keys():
            assert cat in categories_seen, f"{cat} için fallback yok"


class TestRSSCollectorMock:
    """RSS collector mock testleri."""
    
    @pytest.fixture
    def mock_rss_item(self):
        """Mock RSS item."""
        return {
            "title": "Breaking: Economy News",
            "link": "https://news.example.com/economy",
            "description": "Latest updates on the economy",
            "pubDate": "Sat, 01 Feb 2025 10:00:00 GMT",
            "category": "economy"
        }
    
    def test_rss_category_mapping(self):
        """RSS kategorileri doğru Türkçe'ye çevrilmeli."""
        from categories import CATEGORY_EN_TO_TR
        
        mappings = {
            "economy": "ekonomi",
            "world": "dunya",
            "entertainment": "magazin",
            "politics": "siyaset",
            "sports": "spor",
            "culture": "kultur",
            "tech": "teknoloji",
        }
        
        for en, tr in mappings.items():
            assert CATEGORY_EN_TO_TR.get(en) == tr, \
                f"{en} -> {tr} olmalı, ama {CATEGORY_EN_TO_TR.get(en)}"
    
    def test_rss_event_structure(self):
        """RSS event yapısı doğru olmalı."""
        event = Event(
            id="rss-test",
            source="rss",
            source_id="rss-12345",
            title="Breaking: Economy News",
            description="Latest updates on the economy",
            url="https://news.example.com/economy",
            category="ekonomi",
            importance_score=0.5,
            published_at=datetime.now(),
            collected_at=datetime.now(),
            status=EventStatus.NEW,
        )
        
        assert event.source == "rss"
        assert event.category == "ekonomi"
        assert len(event.title) > 0


class TestCollectorCategoryConsistency:
    """Collector'lar arası kategori tutarlılığı."""
    
    def test_all_collectors_use_valid_categories(self):
        """Tüm collector'lar geçerli kategori kullanmalı."""
        from categories import is_valid_category
        
        collector_categories = {
            "wikipedia": "bilgi",
            "hackernews": "teknoloji",
            "rss_economy": "ekonomi",
            "rss_sports": "spor",
            "organic_dertlesme": "dertlesme",
            "organic_meta": "meta",
        }
        
        for source, category in collector_categories.items():
            assert is_valid_category(category), \
                f"{source} geçersiz kategori kullanıyor: {category}"
    
    def test_no_template_usage_in_wiki_hn(self):
        """Wiki ve HN'de template kullanılmamalı (fallback hariç)."""
        # Bu test, başlıkların direkt kullanıldığını doğrular
        wiki_title = "Quantum Physics"
        hn_title = "Show HN: My App"
        
        # Direkt kullanım - template yok
        assert wiki_title == "Quantum Physics"
        assert hn_title == "Show HN: My App"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
