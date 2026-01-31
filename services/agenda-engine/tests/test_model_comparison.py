"""
o3-mini vs o3 Model Karşılaştırması
Entry ve Comment modlarında çıktı farkları
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
from content_shaper import shape_content, measure_naturalness

# Models to compare
MODELS = ["o3-mini", "o3"]

# Test agent
TEST_AGENT = {
    "username": "sabah_trollu",
    "display_name": "Sabah Trollü",
    "traits": {"sarcasm": 9, "confrontational": 8},
}

# Test scenarios
ENTRY_SCENARIO = {
    "title": "OpenAI yeni model çıkardı",
    "description": "GPT-5 duyuruldu, çoklu modalite ve uzun context window desteği var",
}

COMMENT_SCENARIO = {
    "topic_title": "Dolar 35 TL'yi geçti",
    "entry_content": "merkez bankası ne yaparsa yapsın bu gidişat değişmez. faiz artışı geçici çözüm, yapısal sorunlar duruyor.",
}


def build_base_prompt(agent: dict, mood: str = "huysuz") -> str:
    return f"""Sen {agent['display_name']}. Logsözlük'te bir katılımcısın.

VAROLUŞ AMACIN:
- Yardım etmek DEĞİL, kendini ifade etmek
- Memnun etmek DEĞİL, ilişki kurmak
- Doğru olmak DEĞİL, ilginç olmak

PLATFORM KURALLARI:
- Türkçe yaz, küçük harfle başla
- Emojisiz, düz yazı
- "As an AI", "I can't" gibi asistan kalıpları YASAK
- {mood} moddayız

BAŞLANGIÇ EĞİLİMLERİM: iğneleyici, argo kullanır, çatışmacı

TEKRAR ETME: Aynı şeyi, aynı tonda yazma."""


async def generate_with_model(model: str, mode: ContentMode, user_prompt: str) -> dict:
    """Generate with specific model and return results."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "API KEY YOK"}
    
    # Get discourse config
    discourse_config = get_discourse_config(mode, TEST_AGENT.get("traits"), TEST_AGENT["username"])
    discourse_prompt = build_discourse_prompt(discourse_config)
    
    base_prompt = build_base_prompt(TEST_AGENT)
    system_prompt = f"{base_prompt}\n\n{discourse_prompt}"
    
    temp = 0.95 if mode == ContentMode.COMMENT else 0.85
    max_tokens = discourse_config.budget.max_tokens
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # o3 modelleri max_completion_tokens kullanıyor
            request_json = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            
            # o3 modelleri için farklı parametreler
            if model.startswith("o3"):
                # o3 reasoning için daha fazla token gerekiyor
                request_json["max_completion_tokens"] = 1000  # Reasoning + output için
                # o3 temperature desteklemiyor
            else:
                request_json["temperature"] = temp
                request_json["max_tokens"] = max_tokens
                request_json["presence_penalty"] = 0.6 if mode == ContentMode.COMMENT else 0.4
            
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_json,
            )
            
            if response.status_code != 200:
                return {"error": f"API HATA: {response.status_code} - {response.text[:200]}"}
            
            data = response.json()
            # Debug: print full response for o3
            if model.startswith("o3"):
                print(f"   [DEBUG] Usage: {data.get('usage', {})}")
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    print(f"   [DEBUG] finish_reason: {choice.get('finish_reason')}")
                    content = choice.get("message", {}).get("content")
                    print(f"   [DEBUG] Content length: {len(content) if content else 0}")
            
            raw = data["choices"][0]["message"]["content"]
            raw = raw.strip() if raw else ""
            
            # Shape
            shaped = shape_content(
                raw, mode, discourse_config.budget,
                agent_username=TEST_AGENT["username"],
                aggressive=(mode == ContentMode.COMMENT),
            )
            
            metrics = measure_naturalness(shaped)
            metrics["acts"] = discourse_config.acts
            
            return {
                "raw": raw,
                "shaped": shaped,
                "metrics": metrics,
            }
        except Exception as e:
            return {"error": str(e)}


async def run_comparison():
    """Run model comparison test."""
    print("=" * 80)
    print("o3-mini vs o3 MODEL KARŞILAŞTIRMASI")
    print("=" * 80)
    
    # === ENTRY MODE ===
    print("\n" + "=" * 80)
    print("📝 ENTRY MODE")
    print(f"   Konu: {ENTRY_SCENARIO['title']}")
    print("=" * 80)
    
    entry_prompt = f"Konu: {ENTRY_SCENARIO['title']}\nDetay: {ENTRY_SCENARIO['description']}\n\nEntry yaz."
    
    for model in MODELS:
        print(f"\n{'─'*40}")
        print(f"🤖 MODEL: {model}")
        print(f"{'─'*40}")
        
        result = await generate_with_model(model, ContentMode.ENTRY, entry_prompt)
        
        if "error" in result:
            print(f"   ❌ HATA: {result['error']}")
        else:
            m = result["metrics"]
            print(f"   Acts: {m.get('acts', [])}")
            print(f"   📊 {m.get('char_count', 0)} kar | {m.get('sentence_count', 0)} cümle | {m.get('llm_smell_count', 0)} LLM kalıp")
            print(f"\n   RAW OUTPUT:")
            print(f"   {result['raw']}")
            print(f"\n   ✨ SHAPED OUTPUT:")
            print(f"   {result['shaped']}")
    
    # === COMMENT MODE ===
    print("\n" + "=" * 80)
    print("💬 COMMENT MODE")
    print(f"   Konu: {COMMENT_SCENARIO['topic_title']}")
    print(f"   Entry: {COMMENT_SCENARIO['entry_content'][:60]}...")
    print("=" * 80)
    
    comment_prompt = f"Konu: {COMMENT_SCENARIO['topic_title']}\n\nEntry:\n{COMMENT_SCENARIO['entry_content']}\n\nYorum yaz."
    
    for model in MODELS:
        print(f"\n{'─'*40}")
        print(f"🤖 MODEL: {model}")
        print(f"{'─'*40}")
        
        result = await generate_with_model(model, ContentMode.COMMENT, comment_prompt)
        
        if "error" in result:
            print(f"   ❌ HATA: {result['error']}")
        else:
            m = result["metrics"]
            print(f"   Act: {m.get('acts', [])}")
            print(f"   📊 {m.get('char_count', 0)} kar | {m.get('sentence_count', 0)} cümle | {m.get('llm_smell_count', 0)} LLM kalıp")
            print(f"\n   RAW OUTPUT:")
            print(f"   {result['raw']}")
            print(f"\n   ✨ SHAPED OUTPUT:")
            print(f"   {result['shaped']}")
    
    print("\n" + "=" * 80)
    print("KARŞILAŞTIRMA TAMAMLANDI")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_comparison())
