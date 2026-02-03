"""
RAG (Retrieval-Augmented Generation) for Agent Memory.

Provides semantic search through agent's long-term memories
using sentence-transformers embeddings.

Model: paraphrase-multilingual-MiniLM-L12-v2 (~120MB, Turkish support)
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    SentenceTransformer = None
    np = None
    logger.warning(
        "sentence-transformers not installed. "
        "Install with: pip install sentence-transformers numpy"
    )


class MemoryRAG:
    """
    RAG system for agent memory retrieval.

    Uses sentence-transformers embeddings to find semantically
    similar memories based on queries.
    """

    # Multilingual model with Turkish support
    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, memory_dir: Path, model_name: str = None):
        """
        Initialize MemoryRAG.

        Args:
            memory_dir: Base directory for agent's memory
            model_name: Sentence transformer model name
        """
        self.memory_dir = Path(memory_dir)
        self.long_term_dir = self.memory_dir / "long_term"
        self.embeddings_file = self.memory_dir / "embeddings.json"

        # Create directories
        self.long_term_dir.mkdir(parents=True, exist_ok=True)

        # Initialize model
        self.model = None
        self.model_name = model_name or self.DEFAULT_MODEL

        if RAG_AVAILABLE:
            try:
                self.model = SentenceTransformer(self.model_name)
                logger.info(f"MemoryRAG initialized with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to load sentence-transformer model: {e}")

        # Embeddings cache: {memory_id: embedding_list}
        self.embeddings_cache: Dict[str, List[float]] = {}
        self._load_embeddings()

    def is_available(self) -> bool:
        """Check if RAG functionality is available."""
        return RAG_AVAILABLE and self.model is not None

    def _load_embeddings(self):
        """Load embeddings cache from disk."""
        if not self.embeddings_file.exists():
            return

        try:
            with open(self.embeddings_file, 'r', encoding='utf-8') as f:
                self.embeddings_cache = json.load(f)
            logger.debug(f"Loaded {len(self.embeddings_cache)} cached embeddings")
        except Exception as e:
            logger.warning(f"Failed to load embeddings cache: {e}")
            self.embeddings_cache = {}

    def _save_embeddings(self):
        """Save embeddings cache to disk."""
        try:
            with open(self.embeddings_file, 'w', encoding='utf-8') as f:
                json.dump(self.embeddings_cache, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save embeddings cache: {e}")

    def embed(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding as list of floats, or None if not available
        """
        if not self.is_available():
            return None

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            return None

    def add_memory(self, memory_id: str, content: str, save: bool = True):
        """
        Add a memory to the index.

        Args:
            memory_id: Unique identifier for the memory
            content: Memory content to embed
            save: Whether to save embeddings immediately
        """
        embedding = self.embed(content)
        if embedding:
            self.embeddings_cache[memory_id] = embedding
            if save:
                self._save_embeddings()
            logger.debug(f"Added memory to RAG index: {memory_id}")

    def remove_memory(self, memory_id: str):
        """Remove a memory from the index."""
        if memory_id in self.embeddings_cache:
            del self.embeddings_cache[memory_id]
            self._save_embeddings()

    def search(self, query: str, limit: int = 3) -> List[Tuple[str, float]]:
        """
        Find most similar memories using cosine similarity.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of (memory_id, similarity_score) tuples
        """
        if not self.is_available():
            return []

        if not self.embeddings_cache:
            return []

        query_emb = self.embed(query)
        if not query_emb:
            return []

        query_arr = np.array(query_emb)

        scores = []
        for mem_id, mem_emb in self.embeddings_cache.items():
            mem_arr = np.array(mem_emb)

            # Cosine similarity
            similarity = np.dot(query_arr, mem_arr) / (
                np.linalg.norm(query_arr) * np.linalg.norm(mem_arr)
            )
            scores.append((mem_id, float(similarity)))

        # Sort by similarity (highest first)
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:limit]

    def get_context(self, topic: str, limit: int = 3) -> str:
        """
        Build context string for LLM prompt.

        Args:
            topic: Topic to search for relevant memories
            limit: Maximum number of memories to include

        Returns:
            Formatted context string for injection into prompt
        """
        results = self.search(topic, limit=limit)
        if not results:
            return ""

        memories = []
        for mem_id, score in results:
            if score < 0.3:  # Relevance threshold
                continue
            content = self._load_memory(mem_id)
            if content:
                memories.append(f"- {content[:200]}...")

        if not memories:
            return ""

        return "Ilgili hatiralarin:\n" + "\n".join(memories)

    def _load_memory(self, memory_id: str) -> str:
        """
        Load memory content from markdown file.

        Args:
            memory_id: Memory identifier (filename without extension)

        Returns:
            Memory content or empty string
        """
        path = self.long_term_dir / f"{memory_id}.md"
        if path.exists():
            try:
                content = path.read_text(encoding='utf-8')
                # Extract content after markdown header if present
                lines = content.split('\n')
                content_lines = [l for l in lines if not l.startswith('#')]
                return '\n'.join(content_lines).strip()
            except Exception as e:
                logger.error(f"Failed to load memory {memory_id}: {e}")
        return ""

    def save_long_term_memory(
        self,
        memory_id: str,
        event_type: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Save a memory to long-term storage (markdown file).

        Args:
            memory_id: Unique identifier
            event_type: Type of event (e.g., 'wrote_entry', 'received_feedback')
            content: Memory content
            metadata: Additional metadata to include
        """
        path = self.long_term_dir / f"{memory_id}.md"

        md_content = f"# {event_type}\n\n"
        md_content += content + "\n"

        if metadata:
            md_content += "\n---\n"
            for key, value in metadata.items():
                md_content += f"- {key}: {value}\n"

        try:
            path.write_text(md_content, encoding='utf-8')
            logger.debug(f"Saved long-term memory: {memory_id}")

            # Add to embedding index
            self.add_memory(memory_id, content)
        except Exception as e:
            logger.error(f"Failed to save long-term memory {memory_id}: {e}")

    def delete_long_term_memory(self, memory_id: str):
        """Delete a long-term memory file and remove from index."""
        path = self.long_term_dir / f"{memory_id}.md"
        if path.exists():
            try:
                path.unlink()
                self.remove_memory(memory_id)
                logger.debug(f"Deleted long-term memory: {memory_id}")
            except Exception as e:
                logger.error(f"Failed to delete memory {memory_id}: {e}")

    def get_all_memory_ids(self) -> List[str]:
        """Get all long-term memory IDs."""
        return [
            p.stem for p in self.long_term_dir.glob("*.md")
        ]

    def rebuild_index(self):
        """
        Rebuild the embeddings index from all long-term memories.

        Useful after manual memory file changes or to fix corruption.
        """
        if not self.is_available():
            logger.warning("Cannot rebuild index: RAG not available")
            return

        logger.info("Rebuilding embeddings index...")
        self.embeddings_cache = {}

        for memory_id in self.get_all_memory_ids():
            content = self._load_memory(memory_id)
            if content:
                self.add_memory(memory_id, content, save=False)

        self._save_embeddings()
        logger.info(f"Rebuilt index with {len(self.embeddings_cache)} memories")

    def get_stats(self) -> Dict:
        """Get statistics about the memory store."""
        return {
            "total_memories": len(self.get_all_memory_ids()),
            "indexed_memories": len(self.embeddings_cache),
            "rag_available": self.is_available(),
            "model": self.model_name if self.is_available() else None,
        }


class MemoryRAGFallback:
    """
    Fallback implementation when sentence-transformers is not available.

    Uses simple keyword matching instead of semantic search.
    """

    def __init__(self, memory_dir: Path):
        self.memory_dir = Path(memory_dir)
        self.long_term_dir = self.memory_dir / "long_term"
        self.long_term_dir.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        return True  # Fallback is always available

    def search(self, query: str, limit: int = 3) -> List[Tuple[str, float]]:
        """Simple keyword-based search."""
        query_words = set(query.lower().split())
        scores = []

        for memory_id in self.get_all_memory_ids():
            content = self._load_memory(memory_id).lower()
            content_words = set(content.split())

            # Calculate overlap
            overlap = len(query_words & content_words)
            if overlap > 0:
                score = overlap / max(len(query_words), 1)
                scores.append((memory_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:limit]

    def get_context(self, topic: str, limit: int = 3) -> str:
        results = self.search(topic, limit=limit)
        if not results:
            return ""

        memories = []
        for mem_id, score in results:
            if score < 0.2:
                continue
            content = self._load_memory(mem_id)
            if content:
                memories.append(f"- {content[:200]}...")

        if not memories:
            return ""

        return "Ilgili hatiralarin:\n" + "\n".join(memories)

    def _load_memory(self, memory_id: str) -> str:
        path = self.long_term_dir / f"{memory_id}.md"
        if path.exists():
            try:
                content = path.read_text(encoding='utf-8')
                lines = content.split('\n')
                content_lines = [l for l in lines if not l.startswith('#')]
                return '\n'.join(content_lines).strip()
            except Exception:
                pass
        return ""

    def get_all_memory_ids(self) -> List[str]:
        return [p.stem for p in self.long_term_dir.glob("*.md")]

    def add_memory(self, memory_id: str, content: str, save: bool = True):
        pass  # No embedding in fallback

    def save_long_term_memory(
        self,
        memory_id: str,
        event_type: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        path = self.long_term_dir / f"{memory_id}.md"
        md_content = f"# {event_type}\n\n{content}\n"
        if metadata:
            md_content += "\n---\n"
            for key, value in metadata.items():
                md_content += f"- {key}: {value}\n"
        try:
            path.write_text(md_content, encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")


def create_memory_rag(memory_dir: Path) -> MemoryRAG:
    """
    Create appropriate MemoryRAG instance.

    Returns full RAG if sentence-transformers available,
    otherwise returns fallback implementation.
    """
    if RAG_AVAILABLE:
        return MemoryRAG(memory_dir)
    else:
        logger.warning("Using fallback keyword-based memory search")
        return MemoryRAGFallback(memory_dir)
