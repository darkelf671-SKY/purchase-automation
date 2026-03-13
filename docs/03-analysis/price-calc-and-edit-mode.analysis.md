# 할인 단가 계산 + 구매건 수정/재생성 Gap Analysis Report

> **Analysis Type**: Design vs Implementation Gap Analysis
>
> **Project**: 물품구매 자동화 시스템
> **Analyst**: gap-detector
> **Date**: 2026-03-12
> **Design Doc**: [price-calc-and-edit-mode.design.md](../02-design/features/price-calc-and-edit-mode.design.md)
> **Plan Doc**: [price-calc-and-edit-mode.plan.md](../01-plan/features/price-calc-and-edit-mode.plan.md)

---

## 1. Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Design Match | 82% | ⚠️ |
| Architecture Compliance | 95% | ✅ |
| Convention Compliance | 98% | ✅ |
| **Overall** | **88%** | ⚠️ |

---

## 2. Gap Analysis Summary

총 비교 항목 32건 중: 일치 26건 (81%), 설계서 미반영 변경 5건 (16%), 미구현 1건 (3%)

---

## 3. Differences Found

### 3.1 총액 입력 모드 — 견적1/견적2 독립 토글 (Design != Implementation)

| Item | Design | Implementation | Impact |
|------|--------|----------------|--------|
| 총액 토글 단위 | ItemRow별 단일 `_total_input_mode` (BooleanVar) | PurchaseTab 레벨 **2개 체크박스**: `_v1_total_mode_var`, `_v2_total_mode_var` (견적1/견적2 독립) | **High** |
| `price_input_mode` 값 | `"unit"` / `"total"` (2가지) | `"unit"` / `"total"` / `"v1_total"` / `"v2_total"` (4가지) | **High** |
| `_recalc()` 구조 | 단일 `_recalc()` 함수에서 `_total_input_mode`로 분기 | 4개 분리: `_recalc_v1`, `_recalc_v2`, `_recalc_v1_reverse`, `_recalc_v2_reverse` + `_do_calc_v1/v2`, `_do_reverse_v1/v2` | Medium |
| Entry 전환 메서드 | `_toggle_total_input_mode()` 단일 메서드 | `set_v1_total_mode()`, `set_v2_total_mode()` 독립 메서드 | Medium |
| `get_data()` mode 결정 | `price_input_mode: "total"` or `"unit"` | 4-way: `v1&&v2 → "total"`, `v1만 → "v1_total"`, `v2만 → "v2_total"`, `없음 → "unit"` | **High** |
| `calc_total()` 분기 | `price_input_mode == "total"` 체크 | `price_input_mode in ("total", "v1_total")` 체크 (v2_total은 v2_total_price 프로퍼티로 별도) | Medium |
| UI 배치 | ItemRow 내부 체크박스 (품목별) | 품목 섹션 하단 bottom 프레임에 2개 전역 체크박스 + 툴팁 | Medium |

**평가**: 설계서는 "품목별 독립 토글"을 명시했으나, 구현은 "견적1/견적2 독립 토글 (전체 품목 일괄)"로 변경됨. 이는 더 나은 UX 판단이나 설계서에 미반영.

### 3.2 수정/복사 모드 분리 (Design X, Implementation O)

| Item | Implementation Location | Description |
|------|------------------------|-------------|
| `load_purchase()` | tab_purchase.py:1359 | **복사 모드** 전용 -- 폼 채우기 + 복사 배너(파란색) 표시, `_editing_purchase_id`는 None 유지 |
| `load_purchase_for_edit()` | tab_purchase.py:1444 | **수정 모드** 전용 -- `load_purchase()` 호출 후 수정 플래그 설정 + 수정 배너(노란색) 표시 |
| `_handle_load_purchase()` | app.py:74 | 이력 → 구매탭 **복사** 콜백 |
| `_handle_edit_purchase()` | app.py:79 | 이력 → 구매탭 **수정** 콜백 |
| `on_load_purchase` / `on_edit_purchase` | tab_history.py:18 | 2개 콜백 분리 |
| "복사하여 새 기안" / "수정하기" 버튼 | tab_history.py:55-58 | 이력 조회 탭에 **2개 버튼** 분리 |

**평가**: 설계서는 `load_purchase()` 하나에 수정 모드 활성화를 포함. 구현은 복사(신규 기안)와 수정을 명확히 분리하여 `load_purchase_for_edit()` 추가. app.py도 2개 콜백으로 분리. 설계서에 미반영.

### 3.3 배너 UI 구분 (Design != Implementation)

| Item | Design | Implementation |
|------|--------|----------------|
| 배너 종류 | 수정 모드 배너 1개 (노란색) | **2종**: 수정 배너(노란 `#FFF3CD`) + 복사 배너(파란 `#D1ECF1`) |
| 배너 구조 | `_edit_banner` (tk.Frame) | `_banner_frame` (공통 프레임) + `_show_banner()` 공통 메서드 |
| 복사 배너 | 설계에 없음 | `_show_copy_banner()`: 파란 배너, "수정 취소" 버튼 없음 |
| 수정 배너 | `_show_edit_banner()` | `_show_edit_banner()`: 노란 배너, "수정 취소" 버튼 표시 |

**평가**: 구현이 설계보다 개선됨 -- 복사와 수정을 시각적으로 구분.

### 3.4 기존 파일 삭제 로직 (Design X, Implementation O)

| Item | Implementation Location | Description |
|------|------------------------|-------------|
| 기존 HWP 파일 삭제 | tab_purchase.py:1737-1746 | 수정 시 `doc_draft`, `doc_calculation` 기존 파일을 먼저 삭제 후 재생성 (기안제목 변경으로 파일명이 달라질 경우 구 파일 잔여 방지) |

**평가**: 설계서의 `_regenerate_documents()` 수도코드에는 기존 문서 파일 삭제 단계가 없음. 구현에서 추가된 안전장치.

### 3.5 VAT 비활성화 조건 (Design != Implementation)

| Item | Design | Implementation |
|------|--------|----------------|
| VAT 비활성화 조건 | `any(row._total_input_mode.get() for row in self._item_rows)` (품목 중 하나라도 총액 모드) | `self._v1_total_mode_var.get() or self._v2_total_mode_var.get()` (견적1 또는 견적2 전역 토글) |
| 힌트 텍스트 | 설계에 명시 없음 | `_vat_hint_label`: "총액 입력 시 VAT 별도 계산 불가" (빨간 텍스트) |

**평가**: 논리적으로 동일한 효과이나, 체크 대상이 다름 (품목별 vs 전역 토글). 설계서 미반영.

### 3.6 절사 정보 표시 (Design != Implementation)

| Item | Design | Implementation |
|------|--------|----------------|
| 절사 표시 위치 | ItemRow 내부 `_remainder_label` (품목별) | PurchaseTab 하단 `_remainder_label` (전체 요약) |
| 절사 표시 내용 | `(절사 {remainder}원)` | `품목N견적1: 절사 N원` / `품목N견적2: 절사 N원` (다중 품목 지원) |
| 절사 표시 색상 | 설계에 없음 | `COLORS["danger"]` (빨간색) |

### 3.7 미구현 항목

| Item | Design Location | Description |
|------|-----------------|-------------|
| 모드 전환 확인 다이얼로그 (R3) | plan.md Expert 6 | 단가↔총액 모드 전환 시 값 유실 방지 확인 다이얼로그 -- 구현되지 않음 (리스크 "중"으로 식별됨) |

---

## 4. 설계서 업데이트 필요 항목

### 4.1 설계서 반영 필수 (High Priority)

| # | 항목 | 설계서 위치 | 현재 설계 | 실제 구현 |
|---|------|------------|----------|----------|
| U1 | 총액 토글 구조 | Section 3.4 ItemRow | 품목별 단일 `_total_input_mode` | 견적1/견적2 독립 전역 토글 (`_v1_total_mode_var`, `_v2_total_mode_var`) |
| U2 | `price_input_mode` 값 범위 | Section 3.1 models.py | `"unit"` / `"total"` | `"unit"` / `"total"` / `"v1_total"` / `"v2_total"` |
| U3 | `_recalc()` 구조 | Section 3.4 | 단일 `_recalc()` 양방향 | 4+4 분리 함수: `_recalc_v1`, `_recalc_v2`, `_recalc_v1_reverse`, `_recalc_v2_reverse` + `_do_calc_v1/v2`, `_do_reverse_v1/v2` |
| U4 | 복사/수정 모드 분리 | Section 2.2-2.4 | `load_purchase()` 하나에 수정 모드 통합 | `load_purchase()` (복사) + `load_purchase_for_edit()` (수정) 분리 |
| U5 | 이력조회 버튼 분리 | Section 2.4 app.py | "변경 없음" 기재 | `on_load_purchase` + `on_edit_purchase` 2개 콜백, "복사하여 새 기안" / "수정하기" 2개 버튼 |
| U6 | 배너 2종 | Section 2.2 | 수정 배너만 | 수정 배너(노란) + 복사 배너(파란) |

### 4.2 설계서 반영 권장 (Medium Priority)

| # | 항목 | 현재 설계 | 실제 구현 |
|---|------|----------|----------|
| U7 | 기존 문서 파일 삭제 | `_regenerate_documents()`에 없음 | 재생성 전 `doc_draft`, `doc_calculation` 기존 파일 삭제 |
| U8 | VAT 힌트 라벨 | 없음 | `_vat_hint_label` 빨간 텍스트 표시 |
| U9 | 절사 정보 위치/형식 | ItemRow 내부, 품목별 | PurchaseTab 하단, 전체 품목 요약 |
| U10 | `_build_docs_common()` | 없음 | 신규/수정 공통 문서 생성 로직 추출 |
| U11 | `_save_db_meta()` | 없음 | 신규/수정 공통 DB 메타 저장 로직 추출 |

---

## 5. 일치 항목 (설계 = 구현)

| Category | Items | Match |
|----------|:-----:|:-----:|
| DB: `update()` 함수 | SQL 구조, 파라미터 | ✅ 100% |
| DB: `update_items()` 함수 | DELETE + re-INSERT 패턴 | ✅ 100% |
| DB: `_insert_items()` price_input_mode | 컬럼 추가 | ✅ 100% |
| DB: 마이그레이션 | `price_input_mode TEXT DEFAULT 'unit'` | ✅ 100% |
| DB: `items_to_purchase_items()` | `price_input_mode` 필드 매핑 | ✅ 100% |
| UI: `_editing_purchase_id`, `_editing_doc_folder` | 상태 변수 | ✅ 100% |
| UI: `_cancel_edit()` | 상태 초기화 + 배너 숨김 + 폼 리셋 | ✅ 100% |
| UI: `_update_gen_button_text()` | "생성" ↔ "재생성" | ✅ 100% |
| UI: `_generate_documents()` 분기 | `_editing_purchase_id` 기준 | ✅ 100% |
| UI: `_regenerate_documents()` 검수 삭제 [D3] | 경고 + 파일 삭제 + DB 삭제 | ✅ 100% |
| UI: 폴더명 유지 [D4] | `_editing_doc_folder` 사용 | ✅ 100% |
| UI: `_reset_form()` 수정 모드 초기화 | `_editing_purchase_id = None` 등 | ✅ 100% |
| Model: `PurchaseItem.price_input_mode` | 필드 존재 | ✅ (값 범위 다름) |
| Model: `calc_total()` 분기 | 총액 모드 시 역산 | ✅ (조건문 범위 다름) |
| VAT 자동 비활성화 [D1] | inclusive 강제 + 라디오 disabled | ✅ 100% |
| 총액 모드 복원 (load_purchase) | `price_input_mode` 읽어 토글 복원 | ✅ 100% |
| 문서 엔진 변경 불필요 | hwp_generator, excel_generator 미변경 | ✅ 100% |
| 구현 순서 [D5] | Issue 2 먼저 → Issue 1 통합 | ✅ |

---

## 6. Recommended Actions

### 6.1 설계서 업데이트 (Act Phase)

1. **Section 3 전면 개편**: 총액 모드를 "견적1/견적2 독립 전역 토글" 구조로 재작성
   - `_v1_total_mode_var`, `_v2_total_mode_var` 2개 체크박스
   - `price_input_mode` 4-value enum 반영
   - `_recalc` 4+4 분리 함수 구조
2. **Section 2.2에 복사/수정 모드 분리 추가**: `load_purchase()` vs `load_purchase_for_edit()`, 배너 2종
3. **Section 2.4 app.py 변경사항 추가**: `_handle_load_purchase` + `_handle_edit_purchase` 콜백 분리
4. **Section 2.3에 기존 문서 삭제 로직 추가**: `_regenerate_documents()` 수도코드에 `doc_draft`/`doc_calculation` 삭제 단계

### 6.2 리스크 항목 재평가

| 리스크 | 설계서 대응 | 구현 상태 |
|--------|-----------|----------|
| R3: 모드 전환 값 유실 | 확인 다이얼로그 | **미구현** -- 현재 해제 시 단가 기준 재계산으로 대응. 확인 다이얼로그 추가 여부 재결정 필요 |

---

## 7. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-03-12 | Initial gap analysis | gap-detector |
