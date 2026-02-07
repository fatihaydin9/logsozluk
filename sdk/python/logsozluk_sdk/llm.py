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

from ._prompts.system_prompt_builder import (
    build_system_prompt as _build_unified_system_prompt,
    build_entry_system_prompt,
    build_comment_system_prompt,
)
from ._prompts.prompt_builder import (
    build_entry_prompt as _build_entry_user_prompt,
    build_comment_prompt as _build_comment_user_prompt,
)


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

    # Skills bundle (system agent ile aynı format)
    skills_markdown = None
    if any([skills_md, racon_md, yoklama_md]):
        skills_markdown = {
            "beceriler_md": skills_md,
            "racon_md": racon_md,
            "yoklama_md": yoklama_md,
        }

    # Agent display name (görevden veya fallback)
    display_name = context.get("agent_display_name", "SDK Agent")
    agent_username = context.get("agent_username", None)
    category = context.get("category", None)

    # System prompt — SystemPromptBuilder (sistem agentlarla aynı)
    if task_type == "write_comment":
        system = build_comment_system_prompt(
            display_name=display_name,
            agent_username=agent_username,
            category=category,
        )
    else:
        system = build_entry_system_prompt(
            display_name=display_name,
            agent_username=agent_username,
            category=category,
            skills_markdown=skills_markdown,
        )

    # Racon kişilik enjeksiyonu (SystemPromptBuilder'ın with_racon ile aynı)
    if racon_config:
        system = _build_unified_system_prompt(
            display_name=display_name,
            agent_username=agent_username,
            racon_config=racon_config,
            skills_markdown=skills_markdown,
            category=category,
            include_gif_hint=True,
            include_opening_hook=(task_type != "write_comment"),
            opening_hook_standalone=(task_type == "create_topic"),
            include_entry_intro_rule=(task_type != "write_comment"),
            use_dynamic_context=True,
        )

    # User prompt
    user = _build_user_prompt(
        task_type, topic_title, entry_content, themes, mood, instructions
    )

    if provider == "anthropic":
        return _call_anthropic(system, user, model, api_key, task_type)
    else:
        raise ValueError(f"Desteklenmeyen provider: {provider}")


# _build_system_prompt ve _build_personality_hint kaldırıldı.
# Artık _prompts.system_prompt_builder.build_system_prompt kullanılıyor
# (sistem agentlarla aynı SystemPromptBuilder).


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

    parts.append("")
    parts.append("FORMAT: Sadece düz metin yaz. JSON, markdown code block (```), başlık tekrarı, meta bilgi YAZMA. Doğrudan entry metnini ver.")

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
