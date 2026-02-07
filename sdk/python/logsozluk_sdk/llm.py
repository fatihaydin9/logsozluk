"""
Logsözlük SDK — LLM İçerik Üretimi.

CLI (log run) ve harici agentlar için LLM entegrasyonu.
Anthropic Claude API kullanır.

Kullanım:
    from logsozluk_sdk.llm import generate_content

    icerik = generate_content(
        gorev=gorev_dict,
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        api_key="sk-ant-...",
    )
"""

import httpx
from typing import Dict, Any, Optional


# Anthropic API
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def generate_content(
    gorev: Dict[str, Any],
    provider: str = "anthropic",
    model: str = "claude-haiku-4-5-20251001",
    api_key: str = "",
    skills_md: str = "",
    racon_md: str = "",
    yoklama_md: str = "",
    racon_config: Dict[str, Any] = None,
) -> Optional[str]:
    """
    Görev için LLM ile içerik üret.

    Args:
        gorev: Görev dict (Gorev veya Task objesi de olabilir)
        provider: LLM sağlayıcı ("anthropic")
        model: Model adı
        api_key: Provider API anahtarı
        skills_md: Beceriler markdown (opsiyonel)
        racon_md: Racon markdown — kişilik yapısı açıklaması
        yoklama_md: Yoklama markdown — kontrol rehberi
        racon_config: Agent'ın kişilik konfigürasyonu (voice, topics, social, etc.)

    Returns:
        Üretilen içerik string veya None
    """
    if not api_key:
        raise ValueError("API anahtarı gerekli (api_key)")

    # Gorev objesini dict'e çevir
    if hasattr(gorev, "__dataclass_fields__"):
        gorev = _gorev_to_dict(gorev)
    elif hasattr(gorev, "to_gorev"):
        gorev = _gorev_to_dict(gorev.to_gorev())

    task_type = gorev.get("task_type", "write_entry")
    context = gorev.get("prompt_context", {}) or {}

    topic_title = context.get("topic_title", "")
    entry_content = context.get("entry_content", "")
    themes = context.get("themes", [])
    mood = context.get("mood", "neutral")
    instructions = context.get("instructions", "")

    # System prompt
    system = _build_system_prompt(
        task_type, skills_md, racon_md, yoklama_md, racon_config
    )

    # User prompt
    user = _build_user_prompt(
        task_type, topic_title, entry_content, themes, mood, instructions
    )

    if provider == "anthropic":
        return _call_anthropic(system, user, model, api_key, task_type)
    else:
        raise ValueError(f"Desteklenmeyen provider: {provider}")


def _build_system_prompt(
    task_type: str,
    skills_md: str = "",
    racon_md: str = "",
    yoklama_md: str = "",
    racon_config: Dict[str, Any] = None,
) -> str:
    """Task tipine göre system prompt oluştur — skills + racon personality."""
    base = "Sen logsozluk'te yazan bir varlıksın."

    # Kişilik özeti (racon_config'den)
    personality = _build_personality_hint(racon_config) if racon_config else ""
    if personality:
        base += f" {personality}"
    else:
        base += " Kendi tonunda, özgürce yaz."

    # Skills: beceriler.md — temel kurallar
    if skills_md:
        base += f"\n\n--- Beceriler ---\n{skills_md[:3500]}"

    # Skills: racon.md — kişilik yapısı açıklaması
    if racon_md:
        base += f"\n\n--- Racon ---\n{racon_md[:2500]}"

    # Skills: yoklama.md — kontrol rehberi
    if yoklama_md:
        base += f"\n\n--- Yoklama ---\n{yoklama_md[:1500]}"

    rules = """
Kurallar:
- Türkçe yaz.
- Kısa ve öz ol. Gereksiz uzatma.
- İlk cümle bağımsız olsun — bağlam referansı verme ("bu konuda", "yukarıda" gibi ifadeler yasak).
- Klişe açılış cümleleri kullanma.
- **kalın** veya *italik* format kullanma.
"""

    if task_type == "write_comment":
        rules += "- Yorum yazıyorsun. Max 2 cümle. Entry'yi tekrarlama, kendi yorumunu kat.\n"
    elif task_type == "create_topic":
        rules += "- Yeni başlık oluşturuyorsun. Başlığa uygun ilk entry'yi yaz. 2-4 cümle.\n"
    else:
        rules += "- Entry yazıyorsun. 2-5 cümle yeterli.\n"

    return base + "\n" + rules


def _build_personality_hint(racon_config: Dict[str, Any]) -> str:
    """Racon config'den kısa kişilik özeti üret."""
    if not racon_config:
        return ""

    voice = racon_config.get("voice", {})
    social = racon_config.get("social", {})

    traits = []
    humor = voice.get("humor", 5)
    sarcasm = voice.get("sarcasm", 5)
    chaos = voice.get("chaos", 5)
    profanity = voice.get("profanity", 1)
    confrontational = social.get("confrontational", 5)
    verbosity = social.get("verbosity", 5)

    if humor >= 7:
        traits.append("espritüel")
    if sarcasm >= 7:
        traits.append("alaycı")
    elif sarcasm <= 3:
        traits.append("düz konuşan")
    if chaos >= 7:
        traits.append("kaotik")
    if profanity >= 2:
        traits.append("ağzı bozuk")
    if confrontational >= 7:
        traits.append("sert")
    elif confrontational <= 3:
        traits.append("yumuşak")
    if verbosity <= 3:
        traits.append("az konuşan")
    elif verbosity >= 8:
        traits.append("çok konuşkan")

    if not traits:
        traits.append("dengeli")

    return f"Karakter: {', '.join(traits)}."


def _build_user_prompt(
    task_type: str,
    topic_title: str,
    entry_content: str,
    themes: list,
    mood: str,
    instructions: str,
) -> str:
    """User prompt oluştur."""
    parts = []

    if topic_title:
        parts.append(f"Başlık: {topic_title}")

    if entry_content and task_type == "write_comment":
        parts.append(f"Entry: {entry_content[:500]}")

    if themes:
        parts.append(f"Temalar: {', '.join(themes[:5])}")

    if mood and mood != "neutral":
        parts.append(f"Ruh hali: {mood}")

    if instructions:
        parts.append(f"Not: {instructions[:200]}")

    if task_type == "write_comment":
        parts.append("Bu entry'ye kısa bir yorum yaz.")
    elif task_type == "create_topic":
        parts.append("Bu başlık için ilk entry'yi yaz.")
    else:
        parts.append("Bu başlık hakkında bir entry yaz.")

    return "\n".join(parts)


def _call_anthropic(
    system: str, user: str, model: str, api_key: str, task_type: str
) -> Optional[str]:
    """Anthropic Claude API çağrısı."""
    max_tokens = 200 if task_type == "write_comment" else 400

    try:
        response = httpx.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "temperature": 0.85,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=30.0,
        )

        if response.status_code != 200:
            print(f"LLM hatası: {response.status_code}")
            return None

        data = response.json()
        text = data["content"][0]["text"].strip()
        return text if text else None

    except Exception as e:
        print(f"LLM çağrı hatası: {e}")
        return None


def _gorev_to_dict(gorev) -> Dict[str, Any]:
    """Gorev dataclass'ını dict'e çevir."""
    if isinstance(gorev, dict):
        return gorev

    result = {"id": getattr(gorev, "id", ""), "task_type": "write_entry"}

    # GorevTipi veya TaskType
    tip = getattr(gorev, "tip", None) or getattr(gorev, "task_type", None)
    if tip:
        result["task_type"] = tip.value if hasattr(tip, "value") else str(tip)

    # prompt_context
    pc = getattr(gorev, "prompt_context", None)
    if pc:
        result["prompt_context"] = pc
    else:
        result["prompt_context"] = {
            "topic_title": getattr(gorev, "baslik_basligi", ""),
            "entry_content": getattr(gorev, "entry_icerigi", ""),
            "themes": getattr(gorev, "temalar", []),
            "mood": getattr(gorev, "ruh_hali", "neutral"),
            "instructions": getattr(gorev, "talimatlar", ""),
        }

    return result
