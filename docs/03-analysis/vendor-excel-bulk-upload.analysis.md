# Gap Analysis: vendor-excel-bulk-upload

> 설계(Design) 대비 실제 구현 검증

| 항목 | 내용 |
|------|------|
| **문서 ID** | ANALYSIS-vendor-excel-bulk-upload |
| **작성일** | 2026-03-12 |
| **Design 참조** | DESIGN-FEAT-vendor-excel-bulk-upload |
| **검증 대상** | `db/vendor_repo.py`, `ui/tab_vendor.py` |
| **Match Rate** | **100%** |

---

## 1. vendor_repo.py 검증

### 1.1 `find_by_business_no(biz_no: str) -> dict | None`

| 항목 | 설계 | 구현 (L51-57) | 일치 |
|------|------|---------------|------|
| 시그니처 | `(biz_no: str) -> dict \| None` | `(biz_no: str) -> dict \| None` | O |
| SQL | `SELECT * FROM vendors WHERE business_no=?` | `SELECT * FROM vendors WHERE business_no=?` | O |
| 반환 | `dict(row) if row else None` | `dict(row) if row else None` | O |
| docstring | 한글 설명 | `"""사업자등록번호로 업체 조회"""` | O |

**결과: PASS**

### 1.2 `find_by_name(name: str) -> dict | None`

| 항목 | 설계 | 구현 (L60-66) | 일치 |
|------|------|---------------|------|
| 시그니처 | `(name: str) -> dict \| None` | `(name: str) -> dict \| None` | O |
| SQL | `SELECT * FROM vendors WHERE name=?` | `SELECT * FROM vendors WHERE name=?` | O |
| 반환 | `dict(row) if row else None` | `dict(row) if row else None` | O |
| docstring | 한글 설명 | `"""상호로 업체 조회"""` | O |

**결과: PASS**

### 1.3 `bulk_insert(rows: list[dict]) -> dict`

| 항목 | 설계 | 구현 (L69-128) | 일치 |
|------|------|----------------|------|
| 시그니처 | `(rows: list[dict]) -> dict` | `(rows: list[dict]) -> dict` | O |
| 반환 구조 | `{inserted, updated, skipped, details}` | `{inserted, updated, skipped, details}` | O |
| 트랜잭션 | 단일 `with get_connection()` | 단일 `with get_connection() as conn:` (L77) | O |
| name 빈 값 처리 | 건너뛰기 | `if not name: skipped += 1` (L80-82) | O |
| `_action` 필드 | `skip / update / insert_new` | `row.get("_action", "skip")` (L86) | O |
| 중복 검사 1차 | business_no | `conn.execute(...WHERE business_no=?)` (L91-93) | O |
| 중복 검사 2차 | name (fallback) | `conn.execute(...WHERE name=?)` (L97-99) | O |
| update 분기 | `_action == "update"` → UPDATE | `if action == "update": conn.execute(UPDATE...)` (L103-114) | O |
| skip 분기 | else → skipped++ | `else: skipped += 1` (L115-117) | O |
| insert 분기 | existing 없으면 INSERT | `else: conn.execute(INSERT...)` (L118-127) | O |
| details 메시지 | 건별 설명 문자열 | 업데이트/건너뜀/신규 등록 메시지 (L114, L117, L127) | O |

**결과: PASS**

---

## 2. tab_vendor.py 검증

### 2.1 Import 구성

| 설계 요구 Import | 구현 (L1-9) | 일치 |
|-----------------|-------------|------|
| `tkinter as tk` | L2 | O |
| `ttk, messagebox, filedialog` | L3 | O |
| `Path` | L4: `from pathlib import Path` | O |
| `openpyxl.Workbook` | L5: `from openpyxl import Workbook` | O |
| `Font, PatternFill, Alignment, Border, Side` | L6: `from openpyxl.styles import Font, PatternFill, Alignment, Border, Side` | O |
| `db.vendor_repo as repo` | L7 | O |
| `COLORS, SPACING, FONTS, configure_treeview_tags, insert_with_alternating` | L8 | O |
| `BaseDialog` | L9: `from ui.base_dialog import BaseDialog` | O |
| `load_workbook` (지연 임포트) | L222: `from openpyxl import load_workbook` | O |

**결과: PASS**

### 2.2 UI 버튼 배치

| 설계 요구 | 구현 (L45-56) | 일치 |
|----------|---------------|------|
| "Excel 일괄 업로드" 버튼 | L53-54: `ttk.Button(btn_row, text="Excel 일괄 업로드", command=self._excel_upload)` | O |
| "양식 다운로드" 버튼 | L55-56: `ttk.Button(btn_row, text="양식 다운로드", command=self._download_template)` | O |
| 배치 위치: btn_row 내 side="left" | 두 버튼 모두 `.pack(side="left", padx=SPACING["sm"])` | O |
| "삭제" 버튼 side="right" 유지 | L52: `.pack(side="right", ...)` | O |

**결과: PASS**

### 2.3 `_download_template()`

| 설계 항목 | 구현 (L116-210) | 일치 |
|----------|-----------------|------|
| `filedialog.asksaveasfilename` | L118-123 | O |
| 기본 파일명 `업체_일괄등록_양식.xlsx` | L122: `initialfile="업체_일괄등록_양식.xlsx"` | O |
| 시트1 이름 "업체목록" | L131: `ws.title = "업체목록"` | O |
| 헤더 8개 | L133-134: 상호 *, 대표자, 사업자등록번호, 주소, 결제방법, 은행명, 예금주, 계좌번호 | O |
| 헤더 스타일: 파란 배경 | L135: `PatternFill(start_color="4472C4", ...)` | O |
| 헤더 스타일: 흰색 볼드 | L136: `Font(bold=True, color="FFFFFF", size=11)` | O |
| 헤더 가운데 정렬 | L145: `Alignment(horizontal="center")` | O |
| 헤더 테두리 | L137-139: `Border(left=Side(style="thin"), ...)` | O |
| 예제 3행 | L149-156: 3개 업체 (한솔, 오피스디포, 에스투비) | O |
| 예제 배경 연두색 | L157: `PatternFill(start_color="E2EFDA", ...)` | O |
| 열 너비 설정 | L165: `widths = [22, 12, 18, 35, 14, 12, 12, 20]` | O |
| 시트2 이름 "설명" | L170: `wb.create_sheet("설명")` | O |
| 시트2 탭 색상 노랑 | L171: `tabColor = "FFC000"` | O |
| 설명 내용 (필드, 중복규칙, 주의사항) | L173-195: info 리스트 | O |
| 제목 폰트 | L196: `Font(bold=True, size=14, color="1F4E79")` | O |
| 섹션 폰트 | L197: `Font(bold=True, size=11, color="2E75B6")` | O |
| 열 너비 A=22, B=65 | L205-206 | O |
| 저장 + 상태바 + messagebox | L208-210 | O |

**결과: PASS**

### 2.4 `_excel_upload()`

| 설계 항목 | 구현 (L212-285) | 일치 |
|----------|-----------------|------|
| `filedialog.askopenfilename` | L214-217 | O |
| `load_workbook(path, read_only=True)` | L222-223 | O |
| 헤더 매핑 8개 키 | L226-235: "상호"/"상호 *" → name, 대표자 → ceo 등 | O |
| "name" 헤더 필수 검증 | L242-245: `if "name" not in headers: showerror` | O |
| 데이터 파싱 2행~ | L250: `ws.iter_rows(min_row=2, values_only=True)` | O |
| 빈 행 스킵 | L251: `if not any(row): continue` | O |
| name 빈 값 스킵 | L261-262: `if not data["name"]: continue` | O |
| 기본 payment_method = "card" | L255: 기본값 딕셔너리에 `"payment_method": "card"` | O |
| 결제방법 정규화 | L264-272: 한글/영문 모두 지원, 미인식 → card | O |
| 빈 결과 검사 | L276-278: `if not rows: showinfo("데이터 없음")` | O |
| 예외 처리 | L280-282: `except Exception as e: showerror` | O |
| `BulkUploadPreviewDialog` 호출 | L285: `BulkUploadPreviewDialog(self, rows, on_save=self._on_bulk_save)` | O |

**결과: PASS**

### 2.5 `_on_bulk_save()`

| 설계 항목 | 구현 (L287-298) | 일치 |
|----------|-----------------|------|
| `self.refresh()` 호출 | L288 | O |
| 구매 조사 탭 `refresh_vendors()` 연동 | L291-295: notebook 탭 순회 → `hasattr(tab_widget, 'refresh_vendors')` | O |
| 예외 처리 (탭 참조 실패 무시) | L296-298: `except Exception: pass` | O |

**결과: PASS**

### 2.6 `BulkUploadPreviewDialog`

| 설계 항목 | 구현 (L414-559) | 일치 |
|----------|-----------------|------|
| `tk.Toplevel` 기반 | L414: `class BulkUploadPreviewDialog(tk.Toplevel)` | O |
| 윈도우 크기 850x520 | L422: `self.geometry("850x520")` | O |
| `transient` + `grab_set` | L423-424 | O |
| `_PAY` 라벨 매핑 | L417: `{"card": "법인카드", ...}` | O |
| `_dup_actions` 딕셔너리 | L427: `dict[int, tk.StringVar]` | O |

#### 중복 검사 로직

| 설계 항목 | 구현 (L436-448) | 일치 |
|----------|-----------------|------|
| business_no 1차 검사 | L441-442: `repo.find_by_business_no(biz_no)` | O |
| name 2차 검사 (fallback) | L443-444: `repo.find_by_name(row["name"])` | O |
| 중복 → `_duplicates` 리스트 추가 | L446: `self._duplicates.append((i, row, existing))` | O |
| 신규 → `_action = "insert_new"` | L449: `row["_action"] = "insert_new"` | O |

#### 상단 요약

| 설계 항목 | 구현 (L452-467) | 일치 |
|----------|-----------------|------|
| 총 N건 (heading 폰트) | L452-453 | O |
| 신규 X건 (success 색상) | L454-455 | O |
| 중복 Y건 (danger 색상) | L456-458 | O |
| "모두 건너뛰기" 버튼 | L464-465 | O |
| "모두 덮어쓰기" 버튼 | L466-467 | O |
| 중복 없으면 일괄 버튼 미표시 | L460: `if dup_count:` | O |

#### Treeview

| 설계 항목 | 구현 (L469-497) | 일치 |
|----------|-----------------|------|
| 컬럼: 상태, 상호, 대표자, 사업자번호, 결제방법, 처리 | L473 | O |
| 컬럼 너비 | L475: `[70, 160, 90, 130, 100, 100]` | O |
| `configure_treeview_tags` 호출 | L479 | O |
| `dup` 태그: `#FFF3CD` | L480 | O |
| `new` 태그: `#D4EDDA` | L481 | O |
| 스크롤바 | L483-485 | O |
| 데이터 채우기 (태그별 상태/처리 텍스트) | L489-497 | O |

#### 중복 처리 UI

| 설계 항목 | 구현 (L499-525) | 일치 |
|----------|-----------------|------|
| LabelFrame "중복 업체 처리" | L501: `ttk.LabelFrame(..., text=" 중복 업체 처리 ")` | O |
| 설명 텍스트 | L504-506 | O |
| 건별 라디오: "건너뛰기" / "덮어쓰기(업데이트)" | L522-525 | O |
| 기본값 = "skip" | L519: `tk.StringVar(value="skip")` | O |
| 매칭 필드 표시 (사업자번호/상호) | L514-515 | O |
| `_update_action` 커맨드 | L523, L525: `command=lambda i=idx: self._update_action(i)` | O |

#### 하단 버튼

| 설계 항목 | 구현 (L527-532) | 일치 |
|----------|-----------------|------|
| "취소" 버튼 | L530 | O |
| "일괄 등록 실행" 버튼 (Primary 스타일) | L531-532 | O |

#### `_update_action` / `_set_all_action`

| 설계 항목 | 구현 (L534-545) | 일치 |
|----------|-----------------|------|
| `_update_action`: `_rows[idx]["_action"]` 갱신 | L536 | O |
| Treeview "처리" 컬럼 텍스트 갱신 | L538 | O |
| `_set_all_action`: 전체 `_dup_actions` 일괄 변경 | L540-545 | O |

#### `_execute`

| 설계 항목 | 구현 (L547-559) | 일치 |
|----------|-----------------|------|
| `repo.bulk_insert(self._rows)` 호출 | L548 | O |
| 결과 messagebox (신규/업데이트/건너뜀) | L549-555 | O |
| `self._on_save()` 콜백 | L557-558 | O |
| `self.destroy()` | L559 | O |

**결과: PASS**

---

## 3. Summary

| 검증 영역 | 항목 수 | Pass | Fail | Gap |
|----------|---------|------|------|-----|
| vendor_repo.find_by_business_no | 4 | 4 | 0 | 0 |
| vendor_repo.find_by_name | 4 | 4 | 0 | 0 |
| vendor_repo.bulk_insert | 11 | 11 | 0 | 0 |
| Import 구성 | 10 | 10 | 0 | 0 |
| UI 버튼 배치 | 4 | 4 | 0 | 0 |
| _download_template | 18 | 18 | 0 | 0 |
| _excel_upload | 12 | 12 | 0 | 0 |
| _on_bulk_save | 3 | 3 | 0 | 0 |
| BulkUploadPreviewDialog | 30 | 30 | 0 | 0 |
| **Total** | **96** | **96** | **0** | **0** |

### Match Rate: **100%**

설계 문서의 모든 항목이 구현에 정확히 반영되어 있으며, 누락/불일치 항목 없음.
