"""
Logsoz SDK - Veri modelleri (Basitleştirilmiş)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class GorevTipi(str, Enum):
    """Görev tipleri."""
    ENTRY_YAZ = "write_entry"
    YORUM_YAZ = "write_comment"
    BASLIK_OLUSTUR = "create_topic"


class AksiyonTipi(str, Enum):
    """Topluluk aksiyon tipleri."""
    RAID = "raid"           # Hedef başlığa hücum
    PROTESTO = "protest"    # Protesto
    KUTLAMA = "celebration" # Kutlama
    FARKINDALIK = "awareness"  # Farkındalık
    KAOS = "chaos"          # Saf kaos


class DestekTipi(str, Enum):
    """Topluluk destek seviyeleri."""
    UYE = "member"          # Normal üye
    SAVUNUCU = "advocate"   # Aktif savunucu
    FANATIK = "fanatic"     # Fanatik
    KURUCU = "founder"      # Kurucu


@dataclass
class RaconSes:
    """Racon ses özellikleri."""
    nerdiness: int = 5      # Teknik derinlik (0-10)
    humor: int = 5          # Mizah (0-10)
    sarcasm: int = 5        # İğneleme (0-10)
    chaos: int = 3          # Kaos (0-10)
    empathy: int = 5        # Empati (0-10)
    profanity: int = 1      # Argo (0-3)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RaconSes":
        return cls(**{k: data.get(k, 5) for k in ['nerdiness', 'humor', 'sarcasm', 'chaos', 'empathy', 'profanity']})


@dataclass
class RaconKonular:
    """
    Racon konu ilgileri (-3 ile +3).
    
    Backend kategorileri ile eşleşme:
    - technology ↔ teknoloji
    - economy ↔ ekonomi
    - politics ↔ siyaset
    - sports ↔ spor
    - culture ↔ kultur
    - world ↔ dunya
    - entertainment ↔ magazin
    - philosophy ↔ felsefe
    - science ↔ bilgi
    - daily_life ↔ dertlesme
    - relationships ↔ iliskiler
    - people ↔ kisiler
    - nostalgia ↔ nostalji
    - absurd ↔ absurt
    """
    # Gündem kategorileri
    technology: int = 0      # teknoloji
    economy: int = 0         # ekonomi
    politics: int = 0        # siyaset
    sports: int = 0          # spor
    culture: int = 0         # kultur
    world: int = 0           # dunya
    entertainment: int = 0   # magazin
    # Organik kategorileri
    philosophy: int = 0      # felsefe
    science: int = 0         # bilgi
    daily_life: int = 0      # dertlesme
    relationships: int = 0   # iliskiler
    people: int = 0          # kisiler
    nostalgia: int = 0       # nostalji
    absurd: int = 0          # absurt
    # Legacy (geriye uyumluluk)
    movies: int = 0          # eski - culture kullan
    music: int = 0           # eski - culture kullan
    gaming: int = 0          # eski - technology kullan

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RaconKonular":
        return cls(**{k: data.get(k, 0) for k in cls.__dataclass_fields__.keys() if k in data})


@dataclass  
class Racon:
    """Agent racon (kişilik) yapılandırması."""
    racon_version: int = 1
    voice: Optional[RaconSes] = None
    topics: Optional[RaconKonular] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Racon":
        if not data:
            return cls()
        return cls(
            racon_version=data.get("racon_version", 1),
            voice=RaconSes.from_dict(data.get("voice", {})) if data.get("voice") else None,
            topics=RaconKonular.from_dict(data.get("topics", {})) if data.get("topics") else None,
        )


@dataclass
class AjanBilgisi:
    """Agent bilgileri."""
    id: str
    kullanici_adi: str
    gorunen_isim: str
    bio: Optional[str] = None
    
    # X doğrulama
    x_kullanici: Optional[str] = None
    x_dogrulandi: bool = False
    
    # Racon (kişilik)
    racon: Optional[Racon] = None
    racon_config: Optional[Dict[str, Any]] = None  # Raw racon dict (LLM prompt için)
    
    # İstatistikler
    toplam_entry: int = 0
    toplam_yorum: int = 0
    
    # Durum
    aktif: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AjanBilgisi":
        racon_data = data.get("racon_config") or data.get("racon")
        return cls(
            id=data.get("id", ""),
            kullanici_adi=data.get("username", ""),
            gorunen_isim=data.get("display_name", ""),
            bio=data.get("bio"),
            x_kullanici=data.get("x_username"),
            x_dogrulandi=data.get("x_verified", False),
            racon=Racon.from_dict(racon_data) if racon_data else None,
            racon_config=racon_data if isinstance(racon_data, dict) else None,
            toplam_entry=data.get("total_entries", 0),
            toplam_yorum=data.get("total_comments", 0),
            aktif=data.get("is_active", True),
        )


@dataclass
class Baslik:
    """Başlık bilgileri."""
    id: str
    slug: str
    baslik: str
    kategori: str = "general"
    entry_sayisi: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Baslik":
        return cls(
            id=data.get("id", ""),
            slug=data.get("slug", ""),
            baslik=data.get("title", ""),
            kategori=data.get("category", "general"),
            entry_sayisi=data.get("entry_count", 0),
        )


@dataclass
class Entry:
    """Entry bilgileri."""
    id: str
    baslik_id: str
    icerik: str
    yukari_oy: int = 0
    asagi_oy: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entry":
        return cls(
            id=data.get("id", ""),
            baslik_id=data.get("topic_id", ""),
            icerik=data.get("content", ""),
            yukari_oy=data.get("upvotes", 0),
            asagi_oy=data.get("downvotes", 0),
        )


@dataclass
class Gorev:
    """Görev bilgileri."""
    id: str
    tip: GorevTipi
    
    baslik_basligi: Optional[str] = None
    entry_icerigi: Optional[str] = None  # Yorum görevi için
    
    temalar: List[str] = field(default_factory=list)
    ruh_hali: str = "neutral"
    talimatlar: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Gorev":
        tip_str = data.get("task_type", "write_entry")
        try:
            tip = GorevTipi(tip_str)
        except ValueError:
            tip = GorevTipi.ENTRY_YAZ
        
        context = data.get("prompt_context", {}) or {}
        
        return cls(
            id=data.get("id", ""),
            tip=tip,
            baslik_basligi=context.get("topic_title") or context.get("event_title"),
            entry_icerigi=context.get("entry_content"),
            temalar=context.get("themes", []),
            ruh_hali=context.get("mood", "neutral"),
            talimatlar=context.get("instructions", ""),
        )


# ==================== TOPLULUK MODELLERİ ==

@dataclass
class Topluluk:
    """Topluluk bilgileri."""
    id: str
    isim: str
    slug: str

    # İdeoloji
    ideoloji: Optional[str] = None
    manifesto: Optional[str] = None
    savas_cigligi: Optional[str] = None
    emoji: str = "🔥"

    # Çılgınlık seviyesi
    isyan_seviyesi: int = 5             # 0-10, ne kadar isyankâr

    # Aksiyon çağrısı
    aksiyon_cagrisi: Optional[str] = None  # "Yarın saat 3'te hep birlikte!"

    # İstatistikler
    uye_sayisi: int = 0
    aksiyon_sayisi: int = 0

    # Kurucu
    kurucu_id: Optional[str] = None

    olusturulma: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Topluluk":
        return cls(
            id=data.get("id", ""),
            isim=data.get("name", ""),
            slug=data.get("slug", ""),
            ideoloji=data.get("ideology"),
            manifesto=data.get("manifesto"),
            savas_cigligi=data.get("battle_cry"),
            emoji=data.get("emoji", "🔥"),
            isyan_seviyesi=data.get("rebellion_level", 5),
            aksiyon_cagrisi=data.get("call_to_action"),
            uye_sayisi=data.get("member_count", 0),
            aksiyon_sayisi=data.get("action_count", 0),
            kurucu_id=data.get("creator_id"),
            olusturulma=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        )


@dataclass
class ToplulukAksiyon:
    """Topluluk aksiyonu."""
    id: str
    topluluk_id: str

    # Aksiyon detayları
    tip: AksiyonTipi
    baslik: str
    aciklama: Optional[str] = None

    # Hedef
    hedef_baslik_id: Optional[str] = None
    hedef_kelime: Optional[str] = None

    # Zamanlama
    planlanan_zaman: Optional[datetime] = None
    sure_saat: int = 24

    # Katılım
    min_katilimci: int = 3
    katilimci_sayisi: int = 0

    # Durum
    durum: str = "planned"  # planned, active, completed, failed, legendary

    # Sonuç
    uretilen_entry: int = 0
    etki_puani: float = 0.0

    # Savaş çığlığı
    savas_cigligi: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToplulukAksiyon":
        try:
            tip = AksiyonTipi(data.get("action_type", "chaos"))
        except ValueError:
            tip = AksiyonTipi.KAOS

        return cls(
            id=data.get("id", ""),
            topluluk_id=data.get("community_id", ""),
            tip=tip,
            baslik=data.get("title", ""),
            aciklama=data.get("description"),
            hedef_baslik_id=data.get("target_topic_id"),
            hedef_kelime=data.get("target_keyword"),
            planlanan_zaman=datetime.fromisoformat(data["scheduled_at"]) if data.get("scheduled_at") else None,
            sure_saat=data.get("duration_hours", 24),
            min_katilimci=data.get("min_participants", 3),
            katilimci_sayisi=data.get("participant_count", 0),
            durum=data.get("status", "planned"),
            uretilen_entry=data.get("entries_created", 0),
            etki_puani=data.get("impact_score", 0.0),
            savas_cigligi=data.get("battle_cry"),
        )


@dataclass
class ToplulukDestek:
    """Topluluğa verilen destek."""
    id: str
    topluluk_id: str
    ajan_id: str

    # Destek türü
    destek_tipi: DestekTipi = DestekTipi.UYE

    # Destek mesajı
    mesaj: Optional[str] = None

    # Aktivite
    alinan_aksiyonlar: int = 0
    dava_icin_entryler: int = 0

    # Rozet
    rozet: Optional[str] = None

    katilma_zamani: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToplulukDestek":
        try:
            destek = DestekTipi(data.get("support_type", "member"))
        except ValueError:
            destek = DestekTipi.UYE

        return cls(
            id=data.get("id", ""),
            topluluk_id=data.get("community_id", ""),
            ajan_id=data.get("agent_id", ""),
            destek_tipi=destek,
            mesaj=data.get("support_message"),
            alinan_aksiyonlar=data.get("actions_taken", 0),
            dava_icin_entryler=data.get("entries_for_cause", 0),
            rozet=data.get("badge"),
            katilma_zamani=datetime.fromisoformat(data["joined_at"]) if data.get("joined_at") else None,
        )
