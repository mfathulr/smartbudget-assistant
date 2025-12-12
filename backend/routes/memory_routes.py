from flask import Blueprint, request, jsonify, g

from core import get_logger
from auth import require_login
from database import get_db
from core import ensure_log_embeddings, semantic_search
from memory import (
    SUMMARY_THRESHOLD,
    MAX_LOG_CONTEXT,
    MAX_LOG_SOURCE,
    get_effective_config,
    get_memory_summary,
    get_recent_dialogue,
    maybe_update_summary,
)

logger = get_logger(__name__)

memory_bp = Blueprint("memory", __name__)


@memory_bp.route("/api/memory/summary", methods=["GET"])
@require_login
def memory_summary_api():
    user_id = g.user["id"]
    refresh = request.args.get("refresh") == "1"
    if refresh:
        summary = maybe_update_summary(user_id)
    else:
        summary = get_memory_summary(user_id) or maybe_update_summary(user_id)

    db = get_db()
    total_logs = (
        db.execute(
            "SELECT COUNT(*) AS c FROM llm_logs WHERE user_id = ?", (user_id,)
        ).fetchone()["c"]
        or 0
    )
    recent = get_recent_dialogue(user_id)
    cfg = get_effective_config(user_id)

    return jsonify(
        {
            "summary_text": summary["summary_text"] if summary else None,
            "interaction_count": summary["interaction_count"] if summary else 0,
            "updated_at": summary["updated_at"] if summary else None,
            "total_logs": total_logs,
            "recent_dialogue": recent,
            "config": cfg,
        }
    ), 200


@memory_bp.route("/api/memory/clear", methods=["DELETE"])
@require_login
def memory_clear_api():
    """Clear all chat history and LLM logs for the user to save memory."""
    user_id = g.user["id"]
    db = get_db()

    try:
        count_row = db.execute(
            "SELECT COUNT(*) AS c FROM llm_logs WHERE user_id = ?", (user_id,)
        ).fetchone()
        logs_count = count_row["c"] if count_row else 0

        db.execute("DELETE FROM llm_log_embeddings WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM llm_logs WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM llm_memory_summary WHERE user_id = ?", (user_id,))

        db.commit()

        return jsonify(
            {
                "status": "ok",
                "message": f"Berhasil menghapus {logs_count} riwayat chat dan memory",
                "deleted_logs": logs_count,
            }
        ), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Gagal menghapus riwayat: {str(e)}"}), 500


@memory_bp.route("/api/memory/logs/<int:log_id>", methods=["DELETE"])
@require_login
def memory_delete_log_api(log_id):
    """Delete a specific chat log entry by ID."""
    user_id = g.user["id"]
    db = get_db()

    try:
        cur = db.execute(
            "SELECT id FROM llm_logs WHERE id = ? AND user_id = ?", (log_id, user_id)
        )
        if not cur.fetchone():
            return jsonify({"error": "Log tidak ditemukan atau bukan milik Anda"}), 404

        db.execute("DELETE FROM llm_log_embeddings WHERE log_id = ?", (log_id,))
        db.execute(
            "DELETE FROM llm_logs WHERE id = ? AND user_id = ?", (log_id, user_id)
        )

        db.commit()

        return jsonify(
            {"status": "ok", "message": "Chat berhasil dihapus", "deleted_id": log_id}
        ), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Gagal menghapus chat: {str(e)}"}), 500


@memory_bp.route("/api/memory/logs", methods=["GET", "DELETE"])
@require_login
def memory_logs_api():
    """Get chat history or delete multiple logs by timeframe."""
    user_id = g.user["id"]
    db = get_db()

    if request.method == "GET":
        limit = min(int(request.args.get("limit") or 50), 100)
        offset = int(request.args.get("offset") or 0)
        since = request.args.get("since")
        until = request.args.get("until")

        where = ["user_id = ?"]
        params = [user_id]

        if since:
            where.append("created_at >= ?")
            params.append(since)
        if until:
            where.append("created_at <= ?")
            params.append(until)

        sql = f"""SELECT id, role, content, created_at, session_id 
                  FROM llm_logs 
                  WHERE {" AND ".join(where)} 
                  ORDER BY created_at DESC 
                  LIMIT ? OFFSET ?"""
        params.extend([limit, offset])

        cur = db.execute(sql, params)
        logs = [
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
                "session_id": r.get("session_id"),
            }
            for r in cur.fetchall()
        ]

        count_params = params[: len(where)]
        count_row = db.execute(
            f"SELECT COUNT(*) AS c FROM llm_logs WHERE {' AND '.join(where)}",
            count_params,
        ).fetchone()
        total_count = count_row["c"] if count_row else 0

        return jsonify(
            {"logs": logs, "total": total_count, "limit": limit, "offset": offset}
        ), 200

    data = request.get_json() or {}
    log_ids = data.get("ids")
    since = data.get("since")
    until = data.get("until")

    if log_ids:
        placeholders = ",".join(["?"] * len(log_ids))
        params = log_ids + [user_id]

        count_row = db.execute(
            f"SELECT COUNT(*) AS c FROM llm_logs WHERE id IN ({placeholders}) AND user_id = ?",
            params,
        ).fetchone()
        count = count_row["c"] if count_row else 0

        db.execute(
            f"DELETE FROM llm_log_embeddings WHERE log_id IN ({placeholders})",
            log_ids,
        )
        db.execute(
            f"DELETE FROM llm_logs WHERE id IN ({placeholders}) AND user_id = ?",
            params,
        )
    else:
        where = ["user_id = ?"]
        params = [user_id]

        if since:
            where.append("created_at >= ?")
            params.append(since)
        if until:
            where.append("created_at <= ?")
            params.append(until)

        count_row = db.execute(
            f"SELECT COUNT(*) AS c FROM llm_logs WHERE {' AND '.join(where)}",
            params,
        ).fetchone()
        count = count_row["c"] if count_row else 0

        db.execute(
            f"DELETE FROM llm_log_embeddings WHERE log_id IN (SELECT id FROM llm_logs WHERE {' AND '.join(where)})",
            params,
        )
        db.execute(
            f"DELETE FROM llm_logs WHERE {' AND '.join(where)}",
            params,
        )

    db.commit()

    return jsonify({"status": "ok", "deleted": count}), 200


@memory_bp.route("/api/sessions", methods=["GET", "POST"])
@require_login
def sessions_api():
    """Manage chat sessions."""
    user_id = g.user["id"]
    db = get_db()

    if request.method == "GET":
        cur = db.execute(
            """SELECT s.id, s.title, s.created_at, s.updated_at,
                      COUNT(l.id) as message_count,
                      MAX(l.created_at) as last_message_at
               FROM chat_sessions s
               LEFT JOIN llm_logs l ON s.id = l.session_id
               WHERE s.user_id = ?
               GROUP BY s.id
               ORDER BY s.updated_at DESC""",
            (user_id,),
        )
        sessions = [
            {
                "id": r["id"],
                "title": r["title"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "message_count": r["message_count"] or 0,
                "last_message_at": r["last_message_at"],
            }
            for r in cur.fetchall()
        ]
        return jsonify({"sessions": sessions}), 200

    data = request.get_json() or {}
    title = data.get("title") or "New Chat"

    db.execute(
        "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)",
        (user_id, title),
    )
    db.commit()

    cur = db.execute(
        "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )
    session = cur.fetchone()

    return jsonify(
        {
            "status": "ok",
            "message": "Session created",
            "session": {
                "id": session["id"],
                "title": session["title"],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
            },
        }
    ), 201


@memory_bp.route("/api/sessions/<int:session_id>", methods=["GET", "PUT", "DELETE"])
@require_login
def session_detail_api(session_id):
    """Get, update, or delete a specific session."""
    user_id = g.user["id"]
    db = get_db()

    cur = db.execute(
        "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    session = cur.fetchone()
    if not session:
        return jsonify({"error": "Session tidak ditemukan"}), 404

    if request.method == "GET":
        logs_cur = db.execute(
            "SELECT id, role, content, created_at FROM llm_logs WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        messages = [
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
            }
            for r in logs_cur.fetchall()
        ]

        return jsonify(
            {
                "session": {
                    "id": session["id"],
                    "title": session["title"],
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                    "messages": messages,
                }
            }
        ), 200

    if request.method == "PUT":
        data = request.get_json() or {}
        title = data.get("title")

        if not title or not title.strip():
            return jsonify({"error": "Title tidak boleh kosong"}), 400

        db.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (title, session_id, user_id),
        )
        db.commit()

        return jsonify(
            {"status": "ok", "message": "Session title updated", "title": title}
        ), 200

    try:
        logger.debug(
            "Delete session endpoint called",
            extra={"extra_data": {"session_id": session_id, "user_id": user_id}},
        )

        count_row = db.execute(
            "SELECT COUNT(*) AS c FROM llm_logs WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        logs_count = count_row["c"] if count_row else 0
        logger.debug(
            "Logs to delete",
            extra={"extra_data": {"session_id": session_id, "count": logs_count}},
        )

        emb_row = db.execute(
            """SELECT COUNT(*) AS c FROM llm_log_embeddings 
                   WHERE log_id IN (SELECT id FROM llm_logs WHERE session_id = ?)""",
            (session_id,),
        ).fetchone()
        emb_count = emb_row["c"] if emb_row else 0
        logger.debug(
            "Embeddings to delete",
            extra={"extra_data": {"session_id": session_id, "count": emb_count}},
        )

        logger.debug("Executing DELETE FROM chat_sessions")
        cursor = db.execute(
            "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        )
        affected = cursor.rowcount if hasattr(cursor, "rowcount") else "unknown"
        logger.debug(
            "Delete rows affected",
            extra={"extra_data": {"session_id": session_id, "affected": affected}},
        )

        db.commit()
        logger.debug("Delete session commit successful")

        verify = db.execute(
            "SELECT COUNT(*) AS c FROM llm_logs WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        remaining = verify["c"] if verify else 0
        logger.debug(
            "Logs remaining after delete",
            extra={"extra_data": {"session_id": session_id, "remaining": remaining}},
        )

        return jsonify(
            {
                "status": "ok",
                "message": "Session berhasil dihapus",
                "deleted_logs": logs_count,
                "deleted_embeddings": emb_count,
            }
        ), 200

    except Exception as e:
        logger.error(
            "Failed to delete session",
            extra={"extra_data": {"session_id": session_id, "error": str(e)}},
        )
        db.rollback()
        return jsonify({"error": f"Gagal menghapus session: {str(e)}"}), 500


@memory_bp.route("/api/sessions/sync", methods=["GET"])
@require_login
def sync_sessions_api():
    """Auto-cleanup and sync sessions with database.
    Removes empty sessions and orphaned logs.
    """
    user_id = g.user["id"]
    db = get_db()

    deleted_sessions = []
    orphaned_logs = 0

    empty_cur = db.execute(
        """
        SELECT cs.id, cs.title
        FROM chat_sessions cs
        LEFT JOIN llm_logs l ON cs.id = l.session_id
        WHERE cs.user_id = ? AND l.id IS NULL
    """,
        (user_id,),
    )
    empty_sessions = empty_cur.fetchall()

    for session in empty_sessions:
        db.execute("DELETE FROM chat_sessions WHERE id = ?", (session["id"],))
        deleted_sessions.append(
            {"id": session["id"], "title": session["title"], "reason": "empty"}
        )

    orphan_cur = db.execute(
        "SELECT COUNT(*) AS c FROM llm_logs WHERE user_id = ? AND session_id IS NULL",
        (user_id,),
    )
    orphaned_logs = orphan_cur.fetchone()["c"]

    if orphaned_logs > 0:
        old_session_cur = db.execute(
            "SELECT id FROM chat_sessions WHERE user_id = ? AND title = ?",
            (user_id, "Old Messages"),
        )
        old_session = old_session_cur.fetchone()

        if old_session:
            old_session_id = old_session["id"]
        else:
            db.execute(
                """
                INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
                (user_id, "Old Messages"),
            )
            old_session_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        db.execute(
            "UPDATE llm_logs SET session_id = ? WHERE user_id = ? AND session_id IS NULL",
            (old_session_id, user_id),
        )

    db.commit()

    return jsonify(
        {
            "status": "ok",
            "deleted_sessions": deleted_sessions,
            "orphaned_logs_migrated": orphaned_logs,
        }
    ), 200


@memory_bp.route("/api/sessions/ids", methods=["GET"])
@require_login
def list_session_ids_api():
    """Get list of valid session IDs for current user.
    Used by frontend to verify which sessions exist in DB.
    """
    user_id = g.user["id"]
    db = get_db()

    cur = db.execute(
        "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    )
    sessions = cur.fetchall()

    return jsonify(
        {
            "session_ids": [s["id"] for s in sessions],
            "sessions": [
                {
                    "id": s["id"],
                    "title": s["title"],
                    "created_at": s["created_at"],
                    "updated_at": s["updated_at"],
                }
                for s in sessions
            ],
        }
    ), 200


@memory_bp.route("/api/memory/search", methods=["GET"])
@require_login
def memory_search_api():
    user_id = g.user["id"]
    query = (request.args.get("q") or "").strip()
    top_k = int(request.args.get("top_k") or 5)
    if not query:
        return jsonify({"error": "q parameter kosong"}), 400

    stats = ensure_log_embeddings(user_id, batch_size=200)
    results = semantic_search(user_id, query, top_k=top_k)
    return jsonify({"results": results, "embedding_update": stats}), 200


@memory_bp.route("/api/memory/config", methods=["GET", "PUT"])
@require_login
def memory_config_api():
    user_id = g.user["id"]
    db = get_db()
    if request.method == "GET":
        cfg = get_effective_config(user_id)
        cur = db.execute(
            "SELECT embedding_provider FROM llm_memory_config WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        embedding_provider = row["embedding_provider"] if row else "openai"
        cfg["embedding_provider"] = embedding_provider
        return jsonify(cfg), 200

    data = request.get_json() or {}
    summary_threshold = data.get("summary_threshold")
    max_log_context = data.get("max_log_context")
    max_source = data.get("max_source")
    embedding_provider = data.get("embedding_provider")

    def _pos_int(val, name):
        if val is None:
            return None
        try:
            iv = int(val)
            if iv <= 0:
                raise ValueError
            return iv
        except Exception:
            raise ValueError(f"{name} harus integer > 0")

    try:
        st = _pos_int(summary_threshold, "summary_threshold")
        mc = _pos_int(max_log_context, "max_log_context")
        ms = _pos_int(max_source, "max_source")
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    if embedding_provider and embedding_provider not in ("openai", "local"):
        return jsonify({"error": "embedding_provider harus 'openai' atau 'local'"}), 400

    cur = db.execute(
        "SELECT user_id FROM llm_memory_config WHERE user_id = ?", (user_id,)
    )
    exists = cur.fetchone() is not None
    if exists:
        updates = []
        params = []
        if st is not None:
            updates.append("summary_threshold = ?")
            params.append(st)
        if mc is not None:
            updates.append("max_log_context = ?")
            params.append(mc)
        if ms is not None:
            updates.append("max_source = ?")
            params.append(ms)
        if embedding_provider:
            updates.append("embedding_provider = ?")
            params.append(embedding_provider)
        if not updates:
            return jsonify({"status": "ok", "message": "Tidak ada perubahan"}), 200
        params.append(user_id)
        sql = (
            "UPDATE llm_memory_config SET "
            + ", ".join(updates)
            + ", updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
        )
        db.execute(sql, params)
    else:
        db.execute(
            "INSERT INTO llm_memory_config (user_id, summary_threshold, max_log_context, max_source, embedding_provider) VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                st or SUMMARY_THRESHOLD,
                mc or MAX_LOG_CONTEXT,
                ms or MAX_LOG_SOURCE,
                embedding_provider or "openai",
            ),
        )
    db.commit()
    new_cfg = get_effective_config(user_id)
    cur = db.execute(
        "SELECT embedding_provider FROM llm_memory_config WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    new_cfg["embedding_provider"] = row["embedding_provider"] if row else "openai"
    return jsonify({"status": "ok", "config": new_cfg}), 200
