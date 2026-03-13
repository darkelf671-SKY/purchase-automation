# QA 전략 문서 — 총액 입력 모드 & 이력 조회 수정/복사 분리

**작성일**: 2026-03-12
**대상 버전**: v1.2 (총액 입력 모드 + 구매건 수정 모드)
**작성자**: QA Strategist

---

## 1. 검증 범위 및 위험 평가

### 1.1 변경 기능 목록

| 기능 | 관련 파일 | 위험도 | 우선순위 |
|------|-----------|--------|---------|
| 총액 입력 모드 — 견적1/2 독립 제어 (4가지 케이스) | `ui/tab_purchase.py` (ItemRow) | High | 1 |
| 이력 조회 복사/수정 버튼 분리 | `ui/tab_history.py`, `ui/app.py` | High | 2 |
| 수정 모드 배너 (복사=파란, 수정=노란) | `ui/tab_purchase.py` (_show_banner) | Medium | 3 |
| 수정 시 기존 파일 삭제(덮어쓰기) | `ui/tab_purchase.py` (_regenerate_documents) | High | 4 |
| VAT 비활성화 조건 변경 (어느 한쪽이라도 총액이면) | `ui/tab_purchase.py` | High | 5 |

### 1.2 위험도 근거

- **총액 입력 모드**: `_updating` 플래그로 재진입을 막고, `_do_reverse_v1/v2`와 `_do_calc_v1/v2` 간 분기가 많아 엣지 케이스 발생 가능.
- **수정 모드**: DB UPDATE와 파일 덮어쓰기가 동시에 발생. 롤백 없음. 검수 자동 삭제 연동도 포함.
- **VAT 비활성화 조건**: 견적1만 총액 / 견적2만 총액 / 둘 다 총액 / 둘 다 단가 — 4가지 조합에서 라디오버튼 상태와 계산 결과가 모두 달라야 함.

---

## 2. 테스트 케이스 상세

### TC-01 ~ TC-04: 총액 입력 모드 — 4가지 케이스

**전제 조건**: 수량=3, 단가 입력 또는 총액 입력 가능 상태

---

#### TC-01: Case A — 견적1 단가입력 / 견적2 단가입력 (기본 모드)

| 항목 | 내용 |
|------|------|
| 목적 | 기존 모드(unit)가 총액 모드 도입 후에도 정상 동작하는지 확인 |
| 사전 조건 | `_v1_total_mode_var=False`, `_v2_total_mode_var=False` |
| 입력 | 견적1 단가=10,000 / 견적2 단가=12,000 / 수량=3 / VAT=exclusive |
| 기대 결과 | 견적1 금액=33,000, 견적2 금액=39,600 (×1.1 적용) |
| 기대 price_input_mode | `"unit"` |
| DB 저장 확인 | `purchase_items.price_input_mode = "unit"` |
| 불러오기 확인 | 수정 모드로 불러올 때 단가 필드 활성, 금액 필드 readonly |
| VAT 라디오 상태 | exclusive/inclusive 모두 활성 |

---

#### TC-02: Case B — 견적1 총액입력 / 견적2 단가입력

| 항목 | 내용 |
|------|------|
| 목적 | 견적1만 총액 모드일 때 역산 및 VAT 비활성 확인 |
| 입력 | 견적1 총액=30,000 / 견적2 단가=12,000 / 수량=3 |
| 기대 결과 | 견적1 단가=10,000(역산), 견적2 금액=36,000(inclusive 강제) |
| 기대 price_input_mode | `"v1_total"` |
| VAT 라디오 상태 | **disabled** (inclusive 강제) |
| VAT 힌트 라벨 | 경고 텍스트 표시 |
| DB 저장 확인 | `vat_mode = "inclusive"`, `price_input_mode = "v1_total"` |
| 불러오기 확인 | 견적1 금액 필드 활성(입력 가능), 단가 필드 readonly |

---

#### TC-03: Case C — 견적1 단가입력 / 견적2 총액입력

| 항목 | 내용 |
|------|------|
| 목적 | 견적2만 총액 모드일 때 역산 및 VAT 비활성 확인 |
| 입력 | 견적1 단가=10,000 / 견적2 총액=39,000 / 수량=3 |
| 기대 결과 | 견적2 단가=13,000(역산), 견적1 금액=30,000(inclusive 강제) |
| 기대 price_input_mode | `"v2_total"` |
| VAT 라디오 상태 | **disabled** (inclusive 강제) |
| DB 저장 확인 | `vat_mode = "inclusive"`, `price_input_mode = "v2_total"` |
| 불러오기 확인 | 견적2 금액 필드 활성, 단가 필드 readonly |

---

#### TC-04: Case D — 견적1 총액입력 / 견적2 총액입력

| 항목 | 내용 |
|------|------|
| 목적 | 둘 다 총액 모드일 때 양쪽 역산 및 VAT 비활성 확인 |
| 입력 | 견적1 총액=30,000 / 견적2 총액=39,000 / 수량=3 |
| 기대 결과 | 견적1 단가=10,000, 견적2 단가=13,000 (모두 역산) |
| 기대 price_input_mode | `"total"` |
| VAT 라디오 상태 | **disabled** |
| DB 저장 확인 | `price_input_mode = "total"` |
| 불러오기 확인 | 양쪽 금액 필드 활성, 단가 필드 readonly |

---

### TC-05: 수량 변경 시 총액 모드 재계산

| 항목 | 내용 |
|------|------|
| 목적 | 수량 변경 시 `_on_qty_change`가 올바른 분기를 타는지 확인 |
| 시나리오 | TC-04 상태에서 수량 3 → 5로 변경 |
| 기대 결과 | 견적1 단가=6,000(역산), 견적2 단가=7,800(역산) |
| 추가 확인 | `_updating` 플래그로 인한 무한 재진입 없음 |

---

### TC-06 ~ TC-08: 복사 vs 수정 분리

#### TC-06: "복사하여 새 기안" — 새 레코드 생성 확인

| 항목 | 내용 |
|------|------|
| 목적 | 복사 시 INSERT되고 기존 레코드가 변경되지 않는지 확인 |
| 사전 조건 | 이력에 purchase_id=N인 기안 존재 |
| 조작 | 이력 조회 → 항목 선택 → "복사하여 새 기안" 클릭 |
| 기대 결과 1 | 구매 조사 탭으로 전환, 파란색 배너 표시("복사 모드: ...") |
| 기대 결과 2 | `_editing_purchase_id = None` (신규 모드) |
| 기대 결과 3 | 생성 버튼 텍스트 = "기안서 + 산출기초조사서 생성" |
| 기대 결과 4 | 문서 생성 후 DB에 새 id(N+x) INSERT, 기존 id=N 레코드 불변 |
| DB 확인 | `SELECT COUNT(*) FROM purchases` 기존+1 증가 |

---

#### TC-07: "수정하기" — 기존 레코드 UPDATE 확인

| 항목 | 내용 |
|------|------|
| 목적 | 수정 시 UPDATE되고 새 레코드가 생성되지 않는지 확인 |
| 사전 조건 | 이력에 purchase_id=N인 기안 존재 |
| 조작 | 이력 조회 → 항목 선택 → "수정하기" 클릭 |
| 기대 결과 1 | 구매 조사 탭으로 전환, 노란색 배너 표시("수정 모드: ...") |
| 기대 결과 2 | `_editing_purchase_id = N` |
| 기대 결과 3 | 생성 버튼 텍스트 = "기안서 + 산출기초조사서 재생성" |
| 기대 결과 4 | "재생성" 후 DB UPDATE, 총 레코드 수 불변 |
| 기대 결과 5 | `purchase_items`: 기존 품목 삭제 후 재삽입 (CASCADE 활용) |

---

#### TC-08: 두 경로 간 콜백 분리 확인 (app.py)

| 항목 | 내용 |
|------|------|
| 목적 | `_handle_load_purchase` vs `_handle_edit_purchase` 콜백이 각각 올바른 메서드를 호출하는지 확인 |
| 확인 항목 1 | 복사 → `tab_purchase.load_purchase()` 호출 |
| 확인 항목 2 | 수정 → `tab_purchase.load_purchase_for_edit()` 호출 |
| 확인 항목 3 | 두 경로 혼용 없음 |

---

### TC-09 ~ TC-11: 배너 표시/숨김/전환

#### TC-09: 배너 색상 정확성

| 항목 | 내용 |
|------|------|
| 조건 A | 복사 모드 배너: 배경 `#D1ECF1`, 텍스트 `#0C5460` |
| 조건 B | 수정 모드 배너: 배경 `#FFF3CD`, 텍스트 `#856404` |
| 확인 | `_banner_frame.cget("bg")` 값이 예상과 일치 |

#### TC-10: "수정 취소" 버튼 동작

| 항목 | 내용 |
|------|------|
| 조작 | 수정 모드 진입 후 "수정 취소" 클릭 |
| 기대 결과 1 | `_editing_purchase_id = None` |
| 기대 결과 2 | 배너 숨김 (`pack_forget`) |
| 기대 결과 3 | 폼 초기화 (모든 필드 초기값) |
| 기대 결과 4 | 생성 버튼 텍스트 복원 = "기안서 + 산출기초조사서 생성" |

#### TC-11: 복사 모드에서 "수정 취소" 버튼 미표시

| 항목 | 내용 |
|------|------|
| 조건 | 복사 모드 배너 활성화 상태 |
| 기대 결과 | `_edit_cancel_btn` winfo_ismapped() == False |

---

### TC-12: 기안제목 변경 시 구 파일 삭제 (수정 모드)

| 항목 | 내용 |
|------|------|
| 목적 | 수정 시 기존 폴더가 덮어쓰기 되는지 확인 |
| 사전 조건 | 기존 기안 폴더 `data/outputs/노트북구매_2026-01-01` 존재 |
| 조작 | 수정 모드 진입 → 기안제목 변경 → 재생성 |
| 기대 결과 | `_editing_doc_folder` 기준으로 기존 폴더에 덮어쓰기 (폴더명 변경 없음) |
| 주의 | 기안제목이 폴더명이 아닌 `_editing_doc_folder`가 폴더 경로를 결정 |

---

### TC-13: 검수 완료 건 수정 시 경고+삭제

| 항목 | 내용 |
|------|------|
| 목적 | 검수 완료된 구매건 수정 시 경고 대화상자와 검수 자동 삭제 확인 |
| 사전 조건 | 검수 완료 상태의 purchase_id=N 존재 |
| 조작 | "수정하기" → 재생성 클릭 |
| 기대 결과 1 | "검수 기록이 있습니다. 수정 시 검수 기록이 삭제됩니다" 경고 표시 |
| 기대 결과 2 | 확인 시: `inspection_repo.delete_by_purchase(N)` 실행 |
| 기대 결과 3 | DB `inspections` 테이블에서 해당 레코드 삭제 확인 |
| 기대 결과 4 | 이력 조회 탭 "검수" 컬럼 "-"로 변경 |

---

### TC-14 ~ TC-16: VAT 전환 재계산

#### TC-14: exclusive → inclusive 전환

| 항목 | 내용 |
|------|------|
| 사전 조건 | 단가 모드, 견적1 단가=10,000, 수량=3, VAT=exclusive |
| 조작 | VAT "포함"으로 변경 |
| 기대 결과 | 견적1 금액: 33,000 → 30,000 |

#### TC-15: inclusive → exclusive 전환

| 항목 | 내용 |
|------|------|
| 사전 조건 | 단가 모드, 견적1 단가=10,000, 수량=3, VAT=inclusive |
| 조작 | VAT "별도"로 변경 |
| 기대 결과 | 견적1 금액: 30,000 → 33,000 |

#### TC-16: 총액 모드 해제 후 VAT 복원

| 항목 | 내용 |
|------|------|
| 사전 조건 | 견적1 총액 모드 활성 (VAT 라디오 disabled, inclusive 강제) |
| 조작 | "견적1 총액입력" 체크박스 해제 |
| 기대 결과 1 | VAT 라디오버튼 활성화 |
| 기대 결과 2 | 해제 직후 현재 단가 기준으로 금액 재계산 |
| 기대 결과 3 | VAT 힌트 라벨 텍스트 초기화 |

---

### TC-17: 폼 초기화 후 모드 리셋

| 항목 | 내용 |
|------|------|
| 목적 | "입력 초기화" 클릭 시 총액 모드와 수정 모드 상태가 모두 초기화되는지 확인 |
| 사전 조건 | TC-04(둘 다 총액 모드) + 수정 모드 배너 활성 상태 |
| 조작 | "입력 초기화" 클릭 |
| 기대 결과 1 | `_v1_total_mode_var = False`, `_v2_total_mode_var = False` |
| 기대 결과 2 | 모든 ItemRow 총액 모드 해제 (금액 필드 readonly, 단가 필드 활성) |
| 기대 결과 3 | VAT 라디오버튼 활성화 |
| 기대 결과 4 | 배너 숨김 (수정 모드 배너가 있었다면) |
| 기대 결과 5 | `_editing_purchase_id = None` |

---

### TC-18 ~ TC-20: 이력 불러오기 데이터 정합성

#### TC-18: 복사 불러오기 — 필드값 정확성

| 항목 | 내용 |
|------|------|
| 목적 | 이력에서 복사한 데이터가 폼에 정확히 채워지는지 확인 |
| 확인 항목 | 기안제목, 부서명, 기안일, 품명, 규격, 수량, 단위, 견적1/2 단가 및 금액 |
| 특히 주의 | `price_input_mode` 에 따라 올바른 필드(단가 or 금액)가 활성화되는지 |

#### TC-19: 다중 품목 불러오기

| 항목 | 내용 |
|------|------|
| 목적 | 품목 2개 이상인 기안을 불러올 때 ItemRow가 정확히 재현되는지 확인 |
| 사전 조건 | purchase_items 3개인 기안 존재 |
| 기대 결과 | ItemRow 3개 생성, 각 seq/item_name/spec/quantity/unit_price/v2_unit_price 일치 |

#### TC-20: v2_total_mode 복원

| 항목 | 내용 |
|------|------|
| 목적 | `price_input_mode="v2_total"` 로 저장된 기안을 불러올 때 견적2 금액 필드가 활성화되는지 확인 |
| 기대 결과 | 견적2 금액 입력 가능, 단가 readonly, VAT disabled |

---

## 3. 테스트 우선순위 매트릭스

| 우선순위 | 테스트 케이스 | 유형 | 합격 기준 |
|---------|-------------|------|----------|
| P0 (블로킹) | TC-02, TC-03, TC-04 | 계산 정확성 | 역산 오류 없음 |
| P0 (블로킹) | TC-06, TC-07 | DB 무결성 | 레코드 수 변화 검증 |
| P0 (블로킹) | TC-13 | 검수 연동 | 경고+삭제 정상 동작 |
| P1 (필수) | TC-01, TC-05 | 기본 동작 | 기존 단가 모드 회귀 없음 |
| P1 (필수) | TC-08, TC-09, TC-10 | UI 상태 | 콜백/배너/취소 정확 |
| P1 (필수) | TC-14, TC-15, TC-16 | VAT 전환 | 금액 재계산 정확 |
| P2 (권장) | TC-11, TC-12 | UI/파일 | 배너 숨김, 폴더 덮어쓰기 |
| P2 (권장) | TC-17, TC-18, TC-19, TC-20 | 폼 초기화/복원 | 모드 완전 리셋, 데이터 정합 |

---

## 4. 수동 테스트 절차 (UI 기반)

HWP COM이 필요 없는 범위의 테스트는 아래 순서로 수동 검증한다.
HWP 생성 테스트는 Windows + 한글 설치 환경에서만 가능.

### 4.1 VAT + 총액 모드 시나리오 (약 15분)

```
1. python main.py 실행
2. 구매 조사 탭 진입
3. 품목 추가 (품명: 토너, 수량: 3)
4. [견적1 총액입력] 체크 → 견적1 금액 필드 활성 확인
5. VAT 라디오 disabled 확인, 힌트 라벨 확인
6. 견적1 금액=30000 입력 → 단가=10000 자동 표시 확인
7. [견적2 총액입력] 체크 → VAT 여전히 disabled 확인
8. 견적2 금액=39000 입력 → 단가=13000 자동 표시 확인
9. 수량 3 → 5 변경 → 견적1 단가=6000, 견적2 단가=7800 확인
10. [견적1 총액입력] 체크 해제 → VAT 라디오 disabled 유지 확인 (견적2 총액 모드 유지)
11. [견적2 총액입력] 체크 해제 → VAT 라디오 활성 확인
```

### 4.2 복사 vs 수정 시나리오 (약 10분)

```
1. 기안 1건 생성 (품명: 노트북, 견적1=200000, 견적2=250000)
2. 이력 조회 탭 → 해당 항목 선택
3. [복사하여 새 기안] 클릭
   - 파란 배너 확인
   - 생성 버튼 텍스트 "생성" 확인
   - _editing_purchase_id 없음 (신규 모드)
4. 입력 초기화 → 배너 숨김 확인
5. 이력 조회 탭 → 동일 항목 선택
6. [수정하기] 클릭
   - 노란 배너 확인
   - 생성 버튼 텍스트 "재생성" 확인
   - "수정 취소" 버튼 표시 확인
7. 품명 수정 후 재생성
   - DB purchases 레코드 수 불변 확인
8. [수정 취소] → 폼 초기화, 배너 숨김 확인
```

### 4.3 검수 연동 시나리오 (약 10분)

```
1. 기안 생성 → 검수 입력 탭에서 검수 등록
2. 이력 조회 탭 → 검수 완료 항목 선택 ("검수" 컬럼 = "완료")
3. [수정하기] → 재생성 클릭
4. "검수 기록이 삭제됩니다" 경고 확인
5. 확인 후 "검수" 컬럼 "-" 변경 확인
6. DB inspections 레코드 삭제 확인
```

---

## 5. 자동화 테스트 확장 계획 (test_integration.py)

기존 `test_integration.py`에 아래 테스트를 추가한다.

### 5.1 총액 모드 계산 단위 테스트 (DB 없이)

```python
def test_item_row_price_modes():
    """PurchaseItem price_input_mode 별 calc_total 검증"""
    from core.models import PurchaseItem

    # Case A: unit mode
    item_a = PurchaseItem(seq=1, quantity=3, unit_price=10000,
                          price_input_mode="unit")
    assert item_a.calc_total() == 30000

    # Case B: v1_total mode (역산)
    item_b = PurchaseItem(seq=1, quantity=3, total_price=30000,
                          price_input_mode="v1_total")
    item_b.calc_total()
    assert item_b.unit_price == 10000  # 30000 // 3

    # Case D: total mode (역산)
    item_d = PurchaseItem(seq=1, quantity=3, total_price=30000,
                          price_input_mode="total")
    item_d.calc_total()
    assert item_d.unit_price == 10000
```

### 5.2 purchase_repo.update 테스트

```python
def test_purchase_update():
    """수정 모드: INSERT 후 UPDATE, 레코드 수 불변 확인"""
    from db import purchase_repo
    from core.models import PurchaseData, VendorQuote, PurchaseItem

    item = PurchaseItem(seq=1, item_name="수정전", quantity=1,
                        unit_price=10000, total_price=10000)
    v1 = VendorQuote(name="업체A", total_price=10000)
    v2 = VendorQuote(name="업체B", total_price=12000)
    data = PurchaseData(items=[item], vendor1=v1, vendor2=v2)

    pid = purchase_repo.insert(data)
    count_before = len(purchase_repo.select_all())

    item.item_name = "수정후"
    data2 = PurchaseData(items=[item], vendor1=v1, vendor2=v2)
    purchase_repo.update(pid, data2)
    purchase_repo.update_items(pid, [item])

    count_after = len(purchase_repo.select_all())
    row = purchase_repo.select_by_id(pid)

    purchase_repo.delete(pid)

    assert count_before == count_after, "UPDATE가 INSERT를 발생시키면 안 됨"
    assert row["item_name"] == "수정후", "UPDATE 반영 확인"
```

### 5.3 VAT 비활성화 조건 단위 테스트

```python
def test_vat_disable_condition():
    """어느 한쪽이라도 총액 모드이면 VAT 비활성 조건 성립"""
    # 이 테스트는 UI 레이어이므로 로직 함수 분리 후 테스트 가능
    # 현재는 ItemRow._on_total_mode_change 콜백을 통해 PurchaseTab._check_vat_state()가 호출됨
    # 콜백 체인 자체는 수동 테스트로 검증 (TC-02, TC-03, TC-16)
    pass  # 로직 분리 시 추가 예정
```

---

## 6. 합격 기준 (Acceptance Criteria)

### 6.1 필수 합격 (배포 차단 기준)

| 항목 | 기준 |
|------|------|
| 총액 역산 정확도 | `total // quantity` 값과 표시 단가 일치 (TC-02~04) |
| DB 무결성 | 복사=INSERT, 수정=UPDATE 분리 (TC-06, TC-07) |
| 검수 삭제 연동 | 수정 재생성 시 검수 레코드 삭제 확인 (TC-13) |
| 재진입 방지 | 수량 변경 시 무한 루프 없음 (TC-05) |
| 기존 기능 회귀 없음 | TC-01(단가 모드) 정상 동작 |

### 6.2 권장 합격

| 항목 | 기준 |
|------|------|
| 배너 색상 | `#D1ECF1`(복사) / `#FFF3CD`(수정) 정확 (TC-09) |
| 폼 초기화 완전성 | 모드 플래그 전부 초기화 (TC-17) |
| 다중 품목 복원 | N개 품목 불러오기 후 행 수 일치 (TC-19) |

### 6.3 품질 점수 목표

| 메트릭 | 목표 |
|--------|------|
| P0 테스트 합격률 | 100% |
| P1 테스트 합격률 | 100% |
| P2 테스트 합격률 | 80% 이상 |
| 전체 Match Rate | 90% 이상 |

---

## 7. 알려진 제약 및 외부 의존성

| 제약 | 내용 | 대응 |
|------|------|------|
| HWP COM 환경 | Windows + 한글 필수 | HWP 생성 테스트는 수동/별도 환경 |
| tkinter UI 자동화 | 외부 도구 없음 | 수동 테스트 절차(4절) 준수 |
| 파일 삭제 원자성 | PermissionError 재시도 로직 | `_delete_folder_with_retry` 동작 수동 확인 |
| `draft_templates` 테이블 | test_integration.py에 미포함 | 별도 수동 확인 권장 |

---

## 8. 미결 이슈 및 추후 검증 항목

| 항목 | 상태 | 비고 |
|------|------|------|
| `price_input_mode = "v2_total"` — PurchaseItem.calc_total() 미처리 | 위험 | `calc_total()`은 v1 모드만 분기, v2_total은 별도 처리 없음. 검토 필요. |
| 수정 모드 배너와 "복사 모드" 배너 공존 시나리오 | 미검증 | 복사 → 수정 전환 시 배너가 올바르게 교체되는지 확인 필요 |
| 다중 품목 + 총액 모드 + 수정 + 재생성 전체 통합 경로 | 미검증 | 가장 복잡한 경로로 별도 통합 테스트 필요 |

---

*이 문서는 v1.2 변경 기능에 대한 QA 전략이며, 전체 통합 테스트 완료 후 결과를 이 문서에 기록한다.*
