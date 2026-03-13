---
template: plan
version: 1.2
description: 구매조사 입력 프로세스 개선 계획
variables:
  - feature: purchase-input-ux
  - date: 2026-03-10
  - author: Product Manager Agent
  - project: 구매기안 자동화 시스템
  - version: v1.0
---

# purchase-input-ux Planning Document

> **Summary**: PurchaseTab의 구매조사 입력 프로세스에서 발견된 비효율, 사용자 오류 유발 지점, 누락된 검증을 체계적으로 개선한다.
>
> **Project**: 구매기안 자동화 시스템
> **Version**: v1.0
> **Author**: Product Manager Agent
> **Date**: 2026-03-10
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 구매조사 입력 UI에서 필수 검증 누락(견적2 단가 미입력, 수량 0 허용), 데이터 불일치(VAT 역산 오류), 폼 초기화 타이밍 문제(기안서 생성 전 초기화), 단독견적 모드 전환 시 견적2 데이터 잔존 등 다수의 사용자 실수 유발 지점이 존재한다 |
| **Solution** | 유효성 검사 강화, _reset_form 타이밍 조정, 단독견적 전환 시 데이터 초기화, 수량 0 방지, load_purchase VAT 역산 정확도 개선, UX 피드백 보완 |
| **Function/UX Effect** | 잘못된 금액으로 문서가 생성되는 사고를 차단하고, 이력 데이터 재로딩 시 입력값이 정확히 복원되며, 사용자가 오류를 사전에 안내받아 문서 재생성 빈도가 줄어든다 |
| **Core Value** | 공공기관 구매 결재 문서의 정확성과 신뢰성을 높여 담당자의 업무 부담을 줄인다 |

---

## 1. Overview

### 1.1 Purpose

`ui/tab_purchase.py`의 PurchaseTab 클래스 전반에 걸쳐 발견된 비효율과 사용자 실수 유발 지점을 개선한다.
현재 코드에는 (1) 유효성 검사 공백, (2) VAT 역산 부정확, (3) 폼 초기화 타이밍 오류, (4) 단독견적 상태 관리 허점, (5) UX 피드백 미흡의 다섯 가지 범주의 문제가 존재한다.

### 1.2 Background

코드 전체 분석 결과를 아래에 상세히 기술한다.

#### 1.2.1 입력 프로세스 플로우 (현황)

```
[구매 목적 · 부서명 입력]
       ↓
[품목 추가 — 품명(필수)/규격/단위/수량/견적1단가/견적2단가/비고]
       ↓ (price_var.trace_add → _recalc → _update_grand_total)
[VAT 모드 선택 → 금액 자동 재계산]
       ↓
[사이트 바로가기 — 첫 품목 품명/규격을 검색어로 브라우저 오픈]
       ↓
[견적1 / 견적2: 구매처명(Combobox) + URL + 스크린샷 3종]
       ↓ (자동: _update_price_info → 견적1·2 합계 비교 → 최저가 라디오 자동 선택)
[최저가 수동 선택 가능 / 단독견적 체크]
       ↓
[산출기초조사서 생성 버튼]
       ↓ _validate() → _ask_draft_title() → _build_purchase_data()
       ↓ HwpGenerator.generate_calculation() → repo.insert() → _reset_form()
       ↓ (선택) DraftDialog → HwpGenerator.generate_draft()
```

#### 1.2.2 필수 vs 선택 입력 항목

| 항목 | 필수/선택 | 검증 여부 | 비고 |
|------|---------|---------|------|
| 구매 목적 | 필수 | O (_validate) | |
| 부서명 | 선택 | X | 문서에 "-" 대체 |
| 품명 | 필수 | O (_validate, 각 행) | |
| 규격/사양 | 선택 | X | |
| 단위 | 필수(기본값 있음) | X | 기본값 "개" |
| 수량 | 필수(기본값 있음) | X | Spinbox from_=1 이지만 수동 입력 시 0 가능 |
| 견적1 단가 | 필수 | O (_validate) | |
| 견적2 단가 | 선택 | X | 0이어도 통과 — 문서에 0 출력 |
| 구매처명(견적1) | 필수 | O (_validate) | |
| 구매처명(견적2) | 필수(단독견적 제외) | O (_validate) | |
| URL | 선택 | X | |
| 스크린샷 | 선택 | X | |
| 기안제목 | 필수 | O (_TitleInputDialog) | |

#### 1.2.3 자동 계산 vs 수동 입력

| 항목 | 자동/수동 |
|------|---------|
| 견적1 금액(행별) | 자동: price × qty × VAT 배수 |
| 견적2 금액(행별) | 자동: v2_price × qty × VAT 배수 |
| 견적1 합계 | 자동: 모든 행 합산 (readonly) |
| 견적2 합계 | 자동: 모든 행 합산 (readonly) |
| 최저가 자동 선택 | 자동: t1 <= t2 면 견적1 선택 |
| 기안제목 기본값 | 자동: "{item_name} 구매 기안" |
| 출력 폴더명 | 기안제목과 동일 (사용자 수정 가능) |

### 1.3 Related Documents

- 소스: `E:\ClaudeCode\purchase-automation\ui\tab_purchase.py`
- 모델: `E:\ClaudeCode\purchase-automation\core\models.py`
- DB: `E:\ClaudeCode\purchase-automation\db\purchase_repo.py`
- HWP: `E:\ClaudeCode\purchase-automation\documents\hwp_generator.py`
- 기안 다이얼로그: `E:\ClaudeCode\purchase-automation\ui\dialog_draft.py`

---

## 2. Scope

### 2.1 In Scope

- [ ] 유효성 검사 강화 (견적2 단가 0, 수량 0/음수, 부서명 경고)
- [ ] _reset_form 타이밍 수정 (기안서 생성 전 초기화 문제)
- [ ] 단독견적 모드 전환 시 견적2 필드 데이터 명시적 초기화
- [ ] load_purchase VAT 역산 로직 정확도 검증 및 보완
- [ ] 견적2 단가 0일 때 사용자 확인 다이얼로그
- [ ] 수량 입력 방어: Spinbox 수동 텍스트 입력 0 방지
- [ ] _update_price_info 동점(t1==t2) 시 중립 메시지
- [ ] 장문 오류 메시지 개선 (어느 필드인지 명확히)

### 2.2 Out of Scope

- 네이버 API 자동 검색 기능 추가 (별도 feature)
- HWP 템플릿 파일 자리표시자 추가 (사용자 직접 편집 필요)
- S2B 접속 URL 수정 (CLAUDE.md 미결 이슈)
- 탭 2~4 (검수/이력/업체) 관련 변경

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 수량 필드에 0 또는 음수 입력 시 유효성 검사 오류 발생 | High | Pending |
| FR-02 | 단독견적 아닌 경우 견적2 단가가 모든 품목에서 0이면 "견적2 단가가 입력되지 않았습니다" 경고 (진행 여부 확인) | High | Pending |
| FR-03 | _generate_documents 내 _reset_form 호출을 기안서 생성 완료 후로 이동 (현재 산출기초조사서 생성 직후 초기화되어 기안서 다이얼로그가 빈 폼 상태에서 열릴 위험) | High | Pending |
| FR-04 | _on_sole_toggle에서 False → True 전환 시 견적2 URL, 스크린샷 명시적 초기화 (현재 이름만 "단독견적"으로 설정하고 URL/스크린샷 잔존) | Medium | Pending |
| FR-05 | load_purchase 시 vat_mode="inclusive"일 때 div=1.0으로 처리되어 역산 불필요 — 코드는 이미 correct이나 단위 테스트 부재로 회귀 위험. 최소 inline 주석 보강 | Medium | Pending |
| FR-06 | t1 == t2 (동점) 시 _update_price_info 메시지를 "두 견적 금액이 동일합니다. 견적1이 선택됩니다"로 변경 (현재 "견적1이 0원 저렴(자동 선택)" 표시) | Low | Pending |
| FR-07 | 구역캡처 취소 시 status_var "캡처 취소됨" 메시지가 1~2초 후 자동 복구되도록 개선 (현재 영구 표시) | Low | Pending |
| FR-08 | _build_purchase_data에서 VendorQuote.unit_price와 total_price에 동일값(grand) 할당 중 — unit_price 의미 없음. 코드 명확화 또는 제거 | Low | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| 안정성 | 기존 기능 회귀 없음 | 수동 통합 테스트 (산출기초조사서 생성, 기안서 생성, 이력 불러오기) |
| UX | 사용자 오류 발생 시 어느 필드인지 명확히 안내 | 오류 메시지 텍스트 검토 |
| 유지보수성 | VAT 역산 로직 주석 보강으로 가독성 향상 | 코드 리뷰 |

---

## 4. 분석 상세: 발견된 비효율 및 개선 기회

### 4.1 유효성 검사 공백 (Critical)

**FR-01: 수량 0/음수 방어 부재**
- `ItemRow._build`에서 `Spinbox(from_=1)`로 설정하지만 사용자가 직접 텍스트 입력 시 0 또는 음수 입력 가능
- `_validate()`는 수량 검사 없이 품명·단가만 체크
- 수량 0이면 `total_price = price * 0 = 0`이 문서에 그대로 출력됨
- 수정 방향: `_validate()`에 `qty <= 0` 체크 추가

**FR-02: 견적2 단가 0 허용**
- 단독견적이 아닌데 모든 품목의 `v2_price_var`가 비어있거나 0이어도 통과
- 산출기초조사서에 견적2 단가 열이 전부 0으로 출력됨
- 수정 방향: `_validate()`에서 `sole_quote == False`이고 모든 v2 단가가 0이면 확인 다이얼로그

**부서명 미입력 무음 처리**
- 부서명은 문서에 중요한 정보이나 선택으로만 처리하고 경고 없음
- 수정 방향: `_validate()`에 부서명 미입력 경고(진행 여부 확인) 추가 — 강제는 아님

### 4.2 _reset_form 타이밍 문제 (Critical)

`_generate_documents()` 내 현재 흐름:
```
산출기초조사서 생성 완료
  → messagebox.showinfo("생성 완료")
  → self._reset_form()         ← 여기서 _screenshot_paths 포함 전부 초기화
  → messagebox.askyesno("기안서도 생성하시겠습니까?")
  → DraftDialog(... attachment_files=attachment_files)
```

- `attachment_files`는 `_reset_form()` 이전에 지역변수로 캡처되어 있어 내용은 전달됨
- 그러나 `data` 객체 및 `preselect_vendor`도 지역변수로 캡처되어 있어 실제 DraftDialog 동작에 직접 영향은 없음
- **그러나** 사용자가 "기안서 생성 여부" 팝업을 보는 시점에 이미 폼이 초기화되어, 폼으로 돌아가도 내용이 없는 상태
- 만약 기안서 생성 중 오류 발생 시, 사용자는 폼 데이터가 이미 지워진 상태에서 재입력해야 함
- 수정 방향: `_reset_form()`을 `DraftDialog` 처리 완전 종료 후 호출하거나, 기안서 생성 여부 확인 후 "아니오" 선택 시에도 초기화되도록 리팩토링

### 4.3 단독견적 모드 전환 허점 (Medium)

`_on_sole_toggle()` False → True(단독 활성화) 시:
```python
self._v[1]["name"].set("단독견적")
self._v[1]["url"].set("")
# 스크린샷은 초기화 안됨 — self._screenshot_paths[1] 잔존
```
- 견적2 URL은 초기화되나 스크린샷 경로(`_screenshot_paths[1]`)와 레이블은 그대로 유지
- 문서 생성 시 `_build_purchase_data()`에서 `screenshot_path=self._screenshot_paths[1]` 전달
- `attachment_files`에 견적2 스크린샷이 포함되어 기안서에 첨부됨 (의도치 않은 첨부)
- 수정 방향: `_on_sole_toggle` True 전환 시 `reset_ss` 로직 재사용하여 스크린샷 정리

### 4.4 load_purchase VAT 역산 로직 (Medium)

```python
div = 1.1 if vat_mode == "exclusive" else 1.0
raw_price = round(item.get("unit_price", 0) / div) if div != 1.0 else item.get("unit_price", 0)
```
- `vat_mode == "inclusive"`일 때 `div = 1.0` → 역산 없음 — 올바름
- `vat_mode == "none"`일 때 `div = 1.0` → 역산 없음 — 올바름
- `vat_mode == "exclusive"`일 때 `div = 1.1` → 역산 — 올바름
- 로직 자체는 정확하나, `div != 1.0` 조건이 두 가지(none, inclusive)를 동일 처리하는 것이 의미상 불명확
- 실수로 조건을 수정 시 none과 inclusive 구분이 깨질 위험
- 수정 방향: `if vat_mode == "exclusive": ... else: ...` 또는 명시적 분기 + 주석 보강

### 4.5 _build_purchase_data의 VendorQuote 구성 중복 (Low)

```python
return PurchaseData(
    ...
    vendor1=VendorQuote(
        name=...,
        unit_price=grand,    # grand와 동일
        total_price=grand,   # grand와 동일
        ...
    ),
    ...
)
```
- `VendorQuote.unit_price`는 단일 품목 시절 잔재 — 다중 품목 구조에서 의미 없음
- `total_price`와 `unit_price`가 항상 같은 값 → 혼동 유발
- `purchase_repo.insert()`에서 `v1p: data.vendor1.unit_price`를 DB에 저장하므로 데이터 중복 저장 중
- 수정 방향: `VendorQuote.unit_price` 필드 deprecated 처리 또는 `grand_total`로 명확화

### 4.6 _update_price_info 동점 메시지 오류 (Low)

```python
cheaper = 1 if t1 <= t2 else 2
diff = abs(t1 - t2)
self._price_info_label.config(text=f"견적{cheaper}이 {diff:,}원 저렴 (자동 선택)")
```
- `t1 == t2`일 때: "견적1이 0원 저렴 (자동 선택)" — 사용자 혼란 유발
- 수정 방향: `diff == 0`일 때 "두 견적 금액이 동일합니다 (견적1 선택)" 메시지

### 4.7 스크린샷 캡처 UX 미흡 (Low)

**전체캡처 타이밍 문제**
- `capture()`는 `time.sleep(0.5)` 후 즉시 캡처
- 사용자가 "전체캡처" 버튼을 누르는 순간 tkinter 창이 전면에 있어 앱 자체가 찍힘
- 수정 방향: 캡처 전 창 최소화(`root.iconify()`) 후 캡처, 캡처 완료 후 복원

**구역캡처 취소 메시지 잔존**
- ESC 취소 시 `status_var.set("캡처 취소됨")` 이후 자동 복구 없음
- 수정 방향: `self.after(2000, lambda: self.status_var.set(""))` 등으로 자동 복구

### 4.8 견적 정렬과 selected_vendor 관계 불명확성 (Medium)

`_generate_documents`에서:
```python
sel = data.selected_vendor
preselect_vendor = self._vendor_records[sel - 1]
```
- `_vendor_records[0]`은 견적1 Combobox에서 `<<ComboboxSelected>>`로 설정된 업체 레코드
- 그러나 목록에서 선택하지 않고 직접 입력한 경우 `_vendor_records[sel-1]`은 None
- DraftDialog에서 폴백 처리(`sel_name` 이름 비교)가 있으나, 이름이 DB와 불일치 시 업체 미선택 상태로 열림
- 수정 방향: `_vendor_records`가 None인 경우 이름 기반 자동 조회 강화 (현재 DraftDialog 폴백과 중복이지만 일관성 필요)

### 4.9 _reset_form 미포함 항목 (Low)

`_reset_form()`에서 초기화되지 않는 항목:
- `_sole_quote_var` (단독견적 체크박스) — 초기화 안됨
- `_search_field_var` (검색 키워드 라디오) — 초기화 안됨
- `_vat_mode_var`는 `"none"`으로 초기화됨 — 정상

초기화 누락으로 인해 이전 작업의 단독견적 상태가 다음 작업에 그대로 유지될 수 있음.
수정 방향: `_reset_form()`에 `self._sole_quote_var.set(False)` + `self._on_sole_toggle()` 호출 추가

### 4.10 품목 행 삭제 버튼 콜백 지연 패턴 (Low)

```python
row = ItemRow(..., on_delete=lambda: None, ...)  # 더미 콜백
self._rebind_delete_buttons()  # 실제 콜백으로 교체
```
- `_add_item_row`에서 `on_delete=lambda: None`으로 생성 후 `_rebind_delete_buttons`에서 교체
- 교체 전 짧은 순간 버튼이 "아무 동작 없음" 상태 — 실용적 문제는 없으나 설계 불일치
- 수정 방향: `ItemRow` 생성 시 직접 올바른 콜백 전달하도록 리팩토링

---

## 5. Success Criteria

### 5.1 Definition of Done

- [ ] FR-01: 수량 0 입력 시 오류 메시지 표시됨
- [ ] FR-02: 견적2 단가 전체 미입력 시 확인 다이얼로그 표시됨
- [ ] FR-03: _reset_form이 기안서 생성 완전 완료 후 호출됨
- [ ] FR-04: 단독견적 토글 시 견적2 스크린샷 자동 초기화됨
- [ ] FR-05: VAT 역산 로직에 명시적 주석 또는 분기 추가됨
- [ ] FR-06: 동점 메시지 "두 견적 금액이 동일합니다" 표시됨
- [ ] 기존 산출기초조사서 생성 흐름 회귀 없음 (수동 테스트)
- [ ] 기존 이력 불러오기(load_purchase) 회귀 없음 (수동 테스트)

### 5.2 Quality Criteria

- [ ] 수정 후 단독견적 + 일반견적 각 1회 전체 플로우 수동 테스트 통과
- [ ] load_purchase → _generate_documents 왕복 테스트 (VAT 각 3모드) 통과
- [ ] 코드 리뷰: 기존 기능과 동작 동일 확인

---

## 6. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| _reset_form 타이밍 변경 시 기안서 다이얼로그에 데이터 전달 경로 깨짐 | High | Medium | 지역변수 캡처 패턴 유지, 변경 전후 DraftDialog 데이터 전달 추적 |
| 견적2 단가 0 경고 추가 시 기존 사용자 워크플로 방해 | Medium | Low | messagebox.askyesno로 선택 가능하게 하여 강제 블로킹 아닌 확인 방식 사용 |
| VAT 역산 로직 수정 시 load_purchase 금액 오차 | High | Low | exclusive 모드만 역산 발생하므로 해당 케이스 집중 테스트 |
| 단독견적 스크린샷 초기화 추가 시 사용자가 실수로 데이터 손실 | Medium | Low | 초기화 전 경고 없이 자동 삭제 — 이미 reset_ss 패턴과 일관성 유지 |

---

## 7. Architecture Considerations

### 7.1 Project Level

이 프로젝트는 Python + tkinter 데스크톱 앱으로 bkit 레벨 분류와 직접 대응되지 않으나,
현재 구조(core/, db/, documents/, ui/)는 **Dynamic** 레벨의 Feature-based 분리에 해당한다.

### 7.2 Key Architectural Decisions

| Decision | Current | Recommendation |
|----------|---------|----------------|
| 유효성 검사 위치 | _validate() 단일 메서드 | 유지 — 검증 추가 시 이곳에 집중 |
| 상태 초기화 | _reset_form() 단일 메서드 | 유지 — 단독견적 var 초기화 추가 |
| VAT 계산 | ItemRow._recalc + ItemRow.get_data | 유지 — inclusive/exclusive/none 분기 주석 보강 |
| 스크린샷 정리 | cleanup() + _set_file() | 유지 — reset_ss 로직 _on_sole_toggle에서 재사용 |

---

## 8. Next Steps

1. [ ] CTO(팀장) 검토 후 우선순위 확정 (FR-01~FR-04 Critical, FR-05~FR-08 Medium/Low)
2. [ ] Design 문서 작성 (`purchase-input-ux.design.md`) — 각 수정의 구체적 코드 변경안
3. [ ] 구현 (Do 단계) — tab_purchase.py 수정
4. [ ] 수동 통합 테스트 (Check 단계)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-10 | Initial draft — 코드 분석 기반 전체 문제 정리 | Product Manager Agent |
