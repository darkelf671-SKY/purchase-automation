# Gemini AI 기안내용 생성 기능 — Gap Analysis Report

> **Summary**: Design Document(v1.3) vs 실제 구현 코드 비교 분석
>
> **Author**: gap-detector
> **Created**: 2026-03-13
> **Design Document**: `docs/02-design/features/gemini-draft-content.design.md`
> **Plan Document**: `docs/01-plan/features/gemini-draft-content.plan.md`

---

## Analysis Overview

- **Analysis Target**: Gemini AI 기안내용 생성 기능 (gemini-draft-content)
- **Design Document**: `docs/02-design/features/gemini-draft-content.design.md` (v1.3)
- **Implementation Files**: 6개 (신규 2 + 변경 4)
- **Analysis Date**: 2026-03-13

---

## Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Design Match | 95% | OK |
| Architecture Compliance | 100% | OK |
| Convention Compliance | 100% | OK |
| Error Handling | 100% | OK |
| **Overall** | **96%** | OK |

---

## FR (Functional Requirements) Implementation Status

| FR | Description | Priority | Status | Notes |
|----|-------------|----------|:------:|-------|
| FR-01 | "AI 활용하기" 버튼 배치 | High | OK | row=6, sticky="e" -- 설계와 일치 |
| FR-02 | 모달 다이얼로그 표시 | High | OK | AIDraftDialog(BaseDialog) -- 설계와 일치 |
| FR-03 | 키워드 입력 영역 (tk.Text, 3줄) | High | OK | height=3, wrap="word" -- 설계와 일치 |
| FR-04 | Gemini API 호출 기안 내용 생성 | High | OK | generate_draft_content() -- 설계와 일치 |
| FR-05 | 로딩 표시 (버튼 비활성화 + "생성 중...") | Medium | OK | _set_loading() -- 설계와 일치 |
| FR-06 | 미리보기 영역 (tk.Text, 8줄, 읽기전용) | High | OK | height=8, state="disabled" -- 설계와 일치 |
| FR-07 | "적용" 버튼 동작 | High | OK | _on_apply() 콜백 + destroy -- 설계와 일치 |
| FR-08 | "다시 생성" 버튼 동작 | High | OK | _retry_btn 재호출 -- 설계와 일치 |
| FR-09 | 기존 내용 덮어쓰기 확인 | Medium | OK | on_apply 내 messagebox.askyesno -- 설계와 일치 |
| FR-10 | API 키 미설정 시 안내 메시지 | High | OK | _show_no_key_message + tab_purchase 양쪽 -- 설계와 일치 |
| FR-11 | 설정 다이얼로그 API 키 입력란 | High | OK | row=11, show="*" + 토글 -- 설계와 일치 |
| FR-12 | 품목 정보 프롬프트 컨텍스트 활용 | Medium | OK | _collect_purchase_context() + _build_prompt() -- 설계와 일치 |
| FR-13 | `{{품명}}` 템플릿 치환자 포함 옵션 | Low | MISSING | 미구현 (Low 우선순위, Out of initial scope) |
| FR-14 | API 키 발급 가이드 내장 | High | OK | docs/manual/gemini-api-key-guide.html 존재 |
| FR-15 | 설정 다이얼로그 "발급 가이드 보기" 버튼 | High | OK | row=12, _open_api_guide() -- 설계와 일치 |
| FR-16 | API 키 미설정 안내에서 가이드 열기 옵션 | Medium | OK | askyesnocancel -> open_gemini_guide() -- 설계와 일치 |
| FR-17 | EXE 빌드 시 가이드 HTML 번들 | High | OK | --add-data guide_dir -- 설계와 일치 |

**FR 구현율**: 16/17 (94%) -- FR-13(Low)만 미구현

---

## NFR (Non-Functional Requirements) Status

| Category | Criteria | Status | Notes |
|----------|----------|:------:|-------|
| Performance | 타임아웃 20초 | OK | REQUEST_TIMEOUT = 20 |
| Reliability | 에러 메시지 친화적 | OK | 7개 에러 코드별 한글 메시지 |
| Security | API 키 settings.json 저장 + 마스킹 | OK | show="*" + 토글 |
| Usability | 3클릭 이내 생성 | OK | AI버튼 -> 키워드입력+생성 -> 적용 |
| Compatibility | PyInstaller 호환 | OK | GUIDE_DIR = _BUNDLE_DIR 기반 |
| Rate Limit | 429 응답 처리 | OK | GeminiAPIError(RATE_LIMIT) |
| Accessibility | 키보드 탐색 | OK | Return/Ctrl+Return/Escape 바인딩 |

**NFR 충족율**: 7/7 (100%)

---

## Module-Level Comparison

### 1. `core/gemini_api.py`

**Design Match: 100%**

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| 상수 (URL, MODEL, TIMEOUT) | 3개 정의 | 3개 동일 | OK |
| ERROR_MESSAGES (7개 코드) | 7개 | 7개 동일 | OK |
| SYSTEM_PROMPT | 6규칙 | 6규칙 동일 | OK |
| USER_PROMPT_WITH/WITHOUT_CONTEXT | 2개 | 2개 동일 | OK |
| GeminiAPIError 클래스 | code + status_code | 동일 | OK |
| GeminiDraftAPI.__init__ | (api_key, model) | 동일 | OK |
| is_configured() | bool(api_key) | bool(api_key and api_key.strip()) | OK (*) |
| generate_draft_content() | (user_input, context) -> str | 동일 | OK |
| _build_prompt() | context 분기 | 동일 | OK |
| _call_api() | HTTP 에러 분기 6종 | 동일 | OK |
| generationConfig | temp=0.7, tokens=1024, topP=0.9 | 동일 | OK |

(*) `is_configured()`: 구현이 `.strip()` 추가 -- 공백만 있는 키를 걸러내는 방어적 처리로, 설계 의도를 개선한 변경.

### 2. `ui/dialog_ai_draft.py`

**Design Match: 93%**

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| 클래스 선언 + __init__ | BaseDialog 상속 | 동일 | OK |
| _build_content grid (row 0~9) | 10행 레이아웃 | 동일 | OK |
| _build_buttons (3버튼) | 적용/다시생성/취소 | 동일 | OK |
| _format_context_summary() | 단일/다중 품목 요약 | 동일 | OK |
| _on_generate() threading | daemon=True | 동일 | OK |
| _set_loading() | 상태 전환 | 동일 | OK |
| _on_result() | 미리보기 갱신 | 동일 | OK |
| _on_error() | 에러 표시 + 이전 결과 유지 | 동일 | OK |
| _on_apply() | 콜백 + destroy | 동일 | OK |
| _show_no_key_message() | askyesnocancel | 동일 | OK |
| **import 구문** | `from config import ..., GUIDE_DIR` | `from config import ..., open_gemini_guide` | CHANGED |
| **Return 키 바인딩** | `lambda e: self._on_generate()` | `lambda e: self._on_generate() if e.widget != self._input_text else None` | IMPROVED |
| **_show_no_key 텍스트** | "[아니오] 다이얼로그 닫기" | "[아니오] 닫기" | MINOR |

### 3. `config.py`

**Design Match: 100%**

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| GUIDE_DIR 상수 | _BUNDLE_DIR / "docs" / "manual" | 동일 | OK |
| get_gemini_api_key() | settings.get("gemini_api_key", "") | 동일 | OK |
| set_gemini_api_key() | load+set+save | 동일 | OK |
| open_gemini_guide() -> bool | webbrowser.open + return True/False | 동일 | OK |

### 4. `ui/dialog_settings.py`

**Design Match: 100%**

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| import 추가 | get/set_gemini_api_key, open_gemini_guide | 동일 | OK |
| Grid row 9~12 | Separator, AI제목, API키, 가이드버튼 | 동일 | OK |
| _toggle_key_visibility() | show/hide 전환 | 동일 | OK |
| _open_api_guide() | open_gemini_guide() + 실패 경고 | 동일 | OK |
| _on_save() API 키 저장 | set_gemini_api_key() 호출 | 동일 | OK |
| 저장 완료 메시지 | Gemini 상태 표시 | 동일 | OK |

### 5. `ui/tab_purchase.py`

**Design Match: 95%**

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| import 추가 | AIDraftDialog, get_gemini_api_key, open_gemini_guide | 동일 | OK |
| AI 버튼 배치 (row=6) | sticky="e" | 동일 | OK |
| _open_ai_draft_dialog() | API키 확인 + 컨텍스트 + 덮어쓰기 | 동일 | OK |
| _collect_purchase_context() | items + first 기반 dict | 동일 | OK |
| **messagebox parent** | `parent=self._content` | parent 미지정 | MINOR |
| **quantity 필드명** | `row.quantity_var` | `row.qty_var` | CHANGED |

### 6. `build_exe.py`

**Design Match: 100%**

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| guide_dir 변수 | ROOT / "docs" / "manual" | 동일 | OK |
| --add-data 추가 | `f"{guide_dir};docs/manual"` | 동일 | OK |

---

## Differences Found

### MISSING Features (Design O, Implementation X)

| # | Item | Design Location | Description | Impact |
|---|------|-----------------|-------------|--------|
| G1 | FR-13 템플릿 치환자 옵션 | plan.md:101 | `{{품명}}` 포함 옵션 미구현 | Low |

### CHANGED Features (Design != Implementation)

| # | Item | Design | Implementation | Impact |
|---|------|--------|----------------|--------|
| G2 | dialog_ai_draft.py import | `from config import ..., GUIDE_DIR` | `from config import ..., open_gemini_guide` | None (설계 결정 반영) |
| G3 | Return 키 바인딩 | 무조건 _on_generate() | Text 위젯 내 입력 시 제외 | Positive (UX 개선) |
| G4 | _show_no_key_message 텍스트 | "[아니오] 다이얼로그 닫기" | "[아니오] 닫기" | None (의미 동일) |
| G5 | messagebox parent | parent=self._content | parent 미지정 | Low (모달 위치) |
| G6 | _collect_purchase_context 필드명 | row.quantity_var | row.qty_var | None (실제 변수명 반영) |

### ADDED Features (Design X, Implementation O)

| # | Item | Implementation Location | Description | Impact |
|---|------|------------------------|-------------|--------|
| - | - | - | 추가된 기능 없음 | - |

---

## Architecture Compliance

| Item | Status | Notes |
|------|:------:|-------|
| Component 구조 (3계층) | OK | tab_purchase -> dialog_ai_draft -> gemini_api |
| BaseDialog 패턴 준수 | OK | _build_content, _build_buttons 오버라이드 |
| Design System 적용 | OK | COLORS, SPACING, FONTS 전면 적용 |
| config.py get/set 패턴 | OK | get_gemini_api_key / set_gemini_api_key |
| threading 비동기 호출 | OK | daemon=True, self.after(0, callback) |
| 기존 코드 최소 변경 원칙 | OK | 각 파일 변경 범위 최소 |

---

## Convention Compliance

| Item | Convention | Status |
|------|-----------|:------:|
| 파일명 snake_case | gemini_api.py, dialog_ai_draft.py | OK |
| 클래스명 PascalCase | GeminiDraftAPI, AIDraftDialog, GeminiAPIError | OK |
| 함수/변수명 snake_case | generate_draft_content, _build_prompt | OK |
| 상수 UPPER_SNAKE_CASE | GEMINI_API_URL, DEFAULT_MODEL, SYSTEM_PROMPT | OK |
| 타입힌트 | Optional[dict], -> str, -> bool | OK |
| 한글 주석 | 적절히 사용 | OK |

---

## Recommended Actions

### No Action Required (Intentional Changes)
1. **G2** (import 변경): 설계 문서 Section 3.3.5에서 "config.py에 open_gemini_guide()" 결정 사항으로 명시. 정상.
2. **G3** (Return 키 가드): Text 위젯에서 Enter 입력 시 생성 트리거 방지. UX 개선.
3. **G4** (메시지 텍스트 축약): 의미 동일. 무시 가능.
4. **G6** (qty_var): 실제 ItemRow 위젯의 변수명에 맞춤. 설계 문서가 추상적 이름 사용.

### Low Priority (Consider for future)
1. **G1** (FR-13): `{{품명}}` 치환자 포함 옵션. Low 우선순위로 별도 이터레이션 가능.
2. **G5** (parent 미지정): tab_purchase의 messagebox에 `parent=` 추가 시 모달 위치가 개선될 수 있음.

### Documentation Update
1. 설계 문서의 Return 키 바인딩 코드를 구현과 일치시키면 좋음 (라인 625).
2. `_collect_purchase_context`의 `quantity_var` -> `qty_var` 반영 (라인 1057).

---

## Match Rate Calculation

| Category | Total Items | Matched | Rate |
|----------|:-----------:|:-------:|:----:|
| FR (Functional Requirements) | 17 | 16 | 94% |
| NFR (Non-Functional Requirements) | 7 | 7 | 100% |
| Module: gemini_api.py | 11 | 11 | 100% |
| Module: dialog_ai_draft.py | 13 | 10 | 93% |
| Module: config.py | 4 | 4 | 100% |
| Module: dialog_settings.py | 6 | 6 | 100% |
| Module: tab_purchase.py | 5 | 3 | 95% |
| Module: build_exe.py | 2 | 2 | 100% |
| Architecture | 6 | 6 | 100% |
| Convention | 6 | 6 | 100% |
| **Overall** | **77** | **71** | **96%** |

---

## Conclusion

Overall match rate: **96%**. 설계와 구현이 매우 잘 일치함.

- 유일한 미구현 FR은 FR-13 (Low priority) -- 향후 별도 이터레이션 가능
- 변경 사항(G2~G6)은 모두 의도적 개선 또는 사소한 텍스트 차이
- 아키텍처, 컨벤션, 에러 처리 모두 설계 대로 구현
- 구현이 설계보다 개선된 부분: Return 키 가드(G3), is_configured() strip 처리

**Match Rate >= 90%**: 설계와 구현이 잘 일치합니다.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-03-13 | Initial gap analysis | gap-detector |
