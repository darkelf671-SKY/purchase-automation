from db.database import get_connection
from core.models import InspectionData


def insert(data: InspectionData, purchase_id: int) -> int:
    sql = """
        INSERT INTO inspections (
            purchase_id, inspection_date, inspector, witness, inspected_qty,
            has_defect, defect_note, remark
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    with get_connection() as conn:
        cur = conn.execute(sql, (
            purchase_id,
            data.inspection_date,
            data.inspector,
            data.witness,
            data.inspected_qty,
            int(data.has_defect),
            data.defect_note,
            data.remark,
        ))
        return cur.lastrowid


def update_docs(inspection_id: int, doc_list: str = "", doc_rpt: str = ""):
    with get_connection() as conn:
        conn.execute(
            "UPDATE inspections SET doc_inspection_list=?, doc_inspection_rpt=? WHERE id=?",
            (doc_list, doc_rpt, inspection_id)
        )


def select_by_purchase(purchase_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM inspections WHERE purchase_id=? ORDER BY id DESC LIMIT 1",
            (purchase_id,)
        ).fetchone()
        return dict(row) if row else None


def select_all() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM inspections ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def select_all_grouped() -> list[dict]:
    """purchase_id별 최신 검수 1건씩 반환 (이력 조회 N+1 방지용)"""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM inspections
            WHERE id IN (
                SELECT MAX(id) FROM inspections GROUP BY purchase_id
            )
        """).fetchall()
        return [dict(r) for r in rows]


def delete(inspection_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM inspections WHERE id=?", (inspection_id,))


def delete_by_purchase(purchase_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM inspections WHERE purchase_id=?", (purchase_id,))
