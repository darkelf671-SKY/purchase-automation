# 할인 단가 계산 + 구매건 복사/수정 모드 -- 설계서

> **Summary**: 총액 입력 모드(견적1/2 독립 제어)와 이력 조회에서 복사/수정 분리 기능의 상세 설계
>
> **Project**: 구매기안 자동화 시스템
> **Version**: v1.2
> **Author**: 전산팀 장길섭
> **Created**: 2026-03-11
> **Last Modified**: 2026-03-12
> **Status**: Approved
> **Planning Doc**: [price-calc-and-edit-mode.plan.md](../../01-plan/features/price-calc-and-edit-mode.plan.md)

---

## 1. 변경 범위 요약

| 영역 | 복사/수정 모드 | 총액 입력 모드 |
|------|:---:|:---:|
| `db/purchase_repo.py` | `update()`, `update_items()`, `select_by_id()` | `price_input_mode` 컬럼 반영 |
| `db/database.py` | -- | 마이그레이션 (`price_input_mode`) |
| `core/models.py` | -- | `price_input_mode` 필드 (4가지 모드), `calc_total()` 분기 |
| `ui/tab_purchase.py` | 복사/수정 배너, `load_purchase()` / `load_purchase_for_edit()` 분리, `_regenerate_documents()`, 기존 파일 삭제 | 견적1/2 독립 총액 토글, `_recalc()` / `_recalc_reverse()` 분리, 툴팁 |
| `ui/tab_history.py` | "복사하여 새 기안" / "수정하기" 버튼 분리, `on_edit_purchase` 콜백 | -- |
| `ui/app.py` | `_handle_edit_purchase()` 콜백 추가 | -- |
| `documents/hwp_generator.py` | -- | 변경 불필요 (데이터가 올바르게 전달됨) |
| `documents/excel_generator.py` | -- | 변경 불필요 |

---

## 2. 이력 조회 탭 -- 복사/수정 버튼 분리

### 2.1 HistoryTab 변경사항

기존 "구매탭에 불러오기" 단일 버튼을 두 개로 분리:

```python
class HistoryTab(ttk.Frame):
    def __init__(self, parent, status_var,
                 on_load_purchase=None,    # 복사 콜백
                 on_edit_purchase=None):   # 수정 콜백
```

#### 버튼 배치 (btn_row1)

```
┌──────────────────────────────────────────────────────────────────┐
│ [복사하여 새 기안] [수정하기]              [선택 항목 삭제] [폴더 열기] │
└──────────────────────────────────────────────────────────────────┘
```

| 버튼 | 호출 메서드 | 콜백 | 동작 |
|------|-----------|------|------|
| 복사하여 새 기안 | `_load_to_purchase()` | `on_load_purchase(record, items)` | 신규 INSERT (기존 불러오기와 동일) |
| 수정하기 | `_edit_purchase()` | `on_edit_purchase(record, items)` | 수정 모드 진입 (DB UPDATE) |

### 2.2 app.py 콜백 연결

```python
# HistoryTab 생성 시
self._tab_history = HistoryTab(
    ...,
    on_load_purchase=self._handle_load_purchase,
    on_edit_purchase=self._handle_edit_purchase
)

def _handle_load_purchase(self, record, items):
    self.notebook.select(0)
    self._tab_purchase.load_purchase(record, items)

def _handle_edit_purchase(self, record, items):
    self.notebook.select(0)
    self._tab_purchase.load_purchase_for_edit(record, items)
```

---

## 3. 복사/수정 모드 상세 설계

### 3.1 상태 변수 (`ui/tab_purchase.py`)

```python
class PurchaseTab:
    def __init__(self, ...):
        self._editing_purchase_id: int | None = None   # None=신규/복사, int=수정
        self._editing_doc_folder: str | None = None    # 수정 시 기존 폴더 경로
```

### 3.2 모드 배너

배너는 `_content` 최상단에 pack/pack_forget으로 제어한다.

#### 배너 구조

```python
def _build_edit_banner(self):
    """모드 배너 -- 수정/복사 상태 표시 (초기 숨김)"""
    self._banner_frame = tk.Frame(self._content)
    self._banner_frame.pack(fill="x", pady=(0, SPACING["md"]))
    self._banner_frame.pack_forget()  # 초기 숨김

    self._edit_banner_label = tk.Label(
        self._banner_frame, text="", font=FONTS["body"])
    self._edit_banner_label.pack(side="left", padx=SPACING["md"])

    self._edit_cancel_btn = tk.Button(
        self._banner_frame, text="수정 취소", bg="#FFC107", fg="#000",
        relief="flat", padx=8, command=self._cancel_edit)
    self._edit_cancel_btn.pack(side="right", padx=SPACING["md"])
```

#### 복사 모드 배너

```
┌──────────────────────────────────────────────────────────┐
│   복사 모드: "토너 구매" -> 새 기안 작성                    │
└──────────────────────────────────────────────────────────┘
   배경: #D1ECF1 (파란색)   글자: #0C5460
   "수정 취소" 버튼: 숨김 (pack_forget)
```

#### 수정 모드 배너

```
┌──────────────────────────────────────────────────────────────┐
│   수정 모드: "토너 구매" (2026-03-11)           [수정 취소]    │
└──────────────────────────────────────────────────────────────┘
   배경: #FFF3CD (노란색)   글자: #856404
   "수정 취소" 버튼: 표시
```

#### 배너 표시 공통 메서드

```python
def _show_banner(self, bg_color, fg_color, text, show_cancel):
    self._banner_frame.configure(bg=bg_color)
    self._edit_banner_label.config(text=text, bg=bg_color, fg=fg_color)
    if show_cancel:
        self._edit_cancel_btn.pack(side="right", padx=SPACING["md"])
    else:
        self._edit_cancel_btn.pack_forget()
    # _content의 첫 번째 visible 자식 앞에 pack
    self._banner_frame.pack_forget()
    packed = [w for w in self._content.winfo_children()
              if w != self._banner_frame and w.winfo_manager() == "pack"]
    if packed:
        self._banner_frame.pack(fill="x", pady=(0, SPACING["md"]),
                                before=packed[0])
    else:
        self._banner_frame.pack(fill="x", pady=(0, SPACING["md"]))

def _show_edit_banner(self, record):
    item = record.get("item_name", "")
    date = record.get("created_at", "")[:10]
    self._show_banner("#FFF3CD", "#856404",
                      f'  수정 모드: "{item}" ({date})', show_cancel=True)

def _show_copy_banner(self, record):
    item = record.get("item_name", "")
    self._show_banner("#D1ECF1", "#0C5460",
                      f'  복사 모드: "{item}" -> 새 기안 작성', show_cancel=False)
```

### 3.3 `load_purchase()` -- 복사용 (신규 INSERT)

```python
def load_purchase(self, record, items):
    """이력에서 복사하여 새 기안 작성 (신규 INSERT)"""
    self._reset_form()
    # ... 폼 채우기 (품목, 견적, 기안 정보 등) ...
    # 총액 입력 모드 복원 (4가지: unit, total, v1_total, v2_total)
    # ... (상세 로직은 3.8절 참조) ...
    self._show_copy_banner(record)
    # _editing_purchase_id 는 None 유지 -> 신규 INSERT
```

### 3.4 `load_purchase_for_edit()` -- 수정용 (DB UPDATE)

```python
def load_purchase_for_edit(self, record, items):
    """이력에서 수정 모드로 불러오기 (DB UPDATE)"""
    self.load_purchase(record, items)      # 복사와 동일하게 폼 채우기
    self._hide_edit_banner()               # 복사 배너 제거
    self._editing_purchase_id = record["id"]
    self._editing_doc_folder = record.get("doc_folder", "")
    self._show_edit_banner(record)         # 수정 배너 표시
    self._update_gen_button_text()         # "재생성"으로 변경
```

### 3.5 버튼 텍스트 동적 변경

```python
def _update_gen_button_text(self):
    if self._editing_purchase_id:
        self._gen_btn.config(text="기안서 + 산출기초조사서 재생성")
    else:
        self._gen_btn.config(text="기안서 + 산출기초조사서 생성")
```

### 3.6 `_cancel_edit()` -- 수정 취소

```python
def _cancel_edit(self):
    self._editing_purchase_id = None
    self._editing_doc_folder = None
    self._hide_edit_banner()
    self._reset_form()
    self._update_gen_button_text()
```

### 3.7 `_reset_form()` 수정

기존 `_reset_form()` 끝에 수정 모드 상태 초기화 추가:

```python
# 수정 모드 초기화
self._editing_purchase_id = None
self._editing_doc_folder = None
if hasattr(self, '_banner_frame'):
    self._hide_edit_banner()
self._update_gen_button_text()
```

### 3.8 총액 입력 모드 복원 (복사/수정 공통)

`load_purchase()` 내에서 `price_input_mode`를 읽어 견적1/2 총액 모드 복원:

```python
# price_input_mode: "unit" | "total" | "v1_total" | "v2_total"
has_v1_total = any(
    item.get("price_input_mode") in ("total", "v1_total") for item in items)
has_v2_total = any(
    item.get("price_input_mode") in ("total", "v2_total") for item in items)

if has_v1_total:
    self._v1_total_mode_var.set(True)
if has_v2_total:
    self._v2_total_mode_var.set(True)

for row, item in zip(self._item_rows, items):
    mode = item.get("price_input_mode", "unit")
    if mode in ("total", "v1_total"):
        row.set_v1_total_mode(True)
    if mode in ("total", "v2_total"):
        # v2 총액 복원: v2_unit_price * quantity
        v2_qty = item.get("quantity", 1)
        v2_unit = item.get("v2_unit_price", 0)
        row.v2_total_var.set(str(v2_unit * v2_qty))
        row.set_v2_total_mode(True)

if has_v1_total or has_v2_total:
    self._check_vat_for_total_mode()
```

---

## 4. DB 계층 -- 수정 모드 (`db/purchase_repo.py`)

### 4.1 `update(purchase_id, data)`

```python
def update(purchase_id: int, data: PurchaseData):
    sql = """
        UPDATE purchases SET
            item_name=:item_name, spec=:spec, unit=:unit, quantity=:quantity,
            department=:department,
            vendor1_name=:v1n, vendor1_price=:v1p, vendor1_total=:v1t,
            vendor1_url=:v1u, vendor1_screenshot=:v1s,
            vendor2_name=:v2n, vendor2_price=:v2p, vendor2_total=:v2t,
            vendor2_url=:v2u, vendor2_screenshot=:v2s,
            selected_vendor=:sel, item_count=:cnt, vat_mode=:vat_mode,
            draft_date=:draft_date
        WHERE id=:id
    """
    # params = insert()와 동일 구조 + id
```

### 4.2 `update_items(purchase_id, items)`

```python
def update_items(purchase_id: int, items: list):
    with get_connection() as conn:
        conn.execute("DELETE FROM purchase_items WHERE purchase_id=?", (purchase_id,))
        _insert_items(conn, purchase_id, items)
```

- ON DELETE CASCADE는 purchases 삭제 시만 동작하므로 품목 교체 시 직접 DELETE 필요
- `_insert_items()` 기존 함수 재활용

### 4.3 `select_by_id(purchase_id)`

수정 모드에서 기존 문서 파일 경로 조회에 사용:

```python
def select_by_id(purchase_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM purchases WHERE id=?", (purchase_id,)).fetchone()
    return dict(row) if row else None
```

---

## 5. 문서 재생성 (`_regenerate_documents()`)

### 5.1 `_generate_documents()` 분기

```python
def _generate_documents(self):
    if not self._validate():
        return
    if self._editing_purchase_id:
        self._regenerate_documents()
    else:
        self._create_new_documents()
```

### 5.2 `_regenerate_documents()` 핵심 로직

```python
def _regenerate_documents(self):
    purchase_id = self._editing_purchase_id

    # 1. 검수 완료 건 확인 + 삭제 [D3]
    insp = insp_repo.select_by_purchase(purchase_id)
    if insp:
        if not messagebox.askyesno("검수 기록 삭제 경고", ...):
            return
        # 검수 파일 삭제 (doc_inspection_list, doc_inspection_rpt)
        for key in ("doc_inspection_list", "doc_inspection_rpt"):
            path = insp.get(key, "")
            if path and Path(path).exists():
                try:
                    Path(path).unlink()
                except OSError:
                    pass
        insp_repo.delete(insp["id"])

    data = self._build_purchase_data()

    # 2. 기존 문서 파일 삭제 (기안제목 변경 시 구 파일 잔여 방지)
    old_record = repo.select_by_id(purchase_id)
    if old_record:
        for key in ("doc_draft", "doc_calculation"):
            old_path = old_record.get(key, "")
            if old_path and Path(old_path).exists():
                try:
                    Path(old_path).unlink()
                except OSError:
                    pass

    # 3. 기존 폴더 사용 [D4]
    out_dir = Path(self._editing_doc_folder) if self._editing_doc_folder else None
    if not out_dir or not out_dir.exists():
        draft_title = self._draft_title_var.get().strip()
        try:
            out_dir = make_output_dir_named(draft_title)
        except FileExistsError:
            out_dir = Path(self._editing_doc_folder)
            out_dir.mkdir(parents=True, exist_ok=True)

    # 4. 문서 생성 (공통 로직 _build_docs_common 재활용)
    doc_calc, doc_draft = self._build_docs_common(data, out_dir)

    # 5. DB UPDATE
    repo.update(purchase_id, data)
    repo.update_items(purchase_id, data.items)
    self._save_db_meta(purchase_id, out_dir, doc_draft, doc_calc)

    # 6. 완료 후 수정 모드 해제 + 폼 초기화
    self._reset_form()
```

### 5.3 기존 파일 삭제 이유

기안제목이 폴더명/파일명에 포함되므로, 제목 변경 시 새 파일이 생성되고 구 파일이 남는다.
이를 방지하기 위해 재생성 전에 `doc_draft`, `doc_calculation` 경로의 기존 파일을 삭제한다.

---

## 6. 총액 입력 모드 상세 설계

### 6.1 견적1/견적2 독립 제어

기존 설계: 품목별 `_total_input_mode` 단일 체크박스 (견적1/2 동시 전환)

**현재 구현**: PurchaseTab 레벨의 두 개 독립 체크박스

```
┌── 품목 목록 ──────────────────────────────────────────────────────┐
│ [+ 품목 추가] [v] 견적1 총액입력(할인가 역산)                       │
│              [v] 견적2 총액입력(할인가 역산)  [i]                   │
│                                    견적1 합계: 100,000  원         │
│                                    견적2 합계: 105,000  원         │
└──────────────────────────────────────────────────────────────────┘
```

| 체크박스 | 변수 | 동작 |
|---------|------|------|
| 견적1 총액입력(할인가 역산) | `_v1_total_mode_var` | 모든 ItemRow의 견적1 합계 Entry 편집 가능, 단가 readonly |
| 견적2 총액입력(할인가 역산) | `_v2_total_mode_var` | 모든 ItemRow의 견적2 합계 Entry 편집 가능, 단가 readonly |

### 6.2 데이터 모델 (`core/models.py`)

```python
@dataclass
class PurchaseItem:
    # ... 기존 필드 ...
    price_input_mode: str = "unit"  # "unit" | "total" | "v1_total" | "v2_total"

    def calc_total(self) -> int:
        if self.price_input_mode in ("total", "v1_total"):
            # 견적1 총액 고정, 단가 역산
            if self.quantity > 0:
                self.unit_price = self.total_price // self.quantity
            return self.total_price
        else:
            # 기존 로직: 단가 x 수량
            self.total_price = self.unit_price * self.quantity
            return self.total_price
```

#### `price_input_mode` 4가지 값

| 값 | 견적1 | 견적2 | 설명 |
|---|:---:|:---:|------|
| `"unit"` | 단가 입력 | 단가 입력 | 기본값 |
| `"total"` | 총액 입력 | 총액 입력 | 양쪽 모두 총액 모드 |
| `"v1_total"` | 총액 입력 | 단가 입력 | 견적1만 총액 모드 |
| `"v2_total"` | 단가 입력 | 총액 입력 | 견적2만 총액 모드 |

#### ItemRow.get_data()에서 mode 결정

```python
def get_data(self) -> dict:
    v1_total_mode = self._v1_total_mode.get()
    v2_total_mode = self._v2_total_mode.get()

    # price_input_mode 결정
    if v1_total_mode and v2_total_mode:
        mode = "total"
    elif v1_total_mode:
        mode = "v1_total"
    elif v2_total_mode:
        mode = "v2_total"
    else:
        mode = "unit"

    return {
        ...,
        "price_input_mode": mode,
    }
```

### 6.3 DB 마이그레이션 (`db/database.py`)

`_migrate()` 함수의 `pi_cols` 섹션에 추가:

```python
("price_input_mode",
 "ALTER TABLE purchase_items ADD COLUMN price_input_mode TEXT DEFAULT 'unit'"),
```

### 6.4 UI -- ItemRow 양방향 계산

ItemRow에 견적1/2 독립 총액 모드 상태:

```python
class ItemRow:
    def __init__(self, ...):
        self._v1_total_mode = tk.BooleanVar(value=False)
        self._v2_total_mode = tk.BooleanVar(value=False)
        self._updating = False  # 재진입 방지 플래그
```

#### `_recalc()` -- 단가 -> 합계 (기본 모드)

```python
def _recalc(self, *_):
    if self._updating or self._v1_total_mode.get():
        return  # 견적1 총액 모드에서는 무시
    self._updating = True
    try:
        price = int(self.price_var.get().replace(",", ""))
        qty = self.qty_var.get()
        mul = 1.1 if vat == "exclusive" else 1.0
        self.total_var.set(f"{round(price * mul) * qty:,}")
    except (ValueError, tk.TclError):
        self.total_var.set("0")
    finally:
        self._updating = False
    self._on_change()
```

#### `_recalc_reverse()` -- 합계 -> 단가 역산 (총액 모드)

```python
def _recalc_reverse(self, *_):
    if self._updating or not self._v1_total_mode.get():
        return
    self._updating = True
    try:
        total = int(self.total_var.get().replace(",", ""))
        qty = self.qty_var.get()
        self.price_var.set(f"{total // qty:,}" if qty > 0 else "0")
    except (ValueError, tk.TclError):
        self.price_var.set("0")
    finally:
        self._updating = False
    self._on_change()
```

견적2도 동일 패턴 (`_recalc_v2()` / `_recalc_v2_reverse()`).

#### Entry 상태 전환

```python
def set_v1_total_mode(self, enabled: bool):
    self._v1_total_mode.set(enabled)
    self._total_entry.config(state="normal" if enabled else "readonly")
    self._price_entry.config(state="readonly" if enabled else "normal")
    # 전환 후 역산/정산 재실행
    if enabled:
        self._recalc_reverse()
    else:
        self._recalc()

def set_v2_total_mode(self, enabled: bool):
    self._v2_total_mode.set(enabled)
    self._v2_total_entry.config(state="normal" if enabled else "readonly")
    self._v2_price_entry.config(state="readonly" if enabled else "normal")
    if enabled:
        self._recalc_v2_reverse()
    else:
        self._recalc_v2()
```

### 6.5 PurchaseTab 레벨 토글

```python
def _on_v1_total_toggle(self):
    enabled = self._v1_total_mode_var.get()
    for row in self._item_rows:
        row.set_v1_total_mode(enabled)
    self._check_vat_for_total_mode()

def _on_v2_total_toggle(self):
    enabled = self._v2_total_mode_var.get()
    for row in self._item_rows:
        row.set_v2_total_mode(enabled)
    self._check_vat_for_total_mode()
```

### 6.6 VAT 자동 비활성화 [D1]

견적1 또는 견적2 총액 모드가 하나라도 켜지면 VAT를 `inclusive`로 강제:

```python
def _check_vat_for_total_mode(self):
    v1 = self._v1_total_mode_var.get()
    v2 = self._v2_total_mode_var.get()
    if v1 or v2:
        self._vat_mode_var.set("inclusive")
        for rb in self._vat_radios:
            rb.config(state="disabled")
        self._vat_hint_label.config(text="※ 총액 입력 시 VAT 별도 계산 불가")
    else:
        for rb in self._vat_radios:
            rb.config(state="normal")
        self._vat_hint_label.config(text="")
```

### 6.7 절사 정보 표시

총액 모드에서 `총액 - (단가 x 수량) != 0`인 경우 잔여금 표시:

```python
def _update_remainder_info(self):
    remainders = []
    for i, row in enumerate(self._item_rows, 1):
        qty = row.qty_var.get()
        if qty <= 0:
            continue
        # 견적1 절사
        if self._v1_total_mode_var.get():
            total = int(row.total_var.get().replace(",", ""))
            rem = total - (total // qty * qty)
            if rem > 0:
                remainders.append(f"품목{i} 견적1 절사 {rem}원")
        # 견적2 절사 (동일 패턴)
        ...
    self._remainder_label.config(
        text=" | ".join(remainders) if remainders else "")
```

### 6.8 문서 엔진 영향

총액 모드에서도 기존 HWP/Excel 자리표시자 구조 그대로 사용:
- `{{PRICE_01}}` = `unit_price` (역산된 값)
- `{{AMOUNT_01}}` = `total_price` (사용자 입력 고정값)

`PurchaseItem`의 `unit_price`/`total_price`가 이미 올바르게 세팅되어 전달되므로 `hwp_generator.py`, `excel_generator.py` 코드 변경 불필요.

---

## 7. 툴팁 (사용법 안내)

### 7.1 총액 모드 툴팁

품목 목록 하단의 `[i]` 아이콘에 마우스 hover 시 Toplevel 팝업으로 사용법 표시:

```python
# i 아이콘
info_label = ttk.Label(bottom, text="i", foreground=COLORS["info"],
                       cursor="hand2", font=FONTS["body"])
info_label.bind("<Enter>", lambda e: self._show_total_tip(e, _tip_text))
info_label.bind("<Leave>", lambda e: self._hide_total_tip())
```

#### 툴팁 내용

```
인터넷 할인가로 구매할 때 결제 총액을 직접 입력하면
단가가 자동 역산(총액/수량)됩니다.

- 견적1, 견적2를 각각 독립 설정 가능
- 체크 시: [금액] 입력 -> [단가] 자동 계산
- 해제 시: [단가] 입력 -> [금액] 자동 계산
- 총액입력 시 VAT는 'VAT포함'으로 고정

예) 토너 3개, 결제금액 42,000원
    -> 단가 14,000원 자동 표시
```

#### 툴팁 구현

```python
def _show_total_tip(self, event, text):
    if self._total_mode_tooltip:
        self._total_mode_tooltip.destroy()
    self._total_mode_tooltip = tk.Toplevel(self)
    self._total_mode_tooltip.wm_overrideredirect(True)
    self._total_mode_tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root - 120}")
    lbl = tk.Label(self._total_mode_tooltip, text=text,
                   background=COLORS["tooltip_bg"], foreground=COLORS["tooltip_fg"],
                   relief="solid", borderwidth=1, wraplength=350,
                   justify="left", padx=SPACING["md"], pady=SPACING["sm"])
    lbl.pack()

def _hide_total_tip(self):
    if self._total_mode_tooltip:
        self._total_mode_tooltip.destroy()
        self._total_mode_tooltip = None
```

---

## 8. 유효성 검사 변경

총액 모드에 따른 검증 분기:

```python
def _validate(self) -> bool:
    for i, row in enumerate(self._item_rows, 1):
        # 견적1 검증: 모드별
        if self._v1_total_mode_var.get():
            # 총액 모드: 금액(합계) 검증
            total = int(row.total_var.get().replace(",", ""))
            if total <= 0:
                # "품목 N의 견적1 금액을 올바르게 입력하세요."
        else:
            # 단가 모드: 단가 검증
            price = int(row.price_var.get().replace(",", ""))
            if price <= 0:
                # "품목 N의 견적1 단가를 올바르게 입력하세요."
```

---

## 9. 구현 순서

### Phase 1: DB 계층 -- 수정 모드
1. `purchase_repo.py` -> `update()`, `update_items()`, `select_by_id()` 추가

### Phase 2: UI -- 복사/수정 분리
1. `tab_history.py` -> "복사하여 새 기안" / "수정하기" 버튼 분리, `on_edit_purchase` 콜백
2. `app.py` -> `_handle_edit_purchase()` 콜백 추가
3. `tab_purchase.py` -> `load_purchase_for_edit()` 메서드 추가
4. `tab_purchase.py` -> 복사/수정 배너 분리 (`_show_copy_banner`, `_show_edit_banner`)
5. `tab_purchase.py` -> `_cancel_edit()`, `_reset_form()` 수정 모드 초기화
6. `tab_purchase.py` -> 버튼 텍스트 동적 변경

### Phase 3: 문서 재생성
1. `tab_purchase.py` -> `_generate_documents()` 분기 (신규/수정)
2. `tab_purchase.py` -> `_regenerate_documents()` (UPDATE + 기존 파일 삭제 + 덮어쓰기 + 검수 삭제)
3. 기존 로직 -> `_create_new_documents()` 리네임

### Phase 4: 총액 입력 -- 데이터 계층
1. `core/models.py` -> `price_input_mode` 필드 (4가지 값) + `calc_total()` 분기
2. `db/database.py` -> 마이그레이션
3. `db/purchase_repo.py` -> `_insert_items()`에 `price_input_mode` 추가

### Phase 5: 총액 입력 -- UI
1. PurchaseTab -> 견적1/2 독립 체크박스 (`_v1_total_mode_var`, `_v2_total_mode_var`)
2. ItemRow -> `_v1_total_mode` / `_v2_total_mode` 분리, `set_v1_total_mode()` / `set_v2_total_mode()`
3. ItemRow -> `_recalc()` / `_recalc_reverse()` 분리 (재진입 방지 `_updating` 플래그)
4. ItemRow -> `get_data()` 모드별 `price_input_mode` 4가지 결정
5. PurchaseTab -> VAT 자동 비활성화
6. PurchaseTab -> 절사 정보 표시
7. PurchaseTab -> 툴팁 구현
8. PurchaseTab -> `load_purchase()` 총액 모드 복원

### Phase 6: 검증
1. 수정 모드 테스트 (T10-T20)
2. 총액 모드 테스트 (T1-T9)
3. CLAUDE.md 업데이트
4. EXE 빌드

---

## 10. 리스크 대응

| 리스크 | 대응 | 구현 위치 |
|--------|------|-----------|
| 검수-구매 불일치 | 수정 시 검수 자동 삭제 [D3] | `_regenerate_documents()` |
| VAT 이중 적용 | 총액 모드 시 VAT 자동 비활성화 [D1] | `_check_vat_for_total_mode()` |
| 폴더명 불일치 | 폴더명 유지 [D4] | `_editing_doc_folder` 사용 |
| 파일 잔여 (제목 변경) | 재생성 전 기존 doc_draft/doc_calculation 파일 삭제 | `_regenerate_documents()` |
| DB 품목 불일치 | DELETE + re-INSERT | `update_items()` |
| 재진입 계산 루프 | `_updating` 플래그로 차단 | ItemRow `_recalc*()` |
| 복사/수정 혼동 | 색상 구분 배너 (파란/노란) + "수정 취소" 버튼 유무 | `_show_banner()` |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-03-11 | 초안 (수정 모드 + 총액 입력 통합 설계) | 전산팀 장길섭 |
| 2.0 | 2026-03-12 | 구현 결과 반영: 견적1/2 독립 총액 제어, 복사/수정 분리, 배너 색상 구분, 기존 파일 삭제, 툴팁, price_input_mode 4가지 값 | 전산팀 장길섭 |
