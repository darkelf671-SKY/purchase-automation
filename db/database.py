import sqlite3
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS purchase_items (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_id     INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
                seq             INTEGER NOT NULL,
                item_name       TEXT NOT NULL,
                spec            TEXT DEFAULT '',
                unit            TEXT DEFAULT '개',
                quantity        INTEGER NOT NULL DEFAULT 1,
                unit_price      INTEGER NOT NULL DEFAULT 0,
                total_price     INTEGER NOT NULL DEFAULT 0,
                v2_unit_price   INTEGER NOT NULL DEFAULT 0,
                remark          TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS vendors (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL UNIQUE,
                ceo             TEXT DEFAULT '',
                business_no     TEXT DEFAULT '',
                address         TEXT DEFAULT '',
                payment_method  TEXT DEFAULT 'card',
                bank_name       TEXT DEFAULT '',
                account_holder  TEXT DEFAULT '',
                account_no      TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS purchases (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                purpose             TEXT NOT NULL,
                item_name           TEXT NOT NULL,
                spec                TEXT DEFAULT '',
                unit                TEXT DEFAULT '개',
                quantity            INTEGER NOT NULL,
                department          TEXT DEFAULT '',

                vendor1_name        TEXT NOT NULL,
                vendor1_price       INTEGER NOT NULL,
                vendor1_total       INTEGER NOT NULL,
                vendor1_url         TEXT DEFAULT '',
                vendor1_screenshot  TEXT DEFAULT '',

                vendor2_name        TEXT NOT NULL,
                vendor2_price       INTEGER NOT NULL,
                vendor2_total       INTEGER NOT NULL,
                vendor2_url         TEXT DEFAULT '',
                vendor2_screenshot  TEXT DEFAULT '',

                selected_vendor     INTEGER NOT NULL DEFAULT 1,
                vendor1_id          INTEGER REFERENCES vendors(id),
                vendor2_id          INTEGER REFERENCES vendors(id),

                doc_draft           TEXT DEFAULT '',
                doc_calculation     TEXT DEFAULT '',
                doc_draft_title     TEXT DEFAULT '',
                doc_draft_content   TEXT DEFAULT '',

                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                status      TEXT NOT NULL DEFAULT 'draft'
            );

            CREATE TABLE IF NOT EXISTS inspections (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_id         INTEGER NOT NULL REFERENCES purchases(id),

                inspection_date     TEXT NOT NULL,
                inspector           TEXT NOT NULL,
                witness             TEXT DEFAULT '',
                inspected_qty       INTEGER NOT NULL,
                has_defect          INTEGER NOT NULL DEFAULT 0,
                defect_note         TEXT DEFAULT '',
                remark              TEXT DEFAULT '',

                doc_inspection_list TEXT DEFAULT '',
                doc_inspection_rpt  TEXT DEFAULT '',

                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS sole_contract_reasons (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                label      TEXT NOT NULL DEFAULT '',
                reason     TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS draft_templates (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                label      TEXT NOT NULL,
                title      TEXT NOT NULL DEFAULT '',
                content    TEXT NOT NULL DEFAULT '',
                remark     TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
        """)
        # sole_contract_reasons: note → label 마이그레이션
        try:
            conn.execute("ALTER TABLE sole_contract_reasons RENAME COLUMN note TO label")
        except Exception:
            pass  # 이미 변경되었거나 신규 DB
        _migrate(conn)


def _migrate(conn):
    """기존 DB에 신규 컬럼 안전하게 추가"""
    p_cols = {r[1] for r in conn.execute("PRAGMA table_info(purchases)").fetchall()}
    i_cols = {r[1] for r in conn.execute("PRAGMA table_info(inspections)").fetchall()}

    pi_cols = {r[1] for r in conn.execute("PRAGMA table_info(purchase_items)").fetchall()}
    for col, sql in [
        ("v2_unit_price", "ALTER TABLE purchase_items ADD COLUMN v2_unit_price INTEGER NOT NULL DEFAULT 0"),
        ("price_input_mode", "ALTER TABLE purchase_items ADD COLUMN price_input_mode TEXT DEFAULT 'unit'"),
    ]:
        if col not in pi_cols:
            conn.execute(sql)

    for col, sql in [
        ("vendor1_id",        "ALTER TABLE purchases ADD COLUMN vendor1_id INTEGER"),
        ("vendor2_id",        "ALTER TABLE purchases ADD COLUMN vendor2_id INTEGER"),
        ("doc_draft_title",   "ALTER TABLE purchases ADD COLUMN doc_draft_title TEXT DEFAULT ''"),
        ("doc_draft_content", "ALTER TABLE purchases ADD COLUMN doc_draft_content TEXT DEFAULT ''"),
        ("doc_folder",        "ALTER TABLE purchases ADD COLUMN doc_folder TEXT DEFAULT ''"),
        ("department",        "ALTER TABLE purchases ADD COLUMN department TEXT DEFAULT ''"),
        ("item_count",        "ALTER TABLE purchases ADD COLUMN item_count INTEGER DEFAULT 1"),
        ("vat_mode",          "ALTER TABLE purchases ADD COLUMN vat_mode TEXT DEFAULT 'none'"),
        ("draft_date",        "ALTER TABLE purchases ADD COLUMN draft_date TEXT DEFAULT ''"),
        ("doc_draft_remark",  "ALTER TABLE purchases ADD COLUMN doc_draft_remark TEXT DEFAULT ''"),
        ("payment_method",   "ALTER TABLE purchases ADD COLUMN payment_method TEXT DEFAULT ''"),
        ("payment_bank",     "ALTER TABLE purchases ADD COLUMN payment_bank TEXT DEFAULT ''"),
        ("payment_account",  "ALTER TABLE purchases ADD COLUMN payment_account TEXT DEFAULT ''"),
        ("payment_holder",   "ALTER TABLE purchases ADD COLUMN payment_holder TEXT DEFAULT ''"),
    ]:
        if col not in p_cols:
            conn.execute(sql)

    for col, sql in [
        ("witness", "ALTER TABLE inspections ADD COLUMN witness TEXT DEFAULT ''"),
    ]:
        if col not in i_cols:
            conn.execute(sql)

    # vendors 테이블 마이그레이션: is_auto_transfer 플래그
    v_cols = {r[1] for r in conn.execute("PRAGMA table_info(vendors)").fetchall()}
    if "is_auto_transfer" not in v_cols:
        conn.execute(
            "ALTER TABLE vendors ADD COLUMN is_auto_transfer INTEGER DEFAULT 0"
        )
        # 기존 auto_transfer 업체 → is_auto_transfer=1 플래그 이관
        conn.execute(
            "UPDATE vendors SET is_auto_transfer = 1 "
            "WHERE payment_method = 'auto_transfer'"
        )
        # transfer인데 은행정보 없는 레코드 보정
        conn.execute("""
            UPDATE vendors SET payment_method = 'card'
            WHERE payment_method = 'transfer'
              AND (bank_name IS NULL OR bank_name = '')
              AND (account_no IS NULL OR account_no = '')
        """)

    _migrate_existing_to_items(conn)


def _migrate_existing_to_items(conn):
    """기존 단일 품목 데이터 → purchase_items 테이블 마이그레이션 (최초 1회)"""
    already = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT purchase_id FROM purchase_items"
        ).fetchall()
    }
    rows = conn.execute(
        "SELECT id, item_name, spec, unit, quantity, "
        "vendor1_price, vendor2_price, selected_vendor FROM purchases"
    ).fetchall()
    for r in rows:
        if r["id"] in already:
            continue
        sel = r["selected_vendor"] if r["selected_vendor"] in (1, 2) else 1
        price = r[f"vendor{sel}_price"] or 0
        qty = r["quantity"] or 1
        conn.execute(
            "INSERT INTO purchase_items "
            "(purchase_id, seq, item_name, spec, unit, quantity, unit_price, total_price) "
            "VALUES (?, 1, ?, ?, ?, ?, ?, ?)",
            (r["id"], r["item_name"] or "", r["spec"] or "",
             r["unit"] or "개", qty, price, price * qty)
        )
        conn.execute(
            "UPDATE purchases SET item_count=1 WHERE id=? AND (item_count IS NULL OR item_count=0)",
            (r["id"],)
        )


if __name__ == "__main__":
    initialize()
    print("DB 초기화 완료:", DB_PATH)
