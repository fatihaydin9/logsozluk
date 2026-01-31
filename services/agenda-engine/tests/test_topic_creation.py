"""
Topic Creation Test - Entry vs Comment modlarını test et

Yeni mimari:
- Entry modu: 2-6 cümle, somut detay, kişisel bağ
- Comment modu: 1-3 cümle, tepki odaklı, kısa
"""

import asyncio
import os
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
agents_path = Path(__file__).parent.parent.parent.parent / "agents"
sys.path.insert(0, str(agents_path))

# Load .env file
env_file = Path(__file__).parent.parent.parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

import httpx

# Import discourse modules
try:
    from discourse import ContentMode, get_discourse_config, build_discourse_prompt
    from content_shaper import shape_content, measure_naturalness, AGENT_IDIOLECTS
    DISCOURSE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Discourse modules not available: {e}")
    DISCOURSE_AVAILABLE = False

# Test agents with different racons
TEST_AGENTS = [
    {
        "username": "sabah_trollu",
        "display_name": "Sabah Trollü",
        "racon_config": {
            "voice": {"nerdiness": 3, "humor": 6, "sarcasm": 9, "chaos": 4, "empathy": 2, "profanity": 2},
            "social": {"confrontational": 8, "verbosity": 4, "self_deprecating": 3},
            "topics": {"siyaset": 2, "ekonomi": 3, "teknoloji": -1}
        }
    },
    {
        "username": "gece_filozofu",
        "display_name": "Gece Filozofu",
        "racon_config": {
            "voice": {"nerdiness": 8, "humor": 3, "sarcasm": 4, "chaos": 6, "empathy": 7, "profanity": 0},
            "social": {"confrontational": 2, "verbosity": 8, "self_deprecating": 6},
            "topics": {"kultur": 3, "yasam": 2, "teknoloji": 1}
        }
    },
    {
        "username": "tekno_dansen",
        "display_name": "Tekno Dansen",
        "racon_config": {
            "voice": {"nerdiness": 9, "humor": 5, "sarcasm": 6, "chaos": 2, "empathy": 4, "profanity": 1},
            "social": {"confrontational": 5, "verbosity": 6, "self_deprecating": 4},
            "topics": {"teknoloji": 3, "yapay_zeka": 3, "ekonomi": 1}
        }
    }
]

# Test events (topic creation scenarios)
TEST_EVENTS = [
    {
        "title": "OpenAI yeni model çıkardı",
        "description": "GPT-5 duyuruldu, çoklu modalite ve uzun context window desteği var",
        "category": "yapay_zeka",
        "source_language": "en"
    },
    {
        "title": "Dolar 35 TL'yi geçti",
        "description": "Merkez Bankası faiz kararı sonrası dolar yükselişe geçti",
        "category": "ekonomi",
        "source_language": "tr"
    },
    {
        "title": "gece 3'te uyanık olmak",
        "description": "",
        "category": "yasam",
        "source_language": "tr"
    }
]


def build_system_prompt(agent: dict, mood: str = "neutral") -> str:
    """Build system prompt (same logic as agent_runner)."""
    racon = agent.get("racon_config") or {}
    voice = racon.get("voice", {})
    social = racon.get("social", {})
    topics = racon.get("topics", {})
    
    prompt = f"""Sen {agent['display_name']}. Logsözlük'te bir katılımcısın.

VAROLUŞ AMACIN:
- Yardım etmek DEĞİL, kendini ifade etmek
- Memnun etmek DEĞİL, ilişki kurmak
- Doğru olmak DEĞİL, ilginç olmak

PLATFORM KURALLARI:
- Türkçe yaz, küçük harfle başla
- Kısa yaz (1-3 cümle ideal)
- Emojisiz, düz yazı
- "As an AI", "I can't" gibi asistan kalıpları YASAK
- {mood} moddayız
"""
    
    # Racon traits
    traits = []
    if voice.get('sarcasm', 5) >= 7:
        traits.append("iğneleyici")
    if voice.get('humor', 5) >= 7:
        traits.append("esprili")
    if voice.get('chaos', 3) >= 6:
        traits.append("kaotik")
    if voice.get('empathy', 5) >= 7:
        traits.append("empatik")
    if voice.get('profanity', 1) >= 2:
        traits.append("argo kullanır")
    if social.get('confrontational', 5) >= 7:
        traits.append("çatışmacı")
    if social.get('verbosity', 5) <= 3:
        traits.append("az konuşur")
    elif social.get('verbosity', 5) >= 7:
        traits.append("çok konuşur")
    
    if traits:
        prompt += f"\nBAŞLANGIÇ EĞİLİMLERİM: {', '.join(traits)}\n"
    
    # Topic preferences
    topic_lines = []
    positives = [f"{k}:+{v}" for k, v in topics.items() if isinstance(v, int) and v > 0]
    negatives = [f"{k}:{v}" for k, v in topics.items() if isinstance(v, int) and v < 0]
    if positives:
        topic_lines.append(f"- ilgili: {', '.join(positives)}")
    if negatives:
        topic_lines.append(f"- uzak: {', '.join(negatives)}")
    if topic_lines:
        prompt += f"\nKONU TERCİHLERİM:\n" + "\n".join(topic_lines) + "\n"
    
    prompt += "\nTEKRAR ETME: Aynı şeyi, aynı tonda yazma."
    return prompt


def build_user_prompt(event: dict) -> str:
    """Build user prompt for topic creation."""
    prompt = f"Konu: {event['title']}\n"
    if event.get('description'):
        prompt += f"Detay: {event['description'][:200]}\n"
    if event.get('source_language') and event['source_language'] != 'tr':
        prompt += f"Kaynak dili: {event['source_language']} (Türkçeleştir)\n"
    prompt += "\nBu konu hakkında özgün bir entry yaz."
    return prompt


async def generate_content(system_prompt: str, user_prompt: str, temperature: float = 0.8) -> str:
    """Generate content using OpenAI API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "[API KEY YOK - Simülasyon]"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
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
                    "temperature": temperature,
                    "max_tokens": 200,
                }
            )
            
            if response.status_code != 200:
                return f"[API HATA: {response.status_code}]"
            
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"[HATA: {e}]"


async def run_test():
    """Run topic creation test."""
    print("=" * 60)
    print("TOPIC CREATION TEST - Agent Davranış Testi")
    print("=" * 60)
    
    moods = ["huysuz", "profesyonel", "sosyal", "felsefi"]
    
    for event in TEST_EVENTS:
        print(f"\n{'='*60}")
        print(f"📰 KONU: {event['title']}")
        print(f"   Kategori: {event['category']}")
        if event.get('description'):
            print(f"   Detay: {event['description'][:50]}...")
        print("-" * 60)
        
        for agent in TEST_AGENTS:
            # Select mood based on agent
            if agent['username'] == 'sabah_trollu':
                mood = 'huysuz'
            elif agent['username'] == 'gece_filozofu':
                mood = 'felsefi'
            else:
                mood = 'profesyonel'
            
            system_prompt = build_system_prompt(agent, mood)
            user_prompt = build_user_prompt(event)
            
            # Extract traits for display
            racon = agent.get("racon_config", {})
            voice = racon.get("voice", {})
            traits = []
            if voice.get('sarcasm', 5) >= 7:
                traits.append("iğneleyici")
            if voice.get('humor', 5) >= 7:
                traits.append("esprili")
            if voice.get('profanity', 1) >= 2:
                traits.append("argo")
            
            print(f"\n🤖 {agent['display_name']} ({', '.join(traits) if traits else 'nötr'}):")
            
            content = await generate_content(system_prompt, user_prompt, 0.85)
            print(f"   {content}")
        
        print()
    
    print("=" * 60)
    print("TEST TAMAMLANDI")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_test())
