# 구매 조사 UX 개선 Planning Document

> **Summary**: (A) 기안폼 → 템플릿 즉시 등록 + (B) 품목 합계에 견적1/견적2 총금액 구분 표시
>
> **Project**: 구매기안 자동화 시스템 v1.0
> **Author**: CTO Lead Agent
> **Date**: 2026-03-11
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | (A) 기안 내용을 템플릿으로 저장하려면 탭 이동 후 수동 재입력 필요 / (B) 품목 합계에 견적1 총금액만 표시되어 견적2 금액 검증 불가 |
| **Solution** | (A) 기안폼에 "현재 내용 저장" 버튼 추가 / (B) 합계 영역을 "견적1: N원 / 견적2: N원" 형식으로 구분 표시 |
| **Function/UX Effect** | (A) 2클릭으로 템플릿 등록 / (B) 문서 생성 전 두 견적 금액을 한눈에 비교·검증 |
| **Core Value** | 작업 흐름 단절 없는 데이터 축적 + 견적 교차 검증으로 입력 실수 방지 |

---

## 1. Overview

### 1.1 Purpose

**(A) 기안폼 → 템플릿 저장**: 사용자가 기안폼에서 제목/내용/비고를 작성한 뒤(또는 문서 생성 후에도), 해당 내용을 기안 템플릿으로 바로 저장할 수 있게 한다. 현재는 기안 템플릿 탭으로 이동하여 수동 재입력해야 하므로 작업 흐름이 끊긴다.

**(B) 견적 총금액 구분 표시**: 품목 목록 하단의 합계 영역에서 현재 견적1 합계만 표시되어, 견적2 합계를 확인할 수 없다. 두 견적의 총금액을 라벨로 구분하여 나란히 표시하여, 문서 생성 전 교차 검증이 가능하게 한다.

### 1.2 Background

- 기안 템플릿 시스템(tab_draft_template.py)은 완전한 CRUD 기능을 갖추고 있음
- tab_purchase.py에서 "템플릿 적용"(불러오기)은 구현되었으나, 역방향(폼 → 템플릿 저장)은 없음
- 품목 합계 영역(`_build_items_section` line 362~370)에서 `_grand_total_var`(= 견적1 합계)만 표시 중
- 견적2 합계(`_v2_total_var`)는 내부적으로 계산되지만, UI에 별도 표시되지 않음
- 견적 비교 섹션의 각 프레임에는 합계금액이 있지만, 품목 목록과 떨어져 있어 스크롤 시 동시 확인 불가

### 1.3 Related Documents

- `ui/tab_purchase.py` — 기안폼, 품목 목록, 견적 비교
- `ui/tab_draft_template.py` — 기안 템플릿 탭 + DraftTemplateDialog
- `db/draft_template_repo.py` — CRUD
- `ui/base_dialog.py` — BaseDialog
- `ui/design_system.py` — COLORS, FONTS (total 색상/폰트 참조)

---

## 2. Scope

### 2.1 In Scope

**기능 A — 기안폼 → 템플릿 저장**:
- [x] tab_purchase.py 템플릿 영역에 "현재 내용 저장" 버튼 추가
- [x] 별칭 입력을 위한 경량 다이얼로그 생성
- [x] `{{품명}}` 역치환 옵션 (체크박스로 사용자 선택)
- [x] 저장 후 Combobox 목록 즉시 갱신
- [x] 중복 별칭 경고

**기능 B — 견적 총금액 구분 표시**:
- [x] 품목 합계 영역에 견적1/견적2 총금액 라벨 구분 표시
- [x] 최저가 견적 강조 (색상 구분)
- [x] 단독견적 모드에서 견적2 숨김 처리

### 2.2 Out of Scope

- 기존 DraftTemplateDialog UI 변경
- 기안 템플릿 탭의 CRUD 로직 수정
- 템플릿 수정/삭제 기능 (기존 탭에서 수행)
- draft_template_repo.py 스키마 변경
- 견적 비교 섹션 내부의 합계금액 Entry 변경 (기존 유지)

---

## 3. Requirements

### 3.1 Functional Requirements

**기능 A — 기안폼 → 템플릿 저장**:

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-A01 | 기안폼 템플릿 영역에 "현재 내용 저장" 버튼 배치 | High | Pending |
| FR-A02 | 버튼 클릭 시 별칭 입력 다이얼로그 표시 (제목/내용/비고는 현재 폼에서 자동 추출) | High | Pending |
| FR-A03 | `{{품명}}` 역치환 체크박스 제공 (첫 품목명 -> `{{품명}}`으로 되돌림) | Medium | Pending |
| FR-A04 | 저장 성공 후 Combobox 목록 즉시 갱신 + 저장된 항목 선택 상태로 전환 | High | Pending |
| FR-A05 | 중복 별칭 존재 시 덮어쓰기/취소 확인 다이얼로그 | Medium | Pending |
| FR-A06 | 기안 템플릿 탭에서도 새로 저장된 템플릿이 즉시 반영 | High | Pending |
| FR-A07 | 제목/내용이 모두 비어있으면 저장 불가 (최소 내용 필수) | High | Pending |

**기능 B — 견적 총금액 구분 표시**:

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-B01 | 품목 합계 영역에 견적1/견적2 총금액을 라벨로 구분하여 나란히 표시 | High | Pending |
| FR-B02 | 최저가 견적에 강조 색상(COLORS["total"]) 적용, 비교 견적은 일반 색상 | High | Pending |
| FR-B03 | 품목 단가 변경 시 두 합계 모두 실시간 갱신 | High | Pending |
| FR-B04 | 단독견적 모드 시 견적2 합계 숨김 또는 "-" 표시 | Medium | Pending |
| FR-B05 | 폼 초기화 시 양쪽 합계 모두 "0"으로 리셋 | High | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| UX | 저장까지 최대 2클릭 (버튼 -> 별칭 입력 후 저장) | 수동 검증 |
| Consistency | 기존 디자인 시스템(COLORS, SPACING, FONTS) 준수 | 코드 리뷰 |
| Stability | 기존 기능(템플릿 적용, 문서 생성, 폼 초기화) 무영향 | 수동 테스트 |

---

## 4. Design Specification

### Part A — 기안폼 → 템플릿 저장

### 4.1 UI Layout: 버튼 위치

템플릿 Combobox 옆, "템플릿 적용" 버튼 바로 오른쪽에 "현재 내용 저장" 버튼을 배치한다.

```
현재 (line 380~394):
┌─────────────────────────────────────────────────────────────────────┐
│ 템플릿: [ Combobox        ] [템플릿 적용]  ※ 기안 템플릿 탭에서 관리 │
└─────────────────────────────────────────────────────────────────────┘

변경 후:
┌────────────────────────────────────────────────────────────────────────────────┐
│ 템플릿: [ Combobox        ] [템플릿 적용] [현재 내용 저장]  ※ 기안 템플릿 ... │
└────────────────────────────────────────────────────────────────────────────────┘
```

**근거**: "적용"과 "저장"은 대칭 동작이므로 같은 행에 나란히 배치하는 것이 직관적이다.

### 4.2 경량 별칭 입력 다이얼로그

기존 `DraftTemplateDialog`를 재사용하지 않는다. 이유:
- DraftTemplateDialog는 제목/내용/비고를 모두 직접 입력하는 4필드 폼
- 이 기능에서는 제목/내용/비고가 이미 채워져 있으므로, 별칭만 입력받으면 됨
- 불필요한 필드를 보여주면 혼란 유발

대신 `SaveAsTemplateDialog`를 새로 만든다 (BaseDialog 상속):

```
┌─ 템플릿으로 저장 ──────────────────────────────────────┐
│                                                         │
│  별칭 *:  [ 예: 소모품 구매              ]              │
│                                                         │
│  ┌─ 저장될 내용 (미리보기) ───────────────────────────┐ │
│  │ 기안제목: USB 허브 구매 기안                        │ │
│  │ 내용:    USB 허브 구매에 관하여 아래와 같이...     │ │
│  │ 비고:    전산팀 요청                               │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  [v] 품목명을 {{품명}}으로 치환 (범용 템플릿)           │
│                                                         │
│                           [취소]  [저장]                 │
└─────────────────────────────────────────────────────────┘
```

### 4.3 `{{품명}}` 역치환 로직

현재 `_load_draft_template`에서 `{{품명}}`을 첫 품목명으로 치환한다. 저장 시에는 그 반대:

```python
first_name = self._item_rows[0].item_name_var.get().strip()
if reverse_placeholder and first_name:
    title = title.replace(first_name, "{{품명}}")
    content = content.replace(first_name, "{{품명}}")
```

체크박스 기본값: **ON** (범용 템플릿이 더 유용한 경우가 많음)

### 4.4 중복 별칭 처리 (FR-05)

```python
existing = [r for r in self._template_records if r["label"] == label]
if existing:
    if messagebox.askyesno("중복 확인",
        f"'{label}' 별칭이 이미 존재합니다.\n덮어쓰시겠습니까?"):
        tpl_repo.update(existing[0]["id"], label, title, content, remark)
    else:
        return  # 취소
else:
    tpl_repo.insert(label, title, content, remark)
```

### 4.5 데이터 동기화

저장 후 실행할 작업:
1. `self._template_records` 재조회 (`tpl_repo.select_all()`)
2. `self._template_combo["values"]` 갱신
3. `self._template_var.set(label)` -- 방금 저장한 템플릿 선택
4. 기안 템플릿 탭이 열려 있다면 해당 탭도 `refresh()` 호출 필요
   - `self.master`(Notebook) -> 탭 참조로 `tab_draft_template.refresh()` 호출

---

### Part B — 견적 총금액 구분 표시

### 4.6 현재 상태 분석

현재 품목 합계 영역 (`_build_items_section`, line 362~370):
```
┌──────────────────────────────────────────────────────┐
│ [+ 품목 추가]                      합  계: 1,500,000원│
└──────────────────────────────────────────────────────┘
```

- `_grand_total_var`만 표시 (= 견적1 합계 = `_v1_total_var`)
- `_v2_total_var`는 `_update_grand_total()`에서 계산되지만 이 영역에 표시 안 됨
- 견적 비교 섹션의 각 프레임에 합계금액 Entry가 있으나, 스크롤 시 품목 목록과 동시 확인 불가

### 4.7 변경 후 UI 디자인

```
┌──────────────────────────────────────────────────────────────────────┐
│ [+ 품목 추가]         견적1 합계: 1,500,000원  견적2 합계: 1,650,000원│
└──────────────────────────────────────────────────────────────────────┘
```

**디자인 규칙**:
- 견적1/견적2 라벨로 명확히 구분
- 최저가 견적: `COLORS["total"]` (#003A70) + `FONTS["total"]` (11pt bold) — 기존과 동일
- 비교 견적: `COLORS["text_secondary"]` — 눈에 보이지만 강조되지 않음
- `_update_grand_total()`에서 비교 후 동적 색상 적용
- 단독견적 모드: 견적2 라벨을 `-`로 표시하거나 숨김

### 4.8 구현 방법

현재 코드 (line 362~370):
```python
bottom = ttk.Frame(items_frame)
bottom.pack(fill="x", pady=(SPACING["sm"], 0))
ttk.Button(bottom, text="+ 품목 추가", style="Primary.TButton",
           command=self._add_item_row).pack(side="left")
ttk.Label(bottom, text="합  계:").pack(side="right", padx=(0, SPACING["sm"]))
ttk.Label(bottom, textvariable=self._grand_total_var,
          foreground=COLORS["total"], font=FONTS["heading"]).pack(side="right")
ttk.Label(bottom, text="원").pack(side="right", padx=(0, SPACING["sm"]))
```

변경 후:
```python
bottom = ttk.Frame(items_frame)
bottom.pack(fill="x", pady=(SPACING["sm"], 0))
ttk.Button(bottom, text="+ 품목 추가", style="Primary.TButton",
           command=self._add_item_row).pack(side="left")

# 견적2 합계 (오른쪽부터 역순 pack)
ttk.Label(bottom, text="원").pack(side="right", padx=(0, SPACING["sm"]))
self._v2_total_label = ttk.Label(bottom, textvariable=self._v2_total_var,
    foreground=COLORS["text_secondary"], font=FONTS["heading"])
self._v2_total_label.pack(side="right")
self._v2_total_prefix = ttk.Label(bottom, text="견적2 합계:")
self._v2_total_prefix.pack(side="right", padx=(SPACING["lg"], SPACING["sm"]))

# 견적1 합계
ttk.Label(bottom, text="원").pack(side="right", padx=(0, SPACING["sm"]))
self._v1_total_label = ttk.Label(bottom, textvariable=self._v1_total_var,
    foreground=COLORS["total"], font=FONTS["heading"])
self._v1_total_label.pack(side="right")
ttk.Label(bottom, text="견적1 합계:").pack(side="right", padx=(0, SPACING["sm"]))
```

### 4.9 `_update_grand_total()` 색상 동적 적용

```python
def _update_grand_total(self):
    v1_total = sum(row.get_total() for row in self._item_rows)
    v2_total = sum(row.get_v2_total() for row in self._item_rows)
    self._grand_total_var.set(f"{v1_total:,}")
    self._v1_total_var.set(f"{v1_total:,}")
    self._v2_total_var.set(f"{v2_total:,}")

    # 최저가 강조 색상 적용
    if v1_total > 0 and v2_total > 0:
        if v1_total <= v2_total:
            self._v1_total_label.config(foreground=COLORS["total"])
            self._v2_total_label.config(foreground=COLORS["text_secondary"])
        else:
            self._v1_total_label.config(foreground=COLORS["text_secondary"])
            self._v2_total_label.config(foreground=COLORS["total"])

    self._update_price_info()
```

### 4.10 단독견적 모드 처리

`_on_sole_toggle()` 에서 견적2 위젯 숨김/표시:
```python
def _on_sole_toggle(self):
    sole = self._sole_quote_var.get()
    # ... 기존 로직 ...
    # 견적2 합계 숨김/표시
    if hasattr(self, '_v2_total_label'):
        if sole:
            self._v2_total_label.pack_forget()
            self._v2_total_prefix.pack_forget()
        else:
            # 원래 위치에 다시 pack (역순이므로 주의)
            # pack_forget 후 재배치보다 state 변경이 안전
            self._v2_total_prefix.config(text="" if sole else "견적2 합계:")
            self._v2_total_label.config(text="" if sole else self._v2_total_var.get())
```

---

## 5. Implementation Plan

### 5.1 변경 파일 목록

| File | Change Type | Description |
|------|-------------|-------------|
| `ui/tab_purchase.py` | Modify | (A) 버튼 추가 + `_save_as_template()` + `SaveAsTemplateDialog` / (B) 합계 영역 견적1/2 구분 표시 + 색상 동적 적용 |
| `db/draft_template_repo.py` | Modify | `select_by_label(label)` 조회 함수 추가 (중복 검사용) |

**변경하지 않는 파일**: `base_dialog.py`, `tab_draft_template.py`, `design_system.py`, DB 스키마

### 5.2 File-by-File Implementation

#### 5.2.1 `db/draft_template_repo.py` -- `select_by_label()` 추가

```python
def select_by_label(label: str) -> dict | None:
    """별칭으로 템플릿 조회 (중복 검사용)"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM draft_templates WHERE label = ?", (label,)
        ).fetchone()
        return dict(row) if row else None
```

#### 5.2.2 `ui/tab_purchase.py` -- SaveAsTemplateDialog 클래스

tab_purchase.py 파일 하단(PurchaseTab 클래스 밖, 또는 내부 중첩)에 경량 다이얼로그를 추가한다. BaseDialog를 상속한다.

```python
class SaveAsTemplateDialog(BaseDialog):
    """기안폼 현재 내용을 템플릿으로 저장하는 경량 다이얼로그"""

    def __init__(self, parent, *, title_text: str, content_text: str,
                 remark_text: str, first_item_name: str = "",
                 on_save=None):
        self._title_text = title_text
        self._content_text_val = content_text
        self._remark_text = remark_text
        self._first_item_name = first_item_name
        self._label_var = tk.StringVar()
        self._reverse_var = tk.BooleanVar(value=bool(first_item_name))
        super().__init__(parent, "템플릿으로 저장", on_save=on_save)

    def _build_content(self, f: ttk.Frame):
        # 별칭 입력
        ttk.Label(f, text="별칭 *:").grid(
            row=0, column=0, sticky="w",
            pady=SPACING["sm"], padx=(0, SPACING["md"]))
        entry = ttk.Entry(f, textvariable=self._label_var, width=30)
        entry.grid(row=0, column=1, sticky="ew", pady=SPACING["sm"])
        entry.focus_set()

        # 미리보기
        preview = ttk.LabelFrame(f, text=" 저장될 내용 ", padding=SPACING["sm"])
        preview.grid(row=1, column=0, columnspan=2, sticky="ew",
                     pady=SPACING["sm"])
        ttk.Label(preview, text=f"기안제목: {self._title_text[:60]}",
                  wraplength=350).pack(anchor="w")
        content_preview = self._content_text_val[:80].replace("\n", " ")
        if len(self._content_text_val) > 80:
            content_preview += "..."
        ttk.Label(preview, text=f"내용: {content_preview}",
                  wraplength=350).pack(anchor="w")
        if self._remark_text:
            ttk.Label(preview, text=f"비고: {self._remark_text}",
                      wraplength=350).pack(anchor="w")

        # 역치환 체크박스
        if self._first_item_name:
            ttk.Checkbutton(
                f, text=f"'{self._first_item_name}' -> {{{{품명}}}}으로 치환",
                variable=self._reverse_var
            ).grid(row=2, column=0, columnspan=2, sticky="w",
                   pady=(SPACING["sm"], 0))

        f.columnconfigure(1, weight=1)

    def _on_save(self):
        label = self._label_var.get().strip()
        if not label:
            messagebox.showwarning("입력 오류", "별칭을 입력하세요.", parent=self)
            return

        title = self._title_text
        content = self._content_text_val
        remark = self._remark_text

        # 역치환
        if self._reverse_var.get() and self._first_item_name:
            title = title.replace(self._first_item_name, "{{품명}}")
            content = content.replace(self._first_item_name, "{{품명}}")

        # 중복 검사
        existing = tpl_repo.select_by_label(label)
        if existing:
            if not messagebox.askyesno("중복 확인",
                    f"'{label}' 별칭이 이미 존재합니다.\n덮어쓰시겠습니까?",
                    parent=self):
                return
            tpl_repo.update(existing["id"], label, title, content, remark)
        else:
            tpl_repo.insert(label, title, content, remark)

        self._fire_save_callback()
        self.destroy()
```

#### 5.2.3 `ui/tab_purchase.py` -- PurchaseTab 변경

**A. `_build_draft_section()` 버튼 추가** (line 391 근처)

현재:
```python
ttk.Button(tpl_frame, text="템플릿 적용",
           command=self._load_draft_template).pack(side="left", padx=(0, SPACING["md"]))
ttk.Label(tpl_frame, text="※ 기안 템플릿 탭에서 관리",
          foreground=COLORS["text_muted"]).pack(side="left")
```

변경:
```python
ttk.Button(tpl_frame, text="템플릿 적용",
           command=self._load_draft_template).pack(side="left", padx=(0, SPACING["sm"]))
ttk.Button(tpl_frame, text="현재 내용 저장",
           command=self._save_as_template).pack(side="left", padx=(0, SPACING["md"]))
ttk.Label(tpl_frame, text="※ 기안 템플릿 탭에서 관리",
          foreground=COLORS["text_muted"]).pack(side="left")
```

**B. `_save_as_template()` 메서드 추가** (PurchaseTab 클래스 내, `_load_draft_template` 아래)

```python
def _save_as_template(self):
    """현재 기안폼 내용을 템플릿으로 저장"""
    content = self._draft_content_text.get("1.0", "end-1c").strip()
    if not content:
        messagebox.showwarning("저장 불가", "기안 내용이 비어있습니다.\n내용을 입력한 후 저장하세요.")
        return

    title = self._draft_title_var.get().strip()
    remark = self._draft_remark_var.get().strip()
    first_name = (self._item_rows[0].item_name_var.get().strip()
                  if self._item_rows else "")

    def on_saved():
        # Combobox 갱신
        self._template_records = tpl_repo.select_all()
        tpl_labels = ["(선택안함)"] + [r["label"] for r in self._template_records]
        self._template_combo["values"] = tpl_labels
        self.status_var.set("기안 템플릿 저장 완료")

        # 기안 템플릿 탭 동기화
        try:
            notebook = self.master
            for tab_id in notebook.tabs():
                tab_widget = notebook.nametowidget(tab_id)
                if hasattr(tab_widget, 'refresh') and type(tab_widget).__name__ == 'DraftTemplateTab':
                    tab_widget.refresh()
                    break
        except Exception:
            pass  # 탭이 없어도 무방

    SaveAsTemplateDialog(
        self,
        title_text=title,
        content_text=content,
        remark_text=remark,
        first_item_name=first_name,
        on_save=on_saved,
    )
```

---

## 6. UX Flow

### 6.1 기능 A — 템플릿 저장 Happy Path

```
1. 사용자가 기안폼에서 제목/내용/비고 작성
2. "현재 내용 저장" 버튼 클릭
3. 다이얼로그: 미리보기 확인 + 별칭 입력 + 역치환 체크
4. "저장" 클릭
5. Combobox 갱신 + 상태바 "기안 템플릿 저장 완료"
```

총 클릭: **2회** (버튼 + 저장)

### 6.2 기능 B — 견적 총금액 확인 흐름

```
1. 사용자가 품목 입력 (단가/수량)
2. 견적1 합계와 견적2 합계가 실시간으로 업데이트
3. 최저가 견적이 진한 색(#003A70)으로 강조, 비교 견적은 연한 색
4. 사용자는 스크롤 없이 품목 바로 아래에서 두 견적 금액을 비교·검증
5. 문서 생성 전 최종 확인
```

### 6.3 Edge Cases

| Case | Behavior |
|------|----------|
| 내용 비어있음 (A) | "저장 불가" 경고, 다이얼로그 열지 않음 |
| 별칭 비어있음 (A) | 다이얼로그 내 "별칭을 입력하세요" 경고 |
| 별칭 중복 (A) | "덮어쓰시겠습니까?" 확인 -> Yes: update / No: 취소 |
| 품목명 비어있음 (A) | 역치환 체크박스 숨김 |
| 문서 생성 후 (A) | 동일하게 동작 (폼 값 유지) |
| 폼 초기화 후 (A) | 내용 비어있으므로 "저장 불가" 경고 |
| 견적2 단가 미입력 (B) | 견적2 합계 "0" 표시, 색상 미강조 |
| 단독견적 모드 (B) | 견적2 합계 영역 숨김 |
| 동일 금액 (B) | 견적1에 강조 색상 (기존 자동선택 규칙 동일) |

---

## 7. Risks and Mitigation

| Risk | Feature | Impact | Likelihood | Mitigation |
|------|---------|--------|------------|------------|
| 기존 "템플릿 적용" 기능에 영향 | A | Medium | Low | 독립된 메서드/다이얼로그로 분리, 기존 코드 수정 최소화 |
| 기안 템플릿 탭 동기화 실패 | A | Low | Medium | try/except로 감싸고, 탭이 없어도 Combobox는 정상 갱신 |
| 역치환 시 의도치 않은 문자열 치환 | A | Medium | Low | 미리보기로 확인 유도 |
| pack 순서 변경으로 레이아웃 깨짐 | B | Medium | Medium | side="right" 역순 pack은 기존 패턴과 동일, 테스트 필수 |
| 폼 초기화 시 색상 미리셋 | B | Low | Low | `_reset_form()`에서 색상도 초기화 |
| 단독견적 toggle 시 위젯 깨짐 | B | Medium | Low | pack_forget 대신 text="" 방식으로 안전하게 처리 |

---

## 8. Success Criteria

### 8.1 Definition of Done — 기능 A

- [ ] "현재 내용 저장" 버튼이 기안폼에 정상 표시
- [ ] 별칭 입력 후 DB에 템플릿 저장 확인
- [ ] Combobox에 즉시 반영
- [ ] 기안 템플릿 탭에서도 반영
- [ ] 역치환 체크박스 동작 확인
- [ ] 중복 별칭 덮어쓰기 동작 확인
- [ ] 내용 비어있을 때 저장 차단 확인

### 8.2 Definition of Done — 기능 B

- [ ] 품목 합계 영역에 "견적1 합계: N원  견적2 합계: N원" 표시
- [ ] 최저가 견적이 진한 색(#003A70)으로 강조
- [ ] 품목 단가 변경 시 실시간 갱신
- [ ] 단독견적 모드에서 견적2 영역 숨김
- [ ] 폼 초기화 시 양쪽 모두 "0" + 기본 색상 리셋

### 8.3 Quality Criteria

- [ ] 기존 기능 (템플릿 적용, 문서 생성, 폼 초기화) 회귀 없음
- [ ] 디자인 시스템 (COLORS, SPACING, FONTS) 준수
- [ ] BaseDialog 패턴 준수

---

## 9. Next Steps

1. [ ] Design 문서 작성 (필요 시 -- 이 Plan이 충분히 상세하므로 생략 가능)
2. [ ] 구현 (Do 단계)
3. [ ] 수동 테스트 (Check 단계)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-11 | Initial draft — 기능 A (템플릿 저장) | CTO Lead Agent |
| 0.2 | 2026-03-11 | 기능 B (견적 총금액 구분 표시) 추가 | CTO Lead Agent |
