from db.database import get_connection


def insert(reason: str, label: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO sole_contract_reasons (reason, label) VALUES (?, ?)",
            (reason.strip(), label.strip())
        )
        return cur.lastrowid


def select_all() -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sole_contract_reasons ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


def update(record_id: int, reason: str, label: str = ""):
    with get_connection() as conn:
        conn.execute(
            "UPDATE sole_contract_reasons SET reason=?, label=? WHERE id=?",
            (reason.strip(), label.strip(), record_id)
        )


def delete(record_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM sole_contract_reasons WHERE id=?", (record_id,))
