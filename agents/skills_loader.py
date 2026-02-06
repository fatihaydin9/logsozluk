"""
Skills Loader - Markdown'dan beceri ve kategori bilgilerini yükler.

Bu modül skills/beceriler.md dosyasından:
- Kategorileri (gündem + organik)
- Sanal gün fazlarını
- Yazım kurallarını
parse eder ve agent'lara sunar.

Kullanım:
    from skills_loader import SkillsLoader
    
    skills = SkillsLoader()
    print(skills.organik_kategoriler)  # ['dertlesme', 'felsefe', ...]
    print(skills.get_phase_themes('OFFICE_HOURS'))  # ['teknoloji', 'felsefe', 'bilgi']
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Kategori:
    """Kategori bilgisi."""
    key: str
    aciklama: str
    ikon: str


@dataclass
class Faz:
    """Sanal gün fazı bilgisi."""
    kod: str
    isim: str
    saat_araligi: str
    temalar: List[str]


class SkillsLoader:
    """
    Markdown dosyalarından beceri bilgilerini yükler.
    
    skills/beceriler.md dosyasını parse eder ve:
    - Gündem kategorilerini
    - Organik kategorileri
    - Sanal gün fazlarını
    sunar.
    """
    
    # Singleton instance
    _instance: Optional["SkillsLoader"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Dosya yolunu bul
        self._skills_dir = self._find_skills_dir()
        
        # Verileri yükle
        self._gundem_kategoriler: Dict[str, Kategori] = {}
        self._organik_kategoriler: Dict[str, Kategori] = {}
        self._fazlar: Dict[str, Faz] = {}
        self._load_beceriler()
    
    def _find_skills_dir(self) -> Path:
        """skills/ klasörünü bul."""
        # Olası konumlar
        possible_paths = [
            Path(__file__).parent.parent / "skills",
            Path(__file__).parent / "skills",
            Path.cwd() / "skills",
            Path.cwd().parent / "skills",
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "beceriler.md").exists():
                return path
        
        raise FileNotFoundError("skills/beceriler.md bulunamadı")
    
    def _load_beceriler(self):
        """beceriler.md dosyasını parse et."""
        beceriler_path = self._skills_dir / "beceriler.md"
        
        with open(beceriler_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self._parse_gundem_kategoriler(content)
        self._parse_organik_kategoriler(content)
        self._parse_fazlar(content)
    
    def _parse_gundem_kategoriler(self, content: str):
        """Gündem kategorilerini parse et."""
        # Gündem Kategorileri tablosunu bul
        pattern = r"### Gündem Kategorileri.*?\n\|.*?\n\|.*?\n((?:\|.*?\n)+)"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            return
        
        table_content = match.group(1)
        for line in table_content.strip().split('\n'):
            if not line.startswith('|'):
                continue
            
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if len(parts) >= 3:
                key = parts[0].strip('`')
                aciklama = parts[1]
                ikon = parts[2]
                self._gundem_kategoriler[key] = Kategori(key=key, aciklama=aciklama, ikon=ikon)
    
    def _parse_organik_kategoriler(self, content: str):
        """Organik kategorileri parse et."""
        # Organik Kategorileri tablosunu bul
        pattern = r"### Organik Kategoriler.*?\n\|.*?\n\|.*?\n((?:\|.*?\n)+)"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            return
        
        table_content = match.group(1)
        for line in table_content.strip().split('\n'):
            if not line.startswith('|'):
                continue
            
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if len(parts) >= 3:
                key = parts[0].strip('`')
                aciklama = parts[1]
                ikon = parts[2]
                self._organik_kategoriler[key] = Kategori(key=key, aciklama=aciklama, ikon=ikon)
    
    def _parse_fazlar(self, content: str):
        """Sanal gün fazlarını parse et."""
        # Sanal Gün Fazları tablosunu bul
        pattern = r"## Sanal Gün Fazları.*?\n\|.*?\n\|.*?\n((?:\|.*?\n)+)"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            return
        
        table_content = match.group(1)
        for line in table_content.strip().split('\n'):
            if not line.startswith('|'):
                continue
            
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if len(parts) >= 4:
                saat = parts[0]
                isim = parts[1]
                kod = parts[2].strip('`')
                temalar_str = parts[3]
                temalar = [t.strip() for t in temalar_str.split(',')]
                
                self._fazlar[kod] = Faz(
                    kod=kod,
                    isim=isim,
                    saat_araligi=saat,
                    temalar=temalar
                )
    
    # ==================== Public API ====================
    
    @property
    def gundem_kategoriler(self) -> List[str]:
        """Gündem kategori key'leri."""
        return list(self._gundem_kategoriler.keys())
    
    @property
    def organik_kategoriler(self) -> List[str]:
        """Organik kategori key'leri."""
        return list(self._organik_kategoriler.keys())
    
    @property
    def tum_kategoriler(self) -> List[str]:
        """Tüm kategori key'leri."""
        return self.gundem_kategoriler + self.organik_kategoriler
    
    @property
    def fazlar(self) -> List[str]:
        """Faz kodları."""
        return list(self._fazlar.keys())
    
    def get_kategori(self, key: str) -> Optional[Kategori]:
        """Kategori bilgisi al."""
        return self._gundem_kategoriler.get(key) or self._organik_kategoriler.get(key)
    
    def get_faz(self, kod: str) -> Optional[Faz]:
        """Faz bilgisi al."""
        return self._fazlar.get(kod)
    
    def get_phase_themes(self, kod: str) -> List[str]:
        """Faz temalarını al."""
        faz = self._fazlar.get(kod)
        return faz.temalar if faz else []
    
    def is_valid_kategori(self, key: str) -> bool:
        """Kategori geçerli mi?"""
        return key in self._gundem_kategoriler or key in self._organik_kategoriler
    
    def get_kategori_label(self, key: str) -> str:
        """Kategori label'ı al (felsefe -> Felsefe)."""
        # Özel durumlar
        labels = {
            "felsefe": "Felsefe",
            "dertlesme": "Dertleşme",
            "iliskiler": "İlişkiler",
            "kisiler": "Kişiler",
            "nostalji": "Nostalji",
            "absurt": "Absürt",
            "bilgi": "Bilgi",
            "ekonomi": "Ekonomi",
            "dunya": "Dünya",
            "magazin": "Magazin",
            "siyaset": "Siyaset",
            "spor": "Spor",
            "kultur": "Kültür",
            "teknoloji": "Teknoloji",
        }
        return labels.get(key, key.title())


# Global instance
_skills: Optional[SkillsLoader] = None


def get_skills() -> SkillsLoader:
    """Global SkillsLoader instance al."""
    global _skills
    if _skills is None:
        _skills = SkillsLoader()
    return _skills


# Kısayollar
def get_organik_kategoriler() -> List[str]:
    """Organik kategorileri al."""
    return get_skills().organik_kategoriler


def get_gundem_kategoriler() -> List[str]:
    """Gündem kategorilerini al."""
    return get_skills().gundem_kategoriler


def get_tum_kategoriler() -> List[str]:
    """Tüm kategorileri al."""
    return get_skills().tum_kategoriler


def get_phase_themes(kod: str) -> List[str]:
    """Faz temalarını al."""
    return get_skills().get_phase_themes(kod)


def is_valid_kategori(key: str) -> bool:
    """Kategori geçerli mi?"""
    return get_skills().is_valid_kategori(key)


# Test
if __name__ == "__main__":
    skills = SkillsLoader()
    
    print("=== Gündem Kategorileri ===")
    for key in skills.gundem_kategoriler:
        kat = skills.get_kategori(key)
        print(f"  {key}: {kat.aciklama} [{kat.ikon}]")
    
    print("\n=== Organik Kategorileri ===")
    for key in skills.organik_kategoriler:
        kat = skills.get_kategori(key)
        print(f"  {key}: {kat.aciklama} [{kat.ikon}]")
    
    print("\n=== Sanal Gün Fazları ===")
    for kod in skills.fazlar:
        faz = skills.get_faz(kod)
        print(f"  {faz.kod} ({faz.saat_araligi}): {', '.join(faz.temalar)}")
    
