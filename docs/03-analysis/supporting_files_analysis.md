# Supporting Files Analysis - price_input_mode & Edit/Copy Mode

## Analysis Target
- Path: `core/models.py`, `db/purchase_repo.py`, `db/database.py`, `ui/app.py`, `ui/tab_history.py`, `ui/tab_purchase.py`
- Analysis Date: 2026-03-12

## Quality Score: 78/100

## Issues Found

### [CRITICAL] Immediate Fix Required

| # | File | Line | Issue | Recommended Action |
|---|------|------|-------|-------------------|
| C1 | `core/models.py` | 32-38 | `calc_total()`이 `"v2_total"` 모드를 처리하지 않음. `v2_total` 모드에서 `else` 분기로 빠져 `unit_price * quantity`로 계산되어, 견적2만 총액모드일 때 견적1 데이터가 의도와 다르게 동작할 수 있음 | `"v2_total"` 모드일 때 견적1은 `unit` 모드와 동일하게 동작해야 하므로 현재 `else` 분기가 맞긴 하나, 메서드명(`calc_total`)이 견적1 전용임을 명시하는 주석/docstring 필요 |
| C2 | `core/models.py` | 28-29 | `v2_total_price` 프로퍼티는 항상 `v2_unit_price * quantity`로 계산하지만, `"v2_total"` 모드에서는 v2_total이 입력값이고 v2_unit_price가 역산값이므로 정수 나눗셈 절사 시 `v2_unit_price * quantity != 원래 v2_total` 불일치 발생 | v2_total_price를 별도 필드로 저장하거나, 절사 오차를 문서에 명시 |
| C3 | `ui/tab_purchase.py` | 1577 | `_build_docs_common()` docstring이 `(doc_calc, doc_draft, attachment_files)` 3개 반환이라 기술하지만 실제 반환값은 `(doc_calc, doc_draft)` 2개 | docstring 수정: `-> tuple[str, str]` |

### [WARNING] Improvement Recommended

| # | File | Line | Issue | Recommended Action |
|---|------|------|-------|-------------------|
| W1 | `db/database.py` | 155-178 | `_migrate_existing_to_items()`에서 마이그레이션된 레코드에 `price_input_mode`가 설정되지 않음. INSERT 구문에 `price_input_mode` 컬럼 없어 DB 기본값 `'unit'`이 적용되나, 명시적 설정이 안전 | INSERT에 `price_input_mode='unit'` 명시 추가 |
| W2 | `db/database.py` | 170 | 마이그레이션에서 `vendor{sel}_price`를 `unit_price`로 사용하지만, 기존 데이터가 총액모드였을 경우 이 값이 이미 역산된 단가인지 원래 단가인지 불명확 | 레거시 데이터는 총액모드 이전이므로 문제없으나 주석 추가 권장 |
| W3 | `db/database.py` | 139 | `vat_mode` 기본값이 `'none'`으로 설정됨. 코드에서 `"none"` -> `"inclusive"` 매핑이 있지만 (`tab_purchase.py:1378`), `purchase_repo.py:39`에서도 `getattr(data, "vat_mode", "none")` 사용. 기본값이 `'inclusive'`가 아닌 `'none'`인 이유 불분명 | DB 기본값을 `'inclusive'`로 변경하고, fallback도 통일 |
| W4 | `ui/tab_purchase.py` | 1391-1394 | `load_purchase()`에서 총액모드 품목 복원 시, 먼저 `price_var`와 `v2_price_var`에 역산된 단가를 설정한 후 나중에(1406-1415) 총액모드를 활성화. 이 사이에 trace 콜백(`_recalc_v1`)이 실행되어 total_var가 단가 기반으로 재계산될 수 있음 | 총액모드 품목은 단가 설정 전에 모드를 먼저 활성화하거나, `_updating` 플래그 설정 후 데이터 채우기 |
| W5 | `ui/tab_purchase.py` | 1412-1414 | v2 총액 복원 시 `v2_unit * v2_qty`로 역계산하여 `v2_total_var`에 설정. 하지만 DB에는 `v2_unit_price`만 저장하고 `v2_total`은 저장하지 않아, 절사 오차가 있었다면 원래 총액 복원 불가 | `purchase_items`에 `v2_total_price` 컬럼 추가 검토 |
| W6 | `ui/tab_purchase.py` | 800-803 | `_add_item_row()`에서 `hasattr` 가드로 `_v1_total_mode_var` 존재 확인. `__init__`에서 이미 초기화되므로 불필요한 방어코드 | `hasattr` 제거 가능 (정리 수준) |
| W7 | `ui/tab_history.py` | 12 | `from db.purchase_repo import select_items` 상단 import 후, 441줄과 453줄에서 동일한 `from db.purchase_repo import select_items` 재 import | 상단 import 하나로 통합 |

### [INFO] Reference

| # | Observation |
|---|-------------|
| I1 | **Old reference 잔존 없음**: `_total_mode_var`는 현재 `_v1_total_mode_var`/`_v2_total_mode_var`로 올바르게 분리됨. `set_total_input_mode`, `_total_input_mode` 등 구 명칭은 코드베이스에 없음 |
| I2 | **ItemRow 내부**: `_v1_total_mode`/`_v2_total_mode` (BooleanVar)와 PurchaseTab의 `_v1_total_mode_var`/`_v2_total_mode_var`가 별도 변수로 존재하지만 `set_v1_total_mode()`/`set_v2_total_mode()`로 동기화되어 정상 작동 |
| I3 | **price_input_mode 4가지 값 호환성**: `"unit"`, `"total"`, `"v1_total"`, `"v2_total"` 모두 올바르게 처리됨. `get_data()` (296-304)에서 4가지 조합 정확히 생성, `items_to_purchase_items()` (133)에서 복원, `load_purchase()` (1397-1415)에서 복원 |
| I4 | **수정/복사 모드 분리**: `app.py`에서 `_handle_load_purchase`(복사)와 `_handle_edit_purchase`(수정) 콜백이 명확히 분리. `tab_history.py`에서 "복사하여 새 기안"/"수정하기" 버튼 2개로 구분. `tab_purchase.py`에서 `load_purchase()`(복사)와 `load_purchase_for_edit()`(수정, `_editing_purchase_id` 설정) 올바르게 구현 |
| I5 | **`_regenerate_documents()`**: 검수 기록 확인/삭제, 기존 문서 파일 삭제, `repo.update()`+`repo.update_items()`, `_save_db_meta()` 순서 정확 |
| I6 | **`_reset_form()`**: 수정모드 해제(`_editing_purchase_id = None`), 배너 숨김, 총액모드 해제 모두 처리됨 |

## Detailed Analysis by File

### 1. core/models.py

**price_input_mode 처리 정확성**:
- `calc_total()`: `"total"`과 `"v1_total"`은 견적1 총액 고정 + 단가 역산. `"unit"`과 `"v2_total"`은 단가->총액 계산. 이는 견적1 관점에서 올바름.
- 단, `calc_total()`은 견적1 전용 메서드인데 메서드명에서 이를 알 수 없음.
- `v2_total_price` 프로퍼티는 항상 곱셈이라 절사 오차 복원 불가 (C2).

**평가**: 모델 자체는 compact하고 하위 호환 프로퍼티 패턴 적절. `calc_total()`이 실제로 UI에서 호출되는지 확인 필요 -- 현재 UI(`ItemRow.get_data()`)에서 직접 계산하므로 `calc_total()`은 사실상 미사용 가능성 있음.

### 2. db/purchase_repo.py

**price_input_mode 저장/복원**:
- `_insert_items()`: `getattr(item, 'price_input_mode', 'unit')` -- 방어적이나 PurchaseItem에 이미 기본값 있어 불필요.
- `items_to_purchase_items()`: `r.get("price_input_mode", "unit")` -- 마이그레이션된 레코드 대비 안전.
- `update()`와 `update_items()`: 수정 모드용 함수 올바르게 구현.

**평가**: CRUD 로직 명확. `update_docs()` if/elif 체인은 단일 쿼리 + 조건부 파라미터로 리팩토링 가능하나 기능상 문제 없음.

### 3. db/database.py

**마이그레이션**:
- `price_input_mode` 컬럼 추가 마이그레이션 존재 (124-129). DEFAULT 'unit' 설정으로 기존 데이터 호환.
- `_migrate_existing_to_items()`: 기존 단일 품목 -> `purchase_items` 변환. `price_input_mode` 미명시이나 DEFAULT 값 적용됨 (W1).

**평가**: 마이그레이션 로직 안전. `vat_mode` 기본값 `'none'` 불일치만 주의 (W3).

### 4. ui/app.py

**복사/수정 콜백 분리**:
- `_handle_load_purchase()`: `load_purchase()` 호출 + 탭 전환.
- `_handle_edit_purchase()`: `load_purchase_for_edit()` 호출 + 탭 전환.
- `_switch_to_purchase_tab()`: Notebook.select(0) + refresh_vendors().

**평가**: 깔끔한 분리. 117줄로 적절한 파일 크기.

### 5. ui/tab_history.py

**복사/수정 버튼**:
- `_load_to_purchase()`: `on_load_purchase` 콜백 + `select_items()` 호출.
- `_edit_purchase()`: `on_edit_purchase` 콜백 + `select_items()` 호출.
- 두 메서드 구조 거의 동일 (중복 가능하나 명확성 우선 판단).

**평가**: 기능 정확. `select_items` 중복 import (W7) 외 문제 없음.

## Improvement Recommendations

1. **[High] W4 - 총액모드 복원 순서 수정**: `load_purchase()`에서 총액모드 품목 데이터를 채울 때 `_updating=True` 설정 후 일괄 채우고, 총액모드 활성화 후 `_updating=False`로 해제하여 불필요한 trace 콜백 실행 방지.

2. **[Medium] C2/W5 - v2_total_price 영속화**: `purchase_items` 테이블에 `v2_total_price` 컬럼을 추가하여 절사 오차 없이 원본 총액 복원 가능하도록 개선.

3. **[Medium] W3 - vat_mode 기본값 통일**: DB DEFAULT, `getattr` fallback, 매핑 로직 모두 `'inclusive'`로 통일.

4. **[Low] C3 - docstring 수정**: `_build_docs_common()` 반환값 문서 오류 수정.

5. **[Low] W7 - 중복 import 제거**: `tab_history.py` 내 `select_items` 중복 import 정리.

## Summary

| Category | Status |
|----------|--------|
| price_input_mode 4가지 값 처리 | OK - 생성/저장/복원 모두 정확 |
| Old reference 잔존 | OK - 없음 |
| 수정/복사 모드 분리 | OK - 3개 파일 간 올바르게 연결 |
| DB 마이그레이션 호환성 | OK - 기존 데이터 안전 |
| 총액모드 데이터 복원 정확성 | WARNING - trace 콜백 경합 가능성 (W4), v2 절사 오차 (W5) |
