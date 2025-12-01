"""Long-term memory utilities for LLM interactions"""

from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from openai import OpenAI
from database import get_db

# Default constants (can be overridden per user via llm_memory_config)
SUMMARY_THRESHOLD = 12  # regenerate summary after this many new interactions
MAX_LOG_CONTEXT = 8  # number of recent messages to include in live context
MAX_LOG_SOURCE = 200  # number of logs to pull when regenerating summary


def get_effective_config(user_id: int) -> Dict[str, int]:
    """Fetch per-user memory config overrides or return defaults."""
    db = get_db()
    cur = db.execute(
        "SELECT summary_threshold, max_log_context, max_source FROM llm_memory_config WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        return {
            "summary_threshold": SUMMARY_THRESHOLD,
            "max_log_context": MAX_LOG_CONTEXT,
            "max_source": MAX_LOG_SOURCE,
        }
    return {
        "summary_threshold": row["summary_threshold"] or SUMMARY_THRESHOLD,
        "max_log_context": row["max_log_context"] or MAX_LOG_CONTEXT,
        "max_source": row["max_source"] or MAX_LOG_SOURCE,
    }


client = OpenAI()


def log_message(
    user_id: int,
    role: str,
    content: str,
    meta: Optional[dict] = None,
    session_id: Optional[int] = None,
) -> None:
    """Persist a single message into llm_logs"""
    db = get_db()
    db.execute(
        "INSERT INTO llm_logs (user_id, session_id, role, content, meta_json) VALUES (?, ?, ?, ?, ?)",
        (user_id, session_id, role, content, json.dumps(meta) if meta else None),
    )
    db.commit()


def get_recent_dialogue(
    user_id: int, limit: Optional[int] = None, session_id: Optional[int] = None
) -> List[Dict]:
    db = get_db()
    if limit is None:
        cfg = get_effective_config(user_id)
        limit = cfg["max_log_context"]

    where = "user_id = ?"
    params = [user_id]
    if session_id is not None:
        where += " AND session_id = ?"
        params.append(session_id)

    cur = db.execute(
        f"SELECT role, content, created_at FROM llm_logs WHERE {where} ORDER BY id DESC LIMIT ?",
        params + [limit],
    )
    rows = cur.fetchall()
    # reverse to chronological
    return [
        {"role": r["role"], "content": r["content"], "created_at": r["created_at"]}
        for r in reversed(rows)
    ]


def get_memory_summary(user_id: int) -> Optional[Dict]:
    db = get_db()
    cur = db.execute(
        "SELECT summary_text, interaction_count, updated_at FROM llm_memory_summary WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "summary_text": row["summary_text"],
        "interaction_count": row["interaction_count"],
        "updated_at": row["updated_at"],
    }


def maybe_update_summary(user_id: int) -> Optional[Dict]:
    """Regenerate summary if accumulated new interactions exceeds threshold (per-user configurable)."""
    db = get_db()
    cfg = get_effective_config(user_id)
    current = get_memory_summary(user_id)

    cur = db.execute("SELECT COUNT(*) AS c FROM llm_logs WHERE user_id = ?", (user_id,))
    total_logs = cur.fetchone()["c"] or 0

    last_count = current["interaction_count"] if current else 0
    if current and total_logs - last_count < cfg["summary_threshold"]:
        return current

    cur = db.execute(
        "SELECT role, content FROM llm_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, cfg["max_source"]),
    )
    rows = cur.fetchall()
    # Build plain text conversation
    convo_lines = []
    for r in reversed(rows):  # chronological
        tag = "U:" if r["role"] == "user" else "A:"
        # truncate very long lines
        content = r["content"]
        if len(content) > 500:
            content = content[:500] + "..."
        convo_lines.append(f"{tag} {content}")
    convo_text = "\n".join(convo_lines)

    # Summarization prompt (Indonesian focus)
    system_prompt = (
        "Ringkas preferensi user, pola pemasukan/pengeluaran, akun yang sering dipakai, kategori dominan, tujuan tabungan. "
        "Jangan sebut hal yang tidak ada. Format poin singkat maksimum 10 baris."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": convo_text},
            ],
            temperature=0.2,
        )
        summary_text = resp.choices[0].message.content.strip()
    except Exception as e:
        summary_text = f"(Gagal membuat ringkasan otomatis: {e})"

    # Upsert summary
    if current:
        db.execute(
            "UPDATE llm_memory_summary SET summary_text = ?, interaction_count = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (summary_text, total_logs, user_id),
        )
    else:
        db.execute(
            "INSERT INTO llm_memory_summary (user_id, summary_text, interaction_count) VALUES (?, ?, ?)",
            (user_id, summary_text, total_logs),
        )
    db.commit()

    wib = timezone(timedelta(hours=7))
    return {
        "summary_text": summary_text,
        "interaction_count": total_logs,
        "updated_at": datetime.now(wib).isoformat(),
    }


def build_memory_context(user_id: int) -> str:
    """Compose memory context string combining summary + recent dialogue (respect config)."""
    summary = get_memory_summary(user_id)
    recent = get_recent_dialogue(user_id)

    parts = []
    if summary and summary.get("summary_text"):
        parts.append("RINGKASAN MEMORI:")
        parts.append(summary["summary_text"])
        parts.append("")
    parts.append("DIALOG TERAKHIR:")
    for msg in recent:
        prefix = "User" if msg["role"] == "user" else "FIN"
        content = msg["content"]
        if len(content) > 200:
            content = content[:200] + "..."
        parts.append(f"- {prefix}: {content}")
    return "\n".join(parts)


__all__ = [
    "log_message",
    "get_recent_dialogue",
    "get_memory_summary",
    "maybe_update_summary",
    "build_memory_context",
    "get_effective_config",
]
