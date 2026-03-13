# 결제방법 자동 추천 — 상세 설계서

> **작성일**: 2026-03-13
> **Phase**: Design (rev2 — 구매탭 결제방법 라디오 유지)
> **Plan 문서**: `docs/01-plan/features/payment-method-auto-detect.plan.md`
> **영향도**: Medium (업체 UI 변경 + DB 마이그레이션 + 구매탭 자동 추천)

---

## Executive Summary

| 관점 | 내용 |
|------|------|
| **문제** | 업체 등록 시 결제방법 라디오+은행정보 이중 입력. Excel에 영문 코드 노출. 단, 같은 업체라도 건별로 결제방법이 다를 수 있음 |
| **해결책** | 업체 관리: 라디오 제거, 은행 정보만 등록 (capability). 구매 조사: 라디오 **유지**, 업체 선택 시 자동 추천 (decision) |
| **기능/UX 효과** | 업체 등록 단순화 + 구매 건별 결제방법 유연성 100% 유지 |
| **핵심 가치** | UX 단순화 + 건별 유연성 + 하위 호환 100% |

---

## 1. 핵심 함수 설계

### 1.1 `derive_payment_method()` — 위치: `db/vendor_repo.py` 상단

```python
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
```

**호출 지점**:
- `vendor_repo.insert()` / `update()` / `bulk_insert()` → 저장 전 `payment_method` 계산
- `VendorDialog._on_save()` → `validate_bank_info()` 경고
- `tab_purchase._on_draft_vendor_select()` → 기본 추천에 활용 (DB 값 참조)

---

## 2. DB 변경 설계

### 2.1 `database.py` — `_migrate()` 함수에 추가

```python
# vendors 테이블 마이그레이션
v_cols = {r[1] for r in conn.execute("PRAGMA table_info(vendors)").fetchall()}
for col, sql in [
    ("is_auto_transfer",
     "ALTER TABLE vendors ADD COLUMN is_auto_transfer INTEGER DEFAULT 0"),
]:
    if col not in v_cols:
        conn.execute(sql)

# 기존 auto_transfer 업체 → is_auto_transfer=1 플래그 이관
if "is_auto_transfer" not in v_cols:
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
```

---

## 3. `vendor_repo.py` 변경 설계

### 3.1 `insert()` — 저장 전 자동 감지

```python
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
```

### 3.2 `update()` — 동일 패턴

```python
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
```

### 3.3 `bulk_insert()` — 각 행 저장 전 자동 감지

```python
# 각 row 처리 루프 내부 (기존 로직 유지)
row.setdefault("is_auto_transfer", 0)
row["payment_method"] = derive_payment_method(
    row.get("bank_name", ""),
    row.get("account_no", ""),
    bool(row.get("is_auto_transfer", 0)),
)
```

INSERT/UPDATE SQL에 `is_auto_transfer` 컬럼 추가.

---

## 4. `ui/tab_vendor.py` 변경 설계

### 4.1 VendorDialog — `_build_content()` 변경

**제거**: 결제방법 라디오버튼 3개 (L327-336), `_toggle_transfer()` 메서드

**변경 후 row 배치**:
```
row 0: 상호 *        (기존 유지)
row 1: 대표자        (기존 유지)
row 2: 사업자등록번호 (기존 유지)
row 3: 주소          (기존 유지)
row 4: ── 구분선 ─── (Separator)
row 5: 은행명        (항상 표시, state="normal")
row 6: 예금주        (항상 표시, state="normal")
row 7: 계좌번호      (항상 표시, state="normal")
row 8: ☐ 자동이체납부 업체  (체크박스)
row 9: → 기본 결제방법: 법인카드  (자동 감지 미리보기 라벨)
```

**`__init__` 변경**:
```python
def __init__(self, parent, title: str, vendor: dict = None, on_save=None):
    self._vendor = vendor
    self._vars = {}
    self._auto_transfer_var = tk.IntVar(value=0)
    super().__init__(parent, title, on_save=on_save)
    if vendor:
        self._load(vendor)
```

**제거 대상**:
| 기존 코드 | 조치 |
|---------|------|
| `self._pay_var = tk.StringVar(value="card")` | 제거 |
| `self._transfer_labels = []` | 제거 |
| `self._transfer_entries = []` | 제거 |
| 결제방법 라디오버튼 3개 | 제거 |
| `_toggle_transfer()` 메서드 | 제거 |

**추가**: `_update_pay_preview()` 메서드
```python
def _update_pay_preview(self):
    """은행 정보/자동이체에 따라 기본 결제방법 미리보기 갱신"""
    from db.vendor_repo import derive_payment_method
    bank = self._vars.get("bank_name", tk.StringVar()).get()
    acct = self._vars.get("account_no", tk.StringVar()).get()
    is_at = bool(self._auto_transfer_var.get())
    result = derive_payment_method(bank, acct, is_at)
    label = _PAY_LABELS.get(result, result)
    self._pay_preview_var.set(f"→ 기본 결제방법: {label}")
```

### 4.2 VendorDialog — `_load()` 변경

```python
def _load(self, v: dict):
    for key, var in self._vars.items():
        var.set(v.get(key, ""))
    self._auto_transfer_var.set(v.get("is_auto_transfer", 0) or 0)
    self._update_pay_preview()
```

### 4.3 VendorDialog — `_on_save()` 변경

```python
def _on_save(self):
    name = self._vars["name"].get().strip()
    if not name:
        messagebox.showwarning("입력 오류", "상호를 입력하세요.", parent=self)
        return

    bank_name = self._vars["bank_name"].get().strip()
    account_no = self._vars["account_no"].get().strip()

    # 불완전 은행 정보 경고
    from db.vendor_repo import validate_bank_info
    warning = validate_bank_info(bank_name, account_no)
    if warning:
        messagebox.showwarning("은행 정보 확인", warning, parent=self)

    data = {
        "name":             name,
        "ceo":              self._vars["ceo"].get().strip(),
        "business_no":      self._vars["business_no"].get().strip(),
        "address":          self._vars["address"].get().strip(),
        "bank_name":        bank_name,
        "account_holder":   self._vars["account_holder"].get().strip(),
        "account_no":       account_no,
        "is_auto_transfer": self._auto_transfer_var.get(),
        # payment_method는 vendor_repo에서 자동 계산
    }
    try:
        if self._vendor:
            repo.update(self._vendor["id"], data)
        else:
            repo.insert(data)
        self._fire_save_callback()
        self.destroy()
    except Exception as e:
        msg = str(e)
        if "UNIQUE" in msg.upper():
            msg = f"'{name}' 업체명이 이미 등록되어 있습니다."
        messagebox.showerror("저장 오류", msg, parent=self)
```

### 4.4 `_apply_filter()` — 검색 필드 변경

```python
# 기존: ("name", "ceo", "business_no", "address", "payment_method")
# 변경: ("name", "ceo", "business_no", "address", "bank_name")
```

### 4.5 Excel 양식 (`_download_template`) 변경

**헤더**: 8열 → 7열 (결제방법 제거)
```python
headers = ["상호 *", "대표자", "사업자등록번호", "주소",
           "은행명", "예금주", "계좌번호"]
```

**예제**: 7컬럼
```python
examples = [
    ["(주)한솔사무용품", "김철수", "123-45-67890", "서울시 강남구 테헤란로 123",
     "", "", ""],
    ["오피스디포", "이영희", "234-56-78901", "서울시 종로구 종로 456",
     "국민은행", "오피스디포", "123-456-789012"],
    ["에스투비", "박지성", "345-67-89012", "서울시 서초구 서초대로 789",
     "", "", ""],
]
```

**열 너비**: `widths = [22, 12, 18, 35, 12, 12, 20]`

**설명 시트**: 자동 감지 규칙 설명으로 교체 (계획서 참조)

### 4.6 Excel 업로드 파싱 (`_excel_upload`) 변경

**header_map**: `"결제방법": "_legacy_payment"` (하위 호환, 무시)

**기본값**: `payment_method` 제거, `is_auto_transfer: 0` 추가

**결제방법 정규화 코드 삭제** (L263-272)

**파싱 후**: `data.pop("_legacy_payment", None)`

### 4.7 BulkUploadPreviewDialog — 결제방법 자동 감지 표시

```python
from db.vendor_repo import derive_payment_method
auto_pay = derive_payment_method(
    row.get("bank_name", ""),
    row.get("account_no", ""),
    bool(row.get("is_auto_transfer", 0)),
)
pay = self._PAY.get(auto_pay, auto_pay)
```

---

## 5. `ui/tab_purchase.py` 변경 설계

### ★ 핵심: 결제방법 라디오버튼 유지

구매 조사 탭의 `_build_vendor_payment_section()` L702-712 결제방법 라디오버튼 3개는 **변경 없이 유지**.

### 5.1 `_on_draft_vendor_select()` — 자동 추천 로직 추가

```python
def _on_draft_vendor_select(self, _event=None):
    name = self._draft_vendor_var.get()
    v = next((x for x in self._all_vendors if x["name"] == name), None)
    if not v:
        return
    self._dv_ceo_var.set(v["ceo"] or "-")
    self._dv_biz_var.set(v["business_no"] or "-")
    self._dv_addr_var.set(v["address"] or "-")

    # ★ 결제방법 자동 추천 (업체 기본값 → 라디오 자동 선택)
    pay_code = v.get("payment_method", "card")
    self._dv_pay_var.set(PAYMENT_METHODS.get(pay_code, pay_code))
    self._pay_method_var.set(pay_code)  # 라디오 자동 선택 (사용자 변경 가능)

    # 은행 정보 채움
    self._dv_bank_var.set(v.get("bank_name", "") or "")
    self._dv_holder_var.set(v.get("account_holder", "") or "")
    self._dv_account_var.set(v.get("account_no", "") or "")
    self._on_pay_method_change()
```

**변경점**: `pay_code`를 기존과 동일하게 `v.get("payment_method")`로 가져옴. DB에서 자동 계산된 값이므로 별도 `derive_payment_method()` 호출 불필요.

### 5.2 `_on_pay_method_change()` — 은행정보 클리어 제거

```python
def _on_pay_method_change(self):
    """결제방법 라디오 변경 → 은행 정보 프레임 표시/숨김"""
    if self._pay_method_var.get() in ("transfer", "auto_transfer"):
        self._bank_info_frame.grid()
    else:
        self._bank_info_frame.grid_remove()
        # ★ 변경: 은행 정보 클리어하지 않음 (업체 DB 값 보존)
        # 기존에는 card 선택 시 은행 정보를 지웠지만,
        # 이제 업체 은행 정보는 보존하고 프레임만 숨김
```

**기존 코드에서 제거할 3줄**:
```python
# 제거:
# self._dv_bank_var.set("")
# self._dv_holder_var.set("")
# self._dv_account_var.set("")
```

### 5.3 `_build_vendor_payment_section()` — "기본 결제:" 라벨 변경

```python
# 기존 (L694): "기본 결제:" + foreground=COLORS["text_secondary"]
# 변경:        "기본 결제:" + foreground=COLORS["primary"], font bold
ttk.Label(vendor_info, text="기본 결제:").grid(
    row=3, column=0, sticky="w", padx=(0, SPACING["md"]), pady=SPACING["xs"])
ttk.Label(vendor_info, textvariable=self._dv_pay_var,
          foreground=COLORS["primary"],
          font=("맑은 고딕", 10, "bold")).grid(
    row=3, column=1, sticky="w", pady=SPACING["xs"])
```

### 5.4 변경 없음 (유지)

| 항목 | 이유 |
|------|------|
| `_pay_method_var` | 구매 건별 결제방법 선택 (라디오 바인딩) |
| `_build_purchase_data()` L1692 | `data.payment_method = self._pay_method_var.get()` — 건별 확정값 |
| `load_purchase()` L1539-1547 | purchases 테이블 스냅샷 복원 |
| `_validate()` | 결제방법 검증 로직 유지 |

---

## 6. 영향 없음 확인

| 파일 | 이유 |
|------|------|
| `ui/tab_history.py` | purchases.payment_method (건별 확정값) 읽기 전용 |
| `ui/tab_inspection.py` | 동일 |
| `documents/hwp_generator.py` | `_format_payment_method()` — 기존 3종 코드 모두 처리 |
| `core/models.py` | `payment_method` 필드 유지 |
| `db/purchase_repo.py` | purchases 테이블 스냅샷 저장 유지 |

---

## 7. 구현 순서

```
[1] derive_payment_method() + validate_bank_info()    ← 의존성 없음
     ↓
[2] database.py 마이그레이션                           ← 의존성 없음
     ↓
[3] vendor_repo.py (insert/update/bulk_insert)         ← [1]에 의존
     ↓
[4] VendorDialog 리팩토링                               ← [1], [3]에 의존
     ↓
[5] Excel 양식/파싱 변경                                ← [1]에 의존
     ↓
[6] BulkUploadPreviewDialog 변경                        ← [5]에 의존
     ↓
[7] tab_purchase.py (_on_pay_method_change 수정,        ← [3]에 의존
    _dv_pay_var 스타일 변경)
     ↓
[8] 통합 테스트 (S1~S16)                                ← 전체 완료 후
```

---

## 8. 변경 요약 매트릭스

| 파일 | 추가 | 수정 | 삭제 | 영향도 |
|------|:----:|:----:|:----:|:------:|
| `db/vendor_repo.py` | `derive_payment_method()`, `validate_bank_info()` | `insert()`, `update()`, `bulk_insert()` | - | 중간 |
| `db/database.py` | `is_auto_transfer` 마이그레이션 | `_migrate()` | - | 낮음 |
| `ui/tab_vendor.py` (VendorDialog) | `_auto_transfer_var`, `_pay_preview_var`, `_update_pay_preview()` | `__init__`, `_build_content`, `_load`, `_on_save` | `_pay_var`, `_transfer_labels`, `_transfer_entries`, `_toggle_transfer()`, 라디오 3개 | 높음 |
| `ui/tab_vendor.py` (VendorTab) | - | `_apply_filter` 검색 필드 | - | 낮음 |
| `ui/tab_vendor.py` (Excel) | - | `_download_template`, `_excel_upload` | 결제방법 정규화 코드 | 중간 |
| `ui/tab_vendor.py` (Bulk) | - | 미리보기 결제방법 | - | 낮음 |
| `ui/tab_purchase.py` | - | `_on_pay_method_change` (클리어 제거), `_dv_pay_var` 스타일 | - | 낮음 |

---

## 9. 안전 가드

| # | 위험 | 가드 |
|---|------|------|
| SG-1 | 이전 Excel 양식(8열) 업로드 | `header_map`에 `"결제방법": "_legacy_payment"` 유지 |
| SG-2 | 기존 `auto_transfer` 업체 수정 | `_load()`에서 `is_auto_transfer` 반영 |
| SG-3 | `payment_method` 컬럼 외부 참조 | DB에 항상 유효값 저장 (자동 계산) |
| SG-4 | 불완전 은행 정보 | `validate_bank_info()` 경고. 저장 허용 (card로 감지) |
| SG-5 | 구매탭 라디오 유지 → `_pay_method_var` 정상 동작 | 기존 라디오+바인딩 코드 변경 없음 |
| SG-6 | 구매탭에서 라디오 변경 시 은행 정보 소실 | `_on_pay_method_change`에서 클리어 제거 |
