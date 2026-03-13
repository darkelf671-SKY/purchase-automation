# Design: 구매 조사 탭 UI 재구조화

## 1. 변경 전략

**단일 파일 수정**: `ui/tab_purchase.py`만 변경. 로직/모델/DB/HWP 변경 없음.

**핵심 원칙**: 기존 `_build_*` 메서드를 분할/통합/재배치만 수행. 내부 위젯 변수명, 이벤트 핸들러, 데이터 흐름은 모두 유지.

## 2. 빌드 메서드 매핑

### AS-IS → TO-BE

| AS-IS | TO-BE | 변경 내용 |
|-------|-------|----------|
| `_build_draft_section()` (row 0~12) | `_build_draft_section()` (row 0~8만) | row 9~12 제거 |
| (위에서 분리) | `_build_vendor_payment_section()` 신규 | row 9~12를 독립 메서드로 |
| `_build_survey_section()` | (삭제, 분할) | VAT→items로, 사이트→quote로 |
| `_build_items_section()` | `_build_items_section()` | 상단에 VAT 추가 |
| `_build_quote_compare_section()` | `_build_quote_section()` | 상단에 검색키워드+사이트 추가 |

### 새 `_build_ui()` 호출 순서

```python
def _build_ui(self):
    self._build_edit_banner()              # 0. 배너 (불변)
    self._build_items_section()            # ① 품목 및 가격 (VAT 포함)
    self._build_quote_section()            # ② 시장 조사 및 견적 비교
    self._build_vendor_payment_section()   # ③ 계약 업체 및 결제
    self._build_draft_section()            # ④ 기안 작성
    # 품명→기안제목 자동채움 trace
    # 액션 버튼
```

## 3. 각 메서드 상세 설계

### 3.1 `_build_items_section()` — ① 품목 및 가격 입력

LabelFrame 제목: `" ① 품목 및 가격 입력 "`

```
[VAT 라디오] VAT: ○ VAT별도  ○ VAT포함  [총액 힌트]
[구분선]
[품목 테이블 헤더 + Canvas]
[+ 품목 추가] [견적1 총액입력] [견적2 총액입력] [합계 표시]
```

변경 사항:
- VAT 라디오+힌트를 품목 테이블 위에 배치 (기존 survey에서 이동)
- `_vat_radios`, `_vat_hint_label`을 이 메서드에서 생성
- 나머지 품목 테이블 코드는 100% 그대로

### 3.2 `_build_quote_section()` — ② 시장 조사 및 견적 비교

LabelFrame 제목: `" ② 시장 조사 및 견적 비교 "`

```
[검색 키워드] ○ 품명  ○ 규격   [미리보기]
[사이트 버튼] [네이버] [쿠팡] [롯데온] [G마켓] [옥션] [S2B]
[구분선]
[견적1 LabelFrame]  [견적2 LabelFrame]  (기존 _build_quote_frame 재사용)
[최저가 선택] ○ 견적1  ○ 견적2  [비교정보]  ☐ 단독견적
```

변경 사항:
- 검색키워드/사이트 바로가기를 기존 survey에서 이동
- 견적1/2 프레임 (`_build_quote_frame`) 코드 그대로 재사용
- 최저가 선택/단독견적 코드 그대로

### 3.3 `_build_vendor_payment_section()` — ③ 계약 업체 및 결제

LabelFrame 제목: `" ③ 계약 업체 및 결제 "`

```
[구매업체 *] [Combobox]  [신규 등록]
[업체 정보 LabelFrame] 대표자/사업자번호/주소/기본결제
[결제방법 *] ○ 법인카드  ○ 무통장입금  ○ 자동이체
[은행 정보 LabelFrame] 은행명/예금주/계좌 (조건부)
```

변경 사항:
- 기존 `_build_draft_section()` row 9~12를 독립 메서드로 분리
- 부모 프레임만 변경 (draft_frame → vendor_frame)
- `_bank_info_frame`의 부모가 vendor_frame으로 변경

### 3.4 `_build_draft_section()` — ④ 기안 작성

LabelFrame 제목: `" ④ 기안 작성 "`

```
[템플릿] [Combobox] [적용] [저장]  ※ 기안 템플릿 탭
[구분선]
[기안제목 *]  [Entry]  ※ 폴더명
[기안일]      [Entry]  ※ YYYY-MM-DD
[부서명]      [Label]  ※ 설정에서 변경
[내용 *]      [Text 4행]
[비고]        [Entry]
[구분선]
[포함 항목] ☐ 계약방법  ☐ 수의계약 사유  [사유 Combobox]
```

변경 사항:
- row 9~12 (구매업체~은행정보) 제거됨
- 나머지 row 0~8 코드 그대로
- grid row 번호는 변경 불필요 (row 9~12를 안 쓰면 됨)

## 4. 빌드 순서 안전성

| 순서 | 메서드 | 생성 위젯 | 의존 확인 |
|------|--------|----------|----------|
| 1 | items | `_vat_radios`, `_vat_hint_label`, `_items_container`, `_v1/v2_total_mode_var` | `_vat_mode_var`는 `__init__`에서 생성 ✅ |
| 2 | quote | `_v[0]`, `_v[1]`, `_name_combos`, `_selected_var`, `_v2_frame` | `on_vendor_selected`가 `_draft_vendor_var` 참조 → 런타임 이벤트이므로 빌드 시점 무관 ✅ |
| 3 | vendor_payment | `_draft_vendor_var`, `_draft_vendor_combo`, `_dv_*`, `_pay_method_var`, `_bank_info_frame` | quote의 `on_vendor_selected` 런타임 호출 시 이미 존재 ✅ |
| 4 | draft | `_draft_title_var`, `_draft_content_text`, 포함항목 | items의 `_auto_fill_title` trace 바인딩이 이후 실행 ✅ |

## 5. 영향받는 메서드 (변경 불필요, 검증만)

- `load_purchase()`: 위젯 참조만 사용, 빌드 순서 무관 ✅
- `_reset_form()`: 위젯 참조만 사용, `hasattr` 가드 존재 ✅
- `_validate()`: 위젯 참조만 사용 ✅
- `_generate_documents()` / `_build_purchase_data()`: 위젯 참조만 사용 ✅
- `_on_draft_vendor_select()`: 메서드 본체 불변 ✅
- `_check_total_mode_vat()`: `_vat_radios`가 items에서 먼저 생성 ✅
