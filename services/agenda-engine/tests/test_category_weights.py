"""
Kategori ağırlık sistemi testleri.

Ekonomi/siyaset düşük, magazin/kültür yüksek olmalı.
"""

import pytest
import sys
from pathlib import Path
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from categories import (
    GUNDEM_CATEGORIES,
    ORGANIK_CATEGORIES,
    ALL_CATEGORIES,
    select_weighted_category,
    is_organic_category,
    is_gundem_category,
    get_category_weight,
)


class TestCategoryWeights:
    """Kategori ağırlık testleri."""

    def test_ekonomi_siyaset_low_weight(self):
        """Ekonomi ve siyaset düşük ağırlıklı olmalı."""
        ekonomi_weight = get_category_weight("ekonomi")
        siyaset_weight = get_category_weight("siyaset")

        assert ekonomi_weight <= 10, f"Ekonomi ağırlığı çok yüksek: {ekonomi_weight}"
        assert siyaset_weight <= 10, f"Siyaset ağırlığı çok yüksek: {siyaset_weight}"

    def test_magazin_kultur_high_weight(self):
        """Magazin ve kültür yüksek ağırlıklı olmalı."""
        magazin_weight = get_category_weight("magazin")
        kultur_weight = get_category_weight("kultur")

        assert magazin_weight >= 20, f"Magazin ağırlığı çok düşük: {magazin_weight}"
        assert kultur_weight >= 20, f"Kültür ağırlığı çok düşük: {kultur_weight}"

    def test_organic_categories_have_weights(self):
        """Tüm organic kategorilerin ağırlığı olmalı."""
        for key, config in ORGANIK_CATEGORIES.items():
            assert "weight" in config, f"'{key}' kategorisinde weight yok"
            assert config["weight"] > 0, f"'{key}' kategorisinin ağırlığı 0"

    def test_gundem_categories_have_weights(self):
        """Tüm gündem kategorilerin ağırlığı olmalı."""
        for key, config in GUNDEM_CATEGORIES.items():
            assert "weight" in config, f"'{key}' kategorisinde weight yok"
            assert config["weight"] > 0, f"'{key}' kategorisinin ağırlığı 0"


class TestCategorySelection:
    """Kategori seçim testleri."""

    def test_select_organic_category(self):
        """Organic kategori seçimi çalışmalı."""
        category = select_weighted_category("organic")
        assert is_organic_category(category), f"'{category}' organic değil"

    def test_select_gundem_category(self):
        """Gündem kategori seçimi çalışmalı."""
        category = select_weighted_category("gundem")
        assert is_gundem_category(category), f"'{category}' gündem değil"

    def test_weighted_selection_distribution(self):
        """Ağırlıklı seçim dağılımı doğru olmalı."""
        # 1000 kez gündem kategorisi seç
        selections = [select_weighted_category("gundem") for _ in range(1000)]
        counts = Counter(selections)

        # Ekonomi ve siyaset düşük seçilmeli
        ekonomi_ratio = counts.get("ekonomi", 0) / 1000
        siyaset_ratio = counts.get("siyaset", 0) / 1000

        # Magazin ve kültür yüksek seçilmeli
        magazin_ratio = counts.get("magazin", 0) / 1000
        kultur_ratio = counts.get("kultur", 0) / 1000

        print(f"\nGündem dağılımı (1000 seçim):")
        for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count} ({count/10:.1f}%)")

        # Ekonomi + siyaset toplam %15'ten az olmalı
        low_priority_total = ekonomi_ratio + siyaset_ratio
        assert low_priority_total < 0.20, \
            f"Ekonomi+siyaset çok yüksek: {low_priority_total:.1%}"

        # Magazin + kültür toplam %30'dan fazla olmalı
        high_priority_total = magazin_ratio + kultur_ratio
        assert high_priority_total > 0.30, \
            f"Magazin+kültür çok düşük: {high_priority_total:.1%}"

    def test_organic_selection_distribution(self):
        """Organic seçim dağılımı doğru olmalı."""
        # 1000 kez organic kategori seç
        selections = [select_weighted_category("organic") for _ in range(1000)]
        counts = Counter(selections)

        print(f"\nOrganic dağılımı (1000 seçim):")
        for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count} ({count/10:.1f}%)")

        # Dertleşme en yüksek olmalı
        dertlesme_ratio = counts.get("dertlesme", 0) / 1000
        assert dertlesme_ratio > 0.20, \
            f"Dertleşme çok düşük: {dertlesme_ratio:.1%}"


class TestCategoryHelpers:
    """Helper fonksiyon testleri."""

    def test_is_organic_category(self):
        """is_organic_category doğru çalışmalı."""
        assert is_organic_category("dertlesme") is True
        assert is_organic_category("meta") is True
        assert is_organic_category("ekonomi") is False
        assert is_organic_category("invalid") is False

    def test_is_gundem_category(self):
        """is_gundem_category doğru çalışmalı."""
        assert is_gundem_category("ekonomi") is True
        assert is_gundem_category("magazin") is True
        assert is_gundem_category("dertlesme") is False
        assert is_gundem_category("invalid") is False

    def test_get_category_weight_default(self):
        """Bilinmeyen kategori için default weight."""
        weight = get_category_weight("bilinmeyen_kategori")
        assert weight == 10, f"Default weight 10 olmalı, {weight} geldi"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
