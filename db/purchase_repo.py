from db.database import get_connection
from core.models import PurchaseData, PurchaseItem


def insert(data: PurchaseData) -> int:
    """purchases + purchase_items 동시 INSERT"""
    sql = """
        INSERT INTO purchases (
            purpose, item_name, spec, unit, quantity, department,
            vendor1_name, vendor1_price, vendor1_total, vendor1_url, vendor1_screenshot,
            vendor2_name, vendor2_price, vendor2_total, vendor2_url, vendor2_screenshot,
            selected_vendor, item_count, vat_mode, draft_date,
            payment_method, payment_bank, payment_account, payment_holder
        ) VALUES (
            :purpose, :item_name, :spec, :unit, :quantity, :department,
            :v1n, :v1p, :v1t, :v1u, :v1s,
            :v2n, :v2p, :v2t, :v2u, :v2s,
            :sel, :cnt, :vat_mode, :draft_date,
            :pay_method, :pay_bank, :pay_account, :pay_holder
        )
    """
    params = {
        "purpose":    "",
        "item_name":  data.item_name,
        "spec":       data.spec,
        "unit":       data.unit,
        "quantity":   data.quantity,
        "department": data.department,
        "v1n": data.vendor1.name,
        "v1p": data.vendor1.unit_price,
        "v1t": data.vendor1.total_price,
        "v1u": data.vendor1.url,
        "v1s": data.vendor1.screenshot_path,
        "v2n": data.vendor2.name,
        "v2p": data.vendor2.unit_price,
        "v2t": data.vendor2.total_price,
        "v2u": data.vendor2.url,
        "v2s": data.vendor2.screenshot_path,
        "sel":      data.selected_vendor,
        "cnt":      len(data.items),
        "vat_mode": getattr(data, "vat_mode", "none"),
        "draft_date": getattr(data, "draft_date", ""),
        "pay_method":  getattr(data, "payment_method", ""),
        "pay_bank":    getattr(data, "payment_bank", ""),
        "pay_account": getattr(data, "payment_account", ""),
        "pay_holder":  getattr(data, "payment_holder", ""),
    }
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        purchase_id = cur.lastrowid
        _insert_items(conn, purchase_id, data.items)
        return purchase_id


def _insert_items(conn, purchase_id: int, items: list):
    for item in items:
        conn.execute(
            "INSERT INTO purchase_items "
            "(purchase_id, seq, item_name, spec, unit, quantity, "
            "unit_price, total_price, v2_unit_price, remark, price_input_mode) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (purchase_id, item.seq, item.item_name, item.spec or "",
             item.unit, item.quantity, item.unit_price, item.total_price,
             item.v2_unit_price, item.remark or "",
             getattr(item, 'price_input_mode', 'unit'))
        )


def update(purchase_id: int, data: PurchaseData):
    """기존 구매건 UPDATE"""
    sql = """
        UPDATE purchases SET
            item_name=:item_name, spec=:spec, unit=:unit, quantity=:quantity,
            department=:department,
            vendor1_name=:v1n, vendor1_price=:v1p, vendor1_total=:v1t,
            vendor1_url=:v1u, vendor1_screenshot=:v1s,
            vendor2_name=:v2n, vendor2_price=:v2p, vendor2_total=:v2t,
            vendor2_url=:v2u, vendor2_screenshot=:v2s,
            selected_vendor=:sel, item_count=:cnt, vat_mode=:vat_mode,
            draft_date=:draft_date,
            payment_method=:pay_method, payment_bank=:pay_bank,
            payment_account=:pay_account, payment_holder=:pay_holder
        WHERE id=:id
    """
    params = {
        "id":         purchase_id,
        "item_name":  data.item_name,
        "spec":       data.spec,
        "unit":       data.unit,
        "quantity":   data.quantity,
        "department": data.department,
        "v1n": data.vendor1.name,
        "v1p": data.vendor1.unit_price,
        "v1t": data.vendor1.total_price,
        "v1u": data.vendor1.url,
        "v1s": data.vendor1.screenshot_path,
        "v2n": data.vendor2.name,
        "v2p": data.vendor2.unit_price,
        "v2t": data.vendor2.total_price,
        "v2u": data.vendor2.url,
        "v2s": data.vendor2.screenshot_path,
        "sel":      data.selected_vendor,
        "cnt":      len(data.items),
        "vat_mode": getattr(data, "vat_mode", "none"),
        "draft_date": getattr(data, "draft_date", ""),
        "pay_method":  getattr(data, "payment_method", ""),
        "pay_bank":    getattr(data, "payment_bank", ""),
        "pay_account": getattr(data, "payment_account", ""),
        "pay_holder":  getattr(data, "payment_holder", ""),
    }
    with get_connection() as conn:
        conn.execute(sql, params)


def update_items(purchase_id: int, items: list):
    """기존 품목 삭제 후 재삽입"""
    with get_connection() as conn:
        conn.execute("DELETE FROM purchase_items WHERE purchase_id=?", (purchase_id,))
        _insert_items(conn, purchase_id, items)


def select_items(purchase_id: int) -> list:
    """해당 구매건의 품목 목록 (seq 정렬)"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM purchase_items WHERE purchase_id=? ORDER BY seq",
            (purchase_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def items_to_purchase_items(rows: list) -> list:
    """DB 행 → PurchaseItem 리스트 변환"""
    return [
        PurchaseItem(
            seq=r["seq"],
            item_name=r["item_name"],
            spec=r["spec"] or "",
            unit=r["unit"],
            quantity=r["quantity"],
            unit_price=r["unit_price"],
            total_price=r["total_price"],
            v2_unit_price=r.get("v2_unit_price", 0),
            remark=r.get("remark", ""),
            price_input_mode=r.get("price_input_mode", "unit"),
        )
        for r in rows
    ]


def update_docs(purchase_id: int, doc_draft: str = "", doc_calculation: str = ""):
    with get_connection() as conn:
        if doc_draft and doc_calculation:
            conn.execute(
                "UPDATE purchases SET doc_draft=?, doc_calculation=? WHERE id=?",
                (doc_draft, doc_calculation, purchase_id)
            )
        elif doc_draft:
            conn.execute(
                "UPDATE purchases SET doc_draft=? WHERE id=?",
                (doc_draft, purchase_id)
            )
        elif doc_calculation:
            conn.execute(
                "UPDATE purchases SET doc_calculation=? WHERE id=?",
                (doc_calculation, purchase_id)
            )


def update_folder(purchase_id: int, folder: str):
    with get_connection() as conn:
        conn.execute("UPDATE purchases SET doc_folder=? WHERE id=?", (folder, purchase_id))


def update_draft_meta(purchase_id: int, title: str, content: str, remark: str = ""):
    with get_connection() as conn:
        conn.execute(
            "UPDATE purchases SET doc_draft_title=?, doc_draft_content=?, doc_draft_remark=? WHERE id=?",
            (title, content, remark, purchase_id)
        )


def select_all() -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM purchases ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def select_by_id(purchase_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM purchases WHERE id=?", (purchase_id,)
        ).fetchone()
        return dict(row) if row else None


def delete(purchase_id: int):
    with get_connection() as conn:
        # purchase_items는 ON DELETE CASCADE로 자동 삭제
        conn.execute("DELETE FROM purchases WHERE id=?", (purchase_id,))
