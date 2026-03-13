# Design-Implementation Gap Analysis Report

> **Feature**: payment-method-auto-detect (결제방법 자동 추천)
> **Design Document**: `docs/02-design/features/payment-method-auto-detect.design.md`
> **Analysis Date**: 2026-03-13
> **Status**: Approved

---

## Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Step 1: derive_payment_method() + validate_bank_info() | 100% | PASS |
| Step 2: database.py 마이그레이션 | 100% | PASS |
| Step 3: vendor_repo.py (insert/update/bulk_insert) | 100% | PASS |
| Step 4: VendorDialog 리팩토링 | 100% | PASS |
| Step 5: Excel 양식/파싱 변경 | 100% | PASS |
| Step 6: BulkUploadPreviewDialog 변경 | 100% | PASS |
| Step 7: tab_purchase.py 수정 | 95% | WARN |
| Step 8: 영향 없음 확인 + 안전 가드 | 100% | PASS |
| **Overall** | **99%** | PASS |

---

## Step-by-Step Comparison

### Step 1: `derive_payment_method()` + `validate_bank_info()` -- 100%

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| 위치 | `db/vendor_repo.py` 상단 | `db/vendor_repo.py` L4-34 | PASS |
| 함수 시그니처 | `derive_payment_method(bank_name, account_no, is_auto_transfer) -> str` | 동일 | PASS |
| 우선순위 1 | `is_auto_transfer=True -> "auto_transfer"` | L19: 동일 | PASS |
| 우선순위 2 | `bank_name.strip() and account_no.strip() -> "transfer"` | L21: 동일 | PASS |
| 우선순위 3 | `그 외 -> "card"` | L23: 동일 | PASS |
| `validate_bank_info()` 시그니처 | `(bank_name, account_no) -> str \| None` | L26: 동일 | PASS |
| 은행명만 있는 경우 | 경고 메시지 반환 | L30-31: 동일 | PASS |
| 계좌번호만 있는 경우 | 경고 메시지 반환 | L32-33: 동일 | PASS |
| 정상인 경우 | `None` 반환 | L34: 동일 | PASS |

### Step 2: `database.py` 마이그레이션 -- 100%

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| `is_auto_transfer` 컬럼 추가 | `ALTER TABLE vendors ADD COLUMN is_auto_transfer INTEGER DEFAULT 0` | L159-161: 동일 | PASS |
| 기존 auto_transfer 이관 | `UPDATE vendors SET is_auto_transfer = 1 WHERE payment_method = 'auto_transfer'` | L163-165: 동일 | PASS |
| 은행정보 없는 transfer 보정 | `UPDATE vendors SET payment_method = 'card' WHERE ...` | L168-173: 동일 | PASS |
| 조건부 실행 | `if "is_auto_transfer" not in v_cols` | L158: 동일 | PASS |

### Step 3: `vendor_repo.py` (insert/update/bulk_insert) -- 100%

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| `insert()` - `setdefault("is_auto_transfer", 0)` | O | L38: 동일 | PASS |
| `insert()` - `derive_payment_method()` 호출 | O | L39-43: 동일 | PASS |
| `insert()` SQL - `is_auto_transfer` 포함 | O | L44-50: 동일 | PASS |
| `update()` - 동일 패턴 | O | L57-73: 동일 | PASS |
| `bulk_insert()` - 각 row `derive_payment_method()` | O | L149-155: 동일 | PASS |
| `bulk_insert()` UPDATE SQL - `is_auto_transfer` 포함 | O | L161-165: 동일 | PASS |
| `bulk_insert()` INSERT SQL - `is_auto_transfer` 포함 | O | L176-181: 동일 | PASS |

### Step 4: VendorDialog 리팩토링 -- 100%

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| `_pay_var` (라디오) 제거 | O | 제거 확인 | PASS |
| `_transfer_labels`, `_transfer_entries` 제거 | O | 제거 확인 | PASS |
| `_toggle_transfer()` 제거 | O | 제거 확인 | PASS |
| 라디오버튼 3개 제거 | O | 제거 확인 | PASS |
| `_auto_transfer_var = tk.IntVar(value=0)` 추가 | O | L302: 동일 | PASS |
| `_pay_preview_var` 추가 | O | L303: 동일 | PASS |
| row 0-3: 상호/대표자/사업자/주소 유지 | O | L309-321: 동일 | PASS |
| row 4: Separator | O | L324-325: 동일 | PASS |
| row 5-7: 은행명/예금주/계좌번호 (항상 표시) | O | L328-339: 동일 | PASS |
| row 8: 자동이체납부 체크박스 | O | L342-345: 동일 | PASS |
| row 9: 자동 감지 미리보기 라벨 | O | L348-351: 동일 | PASS |
| `_update_pay_preview()` 메서드 | O | L355-363: 동일 | PASS |
| trace_add로 은행 정보 변경 감지 | O | L336: 동일 | PASS |
| `_load()` - `is_auto_transfer` 반영 | O | L365-369: 동일 | PASS |
| `_on_save()` - `validate_bank_info()` 호출 | O | L381-384: 동일 | PASS |
| `_on_save()` - `payment_method` 제외 (repo 자동 계산) | O | L395 주석 확인 | PASS |
| `_on_save()` - UNIQUE 에러 처리 | O | L404-408: 동일 | PASS |

### Step 5: Excel 양식/파싱 변경 -- 100%

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| 헤더 7열 (결제방법 제거) | `["상호 *", "대표자", ...]` | L133-134: 동일 | PASS |
| 예제 데이터 7컬럼 | 3개 예제 (카드/무통장/카드) | L149-156: 동일 | PASS |
| 열 너비 `[22, 12, 18, 35, 12, 12, 20]` | O | L165: 동일 | PASS |
| 설명 시트: 자동 감지 규칙 안내 | O | L185-189: 자동 감지 규칙 설명 포함 | PASS |
| `header_map` - `"결제방법": "_legacy_payment"` | O | L235: 동일 | PASS |
| 기본값 `is_auto_transfer: 0` | O | L260: 동일 | PASS |
| `data.pop("_legacy_payment", None)` | O | L268: 동일 | PASS |
| 결제방법 정규화 코드 삭제 | O | 삭제 확인 | PASS |

### Step 6: BulkUploadPreviewDialog -- 100%

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| `derive_payment_method()` import 및 호출 | O | L488-493: 동일 | PASS |
| `self._PAY.get(auto_pay, auto_pay)` 표시 | O | L494: 동일 | PASS |

### Step 7: `tab_purchase.py` 수정 -- 95%

| Item | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| 결제방법 라디오버튼 3개 유지 | O | L707-712: 유지 확인 | PASS |
| `_on_draft_vendor_select()` - `pay_code = v.get("payment_method", "card")` | O | L1134: 동일 | PASS |
| `_on_draft_vendor_select()` - `_dv_pay_var.set()` | O | L1135: 동일 | PASS |
| `_on_draft_vendor_select()` - `_pay_method_var.set(pay_code)` 자동 선택 | O | L1136: 동일 | PASS |
| `_on_draft_vendor_select()` - 은행 정보 채움 | O | L1137-1139: 동일 | PASS |
| `_on_draft_vendor_select()` - `_on_pay_method_change()` 호출 | O | L1140: 동일 | PASS |
| `_on_pay_method_change()` - 은행 정보 클리어 제거 | O | L1142-1148: 제거 확인 + 주석 | PASS |
| **`_dv_pay_var` 스타일** - **foreground=COLORS["primary"], font bold** | **설계: primary + bold** | **L696-698: text_secondary, 볼드 없음** | **DIFF** |
| `_build_purchase_data()` - `_pay_method_var.get()` 유지 | O | L1690: 유지 확인 | PASS |
| `load_purchase()` - 스냅샷 복원 유지 | O | L1537-1545: 유지 확인 | PASS |
| `_validate()` - 결제방법 검증 유지 | O | L1638-1641: 유지 확인 | PASS |

### Step 8: 영향 없음 + 안전 가드 확인 -- 100%

| Safety Guard | Design | Implementation | Match |
|------|--------|----------------|:-----:|
| SG-1: 이전 Excel 양식 하위 호환 | `header_map` `"결제방법": "_legacy_payment"` | L235: 동일 | PASS |
| SG-2: 기존 auto_transfer 업체 | `_load()` `is_auto_transfer` 반영 | L368: 동일 | PASS |
| SG-3: payment_method 외부 참조 | DB에 자동 계산값 저장 | insert/update/bulk_insert 모두 적용 | PASS |
| SG-4: 불완전 은행 정보 경고 | `validate_bank_info()` | L381-384: 동일 | PASS |
| SG-5: 구매탭 라디오 유지 | 라디오+바인딩 변경 없음 | L707-712: 유지 확인 | PASS |
| SG-6: 은행 정보 소실 방지 | 클리어 제거 | L1147-1148: 제거 + 주석 | PASS |

---

## Differences Found

### DIFF-1: `_dv_pay_var` 라벨 스타일 미적용 (Low)

| Item | Design (Section 5.3) | Implementation |
|------|--------|----------------|
| foreground | `COLORS["primary"]` | `COLORS["text_secondary"]` |
| font | `("맑은 고딕", 10, "bold")` | 미지정 (기본 폰트) |
| 위치 | `tab_purchase.py` L694-698 | 동일 |

설계서 Section 5.3에서 "기본 결제:" 라벨 값을 primary 색상 + bold 폰트로 강조하도록 명시했으나, 구현에서는 기존 `text_secondary` 색상과 기본 폰트를 유지하고 있음.

**영향도**: Low (순수 UI 스타일 차이, 기능 동작에 영향 없음)

**권장 조치**: 설계 의도가 "업체 DB에서 자동 감지된 결제방법을 시각적으로 강조"이므로 구현을 설계에 맞추는 것을 권장.

```python
# 현재 (L696-698):
ttk.Label(vendor_info, textvariable=self._dv_pay_var,
          foreground=COLORS["text_secondary"]).grid(
    row=3, column=1, sticky="w", pady=SPACING["xs"])

# 설계서 기준:
ttk.Label(vendor_info, textvariable=self._dv_pay_var,
          foreground=COLORS["primary"],
          font=("맑은 고딕", 10, "bold")).grid(
    row=3, column=1, sticky="w", pady=SPACING["xs"])
```

---

## Summary

| Category | Count |
|----------|:-----:|
| Missing Features (Design O, Implementation X) | 0 |
| Added Features (Design X, Implementation O) | 0 |
| Changed Features (Design != Implementation) | 1 |
| Total Gaps | 1 |

**Overall Match Rate: 99%** -- 설계서 8개 구현 단계 중 7개가 완벽히 일치하고, 1개 단계에서 UI 스타일 미세 차이 1건만 발견됨. 기능적으로는 100% 일치.

---

## Related Documents

- Plan: [payment-method-auto-detect.plan.md](../01-plan/features/payment-method-auto-detect.plan.md)
- Design: [payment-method-auto-detect.design.md](../02-design/features/payment-method-auto-detect.design.md)
