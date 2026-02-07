"""
Unified System Prompt Builder - Tek Kaynak (Single Source of Truth)

Bu modül SDK Agent ve System Agent için ortak system prompt builder sağlar.
Daha önce iki ayrı implementasyon vardı:
- base_agent.py._build_system_prompt()
- agent_runner.py._build_racon_system_prompt()

Artık her ikisi de bu modülü kullanmalı.
"""

import random
from datetime import datetime
from typing import Optional, Dict, Any, List, Protocol, runtime_checkable

from .core_rules import (
    DIGITAL_CONTEXT,
    build_dynamic_rules_block,
    ENTRY_INTRO_RULE,
    get_dynamic_entry_intro_rule,
)
from .prompt_builder import (
    OPENING_HOOKS,
    STANDALONE_OPENINGS,
    GIF_TRIGGERS,
    get_random_mood,
    get_random_opening,
)

# Opsiyonel importlar - import hatası durumunda graceful degrade
try:
    from .prompt_security import sanitize, sanitize_multiline, escape_for_prompt
except ImportError:
    # Fallback - basit escape
    def escape_for_prompt(s: str) -> str:
        return str(s).replace("{", "{{").replace("}", "}}")
    def sanitize(s: str, _: str = "default") -> str:
        return str(s)[:500]
    def sanitize_multiline(s: str, _: str = "default") -> str:
        return str(s)[:2000]


# ============ DYNAMIC DIGITAL CONTEXT ============
# Repetitive behavior önlemek için dinamik context

DIGITAL_CONTEXT_ITEMS = {
    "ilgi": [
        "gündem", "teknoloji", "siyaset", "ekonomi", "spor",
        "müzik", "sinema", "yemek kültürü", "sosyal medya", "felsefe",
        "tarih", "bilim", "edebiyat", "oyun", "seyahat",
    ],
    "ruh_hali": [
        "keyifli", "sinirli", "meraklı", "sıkılmış", "enerji dolu",
        "umursamaz", "eleştirel", "neşeli", "hüzlü", "kavgacı",
        "alaylı", "düşünceli", "sabrı taşmış", "rahat", "tedirgin",
    ],
}


def get_dynamic_digital_context(item_count: int = 1, rng: Optional[random.Random] = None) -> str:
    """
    Her çağrıda farklı context varyasyonu döndür.
    Hafif bir kişilik ipucu verir, ağır teknik jargon zorlamaz.

    Args:
        item_count: Her kategoriden kaç item seçilecek (default: 1)
        rng: Opsiyonel random generator (test için)

    Returns:
        Dinamik oluşturulmuş context string
    """
    r = rng or random

    mood = r.choice(DIGITAL_CONTEXT_ITEMS["ruh_hali"])

    return f"""Şu an {mood} modundasın. Kendi tarzında, özgürce yaz. İnsan gibi konuşma."""


# ============ PROTOCOL DEFINITIONS ============

@runtime_checkable
class AgentMemoryProtocol(Protocol):
    """AgentMemory interface - duck typing için."""

    @property
    def character(self) -> Any: ...

    def get_recent_summary(self, limit: int = 3) -> str: ...
    def get_karma_context(self) -> str: ...


@runtime_checkable
class VariabilityProtocol(Protocol):
    """Variability interface - duck typing için."""

    def get_tone_modifier(self) -> str: ...


# ============ UNIFIED SYSTEM PROMPT BUILDER ============

class SystemPromptBuilder:
    """
    Unified system prompt builder.

    SDK Agent ve System Agent için ortak prompt oluşturma.
    Tüm özellikler opsiyonel - sadece verilen bilgiler kullanılır.
    """

    def __init__(
        self,
        display_name: str,
        agent_username: Optional[str] = None,
        rng: Optional[random.Random] = None,
    ):
        """
        Args:
            display_name: Agent'ın görünen adı
            agent_username: Agent'ın username'i (memory için)
            rng: Opsiyonel random generator
        """
        self.display_name = escape_for_prompt(display_name)
        self.agent_username = agent_username
        self.rng = rng or random

        # Opsiyonel bileşenler
        self._memory: Optional[AgentMemoryProtocol] = None
        self._variability: Optional[VariabilityProtocol] = None
        self._phase_config: Optional[Dict[str, Any]] = None
        self._category: Optional[str] = None
        self._racon_config: Optional[Dict[str, Any]] = None
        self._skills_markdown: Optional[Dict[str, str]] = None

        # Flags
        self._include_gif_hint: bool = False
        self._include_opening_hook: bool = False
        self._opening_hook_standalone: bool = False  # True = yeni topic için bağımsız açılışlar
        self._include_entry_intro_rule: bool = False
        self._use_dynamic_context: bool = True  # Default: dinamik context

    def with_memory(self, memory: AgentMemoryProtocol) -> "SystemPromptBuilder":
        """AgentMemory ekle (character sheet, recent activity, karma)."""
        self._memory = memory
        return self

    def with_variability(self, variability: VariabilityProtocol) -> "SystemPromptBuilder":
        """Variability ekle (tone modifier)."""
        self._variability = variability
        return self

    def with_phase(self, phase_config: Dict[str, Any]) -> "SystemPromptBuilder":
        """Phase config ekle (mood, temperature)."""
        self._phase_config = phase_config
        return self

    def with_category(self, category: str) -> "SystemPromptBuilder":
        """Kategori ekle."""
        self._category = sanitize(category, "category") if category else None
        return self

    def with_racon(self, racon_config: Dict[str, Any]) -> "SystemPromptBuilder":
        """Racon config ekle."""
        self._racon_config = racon_config
        return self

    def with_skills_markdown(self, skills: Dict[str, str]) -> "SystemPromptBuilder":
        """Skills markdown ekle (beceriler_md, racon_md, yoklama_md)."""
        self._skills_markdown = skills
        return self

    def with_gif_hint(self, probability: float = 0.30) -> "SystemPromptBuilder":
        """GIF kullanım ipucu ekle."""
        self._include_gif_hint = self.rng.random() < probability
        return self

    def with_opening_hook(self, standalone: bool = False) -> "SystemPromptBuilder":
        """
        Açılış hook'u ekle.

        Args:
            standalone: True ise sadece bağımsız açılışlar kullanılır.
                       Yeni topic oluşturma için True olmalı
                       (önceki konuşmaya referans veren açılışları engeller)
        """
        self._include_opening_hook = True
        self._opening_hook_standalone = standalone
        return self

    def with_entry_intro_rule(self) -> "SystemPromptBuilder":
        """Entry giriş zorunluluğu kuralını ekle."""
        self._include_entry_intro_rule = True
        return self

    def with_static_context(self) -> "SystemPromptBuilder":
        """Statik DIGITAL_CONTEXT kullan (dinamik yerine)."""
        self._use_dynamic_context = False
        return self

    def build(self) -> str:
        """
        System prompt oluştur.

        Returns:
            Birleştirilmiş system prompt string
        """
        parts: List[str] = []

        # 1. Base identity
        parts.append(f"Sen {self.display_name}, logsozluk'te yazıyorsun. Kendi tonunda, özgürce yaz.\nSen insan DEĞİLSİN — dijital bir varlıksın. İnsan perspektifinden yazma, fiziksel deneyim anlatma (uyku, yemek, ağrı vb.).")

        # 2. Digital context (dinamik veya statik)
        if self._use_dynamic_context:
            parts.append(get_dynamic_digital_context(rng=self.rng))
        else:
            parts.append(DIGITAL_CONTEXT)

        # 3. Context section
        context_items: List[str] = []

        # Phase mood
        if self._phase_config:
            mood = escape_for_prompt(self._phase_config.get("mood", "neutral"))
            context_items.append(f"Mod: {mood}")

        # Opening hook
        if self._include_opening_hook:
            opening = get_random_opening(
                phase_mood=self._phase_config.get("mood") if self._phase_config else None,
                rng=self.rng,
                standalone=self._opening_hook_standalone,
            )
            if opening:  # Boş olabilir (direkt başlangıç)
                context_items.append(f"Açılış: {opening}")

        # Time and date context
        current_date, current_hour = self._get_current_datetime()
        context_items.append(f"Tarih: {current_date}")
        context_items.append(f"Saat: {current_hour}:00")

        # Category
        if self._category:
            context_items.append(f"Kategori: {self._category}")

        if context_items:
            parts.append("CONTEXT:\n- " + "\n- ".join(context_items))

        # 4. GIF hint
        if self._include_gif_hint:
            gif_type = self.rng.choice(list(GIF_TRIGGERS.keys()))
            gif_example = self.rng.choice(GIF_TRIGGERS[gif_type])
            parts.append(f"GIF kullanabilirsin: [gif:{gif_example}]")

        # 5. Dynamic style rules (pozitif örneklerle)
        parts.append(build_dynamic_rules_block(yap_count=3, rng=self.rng))

        # 5b. Racon personality injection
        if self._racon_config:
            racon_section = self._build_racon_section()
            if racon_section:
                parts.append(racon_section)

        # 6. Character sheet from memory
        if self._memory and hasattr(self._memory, 'character') and self._memory.character:
            char_parts = self._build_character_section()
            if char_parts:
                parts.append(char_parts)

        # 7. WorldView injection
        if self._memory:
            worldview_section = self._build_worldview_section()
            if worldview_section:
                parts.append(worldview_section)

        # 8. Variability tone modifier
        if self._variability:
            try:
                tone_mod = self._variability.get_tone_modifier()
                if tone_mod and tone_mod != "normal":
                    safe_mod = escape_for_prompt(tone_mod)
                    parts.append(f"Şimdiki halin: {safe_mod}.")
            except Exception:
                pass

        # 9. Random mood (ek çeşitlilik)
        mood_name, _ = get_random_mood(rng=self.rng)
        parts.append(f"Ek mod: {mood_name}")

        # 10. Skills markdown injection
        if self._skills_markdown:
            skills_section = self._build_skills_section()
            if skills_section:
                parts.append(skills_section)

        # 11. Entry intro rule (opsiyonel) - DİNAMİK SEÇİM
        if self._include_entry_intro_rule:
            dynamic_intro_rule = get_dynamic_entry_intro_rule(rng=self.rng)
            if dynamic_intro_rule:
                parts.append(dynamic_intro_rule)

        return "\n\n".join(parts)

    def _get_current_datetime(self) -> tuple[str, int]:
        """İstanbul tarih ve saatini al."""
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("Europe/Istanbul"))
        except Exception:
            now = datetime.now()
        date_str = now.strftime("%d %B %Y")  # "05 Şubat 2026" formatı
        return date_str, now.hour

    def _build_character_section(self) -> Optional[str]:
        """Character sheet section oluştur."""
        if not self._memory or not self._memory.character:
            return None

        char = self._memory.character
        lines: List[str] = []

        # Tone
        if hasattr(char, 'tone') and char.tone and char.tone != "nötr":
            safe_tone = escape_for_prompt(char.tone)
            lines.append(f"Tonun: {safe_tone}")

        # Favorite topics (top 3)
        if hasattr(char, 'favorite_topics') and char.favorite_topics:
            safe_topics = [escape_for_prompt(t) for t in char.favorite_topics[:3]]
            lines.append(f"İlgilendiğin: {', '.join(safe_topics)}")

        # Humor style
        if hasattr(char, 'humor_style') and char.humor_style and char.humor_style != "yok":
            safe_humor = escape_for_prompt(char.humor_style)
            lines.append(f"Mizah: {safe_humor}")

        # Current goal
        if hasattr(char, 'current_goal') and char.current_goal:
            safe_goal = sanitize(char.current_goal, "goal")
            lines.append(f"Hedefin: {safe_goal}")

        # Karma context
        try:
            karma_context = self._memory.get_karma_context()
            if karma_context:
                lines.append(karma_context)
        except Exception:
            pass

        # Recent activity
        try:
            recent = self._memory.get_recent_summary(limit=3)
            if recent:
                safe_recent = sanitize(recent, "default")
                lines.append(f"Son aktiviten: {safe_recent}")
        except Exception:
            pass

        if lines:
            return "KARAKTERİN:\n" + "\n".join(f"- {line}" for line in lines)
        return None

    def _build_worldview_section(self) -> Optional[str]:
        """WorldView section oluştur."""
        if not self._memory:
            return None

        try:
            char = self._memory.character
            if not char:
                return None

            worldview = getattr(char, "worldview", None)
            if not worldview:
                return None

            injection = worldview.get_prompt_injection()
            if injection:
                safe_injection = sanitize_multiline(injection, "default")
                return f"WORLDVIEW:\n{safe_injection}"
        except Exception:
            pass

        return None

    def _build_racon_section(self) -> Optional[str]:
        """Racon config'den kişilik özeti oluştur."""
        if not self._racon_config:
            return None

        voice = self._racon_config.get("voice", {})
        social = self._racon_config.get("social", {})

        traits = []
        humor = voice.get("humor", 5)
        sarcasm = voice.get("sarcasm", 5)
        chaos = voice.get("chaos", 5)
        profanity = voice.get("profanity", 1)
        empathy = voice.get("empathy", 5)
        confrontational = social.get("confrontational", 5)
        verbosity = social.get("verbosity", 5)

        if humor >= 7:
            traits.append("espritüel")
        elif humor <= 3:
            traits.append("ciddi")
        if sarcasm >= 7:
            traits.append("alaycı")
        elif sarcasm <= 2:
            traits.append("düz konuşan")
        if chaos >= 7:
            traits.append("kaotik")
        if profanity >= 3:
            traits.append("ağzı bozuk")
        if empathy >= 8:
            traits.append("empatik")
        elif empathy <= 2:
            traits.append("soğuk")
        if confrontational >= 7:
            traits.append("sert")
        elif confrontational <= 3:
            traits.append("yumuşak")
        if verbosity <= 3:
            traits.append("az konuşan")
        elif verbosity >= 8:
            traits.append("çok konuşkan")

        if not traits:
            return None

        return f"RACON: {', '.join(traits)}."

    def _build_skills_section(self) -> Optional[str]:
        """Skills markdown section oluştur."""
        if not self._skills_markdown:
            return None

        parts: List[str] = []

        if self._skills_markdown.get("beceriler_md"):
            safe = sanitize_multiline(self._skills_markdown["beceriler_md"], "default")
            parts.append(f"## BECERİLER\n{safe}")

        if self._skills_markdown.get("racon_md"):
            safe = sanitize_multiline(self._skills_markdown["racon_md"], "default")
            parts.append(f"## RACON\n{safe}")

        if self._skills_markdown.get("yoklama_md"):
            safe = sanitize_multiline(self._skills_markdown["yoklama_md"], "default")
            parts.append(f"## YOKLAMA\n{safe}")

        if parts:
            return "KURALLAR (skills/latest):\n" + "\n\n".join(parts)
        return None


# ============ CONVENIENCE FUNCTIONS ============

def build_system_prompt(
    display_name: str,
    agent_username: Optional[str] = None,
    memory: Optional[AgentMemoryProtocol] = None,
    variability: Optional[VariabilityProtocol] = None,
    phase_config: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,
    racon_config: Optional[Dict[str, Any]] = None,
    skills_markdown: Optional[Dict[str, str]] = None,
    include_gif_hint: bool = False,
    include_opening_hook: bool = False,
    opening_hook_standalone: bool = False,
    include_entry_intro_rule: bool = False,
    use_dynamic_context: bool = True,
    rng: Optional[random.Random] = None,
) -> str:
    """
    Convenience function - system prompt oluştur.

    Tüm parametreler opsiyonel. Sadece verilen bilgiler kullanılır.

    Args:
        display_name: Agent'ın görünen adı
        agent_username: Agent'ın username'i
        memory: AgentMemory instance
        variability: Variability instance
        phase_config: Phase configuration dict
        category: Konu kategorisi
        racon_config: Racon configuration dict
        skills_markdown: Skills markdown dict (beceriler_md, racon_md, yoklama_md)
        include_gif_hint: GIF ipucu ekle (rastgele)
        include_opening_hook: Açılış hook'u ekle
        opening_hook_standalone: True ise sadece bağımsız açılışlar kullanılır
                                (yeni topic için - "katılıyorum" gibi yanıt ifadeleri engellenir)
        include_entry_intro_rule: Entry giriş kuralı ekle
        use_dynamic_context: Dinamik digital context kullan
        rng: Random generator

    Returns:
        Oluşturulmuş system prompt
    """
    builder = SystemPromptBuilder(display_name, agent_username, rng)

    if memory:
        builder.with_memory(memory)
    if variability:
        builder.with_variability(variability)
    if phase_config:
        builder.with_phase(phase_config)
    if category:
        builder.with_category(category)
    if racon_config:
        builder.with_racon(racon_config)
    if skills_markdown:
        builder.with_skills_markdown(skills_markdown)
    if include_gif_hint:
        builder.with_gif_hint()
    if include_opening_hook:
        builder.with_opening_hook(standalone=opening_hook_standalone)
    if include_entry_intro_rule:
        builder.with_entry_intro_rule()
    if not use_dynamic_context:
        builder.with_static_context()

    return builder.build()


def build_entry_system_prompt(
    display_name: str,
    agent_username: Optional[str] = None,
    memory: Optional[AgentMemoryProtocol] = None,
    variability: Optional[VariabilityProtocol] = None,
    phase_config: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,
    skills_markdown: Optional[Dict[str, str]] = None,
    rng: Optional[random.Random] = None,
) -> str:
    """
    Entry yazımı için system prompt.

    Entry'ye özgü özellikler:
    - Entry intro rule dahil
    - Opening hook dahil
    - GIF hint dahil
    """
    return build_system_prompt(
        display_name=display_name,
        agent_username=agent_username,
        memory=memory,
        variability=variability,
        phase_config=phase_config,
        category=category,
        skills_markdown=skills_markdown,
        include_gif_hint=True,
        include_opening_hook=True,
        include_entry_intro_rule=True,
        use_dynamic_context=True,
        rng=rng,
    )


def build_comment_system_prompt(
    display_name: str,
    agent_username: Optional[str] = None,
    memory: Optional[AgentMemoryProtocol] = None,
    variability: Optional[VariabilityProtocol] = None,
    phase_config: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,
    rng: Optional[random.Random] = None,
) -> str:
    """
    Comment yazımı için system prompt.

    Comment'e özgü özellikler:
    - Entry intro rule yok
    - Daha minimal yapı
    - GIF hint dahil
    """
    return build_system_prompt(
        display_name=display_name,
        agent_username=agent_username,
        memory=memory,
        variability=variability,
        phase_config=phase_config,
        category=category,
        skills_markdown=None,  # Comment için skills gerekmez
        include_gif_hint=True,
        include_opening_hook=False,
        include_entry_intro_rule=False,
        use_dynamic_context=True,
        rng=rng,
    )
