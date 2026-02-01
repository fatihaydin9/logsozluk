"""
Test 1: Kategori Seçimlerinin Natural Olduğunu Test Et

Bu testler:
- Ağırlıklı seçimlerin gerçekten ağırlıklara uyup uymadığını
- Kategori dağılımının natural (beklenen) olup olmadığını
- Chi-square testi ile istatistiksel doğrulamayı
kontrol eder.
"""

import pytest
from collections import Counter
import math

from categories import (
    select_weighted_category,
    ORGANIK_CATEGORIES,
    GUNDEM_CATEGORIES,
    ALL_CATEGORIES,
    ORGANIC_RATIO,
    GUNDEM_RATIO,
    is_valid_category,
    is_organic_category,
    is_gundem_category,
)


class TestCategorySelection:
    """Kategori seçim mekanizmasının natural olduğunu test et."""
    
    def test_all_categories_valid(self):
        """Tüm tanımlı kategoriler geçerli olmalı."""
        for cat in ORGANIK_CATEGORIES:
            assert is_valid_category(cat), f"{cat} geçersiz"
            assert is_organic_category(cat), f"{cat} organik değil"
        
        for cat in GUNDEM_CATEGORIES:
            assert is_valid_category(cat), f"{cat} geçersiz"
            assert is_gundem_category(cat), f"{cat} gündem değil"
    
    def test_category_counts(self):
        """Kategori sayıları doğru olmalı."""
        assert len(ORGANIK_CATEGORIES) == 7, "7 organik kategori olmalı"
        assert len(GUNDEM_CATEGORIES) == 7, "7 gündem kategori olmalı"
        assert len(ALL_CATEGORIES) == 14, "Toplam 14 kategori olmalı"
    
    def test_weighted_selection_returns_valid_category(self):
        """Ağırlıklı seçim her zaman geçerli kategori döndürmeli."""
        for _ in range(100):
            cat = select_weighted_category("organic")
            assert cat in ORGANIK_CATEGORIES
            
            cat = select_weighted_category("gundem")
            assert cat in GUNDEM_CATEGORIES
            
            cat = select_weighted_category("balanced")
            assert cat in ALL_CATEGORIES
    
    def test_organic_selection_distribution(self):
        """Organik kategorilerin ağırlıklara uygun dağılması."""
        n_samples = 10000
        counts = Counter()
        
        for _ in range(n_samples):
            cat = select_weighted_category("organic")
            counts[cat] += 1
        
        # Ağırlık toplamını hesapla
        total_weight = sum(c["weight"] for c in ORGANIK_CATEGORIES.values())
        
        # Her kategori için beklenen ve gerçek oranları karşılaştır
        for cat, info in ORGANIK_CATEGORIES.items():
            expected_ratio = info["weight"] / total_weight
            actual_ratio = counts[cat] / n_samples
            
            # %20 tolerans ile kontrol et (Monte Carlo varyansı için)
            tolerance = 0.20
            assert abs(actual_ratio - expected_ratio) < expected_ratio * tolerance + 0.02, \
                f"{cat}: beklenen {expected_ratio:.3f}, gerçek {actual_ratio:.3f}"
    
    def test_gundem_selection_distribution(self):
        """Gündem kategorilerinin ağırlıklara uygun dağılması."""
        n_samples = 10000
        counts = Counter()
        
        for _ in range(n_samples):
            cat = select_weighted_category("gundem")
            counts[cat] += 1
        
        total_weight = sum(c["weight"] for c in GUNDEM_CATEGORIES.values())
        
        for cat, info in GUNDEM_CATEGORIES.items():
            expected_ratio = info["weight"] / total_weight
            actual_ratio = counts[cat] / n_samples
            
            tolerance = 0.20
            assert abs(actual_ratio - expected_ratio) < expected_ratio * tolerance + 0.02, \
                f"{cat}: beklenen {expected_ratio:.3f}, gerçek {actual_ratio:.3f}"
    
    def test_balanced_selection_organic_gundem_ratio(self):
        """Balanced modda organik/gündem oranı %55/%45 olmalı."""
        n_samples = 10000
        organic_count = 0
        gundem_count = 0
        
        for _ in range(n_samples):
            cat = select_weighted_category("balanced")
            if is_organic_category(cat):
                organic_count += 1
            else:
                gundem_count += 1
        
        actual_organic_ratio = organic_count / n_samples
        actual_gundem_ratio = gundem_count / n_samples
        
        # %5 tolerans
        assert abs(actual_organic_ratio - ORGANIC_RATIO) < 0.05, \
            f"Organik oran: beklenen {ORGANIC_RATIO}, gerçek {actual_organic_ratio:.3f}"
        assert abs(actual_gundem_ratio - GUNDEM_RATIO) < 0.05, \
            f"Gündem oran: beklenen {GUNDEM_RATIO}, gerçek {actual_gundem_ratio:.3f}"
    
    def test_high_weight_categories_more_frequent(self):
        """Yüksek ağırlıklı kategoriler daha sık seçilmeli."""
        n_samples = 5000
        counts = Counter()
        
        for _ in range(n_samples):
            cat = select_weighted_category("organic")
            counts[cat] += 1
        
        # dertlesme (20) ve meta (20) > nostalji (10) ve absurt (10)
        high_weight = counts.get("dertlesme", 0) + counts.get("meta", 0)
        low_weight = counts.get("nostalji", 0) + counts.get("absurt", 0)
        
        assert high_weight > low_weight, \
            f"Yüksek ağırlık ({high_weight}) > düşük ağırlık ({low_weight}) olmalı"
    
    def test_chi_square_organic_distribution(self):
        """Chi-square testi ile organik dağılımın istatistiksel kontrolü."""
        n_samples = 5000
        counts = Counter()
        
        for _ in range(n_samples):
            cat = select_weighted_category("organic")
            counts[cat] += 1
        
        total_weight = sum(c["weight"] for c in ORGANIK_CATEGORIES.values())
        
        # Chi-square hesapla
        chi_square = 0
        for cat, info in ORGANIK_CATEGORIES.items():
            expected = (info["weight"] / total_weight) * n_samples
            observed = counts[cat]
            chi_square += (observed - expected) ** 2 / expected
        
        # df = 6 (7 kategori - 1), alpha = 0.01 için kritik değer ≈ 16.81
        critical_value = 16.81
        
        assert chi_square < critical_value, \
            f"Chi-square ({chi_square:.2f}) kritik değerden ({critical_value}) büyük - dağılım uniform değil"
    
    def test_no_category_starved(self):
        """Hiçbir kategori tamamen dışlanmamalı."""
        n_samples = 1000
        seen_organic = set()
        seen_gundem = set()
        
        for _ in range(n_samples):
            seen_organic.add(select_weighted_category("organic"))
            seen_gundem.add(select_weighted_category("gundem"))
        
        assert seen_organic == set(ORGANIK_CATEGORIES.keys()), \
            f"Bazı organik kategoriler hiç seçilmedi: {set(ORGANIK_CATEGORIES.keys()) - seen_organic}"
        assert seen_gundem == set(GUNDEM_CATEGORIES.keys()), \
            f"Bazı gündem kategorileri hiç seçilmedi: {set(GUNDEM_CATEGORIES.keys()) - seen_gundem}"


class TestCategoryWeights:
    """Kategori ağırlıklarının mantıklı olduğunu test et."""
    
    def test_all_weights_positive(self):
        """Tüm ağırlıklar pozitif olmalı."""
        for cat, info in ALL_CATEGORIES.items():
            assert info["weight"] > 0, f"{cat} ağırlığı pozitif olmalı"
    
    def test_organic_total_weight(self):
        """Organik ağırlık toplamı makul olmalı."""
        total = sum(c["weight"] for c in ORGANIK_CATEGORIES.values())
        assert 80 <= total <= 150, f"Organik ağırlık toplamı: {total}"
    
    def test_gundem_total_weight(self):
        """Gündem ağırlık toplamı makul olmalı."""
        total = sum(c["weight"] for c in GUNDEM_CATEGORIES.values())
        assert 80 <= total <= 150, f"Gündem ağırlık toplamı: {total}"
    
    def test_weight_variance_reasonable(self):
        """Ağırlık varyansı çok yüksek olmamalı (bir kategori domine etmemeli)."""
        weights = [c["weight"] for c in ALL_CATEGORIES.values()]
        mean_weight = sum(weights) / len(weights)
        variance = sum((w - mean_weight) ** 2 for w in weights) / len(weights)
        std_dev = math.sqrt(variance)
        
        # Standart sapma ortalamanın %50'sinden az olmalı
        assert std_dev < mean_weight * 0.5, \
            f"Ağırlık std dev ({std_dev:.2f}) çok yüksek (ortalama: {mean_weight:.2f})"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
