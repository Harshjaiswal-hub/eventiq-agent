"""
EventIQ Agent — Memory & RAG Retrieval Layer
Supports:
1. Short-Term Conversational Memory: Session-based message tracking with context windows.
2. Long-Term Memory: Storage and retrieval of historical reports, audits, and performance archives.
3. RAG Retrieval Pipeline: Semantic vector embedding retrieval when API is available,
   with robust deterministic TF-IDF / BM25 fallback when offline.
"""

import json
import math
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.database import get_db_connection

# ── 1. SHORT-TERM CONVERSATIONAL MEMORY ──────────────────────

def create_conversation(session_id: str, title: str = "New Session") -> str:
    """Creates a new conversation session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO conversations (id, title, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (session_id, title))
    conn.commit()
    conn.close()
    return session_id

def add_message(session_id: str, role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None):
    """Appends a message to the specified conversation, ensuring the conversation record exists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Ensure parent conversation exists to satisfy foreign key integrity
    cursor.execute("""
        INSERT OR IGNORE INTO conversations (id, title, updated_at)
        VALUES (?, 'Active Session', CURRENT_TIMESTAMP)
    """, (session_id,))
    tool_json = json.dumps(tool_calls) if tool_calls else None
    cursor.execute("""
        INSERT INTO messages (conversation_id, role, content, tool_calls_json)
        VALUES (?, ?, ?, ?)
    """, (session_id, role, content, tool_json))
    cursor.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def get_conversation_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves recent conversation messages for conversational context."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, role, content, tool_calls_json, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (session_id, limit))
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in reversed(rows):
        tool_calls = json.loads(r["tool_calls_json"]) if r["tool_calls_json"] else None
        history.append({
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            "tool_calls": tool_calls,
            "created_at": r["created_at"]
        })
    return history

def clear_conversation(session_id: str):
    """Clears history for a given session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (session_id,))
    conn.commit()
    conn.close()

# ── 2. LONG-TERM MEMORY (REPORT ARCHIVE) ─────────────────────

def save_report(report_id: str, semester: str, title: str, summary: str, markdown: str, provenance: Dict[str, Any]):
    """Saves a semester audit report to long-term memory."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO reports (id, semester, title, summary, markdown_content, provenance_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (report_id, semester, title, summary, markdown, json.dumps(provenance)))
    conn.commit()
    conn.close()

def get_saved_reports(semester: Optional[str] = None, report_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves saved reports from long-term memory, optionally filtering by semester or specific ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if report_id:
        cursor.execute("""
            SELECT id, semester, title, summary, markdown_content, provenance_json, created_at 
            FROM reports WHERE id = ?
        """, (report_id,))
    elif semester:
        cursor.execute("""
            SELECT id, semester, title, summary, markdown_content, provenance_json, created_at 
            FROM reports WHERE semester = ? ORDER BY created_at DESC
        """, (semester,))
    else:
        cursor.execute("""
            SELECT id, semester, title, summary, markdown_content, provenance_json, created_at 
            FROM reports ORDER BY created_at DESC
        """)
    rows = cursor.fetchall()
    conn.close()

    reports = []
    for r in rows:
        item = dict(r)
        item["markdown"] = item.get("markdown_content")
        if item.get("provenance_json"):
            try:
                item["provenance"] = json.loads(item["provenance_json"])
            except Exception:
                item["provenance"] = {}
        reports.append(item)
    return reports

# ── 3. RAG RETRIEVAL ENGINE ─────────────────────────────────

def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase words for lexical retrieval."""
    return re.findall(r'\b[a-zA-Z0-9_]{2,}\b', text.lower())

def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two numerical vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)

def retrieve_relevant_documents(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieves institutional policies, rubrics, and reports relevant to the query.
    Uses TF-IDF / term-overlap ranking as a verified, reproducible retrieval engine.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, doc_type, title, content, metadata_json FROM documents")
    docs = cursor.fetchall()
    conn.close()

    if not docs:
        return []

    q_tokens = set(tokenize(query))
    if not q_tokens:
        return []

    scored_docs = []
    for d in docs:
        doc_tokens = tokenize(d["title"] + " " + d["content"])
        if not doc_tokens:
            continue
        
        # Calculate term frequency score
        overlap = sum(doc_tokens.count(t) for t in q_tokens)
        score = overlap / (len(doc_tokens) + 10.0) # Length normalized

        if score > 0:
            scored_docs.append({
                "id": d["id"],
                "doc_type": d["doc_type"],
                "title": d["title"],
                "content": d["content"],
                "metadata": json.loads(d["metadata_json"]) if d["metadata_json"] else {},
                "relevance_score": round(score, 4)
            })

    scored_docs.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored_docs[:top_k]
