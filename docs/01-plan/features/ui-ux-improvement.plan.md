# UI/UX 및 구매조사 입력 프로세스 개선 계획 v2

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | 구매조사 탭(829줄)에 56+개 위젯 밀집, 3단계 연속 다이얼로그(기안제목→Yes/No→DraftDialog), 구매목적 필드 활용성 없음, 견적2 단가/수량 검증 누락, _reset_form 타이밍 오류(C-3), 중복 코드 산재 |
| **Solution** | 구매목적 제거, DraftDialog 전체 기능을 구매조사 탭에 통합(0 다이얼로그), 유효성 검사 강화, 기안서 섹션 접기/펼치기, 동적 버튼 텍스트 |
| **Function/UX Effect** | 문서 생성 클릭 5회→1회(80% 감소), 다이얼로그 3개→0개, 검증 누락 0개, C-3 버그 구조적 해결, dialog_draft.py 236줄 삭제 |
| **Core Value** | 원스톱 문서 생성으로 담당자 업무 부담 경감, 공공기관 구매 결재 문서의 정확성·신뢰성 향상 |

---

## CTO 팀 구성

| # | 역할 | 담당 영역 |
|---|------|----------|
| 1 | CTO / Tech Lead | 전체 아키텍처, 우선순위 결정, 리스크 관리 |
| 2 | UI/UX 아키텍트 | 탭 레이아웃, 사용자 동선, 위젯 구성, ASCII 목업 |
| 3 | 프로세스 분석가 (PM) | 입력 프로세스 플로우, 유효성 검사, 비즈니스 로직 |
| 4 | QA / 코드 분석가 | 중복 코드, purpose 참조 전수 조사, 영향 범위 분석 |
| 5 | 보안 전문가 | 부분 저장 위험, HWP COM iconify, 데이터 무결성 |
| 6 | 디자인 시스템 전문가 | 접기/펼치기, 동적 버튼, LabelFrame 일관성 |

---

## 1. 현황 분석

### 1.1 탭별 복잡도

| 탭 | 클래스 | 코드 라인 | 위젯 수 | 복잡도 |
|---|---|---|---|---|
| 구매 조사 | PurchaseTab + ItemRow + _TitleInputDialog | ~829줄 | 56+ | 매우 높음 |
| 검수 입력 | InspectionTab | 395줄 | 25 | 중간 |
| 이력 조회 | HistoryTab | 419줄 | 30 | 중간 |
| 업체 관리 | VendorTab + Dialog | 199줄 | 20 | 낮음 |
| 수의계약 | SoleContractTab + Dialog | 154줄 | 10 | 낮음 |
| 기안서 다이얼로그 | DraftDialog | 236줄 | 25 | 중간 |
| **합계** | | **~2,232줄** | **~166** | |

### 1.2 현재 문서 생성 동선 (최소 15~20회 조작, 다이얼로그 5회 클릭)

```
구매목적 입력 → 품목 입력(품명/규격/수량/단가) → VAT 선택
→ 사이트 조사(브라우저) → 견적1 입력(업체명/URL/스크린샷)
→ 견적2 동일 반복 → 최저가 확인
→ [산출기초조사서 생성] 클릭
→ 기안제목 다이얼로그(1차) → [확인] 클릭
→ "기안서도 생성?" YesNo(2차) → [예] 클릭
→ DraftDialog(3차) → 내용입력 → 업체선택 → [기안서 생성] 클릭
```

**핵심 병목:**
1. 연속 3개 다이얼로그가 작업 흐름을 단절시킴
2. 구매목적 필드가 어떤 문서에도 사용되지 않음 (HWP에 {{PURPOSE}} 미사용)
3. DraftDialog에서 입력하는 정보(내용/업체)가 구매조사와 분리되어 비효율

---

## 2. 발견된 문제점 (우선순위별)

### 2.1 Critical — 즉시 수정

| ID | 문제 | 위치 | 영향 | 통합 시 |
|----|------|------|------|---------|
| C-1 | **수량 0/음수 입력 허용** | `_validate()` 수량 검사 없음 | 금액 0원 문서 생성 | 여전히 필요 |
| C-2 | **견적2 단가 0 검사 없음** | `_validate()` 견적2 단가 미검사 | 산출기초조사서에 견적2 전체 0원 | 여전히 필요 |
| C-3 | **_reset_form 타이밍 오류** | `_generate_documents():761` | 기안서 오류 시 폼 데이터 이미 삭제, `_vendor_records`가 `[None, None]`으로 초기화 | **통합으로 구조적 해결** |
| C-4 | **동일 업체 검증 부재** | `_validate()` | 견적1=견적2 동일 업체로 문서 생성 | **이미 수정 완료** |
| C-5 | **구매목적 필드 무용** | `tab_purchase.py:207` | HWP에 미사용, 사용자 입력 낭비 | **삭제** |

### 2.2 Medium — 개선 필요

| ID | 문제 | 위치 | 영향 | 통합 시 |
|----|------|------|------|---------|
| M-1 | **단독견적 전환 시 스크린샷 잔존** | `_on_sole_toggle():573` | 불필요한 파일 포함 | 여전히 필요 |
| M-2 | **_reset_form에서 단독견적 미초기화** | `_reset_form():494` | 이전 상태 잔존 | 여전히 필요 |
| M-3 | **vendor_records 미선택 시 연동 실패** | `_generate_documents():765` | 직접 타이핑 시 업체 자동연동 안됨 | **통합으로 해결** |
| M-4 | **동점 메시지 "0원 저렴"** | `_update_price_info()` | 혼란 유발 | 여전히 필요 |
| M-5 | **이력 조회 문서 버튼 항상 활성** | `tab_history.py` | 없는 문서 클릭 → 경고만 | 여전히 필요 |

### 2.3 Low — 기회 개선

| ID | 문제 | 위치 |
|----|------|------|
| L-1 | 전체캡처 시 앱 창 미최소화 | screenshot.py |
| L-2 | VendorQuote.unit_price 중복 할당 | _build_purchase_data() |
| L-3 | 검색 키워드 라디오 _reset_form 미초기화 | _reset_form() |
| L-4 | 수의계약 사유 Entry → Text 변경 필요 | SoleContractDialog |

---

## 3. purpose 필드 제거 영향 분석 (전수 조사)

### 3.1 참조 파일 전체 목록

| # | 파일 | 라인 | 용도 | 작업 |
|---|------|------|------|------|
| 1 | `core/models.py:37` | `purpose: str = ""` | 데이터 모델 | 필드 삭제 |
| 2 | `db/database.py:44` | `purpose TEXT NOT NULL` | DB 스키마 | `DEFAULT ''`로 마이그레이션 |
| 3 | `db/purchase_repo.py:9,14,21` | INSERT SQL | DB 저장 | SQL에서 purpose 제거 |
| 4 | `ui/tab_purchase.py:207` | `_purpose_var` 위젯 | UI 입력 | 위젯 삭제 |
| 5 | `ui/tab_purchase.py:495` | `_purpose_var.set("")` | 폼 초기화 | 삭제 |
| 6 | `ui/tab_purchase.py:588` | `_purpose_var.set(...)` | 이력 불러오기 | 삭제 |
| 7 | `ui/tab_purchase.py:622-624` | `if not _purpose_var...` | 유효성 검사 | 블록 삭제 |
| 8 | `ui/tab_purchase.py:673` | `purpose=...` | PurchaseData 생성 | 인자 제거 |
| 9 | `ui/tab_history.py:37` | `_chk_purp` 체크박스 | 검색 대상 | 삭제 |
| 10 | `ui/tab_history.py:76,81` | Treeview "구매목적" 컬럼 | 목록 표시 | 컬럼 제거 |
| 11 | `ui/tab_history.py:114` | 힌트 텍스트 | 안내 | 수정 |
| 12 | `ui/tab_history.py:123,127` | `_dpurpose` StringVar | 상세 패널 | 위젯 삭제 |
| 13 | `ui/tab_history.py:218` | 검색 필터 | 검색 | 삭제 |
| 14 | `ui/tab_history.py:243` | `r.get("purpose")` | Treeview 값 | 삭제 |
| 15 | `ui/tab_history.py:273` | `_dpurpose.set(...)` | 상세 패널 갱신 | 삭제 |
| 16 | `ui/tab_inspection.py:44` | Treeview "구매목적" 컬럼 | 목록 표시 | 컬럼 제거 |
| 17 | `ui/tab_inspection.py:138` | `"purpose"` 검색 필터 | 검색 | 삭제 |
| 18 | `ui/tab_inspection.py:145` | `p.get("purpose")` | Treeview 값 | 삭제 |
| 19 | `ui/tab_inspection.py:357` | `purpose=p["purpose"]` | InspectionData 생성 | 삭제 |
| 20 | `documents/templates/README.md:21` | `{{PURPOSE}}` 문서 | 문서 | 행 삭제 |
| 21 | `ui/tab_manual.py` | purpose 참조 | 구버전 미사용 | 파일 삭제 |
| 22 | `ui/tab_auto.py` | purpose 참조 | 구버전 미사용 | 파일 삭제 |

### 3.2 HWP 템플릿 영향

**결론: HWP 수정 불필요**
- `hwp_generator.py`의 `generate_calculation()`과 `generate_draft()` 모두 `{{PURPOSE}}` 자리표시자를 사용하지 않음
- `templates/README.md`에만 문서화되어 있을 뿐 실제 코드에서 미사용

### 3.3 DB 마이그레이션

```python
# database.py의 _migrate()에 추가:
# 1) 기존 DB: purpose 컬럼 유지 (데이터 보존), INSERT 시 "" 전달
# 2) 신규 DB: purpose TEXT DEFAULT '' (NOT NULL 제거)
```

- SQLite는 `NOT NULL` 제약을 ALTER로 변경 불가
- INSERT SQL에서 purpose에 `""` 전달하면 NOT NULL 제약 통과
- 기존 데이터는 DB에 그대로 보존, UI에서만 미표시

---

## 4. DraftDialog 통합 설계

### 4.1 통합 대상 필드 (DraftDialog → PurchaseTab)

| # | DraftDialog 필드 | 위치 (dialog_draft.py) | 타입 | PurchaseTab 목표 위치 |
|---|-----------------|----------------------|------|---------------------|
| 1 | 제목 (기안제목) | 42-44행 | `StringVar + Entry` | **A. 구매 정보** 섹션 |
| 2 | 내용 | 47-49행 | `Text(height=4)` | **F. 기안서 정보** 섹션 |
| 3 | 비고 | 52-55행 | `StringVar + Entry` | **F. 기안서 정보** 섹션 |
| 4 | 구매방법 포함 | 65-67행 | `BooleanVar + Checkbutton` | **F. 기안서 정보** > 포함항목 |
| 5 | 수의계약 사유 포함 + 콤보 | 70-81행 | `BooleanVar + Checkbutton + Combobox` | **F. 기안서 정보** > 포함항목 |
| 6 | 구매업체 선택 | 84-89행 | `StringVar + Combobox(readonly)` | **F. 기안서 정보** > 구매업체 |
| 7 | 신규 등록 버튼 | 92-93행 | `Button → VendorDialog` | **F. 기안서 정보** > 구매업체 |
| 8 | 업체 정보 표시 | 104-121행 | `4개 Label (자동채움)` | **F. 기안서 정보** > 구매업체 |
| 9 | 기안서 동시 생성 | messagebox.askyesno (763행) | 다이얼로그 | **E. 최저가 선택** 또는 **F** 상단 체크박스 |

### 4.2 신규 탭 섹션 레이아웃 (위 → 아래)

| 순서 | LabelFrame | 내용 | 변경사항 |
|------|-----------|------|---------|
| **A** | `구매 정보` | 기안제목, 부서명, VAT | 구매목적 삭제, 기안제목·VAT 추가 |
| **B** | `사이트 바로가기` | 검색키워드, 사이트 버튼 | 변경 없음 |
| **C** | `품목 목록` | 품목 그리드, 합계 | VAT를 A로 이동 |
| **D** | `견적 1` / `견적 2` | 구매처, URL, 스크린샷 | 변경 없음 |
| **E** | `최저가 선택` | 라디오, 단독견적, **기안서 동시생성** 체크 | 체크박스 1개 추가 |
| **F** | `기안서 정보` (**신규, 접기/펼치기**) | 내용, 비고, 포함항목, 구매업체+정보 | DraftDialog 전체 이전 |
| **G** | 액션 영역 | 입력초기화, **문서 생성** (동적 텍스트) | 버튼명 동적 변경 |

### 4.3 ASCII 목업 — 최종 설계

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║ ┌─ 구매 정보 ───────────────────────────────────────────────────────────────┐║
║ │  기안제목: [_________________________ (폴더명으로 사용) ________________] ║
║ │  부서명:   [_______________________________]                              ║
║ │  VAT:      (●) 없음   ( ) VAT 별도 (입력가×1.1)   ( ) VAT 포함          ║
║ └───────────────────────────────────────────────────────────────────────────┘║
║                                                                             ║
║ ┌─ 사이트 바로가기 ─────────────────────────────────────────────────────────┐║
║ │  검색 키워드: (●) 첫 번째 품명  ( ) 규격/사양   → 검색어: USB허브        ║
║ │  [네이버쇼핑] [쿠팡] [롯데온] [G마켓] [옥션] [S2B]                       ║
║ └───────────────────────────────────────────────────────────────────────────┘║
║                                                                             ║
║ ┌─ 품목 목록 ───────────────────────────────────────────────────────────────┐║
║ │  # │ 품명(필수)│ 규격│ 단위│ 수량│ 견적1단가│ 견적1금액│ 견적2단가│ …│- ║
║ │  1 │ USB허브   │7포트│ 개  │  2  │ 15,000  │ 30,000  │ 16,000  │ …│- ║
║ │  2 │ 마우스    │무선 │ 개  │  5  │  8,000  │ 40,000  │  9,000  │ …│- ║
║ │ [+ 품목 추가]                                     합  계: 70,000 원     ║
║ └───────────────────────────────────────────────────────────────────────────┘║
║                                                                             ║
║ ┌─ 견적 1 ─────────────────────┐  ┌─ 견적 2 ─────────────────────┐        ║
║ │ 구매처명: [▼ 쿠팡 주식회사  ]│  │ 구매처명: [▼ 네이버파이낸셜 ]│        ║
║ │ 합계금액: [70,000] ※자동합산 │  │ 합계금액: [78,000] ※자동합산 │        ║
║ │ URL:      [https://...]      │  │ URL:      [https://...]      │        ║
║ │ 스크린샷: 견적1_쿠팡.png  ✓  │  │ 스크린샷: 없음               │        ║
║ │ [파일선택] [전체캡처] [구역캡처] [초기화]│ │ [파일선택] [전체캡처] …│        ║
║ └──────────────────────────────┘  └──────────────────────────────┘        ║
║                                                                             ║
║ ┌─ 최저가 선택 ─────────────────────────────────────────────────────────────┐║
║ │ (●) 견적 1 선택  ( ) 견적 2 선택   견적1이 8,000원 저렴 (자동 선택)      ║
║ │ ☐ 단독견적 (견적2 없음, 산출조사서 미생성)                                ║
║ │ ☑ 기안서 동시 생성                                                        ║
║ └───────────────────────────────────────────────────────────────────────────┘║
║                                                                             ║
║ ┌─ 기안서 정보 ─── (☑ 기안서 동시 생성 시에만 표시) ────────────────────────┐║
║ │ 내용 *:  ┌─────────────────────────────────────────────────────┐         ║
║ │          │ USB허브 7포트 2개, 무선마우스 5개를 구매하고자      │         ║
║ │          │ 합니다.                                             │         ║
║ │          └─────────────────────────────────────────────────────┘         ║
║ │ 비고:    [________________________]                                       ║
║ │                                                                           ║
║ │ ┌ 포함 항목 선택 ───────────────────────────────────────────────┐         ║
║ │ │ ☑ 구매방법 포함   ☑ 수의계약 사유 포함  [▼ 2천만원이하 수의…]│         ║
║ │ └───────────────────────────────────────────────────────────────┘         ║
║ │                                                                           ║
║ │ 구매업체 *: [▼ 쿠팡 주식회사______] [신규 등록]                           ║
║ │ ┌ 업체 정보 (자동 입력) ────────────────────────────────────────┐         ║
║ │ │ 대표자:     강한승                                            │         ║
║ │ │ 사업자번호: 120-88-00767                                      │         ║
║ │ │ 주소:       서울시 송파구 송파대로 570                         │         ║
║ │ │ 결제방법:   법인카드사용                                       │         ║
║ │ └───────────────────────────────────────────────────────────────┘         ║
║ └───────────────────────────────────────────────────────────────────────────┘║
║                                                                             ║
║  [입력 초기화]                                [  산출기초조사서 + 기안서 생성  ] ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### 4.4 기안서 섹션 접기/펼치기 동작

| "기안서 동시 생성" | 기안서 정보 섹션 | 필수 검증 | 버튼 텍스트 |
|-------------------|-----------------|-----------|-----------|
| **해제** (기본) | `pack_forget()` 숨김 | 내용/업체 건너뜀 | "산출기초조사서 생성" |
| **체크** | `pack()` 표시 + 자동 스크롤 | 내용 필수, 업체 필수 | "산출기초조사서 + 기안서 생성" |
| **단독견적** | 상태 무관 | 해당 시 산출 미생성 | "저장" 또는 "기안서 생성" |

구현 방식:
```python
def _on_draft_toggle(self):
    if self._draft_check_var.get():
        self._draft_frame.pack(fill="x", pady=(0, 6), before=self._action_frame)
        self._sole_records = scr_repo.select_all()  # 최신 수의계약 사유 로드
        self.refresh_vendors()                        # 최신 업체 목록 로드
        # 최저가 업체 자동 선택
        sel = self._selected_var.get()
        vr = self._vendor_records[sel - 1]
        if vr:
            self._draft_vendor_var.set(vr["name"])
            self._on_draft_vendor_select()
    else:
        self._draft_frame.pack_forget()
    self._update_gen_btn_text()
```

### 4.5 기안제목 자동 생성

```python
# 첫 번째 품명 변경 시 기안제목 기본값 자동 채움
def _auto_fill_title(self, *_):
    if not self._title_edited_by_user:
        name = self._item_rows[0].item_name_var.get().strip() if self._item_rows else ""
        if name:
            self._draft_title_var.set(f"{name} 구매 기안")
```

- 사용자가 직접 기안제목을 수정하면 `_title_edited_by_user = True`로 자동채움 중단
- 폴더명으로 사용되므로 파일시스템 금지 문자(`/ \ : * ? " < > |`) 자동 치환

### 4.6 구매업체 자동 연동

```
견적 Combobox 선택 → _vendor_records[slot] 저장 (기존 로직)
최저가 선택 변경 → 기안서 업체 Combobox 자동 설정 (신규)
사용자 수동 변경 → 허용 (자동 연동 오버라이드)
```

---

## 5. 신규 문서 생성 플로우

### 5.1 통합 후 액션 플로우 (0 다이얼로그)

```
[문서 생성] 클릭
  │
  ├─ 1. _validate() — 통합 유효성 검사
  │     ├─ 기안제목 필수 (폴더명)
  │     ├─ 품목 검증: 품명, 단가 > 0, 수량 >= 1  ← C-1 추가
  │     ├─ 구매처명 검증 (견적1 필수, 견적2는 비단독 시 필수)
  │     ├─ 견적1·2 동일 업체 방지  ← C-4 기존
  │     ├─ 견적2 단가 > 0 경고 (비단독 시)  ← C-2 추가
  │     └─ IF 기안서 동시생성:
  │           ├─ 내용 필수
  │           └─ 구매업체 선택 필수
  │
  ├─ 2. 폴더 생성
  │     ├─ make_output_dir_named(기안제목)
  │     └─ IF FileExistsError → messagebox.showerror (유일한 팝업)
  │
  ├─ 3. 스크린샷 복사 (기존 동일)
  │
  ├─ 4. 메인 창 최소화 (HWP 보안 다이얼로그용)
  │     └─ root.iconify() — 1회만 (산출+기안 연속 생성)
  │
  ├─ 5. 산출기초조사서 생성 (비단독 시)
  │     └─ HwpGenerator.generate_calculation()
  │
  ├─ 6. 기안서 생성 (체크 시)
  │     ├─ draft_info 수집 (탭에서 직접)
  │     ├─ vendor 정보 수집 (탭의 구매업체 콤보에서)
  │     └─ HwpGenerator.generate_draft()
  │
  ├─ 7. 메인 창 복원
  │     └─ root.deiconify() + root.lift()
  │
  ├─ 8. DB 저장
  │     ├─ repo.insert(data)
  │     ├─ repo.update_docs()
  │     ├─ repo.update_folder()
  │     └─ repo.update_draft_meta() (기안서 생성 시)
  │
  ├─ 9. 완료 메시지
  │     └─ messagebox.showinfo("완료", 생성된 문서 목록)
  │
  └─ 10. _reset_form()  ← 모든 작업 성공 후에만! (C-3 해결)
```

### 5.2 C-3 버그 구조적 해결 확인

**현재 (문제):**
```python
self._reset_form()                    # 761행: 폼 삭제
if messagebox.askyesno(...):          # 763행: 기안서 질문
    preselect_vendor = self._vendor_records[sel - 1]   # 765행: None! (reset에서 삭제됨)
    DraftDialog(self, data, ...)      # 767행: vendor 연동 실패
```

**통합 후 (해결):**
```python
try:
    # ... 모든 문서 생성 (vendor_records 유효 상태) ...
    self._reset_form()                # 성공 후에만
except Exception:
    pass                              # 실패 시 폼 데이터 100% 보존
```

### 5.3 HWP COM iconify 단순화

**현재 (DraftDialog 있을 때):**
```python
# 산출기초조사서: root.iconify() → root.deiconify()
# 기안서 (DraftDialog): self.grab_release() → self.withdraw() → main.iconify()
#                        → finally: main.deiconify() → self.deiconify() → self.grab_set()
```

**통합 후:**
```python
root = self.winfo_toplevel()
root.iconify()
try:
    # 산출기초조사서 생성 (비단독 시)
    # 기안서 생성 (체크 시)
finally:
    root.deiconify()
    root.lift()
    self.update_idletasks()
```
- DraftDialog 윈도우 관리 코드 전부 제거 (grab_release, withdraw, deiconify, grab_set)
- iconify 1회로 양쪽 문서 모두 처리

---

## 6. 보안 분석

### 6.1 부분 저장 위험

**시나리오**: 산출기초조사서 성공 → 기안서 실패 → 기안 메타데이터 유실

**대응**:
1. `repo.insert()` 직후 `update_draft_meta(purchase_id, title, content)` 즉시 호출
2. HWP 생성 성공 시 `update_docs()`로 파일 경로만 갱신
3. 2단계 전략으로 기안서 HWP 실패해도 메타데이터는 DB에 보존

### 6.2 vendor_repo 캐시

- `vendor_repo.select_all()`은 매번 `SELECT * FROM vendors` 실행 (캐시 없음)
- 통합 후 `refresh_vendors()`를 확장하여 기안서 업체 콤보박스도 함께 갱신

---

## 7. 수정 대상 파일 목록 (우선순위순)

| # | 파일 | 변경 규모 | 주요 작업 |
|---|------|----------|----------|
| 1 | `ui/tab_purchase.py` | **대규모** | purpose 제거, 기안서 섹션 UI 추가, _TitleInputDialog 삭제, _generate_documents 리팩토링, _validate 강화, _reset_form 수정, refresh_vendors 확장 |
| 2 | `core/models.py` | **소규모** | `purpose` 필드 삭제 |
| 3 | `db/purchase_repo.py` | **소규모** | INSERT SQL에서 purpose 제거 (빈 문자열 기본값) |
| 4 | `db/database.py` | **소규모** | `NOT NULL` → `DEFAULT ''`, _migrate 호환 코드 |
| 5 | `ui/tab_history.py` | **중규모** | purpose 컬럼/검색/상세 삭제, Treeview 재구성 |
| 6 | `ui/tab_inspection.py` | **소규모** | purpose 검색/Treeview 제거 |
| 7 | `ui/dialog_draft.py` | **삭제** | 전체 파일 삭제 |

### 영향 없는 파일
- `documents/hwp_generator.py` — purpose 미사용, 변경 불필요
- `documents/excel_generator.py`, `db/vendor_repo.py`, `db/inspection_repo.py` — 무관
- `ui/tab_vendor.py`, `ui/tab_sole_contract.py` — 무관
- `core/screenshot.py`, `core/semi_auto.py` — 무관

---

## 8. 위젯 수 비교

| 항목 | Before | After |
|------|--------|-------|
| PurchaseTab 고정 위젯 | ~65 | ~87 (purpose -2, 기안제목 +2, 기안서정보 +22) |
| _TitleInputDialog | ~6 | **0 (삭제)** |
| messagebox.askyesno | 1 | **0 (삭제)** |
| DraftDialog | ~25 | **0 (삭제)** |
| **총 위젯 수** (1품목 기준) | **~108** | **~98** |
| **다이얼로그 수** | **3** | **0** |
| **문서 생성 클릭 수** | **5회** | **1회** |
| **파일 수** | 2 (tab_purchase + dialog_draft) | **1** (tab_purchase만) |

---

## 9. 코드 라인 수 예상

| 항목 | 현재 | 통합 후 |
|------|------|---------|
| tab_purchase.py | 829줄 | ~880줄 |
| dialog_draft.py | 236줄 | **0줄 (삭제)** |
| **합계** | **1,065줄** | **~880줄 (-17%)** |

상세:
- 삭제: _TitleInputDialog(-44줄), _ask_draft_title(-6줄), purpose 관련(-8줄), 다이얼로그 호출(-8줄)
- 추가: 기안서 섹션 UI(+80줄), 기안서 생성 로직(+30줄), 토글/이벤트(+10줄)

---

## 10. 수정 후 예상 동선

```
기안제목 입력 → 부서명 → VAT → 품목 입력 → 사이트 조사
→ 견적1/2 입력(구매처명/URL/스크린샷) → 최저가 확인
→ ☑ 기안서 동시 생성 (기안서 정보 펼침)
→ 내용 입력 → [문서 생성] 클릭 → 완료
```

| 지표 | 현재 | 개선 후 |
|------|------|---------|
| 다이얼로그 수 | 3개 (순차) | **0개** |
| 문서 생성 클릭 수 | 5회 | **1회** |
| 필수 입력 필드 조작 | 15~20회 | **8~12회** |
| 검증 누락 항목 | 3개 (수량/견적2단가/동일업체) | **0개** |
| 구매목적 입력 | 필요 | **삭제** |
| _reset_form 버그 | C-3 존재 | **구조적 해결** |
| vendor 연동 실패 | M-3 존재 | **구조적 해결** |

---

## 11. 구현 우선순위 로드맵

```
Phase 1 (유효성 검사)    ████████  C-1,C-2 검증 + M-1,M-2,M-4 수정
Phase 2 (핵심 통합)      ██████████████████  purpose 삭제 + DraftDialog 통합 + C-3 해결
Phase 3 (부속 정리)      ██████  tab_history/tab_inspection purpose 제거
Phase 4 (코드 정리)      ████    dialog_draft.py 삭제, 미사용 파일 정리
```

### Phase 1: 유효성 검사 강화
- `_validate()`: 수량 >= 1 검사 추가 (C-1)
- `_validate()`: 견적2 단가 > 0 경고 (C-2)
- `_on_sole_toggle()`: 스크린샷 초기화 (M-1)
- `_reset_form()`: `_sole_quote_var.set(False)` + `_v2_frame.grid()` (M-2)
- `_update_price_info()`: 동점 시 "동일 금액" 표시 (M-4)

### Phase 2: 핵심 통합 (이번 작업의 메인)
- purpose 필드 제거 (models.py, tab_purchase.py, purchase_repo.py)
- 기안제목 Entry를 구매 정보 섹션에 추가
- VAT를 구매 정보 섹션으로 이동
- "기안서 동시 생성" 체크박스 추가
- 기안서 정보 섹션 추가 (접기/펼치기)
- _TitleInputDialog 삭제
- _generate_documents() 리팩토링 (0 다이얼로그)
- _reset_form() 타이밍 수정 (C-3 해결)
- refresh_vendors() 확장

### Phase 3: 부속 파일 정리
- tab_history.py: purpose 컬럼/검색/상세 제거
- tab_inspection.py: purpose 검색/Treeview 제거
- database.py: purpose DEFAULT '' 마이그레이션

### Phase 4: 코드 정리
- dialog_draft.py 파일 삭제
- tab_manual.py, tab_auto.py 삭제 (구버전)

---

## 12. 리스크 분석

| 리스크 | 영향도 | 대응 |
|--------|--------|------|
| _generate_documents 대규모 리팩토링 | **높음** | 단계적 테스트: 산출만 → 기안만 → 동시생성 |
| purpose 삭제 시 기존 DB NOT NULL 충돌 | **중간** | INSERT에 빈 문자열 전달, _migrate에서 안전 처리 |
| tab_purchase.py 880줄 비대화 | **중간** | 기안서 섹션을 별도 Frame 클래스로 분리 가능 |
| HWP COM iconify 1회로 변경 시 보안 다이얼로그 | **낮음** | 기존 패턴과 동일, 다이얼로그 관리만 단순화 |
| load_purchase()에서 기안서 필드 복원 | **낮음** | 이력 탭에서 기안 메타 로드 시 별도 처리 |

---

## 13. 기존 계획 항목 매핑 (v1 → v2)

| v1 항목 | v2 상태 | 비고 |
|---------|---------|------|
| Phase 1: 유효성 검사 강화 | **유지** | Phase 1으로 동일 |
| Phase 2: 다이얼로그 통합 (DraftDialog 유지) | **대체** → Phase 2: DraftDialog 전면 통합 | 다이얼로그 0개로 확대 |
| Phase 3: UI 레이아웃 개선 | **흡수** → Phase 2에 통합 | VAT 이동, 접기/펼치기 포함 |
| Phase 4: 코드 중복 제거 | **유지** → Phase 4 | dialog_draft.py 삭제 추가 |
| 구매목적 필드 | **미포함** → **v2에서 삭제** | C-5로 새로 등록 |
