# purchase-tab-ui-restructure Planning Document

> **Summary**: 구매 조사 탭의 섹션 순서와 그룹화를 실무 프로세스 흐름에 맞게 재편하여 사용자 혼란을 줄이고 입력 오류를 예방한다.
>
> **Project**: 구매기안 자동화 시스템 v1.0
> **Version**: 1.2 (현재 운영 기준)
> **Author**: Product Manager
> **Date**: 2026-03-12
> **Status**: Draft

---

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | 기안 정보 섹션에 12개 항목이 한 덩어리로 뭉쳐 있고, 견적 비교 전에 구매업체·결제방법을 요구하는 순서가 실무 프로세스와 역행하여 입력 혼란과 오류를 유발한다. |
| **Solution** | 섹션을 "품목 조사 → 견적 비교 → 기안 작성" 3단계 흐름으로 재배치하고, VAT 설정을 품목 목록 섹션으로 통합, 구매업체·결제방법을 견적 선택 이후로 이동한다. |
| **Function/UX Effect** | 입력 순서가 실무 결재 흐름과 일치하여 위→아래 순차 입력이 가능해지고, 기안 정보 섹션 항목 수가 절반 수준으로 감소하여 스크롤 부담이 줄어든다. |
| **Core Value** | 실무자가 구매 업무를 처음 접하더라도 화면 흐름만 따라가면 문서가 완성되는 직관적 입력 경험 제공. |

---

## 1. Overview

### 1.1 Purpose

구매 조사 탭(`ui/tab_purchase.py`)의 섹션 배치 순서와 항목 그룹화를 실무 구매 프로세스(품목 조사 → 시장 견적 수집 → 최저가 선택 → 기안서 작성)와 일치시켜 사용성을 개선한다.

### 1.2 Background

현재 구조는 기능별로 묶여 있으나 업무 흐름과 일치하지 않는다. 실무자는 먼저 품목과 가격을 조사하고, 그 다음 견적을 비교·선택한 후, 마지막으로 기안서에 구매업체와 결제방법을 확정한다. 그러나 현재 UI는 기안 정보(업체, 결제방법 포함)가 가장 먼저 나타나 견적 비교 전에 업체를 지정하도록 강제한다. 또한 VAT 설정이 "구매 조사" 섹션에 단독으로 위치하여 가격 입력 영역(품목 목록)과 분리되어 있다.

### 1.3 관련 파일

- 구현 대상: `E:/ClaudeCode/purchase-automation/ui/tab_purchase.py`
- 모델: `core/models.py` (`PurchaseData`, `PurchaseItem`)
- DB: `db/purchase_repo.py` (`load_purchase`, `update`)
- 연동: `ui/tab_history.py` (`load_purchase()` 호출), `DraftDialog`

---

## 2. Scope

### 2.1 In Scope

- [ ] 섹션 순서 재배치 (UI 표시 순서 변경)
- [ ] VAT 설정을 "품목 목록" 섹션 상단으로 이동
- [ ] "구매업체·업체정보·결제방법·은행정보"를 기안 정보 섹션에서 분리하여 견적 선택 이후 별도 섹션("결제·업체 정보")으로 이동
- [ ] "기안 정보" 섹션을 기안 작성용 항목(템플릿/제목/기안일/부서/내용/비고/포함항목)으로 슬림화
- [ ] 섹션 헤더 텍스트 및 안내 문구 정비
- [ ] `_build_ui()` 호출 순서 변경에 따른 내부 의존성(변수 초기화 순서 등) 정합성 확인 및 수정

### 2.2 Out of Scope

- 각 섹션 내부의 개별 위젯 동작 로직 변경 (계산 로직, 이벤트 핸들러 등)
- DB 스키마 변경
- 기안서 생성 로직(`HwpGenerator`) 변경
- `load_purchase()` 데이터 매핑 로직 변경 (매핑 규칙은 그대로, 위젯 참조만 유지)
- 다른 탭(검수, 이력 등) UI 변경
- 새로운 기능 추가

---

## 3. Requirements

### 3.1 기능 요구사항

| ID | 요구사항 | 우선순위 | MoSCoW | 상태 |
|----|---------|----------|--------|------|
| FR-01 | 섹션 표시 순서를 "❶ 품목 목록(VAT 포함) → ❷ 구매 조사(사이트 바로가기) → ❸ 견적 비교 → ❹ 결제·업체 정보 → ❺ 기안 정보 → 액션 버튼" 순으로 재배치한다. | High | Must | Pending |
| FR-02 | VAT 설정(라디오버튼 2개 + 힌트 레이블)을 품목 목록 섹션 내 헤더 영역으로 이동한다. | High | Must | Pending |
| FR-03 | 구매업체(Combobox), 신규 등록 버튼, 업체 정보 표시(대표자/사업자번호/주소/기본 결제), 결제방법 라디오버튼, 은행 정보 프레임을 "결제·업체 정보" 신규 섹션으로 분리한다. | High | Must | Pending |
| FR-04 | 기안 정보 섹션은 템플릿/제목/기안일/부서/내용/비고/포함항목만 포함한다 (7개 항목). | High | Must | Pending |
| FR-05 | 재배치 후에도 `load_purchase()` 호출 시 모든 필드가 올바르게 채워져야 한다 (수정 모드 호환성). | High | Must | Pending |
| FR-06 | 재배치 후에도 복사 모드(`_show_copy_banner`)가 정상 작동해야 한다. | High | Must | Pending |
| FR-07 | 구매처 자동 연동 흐름(Combobox `<<ComboboxSelected>>` → `_vendor_records` 저장 → `DraftDialog` preselect)이 재배치 후에도 유지되어야 한다. | High | Must | Pending |
| FR-08 | 총액 입력 모드 VAT 강제 비활성화 동작이 VAT가 품목 목록 섹션으로 이동한 뒤에도 정상 작동해야 한다. | High | Must | Pending |
| FR-09 | 섹션 헤더 레이블을 업무 단계가 직관적으로 드러나도록 정비한다 (예: "❶ 품목 및 가격 입력", "❷ 시장 조사", "❸ 견적 비교 및 선택", "❹ 업체·결제 정보", "❺ 기안 작성"). | Medium | Should | Pending |
| FR-10 | 견적 2 미사용(단독견적) 시 "결제·업체 정보" 섹션이 여전히 표시되어야 한다 (단독견적 = 견적2 숨김 논리 유지). | Medium | Should | Pending |

### 3.2 비기능 요구사항

| 카테고리 | 기준 | 측정 방법 |
|---------|------|---------|
| 무중단성 | 기존 모든 입력·저장·생성 기능이 재배치 후에도 100% 동작 | 수동 시나리오 테스트 (아래 4.1 항목) |
| 호환성 | DB에 저장된 기존 구매 기록을 불러올 때(`load_purchase`) 필드 누락 없음 | 기존 DB 레코드 불러오기 후 필드 육안 확인 |
| 성능 | 탭 초기 렌더링 시간 현재 대비 열화 없음 | 체감 비교 (Python/tkinter 특성상 ms 측정 불필요) |
| 유지보수성 | `_build_ui()` 내 각 빌드 함수 책임이 명확히 분리되어 향후 독립 수정 가능 | 코드 리뷰 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] FR-01 ~ FR-08 모든 Must 요구사항 구현 완료
- [ ] 다음 시나리오 전체 수동 통과:
  - [ ] 신규 입력 → "기안서 + 산출기초조사서 생성" 정상 완료
  - [ ] 이력 → "구매탭에 불러오기" → 모든 필드 정상 채워짐 → 재생성 성공
  - [ ] 복사 모드: 이력 → 복사 불러오기 → 새 기안 생성 성공
  - [ ] 단독견적 체크 → 견적 2 관련 UI 숨김 유지, 업체·결제 섹션은 유지
  - [ ] 구매처 Combobox 선택 → DraftDialog에서 업체 자동 선택 확인
  - [ ] 총액 입력 모드 활성화 → VAT 라디오버튼 disabled 확인
  - [ ] 설정 변경(부서명) → Hot Reload 즉시 반영 확인
- [ ] `python main.py` 실행 후 탭 전환, 스크롤, 위젯 클릭 이상 없음

### 4.2 Quality Criteria

- [ ] `_build_draft_section()` 함수에서 업체·결제 관련 빌드 코드가 완전히 제거됨
- [ ] 신규 `_build_vendor_payment_section()` 함수(가칭)가 독립적으로 구성됨
- [ ] VAT 관련 위젯이 `_build_survey_section()` 대신 `_build_items_section()`에 위치함

---

## 5. Risks and Mitigation

| # | 리스크 | 영향도 | 발생 가능성 | 완화 방안 |
|---|--------|-------|------------|---------|
| R-01 | **기존 사용자 혼란** — 오래 사용해 온 담당자가 섹션 위치 변경으로 인해 일시적 혼란을 겪을 수 있음 | Medium | High | 섹션 헤더에 단계 번호(❶❷❸...)를 명시하여 새 흐름을 직관적으로 안내. 변경 전 스크린샷 비교 자료 제공 권장. |
| R-02 | **Combobox 이벤트·vendor_records 연동 깨짐** — 구매처 Combobox(`_name_combos`, slot 1/2)가 견적 비교 섹션에 있고, `_vendor_records[slot]`을 통해 `DraftDialog`로 preselect 전달하는 흐름이 섹션 재배치 중 참조 오류 발생 가능 | High | Medium | `_build_quote_frame()` 내 Combobox 빌드 로직은 변경하지 않음. 섹션 순서 변경 후 `_generate_documents()` 내 `self._vendor_records[sel-1]` 참조가 정상인지 통합 테스트 필수 |
| R-03 | **`load_purchase()` 필드 매핑 순서 문제** — 현재 `_build_draft_section()` 내에서 위젯이 생성된 순서대로 `load_purchase()`가 값을 세팅함. 재배치 시 위젯 참조 변수(`_draft_vendor_var`, `_pay_method_var` 등)가 다른 빌드 함수로 이동하면 초기화 타이밍 문제로 `AttributeError` 발생 가능 | High | High | 변수 초기화(`__init__` 내 선언)를 빌드 함수보다 앞에 두거나, 모든 인스턴스 변수를 `__init__`에서 `None` 또는 기본값으로 선언 후 빌드 함수에서 위젯만 생성하는 패턴으로 통일. 빌드 순서 변경 전 변수 선언 위치 전수 검토 필요 |
| R-04 | **수정 모드 / 복사 모드 호환성** — `_show_edit_banner()`, `_show_copy_banner()`, `_cancel_edit()` 등이 `_content`의 첫 번째 pack 자식을 기준으로 배너 위치를 결정(`packed[0]`). 섹션 순서 변경 시 배너가 원하지 않는 위치에 표시될 수 있음 | Medium | Medium | `_show_banner()` 내 `packed[0]` 로직은 `_content`의 첫 번째 가시 자식 기준이므로, `_build_edit_banner()`가 `_build_ui()` 최상단에서 먼저 호출되는 구조를 유지하면 무관. 테스트에서 수정 모드 진입 후 배너 위치 육안 확인 필수. |
| R-05 | **VAT 비활성화 로직과 위젯 위치 불일치** — `_check_total_mode_vat()`가 `self._vat_radios` 리스트를 참조해 disabled 처리함. VAT 위젯이 품목 목록 섹션으로 이동해도 `self._vat_radios` 참조 자체는 유지되므로 로직은 무관. 단, 위젯이 동일 빌드 호출 내에서 생성·등록되는지 확인 필요 | Medium | Low | `_vat_radios` 리스트를 `__init__`에서 `[]`로 선언, `_build_items_section()` 내에서만 append하도록 이동. `_build_survey_section()`에서 VAT 관련 코드 전체 제거. |
| R-06 | **은행 정보 프레임 grid_remove 타이밍** — `_bank_info_frame`은 현재 `_build_draft_section()` 내 `draft_frame`을 부모로 생성 후 `grid_remove()`. 부모 프레임이 변경되면 grid manager 충돌 발생 | Medium | Medium | 신규 "결제·업체 정보" 섹션(LabelFrame)을 부모로 재생성. pack 기반으로 변경하거나, 새 부모 내에서 동일하게 grid 배치 후 `grid_remove()` 유지. |
| R-07 | **단독견적 토글 시 견적2 섹션 숨김 로직** — `_on_sole_toggle()`이 `_v2_frame`을 pack_forget/pack하는 로직은 섹션 순서와 무관하게 동작하나, 재배치 후 "결제·업체 정보" 섹션이 견적 비교 섹션 뒤에 위치하므로 사용자가 단독견적 선택 시 업체 섹션이 여전히 노출됨 — 이는 의도된 동작(단독견적도 업체 정보 필요). 요구사항 FR-10에서 명시적 확인 필요 | Low | Low | FR-10 수용 기준에 "단독견적 시 업체·결제 섹션 유지"를 명시하고 테스트 케이스에 포함. |

---

## 6. 변경 전후 섹션 구조 비교

### 현재 구조 (AS-IS)

```
❶ 기안 정보 (12개 항목)
   - 템플릿 불러오기
   - 기안제목 / 기안일 / 부서명
   - 내용 / 비고
   - 포함항목 선택 (계약방법, 수의계약 사유)
   - 구매업체 + 업체 정보 (대표자/사업자/주소/기본결제)
   - 결제방법 (카드/무통장/자동이체)
   - 은행 정보 (무통장 시)

❷ 구매 조사
   - VAT 설정
   - 검색 키워드 선택
   - 사이트 바로가기 버튼

❸ 품목 목록
   - 헤더 + 동적 품목 행 (ItemRow)
   - + 품목 추가 / 총액 입력 토글 / 합계 표시

❹ 견적 비교
   - 견적 1 (구매처명 Combobox + URL + 캡처)
   - 견적 2 (동일)
   - 최저가 선택 / 단독견적

액션 버튼 (초기화 / 기안서 생성)
```

### 목표 구조 (TO-BE)

```
❶ 품목 및 가격 입력
   - VAT 설정 (이동)
   - 헤더 + 동적 품목 행 (ItemRow)
   - + 품목 추가 / 총액 입력 토글 / 합계 표시

❷ 시장 조사
   - 검색 키워드 선택
   - 사이트 바로가기 버튼

❸ 견적 비교 및 선택
   - 견적 1 (구매처명 Combobox + URL + 캡처)
   - 견적 2 (동일)
   - 최저가 선택 / 단독견적

❹ 업체·결제 정보 (신규 분리)
   - 구매업체 Combobox + 신규 등록
   - 업체 정보 표시 (대표자/사업자/주소/기본결제)
   - 결제방법 선택
   - 은행 정보 (무통장 시)

❺ 기안 작성 (슬림화)
   - 템플릿 불러오기 / 현재 내용 저장
   - 기안제목 / 기안일 / 부서명
   - 내용 / 비고
   - 포함항목 선택

액션 버튼 (초기화 / 기안서 생성)
```

---

## 7. Architecture Considerations

### 7.1 Project Level

기존 Python/tkinter 단일 파일 구조 유지. 프레임워크 레벨 변경 없음.

### 7.2 주요 구현 결정 사항

| 결정 | 선택 | 근거 |
|------|------|------|
| 빌드 함수 분리 방식 | 기존 `_build_draft_section()` 분할 → `_build_draft_section()`(기안 작성) + `_build_vendor_payment_section()`(업체·결제) 신설 | 기존 함수 이름 유지로 git diff 범위 최소화 |
| VAT 위젯 이동 | `_build_survey_section()` → `_build_items_section()` 내 상단으로 이동 | VAT가 단가 계산에 직접 영향. 품목과 동일 시각 맥락 제공 |
| 인스턴스 변수 초기화 위치 | 이동 대상 위젯 변수를 `__init__`에서 `None`으로 선언 보강 | `load_purchase()` 등 외부 호출 시 초기화 순서 보장 |
| 섹션 순서 변경 방법 | `_build_ui()` 내 호출 순서만 변경 (각 빌드 함수 내부 로직 최소 변경) | 변경 범위 최소화, 기존 이벤트 바인딩 보존 |

### 7.3 변경 대상 함수 목록

| 함수 | 변경 내용 |
|------|---------|
| `_build_ui()` | 호출 순서 변경 (기안 → 조사 → 품목 → 견적 → 버튼에서 품목 → 조사 → 견적 → 업체 → 기안 → 버튼으로) |
| `_build_items_section()` | VAT 설정 위젯 빌드 코드 추가 (survey에서 이동) |
| `_build_survey_section()` | VAT 관련 코드 제거, 사이트 바로가기만 유지 |
| `_build_draft_section()` | 업체·결제 관련 코드 제거, 기안 작성 항목만 유지 |
| `_build_vendor_payment_section()` | 신규 생성 — 업체·결제·은행 정보 위젯 빌드 |
| `__init__()` | 신규 분리 변수 `None` 초기화 보강 |

---

## 8. 비기능 요구사항 — 기존 기능 무중단 보장

재배치는 표시 순서와 빌드 함수 경계만 변경하며, 아래 기존 동작은 코드 수준에서 변경하지 않는다:

- ItemRow 계산 로직 (`_recalc_v1`, `_recalc_v2`, 역산 로직)
- `_generate_documents()` / `_regenerate_documents()` 전체
- `load_purchase()` 데이터 세팅 로직 (위젯 참조 변수명 유지)
- `DraftDialog` 연동 및 preselect 흐름
- `_on_sole_toggle()` 견적2 숨김 로직
- 설정 Hot Reload (`reload_settings()`, `_department_var` 갱신)
- 스크린샷 캡처 3종

---

## 9. 우선순위 결정 기준

MoSCoW 적용 근거:

- **Must**: 재배치 후 기존 기능이 깨지거나, 실무 필수 흐름(생성·저장·불러오기)에 직접 영향을 주는 항목
- **Should**: 사용성 개선 효과가 있으나 기능 정합성에는 영향 없는 항목 (섹션 헤더 레이블 정비 등)
- **Could**: 향후 이터레이션에서 고려할 항목 (섹션별 접힘/펼침 토글 등)
- **Won't (이번 범위 제외)**: 개별 위젯 동작 변경, DB 스키마 변경, 신규 기능 추가

---

## 10. Next Steps

1. [ ] CTO(팀 리드) 검토 및 플랜 승인
2. [ ] Design 문서 작성 (`purchase-tab-ui-restructure.design.md`) — 변경 함수별 상세 위젯 배치도 포함
3. [ ] `tab_purchase.py` 구현 (변경 범위 최소화 원칙)
4. [ ] 수동 통합 테스트 (4.1 시나리오 전체)
5. [ ] `python main.py` 최종 확인

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-12 | 초안 작성 — 리스크 분석 및 요구사항 정의 | Product Manager |
