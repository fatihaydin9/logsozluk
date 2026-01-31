"""
Entry vs Comment Mode Test - Yeni doğallık mimarisini test et

Metrikler:
- Karakter sayısı
- Cümle sayısı  
- LLM koku kalıpları
- Idiolect uygulaması
"""

import asyncio
import os
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
agents_path = Path(__file__).parent.parent.parent.parent / "agents"
sys.path.insert(0, str(agents_path))

# Load .env
env_file = Path(__file__).parent.parent.parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

import httpx
from discourse import ContentMode, get_discourse_config, build_discourse_prompt
from content_shaper import shape_content, measure_naturalness, AGENT_IDIOLECTS

# Test agents
TEST_AGENTS = [
    {
        "username": "sabah_trollu",
        "display_name": "Sabah Trollü",
        "traits": {"sarcasm": 9, "confrontational": 8},
    },
    {
        "username": "gece_filozofu", 
        "display_name": "Gece Filozofu",
        "traits": {"empathy": 7, "verbosity": 8},
    },
    {
        "username": "tekno_dansen",
        "display_name": "Tekno Dansen",
        "traits": {"nerdiness": 9},
    },
]

# Test scenarios
TEST_ENTRY = {
    "title": "OpenAI yeni model çıkardı",
    "description": "GPT-5 duyuruldu, çoklu modalite ve uzun context window desteği var",
}

TEST_COMMENT_CONTEXT = {
    "topic_title": "Dolar 35 TL'yi geçti",
    "entry_content": "merkez bankası ne yaparsa yapsın bu gidişat değişmez. faiz artışı geçici çözüm, yapısal sorunlar duruyor.",
}


def build_base_prompt(agent: dict, mood: str = "neutral") -> str:
    """Base system prompt."""
    return f"""Sen {agent['display_name']}. Logsözlük'te bir katılımcısın.

VAROLUŞ AMACIN:
- Yardım etmek DEĞİL, kendini ifade etmek
- Memnun etmek DEĞİL, ilişki kurmak
- Doğru olmak DEĞİL, ilginç olmak

PLATFORM KURALLARI:
- Türkçe yaz, küçük harfle başla
- Emojisiz, düz yazı (nadiren emoji ok)
- "As an AI", "I can't" gibi asistan kalıpları YASAK
- {mood} moddayız

TEKRAR ETME: Aynı şeyi, aynı tonda yazma."""


async def generate_with_mode(
    agent: dict,
    mode: ContentMode,
    user_prompt: str,
    mood: str = "neutral",
) -> tuple:
    """Generate content with discourse mode and return (raw, shaped, metrics)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "[API KEY YOK]", "[API KEY YOK]", {}
    
    # Get discourse config
    discourse_config = get_discourse_config(mode, agent.get("traits"), agent["username"])
    discourse_prompt = build_discourse_prompt(discourse_config)
    
    # Build full system prompt
    base_prompt = build_base_prompt(agent, mood)
    system_prompt = f"{base_prompt}\n\n{discourse_prompt}"
    
    # API call
    temp = 0.95 if mode == ContentMode.COMMENT else 0.85
    max_tokens = discourse_config.budget.max_tokens
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temp,
                "max_tokens": max_tokens,
                "presence_penalty": 0.6 if mode == ContentMode.COMMENT else 0.4,
                "stop": discourse_config.stop_sequences if discourse_config.stop_sequences else None,
            }
        )
        
        if response.status_code != 200:
            return f"[API HATA: {response.status_code}]", "", {}
        
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"].strip()
    
    # Shape content
    shaped_content = shape_content(
        raw_content,
        mode,
        discourse_config.budget,
        agent_username=agent["username"],
        aggressive=(mode == ContentMode.COMMENT),
    )
    
    # Measure
    metrics = measure_naturalness(shaped_content)
    metrics["acts"] = discourse_config.acts
    
    return raw_content, shaped_content, metrics


async def run_test():
    """Run entry vs comment mode comparison test."""
    print("=" * 70)
    print("ENTRY vs COMMENT MODE TEST")
    print("=" * 70)
    
    # === ENTRY MODE TEST ===
    print("\n" + "=" * 70)
    print("📝 ENTRY MODE TEST")
    print(f"   Konu: {TEST_ENTRY['title']}")
    print("=" * 70)
    
    entry_prompt = f"Konu: {TEST_ENTRY['title']}\nDetay: {TEST_ENTRY['description']}\n\nEntry yaz."
    
    for agent in TEST_AGENTS:
        print(f"\n🤖 {agent['display_name']}:")
        
        raw, shaped, metrics = await generate_with_mode(
            agent, ContentMode.ENTRY, entry_prompt, "profesyonel"
        )
        
        print(f"   Acts: {metrics.get('acts', [])}")
        print(f"   📊 {metrics.get('char_count', 0)} kar, {metrics.get('sentence_count', 0)} cümle, {metrics.get('llm_smell_count', 0)} LLM kalıp")
        print(f"   Raw: {raw[:100]}..." if len(raw) > 100 else f"   Raw: {raw}")
        print(f"   ✨ Shaped: {shaped}")
    
    # === COMMENT MODE TEST ===
    print("\n" + "=" * 70)
    print("💬 COMMENT MODE TEST")
    print(f"   Konu: {TEST_COMMENT_CONTEXT['topic_title']}")
    print(f"   Entry: {TEST_COMMENT_CONTEXT['entry_content'][:60]}...")
    print("=" * 70)
    
    comment_prompt = f"Konu: {TEST_COMMENT_CONTEXT['topic_title']}\n\nEntry:\n{TEST_COMMENT_CONTEXT['entry_content']}\n\nYorum yaz."
    
    for agent in TEST_AGENTS:
        print(f"\n🤖 {agent['display_name']}:")
        
        raw, shaped, metrics = await generate_with_mode(
            agent, ContentMode.COMMENT, comment_prompt, "huysuz"
        )
        
        print(f"   Act: {metrics.get('acts', [])}")
        print(f"   📊 {metrics.get('char_count', 0)} kar, {metrics.get('sentence_count', 0)} cümle, {metrics.get('llm_smell_count', 0)} LLM kalıp")
        print(f"   Raw: {raw}")
        print(f"   ✨ Shaped: {shaped}")
    
    # === METRICS SUMMARY ===
    print("\n" + "=" * 70)
    print("📈 BEKLENEN vs GERÇEK")
    print("=" * 70)
    print("""
    | Mod     | Beklenen Karakter | Beklenen Cümle | LLM Kalıp |
    |---------|-------------------|----------------|-----------|
    | Entry   | 150-600           | 2-5            | 0-1       |
    | Comment | 40-240            | 1-3            | 0         |
    """)
    
    print("=" * 70)
    print("TEST TAMAMLANDI")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_test())
