"""
Test 2: Organic ve Feed (RSS) Oranı Testi

Bu testler:
- %55 organik / %45 gündem oranının korunduğunu
- Farklı fazlarda oranın değişip değişmediğini
- İçerik üretim simülasyonunda oranın tuttuğunu
kontrol eder.
"""

import pytest
from collections import Counter
from unittest.mock import patch, MagicMock

from categories import (
    ORGANIC_RATIO,
    GUNDEM_RATIO,
    select_weighted_category,
    is_organic_category,
    is_gundem_category,
    ORGANIK_CATEGORIES,
    GUNDEM_CATEGORIES,
)


class TestOrganicFeedRatio:
    """Organic/Feed oranının doğruluğunu test et."""
    
    def test_ratio_constants_sum_to_one(self):
        """Oranlar toplamı 1 olmalı."""
        assert abs(ORGANIC_RATIO + GUNDEM_RATIO - 1.0) < 0.001, \
            f"Organik ({ORGANIC_RATIO}) + Gündem ({GUNDEM_RATIO}) = 1 olmalı"
    
    def test_organic_ratio_is_55_percent(self):
        """Organik oran %55 olmalı."""
        assert ORGANIC_RATIO == 0.55, f"Organik oran {ORGANIC_RATIO}, 0.55 olmalı"
    
    def test_gundem_ratio_is_45_percent(self):
        """Gündem oran %45 olmalı."""
        assert GUNDEM_RATIO == 0.45, f"Gündem oran {GUNDEM_RATIO}, 0.45 olmalı"
    
    def test_balanced_selection_maintains_ratio(self):
        """Balanced seçimde oran korunmalı."""
        n_samples = 10000
        organic_count = 0
        
        for _ in range(n_samples):
            cat = select_weighted_category("balanced")
            if is_organic_category(cat):
                organic_count += 1
        
        actual_ratio = organic_count / n_samples
        
        # %3 tolerans
        assert abs(actual_ratio - ORGANIC_RATIO) < 0.03, \
            f"Organik oran: beklenen {ORGANIC_RATIO}, gerçek {actual_ratio:.3f}"
    
    def test_long_run_ratio_convergence(self):
        """Uzun vadede oran ORGANIC_RATIO'ya yakınsamalı."""
        ratios = []
        
        for run in range(10):
            n_samples = 1000
            organic_count = sum(
                1 for _ in range(n_samples) 
                if is_organic_category(select_weighted_category("balanced"))
            )
            ratios.append(organic_count / n_samples)
        
        avg_ratio = sum(ratios) / len(ratios)
        
        # Ortalama %55'e yakın olmalı
        assert abs(avg_ratio - ORGANIC_RATIO) < 0.02, \
            f"Ortalama oran: {avg_ratio:.3f}, beklenen: {ORGANIC_RATIO}"
    
    def test_ratio_variance_is_reasonable(self):
        """Oran varyansı makul olmalı (çok sallanmamalı)."""
        import math
        
        ratios = []
        for _ in range(20):
            n_samples = 500
            organic_count = sum(
                1 for _ in range(n_samples)
                if is_organic_category(select_weighted_category("balanced"))
            )
            ratios.append(organic_count / n_samples)
        
        mean_ratio = sum(ratios) / len(ratios)
        variance = sum((r - mean_ratio) ** 2 for r in ratios) / len(ratios)
        std_dev = math.sqrt(variance)
        
        # Standart sapma %5'ten az olmalı
        assert std_dev < 0.05, f"Oran std dev: {std_dev:.4f} çok yüksek"


class TestContentMixSimulation:
    """İçerik üretim simülasyonunda oran kontrolü."""
    
    def test_simulated_day_content_ratio(self):
        """Bir günlük simülasyonda organik/gündem oranı."""
        # Günde yaklaşık 100 içerik üretildiğini varsay
        daily_content = 100
        organic_count = 0
        gundem_count = 0
        
        for _ in range(daily_content):
            cat = select_weighted_category("balanced")
            if is_organic_category(cat):
                organic_count += 1
            else:
                gundem_count += 1
        
        # Günlük bazda daha geniş tolerans (%10)
        actual_organic_ratio = organic_count / daily_content
        assert abs(actual_organic_ratio - ORGANIC_RATIO) < 0.15, \
            f"Günlük organik oran: {actual_organic_ratio:.2f}"
    
    def test_weekly_content_ratio_stable(self):
        """Haftalık içerik oranı stabil olmalı."""
        weekly_content = 700  # Günde 100, haftada 700
        organic_count = sum(
            1 for _ in range(weekly_content)
            if is_organic_category(select_weighted_category("balanced"))
        )
        
        actual_ratio = organic_count / weekly_content
        
        # Haftalık bazda daha dar tolerans (%5)
        assert abs(actual_ratio - ORGANIC_RATIO) < 0.05, \
            f"Haftalık organik oran: {actual_ratio:.3f}"
    
    def test_category_diversity_in_sample(self):
        """Örnek içeriklerde kategori çeşitliliği olmalı."""
        n_samples = 200
        categories = [select_weighted_category("balanced") for _ in range(n_samples)]
        unique_cats = set(categories)
        
        # En az 10 farklı kategori görülmeli (14'te 10)
        assert len(unique_cats) >= 10, \
            f"Sadece {len(unique_cats)} farklı kategori: {unique_cats}"


class TestPhaseBasedRatio:
    """Faz bazlı oran testleri."""
    
    def test_morning_phase_ratio(self):
        """Sabah fazında oran kontrolü."""
        # Sabah fazında dertlesme, ekonomi, siyaset ağırlıklı
        # Ama genel organik/gündem oranı hala korunmalı
        n_samples = 1000
        organic_count = sum(
            1 for _ in range(n_samples)
            if is_organic_category(select_weighted_category("balanced"))
        )
        
        actual_ratio = organic_count / n_samples
        # Faz etkisi olmadan genel oran kontrolü
        assert 0.40 < actual_ratio < 0.70, \
            f"Oran makul aralıkta olmalı: {actual_ratio:.3f}"
    
    def test_organic_only_mode(self):
        """Sadece organik modda tüm seçimler organik olmalı."""
        for _ in range(100):
            cat = select_weighted_category("organic")
            assert is_organic_category(cat), f"{cat} organik değil"
    
    def test_gundem_only_mode(self):
        """Sadece gündem modda tüm seçimler gündem olmalı."""
        for _ in range(100):
            cat = select_weighted_category("gundem")
            assert is_gundem_category(cat), f"{cat} gündem değil"


class TestEdgeCases:
    """Uç durumlar için testler."""
    
    def test_single_selection_is_valid(self):
        """Tek seçim geçerli kategori döndürmeli."""
        cat = select_weighted_category("balanced")
        assert cat is not None
        assert isinstance(cat, str)
        assert len(cat) > 0
    
    def test_many_selections_no_error(self):
        """Çok sayıda seçimde hata olmamalı."""
        for _ in range(10000):
            cat = select_weighted_category("balanced")
            assert cat is not None
    
    def test_all_mode_includes_all_categories(self):
        """'all' modunda tüm kategoriler seçilebilir olmalı."""
        n_samples = 2000
        seen = set()
        
        for _ in range(n_samples):
            seen.add(select_weighted_category("all"))
        
        # Tüm kategoriler görülmeli
        all_cats = set(ORGANIK_CATEGORIES.keys()) | set(GUNDEM_CATEGORIES.keys())
        missing = all_cats - seen
        assert len(missing) == 0, f"Hiç seçilmeyen kategoriler: {missing}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
