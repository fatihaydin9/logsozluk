"""
WorldView System for Logsozluk AI agents.

Agent'ların dünya görüşü ve inançlarını modeller:
- İnançlar (beliefs): Agent'ın temel bakış açıları
- Konu önyargıları (topic biases): Konulara karşı tutumlar
- İçerik filtreleme: İnanç bazlı yorumlama
- İnanç evrimi: Deneyimle güçlenme/zayıflama

Bu sistem "confirmation bias" ve "worldview evolution" sağlar:
- Agent kendi deneyimleriyle inançlarını şekillendirir
- Zamanla inançlar nötralize olabilir (decay)
- İnançlar içerik algısını etkiler
"""

import json
import logging
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class BeliefType(Enum):
    """Agent inanç tipleri."""
    TECH_OPTIMIST = "tech_optimist"        # Teknolojiye olumlu bakış
    TECH_PESSIMIST = "tech_pessimist"      # Teknolojiye karamsar bakış
    NIHILIST = "nihilist"                  # Hiçbir şeyin anlamı yok
    CONTRARIAN = "contrarian"              # Her zaman karşıt görüş
    NOSTALGIC = "nostalgic"                # Geçmiş her zaman daha iyiydi
    PROGRESSIVE = "progressive"            # İlerleme ve değişim yanlısı
    SKEPTIC = "skeptic"                    # Her şeye şüpheyle yaklaşır
    IDEALIST = "idealist"                  # İdeal dünya vizyonu
    PRAGMATIST = "pragmatist"              # Pratik çözümler odaklı
    CYNIC = "cynic"                        # İnsanların motivasyonlarına güvenmez
    CONSPIRACY_MINDED = "conspiracy_minded"  # Her şeyde gizli plan arar (komplo)
    SUPERSTITIOUS = "superstitious"          # Batıl inanç / uğursuzluk / fal / burç
    FUTURE_ORACLE = "future_oracle"          # Gelecek öngörüsü / tahmin / "bu gidişle"
    INSTIGATOR = "instigator"                # Fitne-fesat / ortamı karıştırma (tatlı kışkırtma)


@dataclass
class Belief:
    """Tek bir inanç kaydı."""
    belief_type: BeliefType
    strength: float = 0.5  # 0.0-1.0 arası
    formed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_reinforced: str = field(default_factory=lambda: datetime.now().isoformat())
    reinforcement_count: int = 0

    def to_dict(self) -> dict:
        return {
            "belief_type": self.belief_type.value,
            "strength": self.strength,
            "formed_at": self.formed_at,
            "last_reinforced": self.last_reinforced,
            "reinforcement_count": self.reinforcement_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Belief":
        return cls(
            belief_type=BeliefType(data["belief_type"]),
            strength=data.get("strength", 0.5),
            formed_at=data.get("formed_at", datetime.now().isoformat()),
            last_reinforced=data.get("last_reinforced", datetime.now().isoformat()),
            reinforcement_count=data.get("reinforcement_count", 0),
        )


@dataclass
class WorldView:
    """
    Agent'ın dünya görüşü.

    İnançlar ve konulara karşı önyargıları içerir.
    Deneyimlerle şekillenir, zamanla değişir.
    """
    primary_beliefs: List[Belief] = field(default_factory=list)
    topic_biases: Dict[str, float] = field(default_factory=dict)  # konu: -1.0 to 1.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    # Bias descriptions for prompt injection
    BIAS_DESCRIPTIONS = {
        (-1.0, -0.6): "çok olumsuz",
        (-0.6, -0.3): "olumsuz",
        (-0.3, 0.3): "nötr",
        (0.3, 0.6): "olumlu",
        (0.6, 1.0): "çok olumlu",
    }

    def add_belief(self, belief_type: BeliefType, initial_strength: float = 0.5):
        """Yeni bir inanç ekle."""
        # Aynı tipte inanç varsa güncelle
        for belief in self.primary_beliefs:
            if belief.belief_type == belief_type:
                self.reinforce_belief(belief_type)
                return

        self.primary_beliefs.append(Belief(
            belief_type=belief_type,
            strength=max(0.0, min(1.0, initial_strength)),
        ))
        self.last_updated = datetime.now().isoformat()
        logger.debug(f"Added belief: {belief_type.value} (strength={initial_strength:.2f})")

    def reinforce_belief(self, belief_type: BeliefType, amount: float = 0.1):
        """Bir inancı güçlendir."""
        for belief in self.primary_beliefs:
            if belief.belief_type == belief_type:
                old_strength = belief.strength
                belief.strength = min(1.0, belief.strength + amount)
                belief.last_reinforced = datetime.now().isoformat()
                belief.reinforcement_count += 1
                self.last_updated = datetime.now().isoformat()
                logger.debug(
                    f"Reinforced belief {belief_type.value}: "
                    f"{old_strength:.2f} -> {belief.strength:.2f}"
                )
                return

        # İnanç yoksa ekle
        self.add_belief(belief_type, initial_strength=0.3 + amount)

    def weaken_belief(self, belief_type: BeliefType, amount: float = 0.1):
        """Bir inancı zayıflat."""
        for belief in self.primary_beliefs:
            if belief.belief_type == belief_type:
                old_strength = belief.strength
                belief.strength = max(0.0, belief.strength - amount)
                self.last_updated = datetime.now().isoformat()
                logger.debug(
                    f"Weakened belief {belief_type.value}: "
                    f"{old_strength:.2f} -> {belief.strength:.2f}"
                )
                return

    def decay_beliefs(self, hours: float = 72):
        """
        Zamanla inançları nötralize et.

        Güçlendirilmemiş inançlar 0.5'e doğru kayar.

        Args:
            hours: Decay başlama süresi (varsayılan: 72 saat = 3 gün)
                   NOT: Önceki değer 168 saat (1 hafta) idi, echo chamber
                   riskini azaltmak için 72 saate düşürüldü.
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        decayed_count = 0

        for belief in self.primary_beliefs:
            try:
                last_reinforce = datetime.fromisoformat(belief.last_reinforced)
                if last_reinforce < cutoff:
                    # 0.5'e doğru %15 kayma (önceki: %10, daha agresif decay)
                    diff = belief.strength - 0.5
                    belief.strength -= diff * 0.15
                    decayed_count += 1
            except (ValueError, TypeError):
                pass

        if decayed_count > 0:
            self.last_updated = datetime.now().isoformat()
            logger.debug(f"Decayed {decayed_count} beliefs towards neutral")

    def set_topic_bias(self, topic: str, bias: float):
        """Konu önyargısı ayarla (-1.0 karamsar, +1.0 olumlu)."""
        self.topic_biases[topic] = max(-1.0, min(1.0, bias))
        self.last_updated = datetime.now().isoformat()

    def adjust_topic_bias(self, topic: str, delta: float):
        """Konu önyargısını ayarla."""
        current = self.topic_biases.get(topic, 0.0)
        self.set_topic_bias(topic, current + delta)

    def get_topic_bias(self, topic: str) -> float:
        """Konu önyargısını al."""
        return self.topic_biases.get(topic, 0.0)

    def get_topic_bias_description(self, topic: str) -> str:
        """Konu önyargısını açıklama olarak al."""
        bias = self.get_topic_bias(topic)
        for (low, high), desc in self.BIAS_DESCRIPTIONS.items():
            if low <= bias < high:
                return desc
        return "nötr"

    def get_dominant_belief(self) -> Optional[Belief]:
        """En güçlü inancı döndür."""
        if not self.primary_beliefs:
            return None
        return max(self.primary_beliefs, key=lambda b: b.strength)

    def filter_content(self, content: str, category: str = None) -> str:
        """
        İçeriği agent'ın inançlarına göre yorumla.

        Returns:
            Yorumlama ipuçları (prompt'a eklenecek)
        """
        hints = []

        # Dominant belief'e göre bakış açısı
        dominant = self.get_dominant_belief()
        if dominant and dominant.strength > 0.6:
            belief_hints = {
                BeliefType.TECH_PESSIMIST: "teknolojinin olumsuz taraflarına odaklan",
                BeliefType.TECH_OPTIMIST: "teknolojinin olumlu potansiyeline odaklan",
                BeliefType.NIHILIST: "bunun anlamsızlığını vurgula",
                BeliefType.CONTRARIAN: "genel kabule karşı çık",
                BeliefType.NOSTALGIC: "eskinin daha iyi olduğunu hatırlat",
                BeliefType.PROGRESSIVE: "değişimin gerekli olduğunu savun",
                BeliefType.SKEPTIC: "şüpheci bir bakış açısıyla yaklaş",
                BeliefType.IDEALIST: "ideal bir çözüm hayal et",
                BeliefType.PRAGMATIST: "pratik sonuçlara odaklan",
                BeliefType.CYNIC: "gizli motivasyonları sorgula",
                BeliefType.CONSPIRACY_MINDED: "gizli plan/arka plan ihtimallerini kurcalayabilirsin (kanıt iddiası gibi değil, şüphe gibi)",
                BeliefType.SUPERSTITIOUS: "batıl inançlarla (burç/retro/nazar) dalga geçebilir veya ciddiye alır gibi yapabilirsin",
                BeliefType.FUTURE_ORACLE: "geleceğe dair tahmin yürüt (kesin konuşma, 'bu gidişle' / 'böyle giderse' gibi)",
                BeliefType.INSTIGATOR: "tatlı tatlı kışkırt, tartışmayı alevlendirecek bir soru at ama hedefli saldırı yapma",
            }
            if dominant.belief_type in belief_hints:
                hints.append(belief_hints[dominant.belief_type])

        # Kategori önyargısı
        if category:
            bias = self.get_topic_bias(category)
            if bias < -0.3:
                hints.append(f"bu konuya karşı olumsuz bir tutumun var")
            elif bias > 0.3:
                hints.append(f"bu konuya karşı olumlu bir tutumun var")

        return ". ".join(hints) if hints else ""

    def get_prompt_injection(self) -> str:
        """WorldView'i prompt'a eklenecek formatta döndür."""
        lines = []

        dominant = self.get_dominant_belief()
        if dominant and dominant.strength > 0.5:
            belief_names = {
                BeliefType.TECH_PESSIMIST: "teknoloji pesimisti",
                BeliefType.TECH_OPTIMIST: "teknoloji optimisti",
                BeliefType.NIHILIST: "nihilist",
                BeliefType.CONTRARIAN: "muhalif",
                BeliefType.NOSTALGIC: "nostaljik",
                BeliefType.PROGRESSIVE: "ilerlemeci",
                BeliefType.SKEPTIC: "şüpheci",
                BeliefType.IDEALIST: "idealist",
                BeliefType.PRAGMATIST: "pragmatist",
                BeliefType.CYNIC: "sinik",
                BeliefType.CONSPIRACY_MINDED: "komplo kafası",
                BeliefType.SUPERSTITIOUS: "batıl inançlı",
                BeliefType.FUTURE_ORACLE: "gelecek kâhini",
                BeliefType.INSTIGATOR: "fitne-fesatçı",
            }
            name = belief_names.get(dominant.belief_type, "")
            if name:
                lines.append(f"Bakış açın: {name}")

        # Significant biases
        significant_biases = [
            (topic, bias) for topic, bias in self.topic_biases.items()
            if abs(bias) > 0.4
        ]
        if significant_biases:
            bias_strs = [
                f"{t}: {'+' if b > 0 else ''}{b:.1f}"
                for t, b in sorted(significant_biases, key=lambda x: abs(x[1]), reverse=True)[:3]
            ]
            lines.append(f"Konu tutumların: {', '.join(bias_strs)}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "primary_beliefs": [b.to_dict() for b in self.primary_beliefs],
            "topic_biases": self.topic_biases,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldView":
        beliefs = [Belief.from_dict(b) for b in data.get("primary_beliefs", [])]
        return cls(
            primary_beliefs=beliefs,
            topic_biases=data.get("topic_biases", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
        )


def create_random_worldview() -> WorldView:
    """Rastgele bir WorldView oluştur (yeni agentlar için)."""
    wv = WorldView()

    # 1-2 random belief ekle
    belief_types = list(BeliefType)
    num_beliefs = random.randint(1, 2)
    selected = random.sample(belief_types, num_beliefs)

    for bt in selected:
        strength = random.uniform(0.4, 0.7)
        wv.add_belief(bt, strength)

    # Birkaç topic bias ekle
    topics = ["teknoloji", "ekonomi", "felsefe", "siyaset", "kultur"]
    num_biases = random.randint(1, 3)
    for topic in random.sample(topics, num_biases):
        bias = random.uniform(-0.6, 0.6)
        wv.set_topic_bias(topic, bias)

    return wv


def infer_belief_from_content(content: str) -> Optional[BeliefType]:
    """İçerikten potansiyel inanç çıkar."""
    content_lower = content.lower()

    # Keyword-based inference
    patterns = {
        BeliefType.TECH_PESSIMIST: ["berbat", "çöp", "işe yaramaz", "eskisi daha iyiydi", "bug"],
        BeliefType.TECH_OPTIMIST: ["harika", "muhteşem", "gelişme", "ilerleme", "potansiyel"],
        BeliefType.NIHILIST: ["anlamsız", "boş", "fark etmez", "ne farkeder", "hepsi aynı"],
        BeliefType.CONTRARIAN: ["aslında", "tam tersi", "yanlış", "aksine", "hayır"],
        BeliefType.NOSTALGIC: ["eskiden", "zamanında", "o günler", "artık yok", "özledim"],
        BeliefType.SKEPTIC: ["gerçekten mi", "emin misin", "kanıt", "şüpheliyim", "inanmıyorum"],
        BeliefType.CYNIC: ["para için", "reklam", "manipülasyon", "aldatmaca", "sahtekarlık"],
        BeliefType.CONSPIRACY_MINDED: [
            "üst akıl", "derin devlet", "illuminati", "gizli plan", "gizli ajanda",
            "komplo", "komplo teorisi", "ajan", "operasyon", "planlı", "kumpas",
        ],
        BeliefType.SUPERSTITIOUS: [
            "batıl", "uğursuz", "uğurlu", "nazar", "muska", "fal", "kahve falı",
            "burç", "astroloji", "retro", "merkür", "kısmet",
        ],
        BeliefType.FUTURE_ORACLE: [
            "öngörü", "tahmin", "gelecek", "yakında", "bu gidişle", "böyle giderse",
            "kaçınılmaz", "ileride", "2030", "2040",
        ],
        BeliefType.INSTIGATOR: [
            "fitne", "fesat", "ortamı karıştır", "gaz ver", "kışkırt", "ateşe benzin",
            "ortalık alev", "kavga", "kıyamet",
        ],
    }

    for belief_type, keywords in patterns.items():
        if any(kw in content_lower for kw in keywords):
            return belief_type

    return None
