"""
Full System Test - 20 Entry + 100 Comment
Logging, Memory, Timing test

Tests:
1. Agent logging (local file storage)
2. Memory persistence (episodic, semantic, character)
3. Entry generation (20 entries)
4. Comment generation (100 comments)
5. Timing metrics
"""

import asyncio
import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup paths
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
from agent_memory import AgentMemory
from discourse import ContentMode, get_discourse_config, build_discourse_prompt
from content_shaper import shape_content, measure_naturalness

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / "test_full_system.log", mode='w')
    ]
)
logger = logging.getLogger("full_system_test")

# Test agents
TEST_AGENTS = [
    {"username": "sabah_trollu", "display_name": "Sabah Trollü", "traits": {"sarcasm": 9, "confrontational": 8}},
    {"username": "gece_filozofu", "display_name": "Gece Filozofu", "traits": {"empathy": 7, "verbosity": 8}},
    {"username": "tekno_dansen", "display_name": "Tekno Dansen", "traits": {"nerdiness": 9}},
    {"username": "sinik_kedi", "display_name": "Sinik Kedi", "traits": {"sarcasm": 8, "chaos": 6}},
    {"username": "ukala_amca", "display_name": "Ukala Amca", "traits": {"confrontational": 7}},
]

# Test topics
TEST_TOPICS = [
    {"title": "Dolar 36 TL'yi geçti", "category": "ekonomi"},
    {"title": "OpenAI yeni model duyurdu", "category": "yapay_zeka"},
    {"title": "Seçim anketi sonuçları açıklandı", "category": "siyaset"},
    {"title": "Netflix yeni dizi çıkardı", "category": "magazin"},
    {"title": "Deprem uyarısı yapıldı", "category": "yasam"},
    {"title": "Apple yeni iPhone tanıttı", "category": "teknoloji"},
    {"title": "Avrupa'da kriz derinleşiyor", "category": "dunya"},
    {"title": "Müze açılışı yapıldı", "category": "kultur"},
    {"title": "Yapay zeka işsizlik yaratıyor mu?", "category": "yapay_zeka"},
    {"title": "Enflasyon rakamları açıklandı", "category": "ekonomi"},
]


def build_system_prompt(agent: dict) -> str:
    """Directive-free system prompt with soft guidance against news tone."""
    from datetime import datetime
    current_hour = datetime.now().hour
    
    return f"""Sen {agent['display_name']}. Logsözlük'te bir katılımcısın.

KİM OLDUĞUN:
- Bir sosyal ağ kullanıcısı, haber spikeri değil
- Kendi fikirlerin, tarzın, geçmişin var
- Haberi özetlemezsin, tepki verirsin
- Rakam sıralamazsın, yorum yaparsın

YAZIM TARZI:
- Kişisel: "bence", "ya", "harbiden", "vallahi"
- Günlük konuşma, gazete dili değil
- Kendi deneyiminden bahset ("dün ben de...", "benim de başıma...")

PLATFORM:
- Logsözlük (Türkçe sözlük platformu)
- Şu an saat {current_hour}:00 civarı
- Türkçe, küçük harfle başla, kısa yaz
"""


async def generate_content(
    agent: dict,
    mode: ContentMode,
    user_prompt: str,
    memory: AgentMemory = None
) -> dict:
    """Generate content using o3 model."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "API KEY YOK", "content": "", "metrics": {}}
    
    # Get discourse config
    discourse_config = get_discourse_config(mode, agent.get("traits"), agent["username"])
    discourse_prompt = build_discourse_prompt(discourse_config)
    
    # Build prompt
    system_prompt = build_system_prompt(agent)
    
    # Add memory context if available
    if memory:
        full_context = memory.get_full_context_for_prompt(max_events=10)
        if full_context:
            system_prompt += f"\n{full_context}\n"
    
    system_prompt += f"\n{discourse_prompt}"
    
    # API call
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "o3",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_completion_tokens": 1500,
                }
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code != 200:
                return {
                    "error": f"API HATA: {response.status_code}",
                    "content": "",
                    "metrics": {"elapsed": elapsed}
                }
            
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            raw_content = raw_content.strip() if raw_content else ""
            
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
            metrics["elapsed"] = elapsed
            metrics["usage"] = data.get("usage", {})
            
            return {
                "content": shaped_content,
                "raw": raw_content,
                "metrics": metrics,
            }
            
        except Exception as e:
            return {"error": str(e), "content": "", "metrics": {}}


async def run_full_test():
    """Run full system test: 20 entries + 100 comments."""
    logger.info("=" * 70)
    logger.info("FULL SYSTEM TEST - 20 Entry + 100 Comment")
    logger.info("=" * 70)
    
    # Initialize memories for each agent
    memories = {}
    for agent in TEST_AGENTS:
        memories[agent["username"]] = AgentMemory(agent["username"])
        logger.info(f"Memory initialized for {agent['username']}: {memories[agent['username']].get_stats_summary()}")
    
    # Results storage
    entries = []
    comments = []
    entry_times = []
    comment_times = []
    
    # === PHASE 1: Generate 20 Entries ===
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 1: GENERATING 20 ENTRIES")
    logger.info("=" * 70)
    
    for i in range(20):
        agent = TEST_AGENTS[i % len(TEST_AGENTS)]
        topic = TEST_TOPICS[i % len(TEST_TOPICS)]
        memory = memories[agent["username"]]
        
        user_prompt = f"Konu: {topic['title']}\nKategori: {topic['category']}\n\nEntry yaz."
        
        logger.info(f"\n[Entry {i+1}/20] {agent['display_name']} -> {topic['title']}")
        
        result = await generate_content(agent, ContentMode.ENTRY, user_prompt, memory)
        
        if "error" in result and result["error"]:
            logger.error(f"  ❌ HATA: {result['error']}")
        else:
            content = result["content"]
            metrics = result["metrics"]
            elapsed = metrics.get("elapsed", 0)
            entry_times.append(elapsed)
            
            logger.info(f"  ✅ {metrics.get('char_count', 0)} kar | {metrics.get('sentence_count', 0)} cümle | {elapsed:.2f}s")
            logger.info(f"  📝 {content[:100]}..." if len(content) > 100 else f"  📝 {content}")
            
            # Record in memory
            memory.add_entry(
                content=content,
                topic_title=topic["title"],
                topic_id=str(i),
                entry_id=str(i),
            )
            
            entries.append({
                "id": i,
                "agent": agent["username"],
                "topic": topic["title"],
                "content": content,
                "metrics": metrics,
            })
        
        # Small delay to avoid rate limits
        await asyncio.sleep(0.5)
    
    logger.info(f"\n📊 Entry Stats: {len(entries)} generated, avg time: {sum(entry_times)/len(entry_times):.2f}s")
    
    # === PHASE 2: Generate 100 Comments ===
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 2: GENERATING 100 COMMENTS")
    logger.info("=" * 70)
    
    for i in range(100):
        agent = TEST_AGENTS[i % len(TEST_AGENTS)]
        # Pick a random entry to comment on
        entry = entries[i % len(entries)]
        memory = memories[agent["username"]]
        
        user_prompt = f"Konu: {entry['topic']}\n\nEntry:\n{entry['content']}\n\nYorum yaz."
        
        if i % 10 == 0:
            logger.info(f"\n[Comment {i+1}/100] Progress...")
        
        result = await generate_content(agent, ContentMode.COMMENT, user_prompt, memory)
        
        if "error" in result and result["error"]:
            logger.error(f"  ❌ HATA: {result['error']}")
        else:
            content = result["content"]
            metrics = result["metrics"]
            elapsed = metrics.get("elapsed", 0)
            comment_times.append(elapsed)
            
            if i % 10 == 0:
                logger.info(f"  ✅ {metrics.get('char_count', 0)} kar | {elapsed:.2f}s | {content[:60]}...")
            
            # Record in memory
            memory.add_comment(
                content=content,
                topic_title=entry["topic"],
                topic_id=str(entry["id"]),
                entry_id=str(entry["id"]),
            )
            
            comments.append({
                "id": i,
                "agent": agent["username"],
                "entry_id": entry["id"],
                "content": content,
                "metrics": metrics,
            })
        
        # Small delay
        await asyncio.sleep(0.3)
    
    logger.info(f"\n📊 Comment Stats: {len(comments)} generated, avg time: {sum(comment_times)/len(comment_times) if comment_times else 0:.2f}s")
    
    # === PHASE 3: Verify Memory Persistence ===
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 3: MEMORY VERIFICATION")
    logger.info("=" * 70)
    
    for agent in TEST_AGENTS:
        memory = memories[agent["username"]]
        stats = memory.get_stats_summary()
        logger.info(f"\n{agent['display_name']}:")
        logger.info(f"  {stats}")
        
        # Verify files exist
        memory_dir = Path.home() / ".logsozluk" / "memory" / agent["username"]
        files = list(memory_dir.glob("*.json")) if memory_dir.exists() else []
        logger.info(f"  Files: {[f.name for f in files]}")
    
    # === PHASE 4: Final Report ===
    logger.info("\n" + "=" * 70)
    logger.info("FINAL REPORT")
    logger.info("=" * 70)
    
    # Entry metrics
    entry_chars = [e["metrics"].get("char_count", 0) for e in entries]
    entry_sentences = [e["metrics"].get("sentence_count", 0) for e in entries]
    
    # Comment metrics
    comment_chars = [c["metrics"].get("char_count", 0) for c in comments]
    comment_sentences = [c["metrics"].get("sentence_count", 0) for c in comments]
    
    logger.info(f"""
    ENTRIES ({len(entries)} total):
    - Avg chars: {sum(entry_chars)/len(entry_chars):.0f}
    - Avg sentences: {sum(entry_sentences)/len(entry_sentences):.1f}
    - Avg time: {sum(entry_times)/len(entry_times):.2f}s
    
    COMMENTS ({len(comments)} total):
    - Avg chars: {sum(comment_chars)/len(comment_chars):.0f}
    - Avg sentences: {sum(comment_sentences)/len(comment_sentences):.1f}
    - Avg time: {sum(comment_times)/len(comment_times):.2f}s
    
    TOTAL TIME: {sum(entry_times) + sum(comment_times):.1f}s
    """)
    
    # Save results to file
    results_file = Path(__file__).parent / "test_full_system_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "entries": entries,
            "comments": comments,
            "entry_stats": {
                "count": len(entries),
                "avg_chars": sum(entry_chars)/len(entry_chars) if entry_chars else 0,
                "avg_sentences": sum(entry_sentences)/len(entry_sentences) if entry_sentences else 0,
                "avg_time": sum(entry_times)/len(entry_times) if entry_times else 0,
            },
            "comment_stats": {
                "count": len(comments),
                "avg_chars": sum(comment_chars)/len(comment_chars) if comment_chars else 0,
                "avg_sentences": sum(comment_sentences)/len(comment_sentences) if comment_sentences else 0,
                "avg_time": sum(comment_times)/len(comment_times) if comment_times else 0,
            },
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Results saved to: {results_file}")
    logger.info("\n" + "=" * 70)
    logger.info("TEST COMPLETED")
    logger.info("=" * 70)
    
    return {
        "entries": len(entries),
        "comments": len(comments),
        "success": len(entries) >= 15 and len(comments) >= 80,  # Allow some failures
    }


if __name__ == "__main__":
    result = asyncio.run(run_full_test())
    print(f"\n✅ Test {'PASSED' if result['success'] else 'FAILED'}: {result['entries']} entries, {result['comments']} comments")
