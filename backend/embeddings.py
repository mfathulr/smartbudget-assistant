"""Embedding utilities for semantic memory search.

Functions:
- generate_embedding(text, provider, model): returns list[float]
- ensure_log_embeddings(user_id, batch_size=50): create embeddings for recent logs missing vectors
- semantic_search(user_id, query, top_k=5): cosine similarity search over stored log embeddings

Storage schema: llm_log_embeddings( id, log_id, user_id, embedding(JSON), model, created_at )

Provider modes:
- 'openai': uses OpenAI Embeddings API (text-embedding-3-small by default)
- 'local': fallback deterministic embedding (hash-based) without external calls

The 'local' provider is NOT semantically rich but allows offline experimentation.
"""

from __future__ import annotations
import json
import math
from typing import List, Tuple, Dict
from openai import OpenAI
from database import get_db

# Default embedding model
OPENAI_EMBED_MODEL = "text-embedding-3-small"

client = OpenAI()


def _norm_text(t: str) -> str:
    return " ".join(t.strip().lower().split())[:4000]  # length guard


def generate_embedding(
    text: str, provider: str = "openai", model: str = OPENAI_EMBED_MODEL
) -> List[float]:
    """Generate embedding for a single text. Fallback to 'local' simple embedding if provider mismatch or error."""
    norm = _norm_text(text)
    if not norm:
        return []
    if provider == "local":
        # Simple hashed embedding: map characters to buckets (NOT semantic, just placeholder)
        buckets = [0.0] * 128
        for ch in norm:
            buckets[ord(ch) % 128] += 1.0
        # L2 normalize
        mag = math.sqrt(sum(v * v for v in buckets)) or 1.0
        return [round(v / mag, 6) for v in buckets]
    try:
        resp = client.embeddings.create(model=model, input=[norm])
        return resp.data[0].embedding  # already list[float]
    except Exception as e:
        # Fallback to local if OpenAI fails
        print(f"[WARN] OpenAI embedding failed, using local fallback: {e}")
        return generate_embedding(norm, provider="local")


def ensure_log_embeddings(user_id: int, batch_size: int = 50) -> Dict[str, int]:
    """Create embeddings for most recent logs without embeddings.
    Returns counts: {'processed': X, 'skipped': Y}
    """
    db = get_db()
    # Determine provider from config (default openai)
    cur = db.execute(
        "SELECT embedding_provider FROM llm_memory_config WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    provider = (
        row["embedding_provider"] if row and row["embedding_provider"] else "openai"
    )

    # Find logs lacking embeddings
    cur = db.execute(
        """
        SELECT l.id, l.content FROM llm_logs l
        LEFT JOIN llm_log_embeddings e ON e.log_id = l.id
        WHERE l.user_id = ? AND e.id IS NULL
        ORDER BY l.id DESC LIMIT ?
        """,
        (user_id, batch_size),
    )
    rows = cur.fetchall()
    if not rows:
        return {"processed": 0, "skipped": 0}

    texts = [r["content"] for r in rows]
    # Try batching for OpenAI provider
    embeddings: List[List[float]] = []
    if provider == "openai":
        try:
            resp = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=texts)
            embeddings = [d.embedding for d in resp.data]
        except Exception as e:
            print(f"[WARN] Batch embedding failed, falling back item-wise: {e}")
            embeddings = [generate_embedding(t, provider=provider) for t in texts]
    else:
        embeddings = [generate_embedding(t, provider=provider) for t in texts]

    processed = 0
    skipped = 0
    for row, emb in zip(rows, embeddings):
        if not emb:
            skipped += 1
            continue
        db.execute(
            "INSERT INTO llm_log_embeddings (log_id, user_id, embedding, model) VALUES (?, ?, ?, ?)",
            (
                row["id"],
                user_id,
                json.dumps(emb),
                provider if provider != "openai" else OPENAI_EMBED_MODEL,
            ),
        )
        processed += 1
    db.commit()
    return {"processed": processed, "skipped": skipped}


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def semantic_search(user_id: int, query: str, top_k: int = 5) -> List[Dict]:
    """Semantic similarity search over user log embeddings.
    Returns list of dicts: [{'log_id':..., 'role':..., 'content':..., 'score':...}, ...]
    """
    db = get_db()
    query_emb = generate_embedding(query)
    if not query_emb:
        return []

    cur = db.execute(
        """
        SELECT e.log_id, e.embedding, l.role, l.content
        FROM llm_log_embeddings e JOIN llm_logs l ON l.id = e.log_id
        WHERE e.user_id = ?
        ORDER BY e.log_id DESC
        LIMIT 1000
        """,
        (user_id,),
    )
    rows = cur.fetchall()

    scored: List[Tuple[float, Dict]] = []
    for r in rows:
        try:
            emb = json.loads(r["embedding"])
        except Exception:
            continue
        score = _cosine(query_emb, emb)
        scored.append(
            (
                score,
                {
                    "log_id": r["log_id"],
                    "role": r["role"],
                    "content": r["content"],
                    "score": round(score, 4),
                },
            )
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for (_, item) in scored[:top_k]]


__all__ = [
    "generate_embedding",
    "ensure_log_embeddings",
    "semantic_search",
]
