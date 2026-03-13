from db.database import get_connection


def derive_payment_method(
    bank_name: str = "",
    account_no: str = "",
    is_auto_transfer: bool = False,
) -> str:
    """은행 정보로 업체 기본 결제방법 자동 감지.

    용도: 업체 등록/수정 시 기본 결제방법(capability) 계산.
    구매 건별 결제방법(decision)은 구매 조사 탭에서 사용자가 선택.

    우선순위:
    1. is_auto_transfer=True → "auto_transfer"
    2. bank_name AND account_no 모두 유효 → "transfer"
    3. 그 외 → "card"
    """
    if is_auto_transfer:
        return "auto_transfer"
    if bank_name.strip() and account_no.strip():
        return "transfer"
    return "card"


def validate_bank_info(bank_name: str, account_no: str) -> str | None:
    """불완전 은행 정보 경고 메시지 반환. 정상이면 None."""
    has_bank = bool(bank_name.strip())
    has_acct = bool(account_no.strip())
    if has_bank and not has_acct:
        return "은행명은 있지만 계좌번호가 없습니다.\n무통장입금으로 인식되지 않습니다."
    if not has_bank and has_acct:
        return "계좌번호는 있지만 은행명이 없습니다.\n무통장입금으로 인식되지 않습니다."
    return None


def insert(data: dict) -> int:
    data.setdefault("is_auto_transfer", 0)
    data["payment_method"] = derive_payment_method(
        data.get("bank_name", ""),
        data.get("account_no", ""),
        bool(data.get("is_auto_transfer", 0)),
    )
    sql = """
        INSERT INTO vendors (name, ceo, business_no, address,
                             payment_method, bank_name, account_holder, account_no,
                             is_auto_transfer)
        VALUES (:name, :ceo, :business_no, :address,
                :payment_method, :bank_name, :account_holder, :account_no,
                :is_auto_transfer)
    """
    with get_connection() as conn:
        cur = conn.execute(sql, data)
        return cur.lastrowid


def update(vendor_id: int, data: dict):
    data.setdefault("is_auto_transfer", 0)
    data["payment_method"] = derive_payment_method(
        data.get("bank_name", ""),
        data.get("account_no", ""),
        bool(data.get("is_auto_transfer", 0)),
    )
    sql = """
        UPDATE vendors SET
            name=:name, ceo=:ceo, business_no=:business_no, address=:address,
            payment_method=:payment_method, bank_name=:bank_name,
            account_holder=:account_holder, account_no=:account_no,
            is_auto_transfer=:is_auto_transfer
        WHERE id=:id
    """
    with get_connection() as conn:
        conn.execute(sql, {**data, "id": vendor_id})


def select_all() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM vendors ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def select_by_id(vendor_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM vendors WHERE id=?", (vendor_id,)).fetchone()
        return dict(row) if row else None


def get_names() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT name FROM vendors ORDER BY name").fetchall()
        return [r[0] for r in rows]


def delete(vendor_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM vendors WHERE id=?", (vendor_id,))


def find_by_business_no(biz_no: str) -> dict | None:
    """사업자등록번호로 업체 조회"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM vendors WHERE business_no=?", (biz_no,)
        ).fetchone()
        return dict(row) if row else None


def find_by_name(name: str) -> dict | None:
    """상호로 업체 조회"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM vendors WHERE name=?", (name,)
        ).fetchone()
        return dict(row) if row else None


def bulk_insert(rows: list[dict]) -> dict:
    """일괄 등록 — 중복 처리 포함. 결과 딕셔너리 반환.

    Returns:
        {"inserted": int, "updated": int, "skipped": int,
         "details": list[str]}
    """
    result = {"inserted": 0, "updated": 0, "skipped": 0, "details": []}
    with get_connection() as conn:
        for row in rows:
            name = row.get("name", "").strip()
            if not name:
                result["skipped"] += 1
                result["details"].append("상호 누락 → 건너뜀")
                continue

            biz_no = row.get("business_no", "").strip()
            action = row.get("_action", "skip")  # skip / update / insert_new

            # 사업자번호 중복 검사
            existing = None
            if biz_no:
                existing = conn.execute(
                    "SELECT * FROM vendors WHERE business_no=?", (biz_no,)
                ).fetchone()

            # 상호 중복 검사 (사업자번호 없는 경우)
            if not existing:
                existing = conn.execute(
                    "SELECT * FROM vendors WHERE name=?", (name,)
                ).fetchone()

            # 자동 감지: 저장 전 payment_method 계산
            row.setdefault("is_auto_transfer", 0)
            row["payment_method"] = derive_payment_method(
                row.get("bank_name", ""),
                row.get("account_no", ""),
                bool(row.get("is_auto_transfer", 0)),
            )

            if existing:
                existing = dict(existing)
                if action == "update":
                    conn.execute(
                        """UPDATE vendors SET
                            name=:name, ceo=:ceo, business_no=:business_no,
                            address=:address, payment_method=:payment_method,
                            bank_name=:bank_name, account_holder=:account_holder,
                            account_no=:account_no, is_auto_transfer=:is_auto_transfer
                        WHERE id=:id""",
                        {**row, "id": existing["id"]}
                    )
                    result["updated"] += 1
                    result["details"].append(f"'{name}' 업데이트 (기존 ID:{existing['id']})")
                else:
                    result["skipped"] += 1
                    result["details"].append(f"'{name}' 중복 → 건너뜀")
            else:
                conn.execute(
                    """INSERT INTO vendors (name, ceo, business_no, address,
                        payment_method, bank_name, account_holder, account_no,
                        is_auto_transfer)
                    VALUES (:name, :ceo, :business_no, :address,
                        :payment_method, :bank_name, :account_holder, :account_no,
                        :is_auto_transfer)""",
                    row
                )
                result["inserted"] += 1
                result["details"].append(f"'{name}' 신규 등록")
    return result
