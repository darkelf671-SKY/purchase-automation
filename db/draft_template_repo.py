"""기안 템플릿 CRUD"""
from db.database import get_connection


def insert(label: str, title: str, content: str, remark: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO draft_templates (label, title, content, remark) "
            "VALUES (?, ?, ?, ?)",
            (label, title, content, remark)
        )
        return cur.lastrowid


def update(record_id: int, label: str, title: str, content: str, remark: str = ""):
    with get_connection() as conn:
        conn.execute(
            "UPDATE draft_templates SET label=?, title=?, content=?, remark=? WHERE id=?",
            (label, title, content, remark, record_id)
        )


def select_all() -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM draft_templates ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def select_by_label(label: str) -> dict | None:
    """별칭으로 템플릿 조회 (중복 검사용)"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM draft_templates WHERE label = ?", (label,)
        ).fetchone()
        return dict(row) if row else None


def delete(record_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM draft_templates WHERE id=?", (record_id,))
