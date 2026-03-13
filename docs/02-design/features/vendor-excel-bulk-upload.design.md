# Feature Design: vendor-excel-bulk-upload

> 업체 Excel 일괄 업로드 기능 상세 설계

| 항목 | 내용 |
|------|------|
| **문서 ID** | DESIGN-FEAT-vendor-excel-bulk-upload |
| **작성일** | 2026-03-12 |
| **Plan 참조** | PLAN-FEAT-vendor-excel-bulk-upload |

---

## 1. Change Strategy

### 1.1 변경 파일 요약

| 파일 | 변경 유형 | 변경 범위 |
|------|----------|----------|
| `db/vendor_repo.py` | 함수 추가 | `find_by_business_no()`, `find_by_name()`, `bulk_insert()` 3개 함수 추가 |
| `ui/tab_vendor.py` | 메서드 + 클래스 추가 | `_download_template()`, `_excel_upload()`, `_on_bulk_save()` 메서드 추가. `BulkUploadPreviewDialog` 클래스 추가. 버튼 2개 추가 |

### 1.2 의존성

- `openpyxl.Workbook`, `openpyxl.load_workbook` — Excel 생성/읽기
- `openpyxl.styles.Font`, `PatternFill`, `Alignment`, `Border`, `Side` — 헤더 스타일링
- `db.vendor_repo` — `find_by_business_no`, `find_by_name`, `bulk_insert`
- `ui.design_system` — `COLORS`, `FONTS`, `SPACING`, `configure_treeview_tags`

---

## 2. Detailed Method Design

### 2.1 `vendor_repo.find_by_business_no(biz_no: str) -> dict | None`

```python
def find_by_business_no(biz_no: str) -> dict | None:
    """사업자등록번호로 업체 조회"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM vendors WHERE business_no=?", (biz_no,)
        ).fetchone()
        return dict(row) if row else None
```

- 입력: 사업자등록번호 문자열 (예: `"123-45-67890"`)
- 반환: 업체 딕셔너리 또는 None
- 용도: `bulk_insert` 및 `BulkUploadPreviewDialog`에서 중복 검사 1차 기준

### 2.2 `vendor_repo.find_by_name(name: str) -> dict | None`

```python
def find_by_name(name: str) -> dict | None:
    """상호로 업체 조회"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM vendors WHERE name=?", (name,)
        ).fetchone()
        return dict(row) if row else None
```

- 입력: 상호명 문자열
- 반환: 업체 딕셔너리 또는 None
- 용도: 사업자등록번호가 없는 경우 중복 검사 2차 기준

### 2.3 `vendor_repo.bulk_insert(rows: list[dict]) -> dict`

```python
def bulk_insert(rows: list[dict]) -> dict:
    result = {"inserted": 0, "updated": 0, "skipped": 0, "details": []}
    with get_connection() as conn:
        for row in rows:
            # 1. name 빈 값 → 건너뛰기
            # 2. business_no 중복 검사 (conn 내부 쿼리)
            # 3. name 중복 검사 (fallback)
            # 4. _action 필드로 분기: "insert_new" / "update" / "skip"
            #    - insert_new: INSERT
            #    - update: UPDATE WHERE id=existing["id"]
            #    - skip: 건너뛰기
    return result
```

- **트랜잭션**: 단일 `with get_connection()` 블록 = 전체 일괄 커밋
- **`_action` 필드**: `BulkUploadPreviewDialog`에서 사용자 선택에 따라 각 row에 삽입
  - `"insert_new"`: 신규 등록
  - `"update"`: 기존 레코드 덮어쓰기
  - `"skip"`: 건너뛰기 (기본값)
- **반환값**: `{inserted: int, updated: int, skipped: int, details: list[str]}`

### 2.4 `VendorTab._download_template()`

Excel 양식 파일 생성. 2개 시트 구성:

#### 시트1: "업체목록"

| 행 | 내용 | 스타일 |
|----|------|--------|
| 1 (헤더) | 상호 *, 대표자, 사업자등록번호, 주소, 결제방법, 은행명, 예금주, 계좌번호 | 파란 배경(`#4472C4`), 흰색 볼드, 가운데 정렬, 테두리 |
| 2~4 (예제) | 3개 업체 예제 데이터 | 연두 배경(`#E2EFDA`), 테두리 |

- 열 너비: `[22, 12, 18, 35, 14, 12, 12, 20]`
- 예제 데이터:
  - (주)한솔사무용품 / 김철수 / 123-45-67890 / card
  - 오피스디포 / 이영희 / 234-56-78901 / transfer + 계좌정보
  - 에스투비 / 박지성 / 345-67-89012 / auto_transfer

#### 시트2: "설명"

- 탭 색상: `#FFC000` (노랑)
- 내용: 필드별 설명, 결제방법 코드표, 중복 처리 규칙, 주의사항
- 스타일: 제목 = 볼드 14pt `#1F4E79`, 섹션 = 볼드 11pt `#2E75B6`

#### 저장 흐름

1. `filedialog.asksaveasfilename()` → 경로 선택
2. `Workbook()` 생성 → 시트 구성 → `wb.save(path)`
3. 상태바 + messagebox 알림

### 2.5 `VendorTab._excel_upload()`

```
1. filedialog.askopenfilename() → 파일 선택
2. load_workbook(path, read_only=True)
3. 헤더 매핑 (header_map):
   "상호" / "상호 *" → "name"
   "대표자" → "ceo"
   "사업자등록번호" → "business_no"
   "주소" → "address"
   "결제방법" → "payment_method"
   "은행명" → "bank_name"
   "예금주" → "account_holder"
   "계좌번호" → "account_no"
4. "name" 헤더 필수 검증 → 없으면 에러 반환
5. 데이터 행 파싱 (2행~):
   - 빈 행 스킵 (any(row) == False)
   - name 빈 값 스킵
   - 결제방법 정규화 (payment_method normalize)
6. BulkUploadPreviewDialog(self, rows, on_save=self._on_bulk_save)
```

#### 결제방법 정규화 매핑

| 입력값 (대소문자 무관) | 변환 결과 |
|----------------------|----------|
| `법인카드`, `카드`, `card`, 빈 값 | `card` |
| `무통장입금`, `무통장`, `transfer` | `transfer` |
| `자동이체`, `자동이체납부`, `자동 이체 납부`, `auto_transfer` | `auto_transfer` |
| 기타 | `card` (기본값) |

### 2.6 `BulkUploadPreviewDialog`

`tk.Toplevel` 기반 미리보기 다이얼로그.

#### 레이아웃 구조

```
┌─────────────────────────────────────────────────────┐
│ [상단 요약]                                          │
│  총 N건  신규: X건  중복: Y건   [모두 건너뛰기] [모두 덮어쓰기] │
├─────────────────────────────────────────────────────┤
│ [Treeview - 850x520]                                │
│  상태 | 상호 | 대표자 | 사업자번호 | 결제방법 | 처리   │
│  신규   (주)한솔   김철수   123-45-...   법인카드   등록   │  ← 초록 배경
│  중복   오피스디포  이영희   234-56-...   무통장입금  건너뛰기│  ← 노랑 배경
├─────────────────────────────────────────────────────┤
│ [중복 업체 처리 LabelFrame]  (중복 있을 때만 표시)      │
│  '오피스디포' (사업자번호 일치: '오피스디포')             │
│    ○ 건너뛰기  ○ 덮어쓰기(업데이트)                    │
├─────────────────────────────────────────────────────┤
│                            [일괄 등록 실행] [취소]     │
└─────────────────────────────────────────────────────┘
```

#### 중복 검사 로직 (생성자에서 실행)

```python
for i, row in enumerate(self._rows):
    existing = None
    biz_no = row.get("business_no", "").strip()
    if biz_no:
        existing = repo.find_by_business_no(biz_no)    # 1차: 사업자번호
    if not existing:
        existing = repo.find_by_name(row["name"])       # 2차: 상호명
    if existing:
        self._duplicates.append((i, row, existing))
    else:
        row["_action"] = "insert_new"
```

#### Treeview 태그

| 태그 | 배경색 | 용도 |
|------|--------|------|
| `new` | `#D4EDDA` (연두) | 신규 업체 |
| `dup` | `#FFF3CD` (연노랑) | 중복 업체 |

#### 중복 처리 UI

- 중복 건마다 `ttk.Radiobutton` 2개: "건너뛰기" (기본) / "덮어쓰기(업데이트)"
- `_dup_actions: dict[int, tk.StringVar]` — 인덱스별 처리 선택 저장
- `_update_action(idx)`: 라디오 변경 시 `_rows[idx]["_action"]` 갱신 + Treeview "처리" 컬럼 갱신
- `_set_all_action(action)`: "모두 건너뛰기"/"모두 덮어쓰기" 일괄 적용

#### 실행 (`_execute`)

1. `repo.bulk_insert(self._rows)` 호출
2. 결과 messagebox 표시 (신규/업데이트/건너뜀 건수)
3. `self._on_save()` 콜백 실행
4. 다이얼로그 닫기

---

## 3. Duplicate Handling Flow

```
Excel 행 1건 처리:
│
├─ business_no 존재?
│   ├─ Yes → find_by_business_no(biz_no)
│   │         ├─ 일치 → 중복 (dup)
│   │         └─ 불일치 → find_by_name(name)
│   │                     ├─ 일치 → 중복 (dup)
│   │                     └─ 불일치 → 신규 (insert_new)
│   └─ No → find_by_name(name)
│            ├─ 일치 → 중복 (dup)
│            └─ 불일치 → 신규 (insert_new)
│
├─ 중복인 경우:
│   ├─ 사용자 선택: "건너뛰기" → _action = "skip" → skipped++
│   └─ 사용자 선택: "덮어쓰기" → _action = "update" → UPDATE WHERE id → updated++
│
└─ 신규인 경우:
    └─ _action = "insert_new" → INSERT → inserted++
```

---

## 4. UI Integration

### 4.1 VendorTab 버튼 배치

`btn_row` 프레임에 기존 "업체 추가" / "수정" / "삭제" 버튼 외 2개 추가:

```python
ttk.Button(btn_row, text="Excel 일괄 업로드",
           command=self._excel_upload).pack(side="left", padx=SPACING["sm"])
ttk.Button(btn_row, text="양식 다운로드",
           command=self._download_template).pack(side="left", padx=SPACING["sm"])
```

배치 순서 (좌→우): 업체 추가 | 수정 | Excel 일괄 업로드 | 양식 다운로드 | (우측) 삭제

### 4.2 `_on_bulk_save()` 연동

```python
def _on_bulk_save(self):
    self.refresh()                          # 업체 탭 Treeview 갱신
    # 구매 조사 탭 업체 Combobox 갱신
    notebook = self.master
    for tab_id in notebook.tabs():
        tab_widget = notebook.nametowidget(tab_id)
        if hasattr(tab_widget, 'refresh_vendors'):
            tab_widget.refresh_vendors()
            break
```

- `refresh_vendors()`: 구매 조사 탭(`tab_purchase.py`)의 업체 Combobox 값 갱신 메서드
- 예외 처리: `try/except` 감싸서 탭 참조 실패 시 무시

---

## 5. Import 구성

### ui/tab_vendor.py

```python
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import db.vendor_repo as repo
from ui.design_system import COLORS, SPACING, FONTS, configure_treeview_tags, insert_with_alternating
from ui.base_dialog import BaseDialog
```

- `Workbook`: 양식 다운로드에서 신규 Excel 생성
- `load_workbook`: `_excel_upload` 내부에서 지연 임포트 (`from openpyxl import load_workbook`)
- `Font, PatternFill, Alignment, Border, Side`: 헤더/예제 행 스타일링
