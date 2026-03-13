# 할인 단가 계산 + 구매건 수정/재생성 기능 계획서

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | (1) 인터넷 할인가로 2개 이상 구매 시 총액÷수량의 나머지 발생으로 단가×수량≠총액 불일치 (2) 문서 생성 후 수정/재생성 불가, 이력조회→복사→폴더명 변경의 번거로운 우회 필요 |
| **Solution** | (1) "총액 입력 모드" 추가: 총액 입력 → 단가 자동 역산 + VAT 자동 비활성화 (2) "수정 모드" 추가: 기존 구매건 불러오기 → 폼 수정 → 기존 폴더에 문서 덮어쓰기 재생성 |
| **Function UX Effect** | 총액 입력 시 단가가 자동 계산되어 1원 단위까지 정확한 공문서 생성, 기존 구매건을 탭 이동 없이 직접 수정·재생성 가능 |
| **Core Value** | 공공기관 비교견적 서류의 금액 정합성 100% 보장, 문서 수정 작업 시간 70% 단축 (5단계→2단계) |

---

## 의사결정 확정사항

| # | 항목 | 확정 | 근거 |
|---|------|------|------|
| D1 | 총액 입력 시 VAT | **자동 비활성화** — 총액 모드 활성화 시 VAT를 `inclusive`로 강제 설정 | 총액 입력은 이미 최종 금액이므로 VAT 이중 적용 방지 |
| D2 | 서류 비고 | **미기재 (사용자 직접)** — 시스템은 비고를 자동 기재하지 않음 | 공공기관마다 비고 표기 관행이 다르므로 사용자 재량 |
| D3 | 검수 완료 건 수정 | **경고 + 검수 삭제 연동** — 경고 다이얼로그 후 검수 기록 자동 삭제 + 재검수 안내 | 검수-구매 불일치 방지, 재검수 유도 |
| D4 | 폴더명 | **폴더명 유지** — 현재 기안명이 폴더명으로 지정되는 시스템 유지 | 폴더명 변경 시 외부 참조 깨짐 방지 |
| D5 | 개발 순서 | **Issue 2 먼저 → Issue 1 통합** — 수정 모드를 먼저 구현 후 총액 입력 모드를 그 위에 구축 | 수정 모드가 더 시급한 실무 문제 |

---

## CTO Team Brainstorming (6인 전문가 패널)

---

## Issue 1: 할인 단가 계산 문제

### 문제 상세 분석

**현재 흐름**:
```
사용자 입력: 단가 33,333원 × 수량 3개
시스템 계산: 33,333 × 3 = 99,999원
실제 결제액: 100,000원 (할인 적용 총액)
∴ 서류 금액 99,999원 ≠ 실제 결제액 100,000원 → 공문서 부정확
```

**실제 시나리오**:
- 쿠팡/네이버쇼핑에서 토너 3개 묶음 할인가 97,500원
- 단가 = 97,500 ÷ 3 = 32,500원 (나누어 떨어짐) → 문제 없음
- 토너 3개 할인가 100,000원
- 단가 = 100,000 ÷ 3 = 33,333.33... → **나머지 1원 발생**
- 서류에 33,333 × 3 = 99,999원 기재 → 실제 결제액과 1원 차이

**현재 코드 (`tab_purchase.py` ItemRow)**:
```python
# 현재: 단가 → 합계 (단방향)
def _recalc(self, *_):
    price = int(self.price_var.get().replace(",", ""))
    self.total_var.set(f"{round(price * mul) * qty:,}")
```
- 사용자가 단가만 입력 → 합계는 자동 계산 (readonly)
- **총액을 입력하여 단가를 역산하는 기능 없음**

---

### Expert 1: CTO / 기술 총괄

**판단**: 총액 입력 모드 추가 **승인**

핵심 설계 결정:

| 결정사항 | 확정안 | 이유 |
|----------|--------|------|
| 입력 모드 | 단가 입력(기존) + **총액 입력(신규)** 토글 | 기존 워크플로우 보존 |
| 나머지 처리 | 단가 = 총액÷수량 (내림), 총액은 사용자 입력값 고정 | 총액 정합성 최우선 |
| VAT 처리 | **총액 모드 시 VAT 자동 비활성화** (`inclusive` 강제) | [D1] 이중 적용 방지 |
| 비고 처리 | **미기재** — 사용자가 직접 비고 작성 | [D2] 기관별 관행 상이 |
| UI 전환 | 체크박스 "총액 입력" 토글 | 최소 UI 변경 |
| 다중 품목 | 품목별 독립 (총액 입력은 품목 단위) | 품목마다 할인율이 다를 수 있음 |

---

### Expert 2: 공공조달 도메인 전문가

**공공기관 금액 표기 규칙**:

1. **산출기초조사서**: 단가 × 수량 = 금액이 정확히 일치해야 함
2. **기안서**: 총 구매금액 = Σ(품목별 금액) 이 정확해야 함
3. **1원 차이도 감사 지적 가능** → 반드시 총액과 일치시켜야 함

**확정된 보정 방식 (방법 D)**:
```
총액 100,000원 ÷ 3개 = 33,333원 ... 나머지 1원

→ 단가: 33,333원 (내림), 수량: 3개, 총액: 100,000원 (사용자 입력값 고정)
→ 단가×수량=99,999 이지만 서류의 총액 필드는 100,000원 고정
→ 비고: 사용자가 필요 시 직접 기재 [D2]
```

**VAT 처리 [D1]**:
- 총액 입력 모드 활성화 시 → VAT 모드 자동으로 `inclusive`(VAT 포함) 설정
- VAT 체크박스 비활성화 (readonly), 도구팁: "총액 입력 시 VAT 별도 계산 불가"
- 총액 입력 모드 해제 시 → VAT 체크박스 복원

---

### Expert 3: 백엔드 아키텍트

**데이터 모델 변경 분석**:

현재 `PurchaseItem`:
```python
unit_price: int      # 단가
total_price: int     # = unit_price × quantity (항상)
```

**변경안**: `total_price`를 사용자 입력값으로 독립 저장 가능하게

```python
# 변경 후
unit_price: int           # 단가 (역산값 또는 직접 입력)
total_price: int          # 총액 (사용자 입력 or unit_price × quantity)
price_input_mode: str     # "unit" (단가 입력) | "total" (총액 입력)
```

**calc_total() 변경**:
```python
def calc_total(self) -> int:
    if self.price_input_mode == "total":
        # 총액 고정, 단가 역산 (나머지 무시)
        self.unit_price = self.total_price // self.quantity
        return self.total_price  # 사용자 입력 총액 유지
    else:
        # 기존 로직
        self.total_price = self.unit_price * self.quantity
        return self.total_price
```

**DB 영향**: `purchase_items` 테이블에 `price_input_mode TEXT DEFAULT 'unit'` 컬럼 추가 (하위 호환)

**v2 (비교 업체) 동일 적용**: `v2_unit_price`, `v2_total_price`도 같은 패턴

---

### Expert 4: 프론트엔드 아키텍트

**UI 변경안 (ItemRow)**:

```
현재:
┌────────────────────────────────────────────────┐
│ 품명 [     ] 규격 [     ] 단위 [  ] 수량 [ ]   │
│ 견적1 단가 [33,333] 합계 [99,999] (readonly)   │
│ 견적2 단가 [35,000] 합계 [105,000] (readonly)  │
└────────────────────────────────────────────────┘

변경 후:
┌────────────────────────────────────────────────┐
│ 품명 [     ] 규격 [     ] 단위 [  ] 수량 [ ]   │
│ ☐총액입력                                       │
│ 견적1 단가 [33,333] 합계 [100,000] ← 편집 가능  │
│ 견적2 단가 [35,000] 합계 [105,000] ← 편집 가능  │
└────────────────────────────────────────────────┘
```

**동작 로직**:
- `☐총액입력` 체크 OFF (기본): 기존과 동일 — 단가 입력 → 합계 자동
- `☐총액입력` 체크 ON:
  - 합계 Entry를 `readonly` → `normal`로 전환
  - 단가 Entry를 `normal` → `readonly`로 전환
  - 합계 입력 → 단가 자동 역산 (`total // quantity`)
  - 나머지 발생 시 단가 옆에 "(절사)" 표시
  - **VAT 체크박스 자동 비활성화** → `inclusive` 강제 [D1]

**_recalc() 변경**:
```python
def _recalc(self, *_):
    if self._total_input_mode.get():
        # 총액 입력 모드: 합계 → 단가 역산
        total = int(self.total_var.get().replace(",", ""))
        qty = self.qty_var.get()
        if qty > 0:
            unit = total // qty
            remainder = total - (unit * qty)
            self.price_var.set(f"{unit:,}")
            if remainder > 0:
                self._remainder_label.config(text=f"(절사 {remainder}원)")
            else:
                self._remainder_label.config(text="")
    else:
        # 기존 단가 입력 모드
        price = int(self.price_var.get().replace(",", ""))
        self.total_var.set(f"{round(price * mul) * qty:,}")
```

---

### Expert 5: QA / 테스트 전략가

**테스트 케이스 (Issue 1)**:

| # | 시나리오 | 입력 | 기대 결과 | 위험도 |
|---|----------|------|-----------|--------|
| T1 | 나누어 떨어지는 경우 | 총액 90,000 ÷ 3 | 단가 30,000, 합계 90,000 | 낮음 |
| T2 | 나머지 1원 | 총액 100,000 ÷ 3 | 단가 33,333, 합계 100,000 | 높음 |
| T3 | 나머지 다수 | 총액 100,007 ÷ 3 | 단가 33,335, 합계 100,007 | 높음 |
| T4 | 수량 1개 | 총액 50,000 ÷ 1 | 단가 50,000, 합계 50,000 | 낮음 |
| T5 | VAT 자동 비활성화 | 총액 모드 ON | VAT → inclusive 강제, 체크박스 disabled | **최고** |
| T6 | 모드 전환 | 단가→총액→단가 토글 | 값 정합성 유지, VAT 복원 | 높음 |
| T7 | HWP 문서 출력 | 총액 모드로 문서 생성 | 단가/합계 행 정확, 총액 고정 | **최고** |
| T8 | Excel 출력 | 총액 모드 검수내역서 | 단가/합계 열 정확 | 높음 |
| T9 | 다중 품목 혼합 | 품목1: 단가모드, 품목2: 총액모드 | grand_total 정확 | 높음 |

---

### Expert 6: 리스크 매니저

**Issue 1 리스크**:

| # | 리스크 | 확률 | 영향 | 대응 |
|---|--------|------|------|------|
| R1 | 총액 모드에서 VAT 이중 적용 | ~~중~~ **제거** | - | [D1] VAT 자동 비활성화로 원천 차단 |
| R2 | 단가×수량≠총액 표기가 감사 지적 | 낮 | 높 | [D2] 비고는 사용자 직접 기재 — 기관별 관행 대응 |
| R3 | 모드 전환 시 기존 값 유실 | 중 | 중 | 전환 시 확인 다이얼로그 |
| R4 | DB 마이그레이션 실패 | 낮 | 높 | DEFAULT 'unit' 하위 호환 |

---

## Issue 2: 구매건 수정/문서 재생성 기능

### 문제 상세 분석

**현재 워크플로우 (수정이 필요할 때)**:
```
1. 이력 조회 탭 → 해당 구매건 선택
2. "구매탭에 불러오기" 클릭 → 구매 조사 탭으로 이동
3. 구매 조사 탭에 데이터 로드됨
4. 수정 후 "산출기초조사서 생성" → 새 구매건 + 새 폴더 생성
5. 기존 구매건은 그대로 남아 있음 (중복)
6. 기존 폴더/파일 수동 삭제 필요

∴ 5단계 + 수동 정리 필요
```

**개선 워크플로우**:
```
1. 이력 조회 탭 → 해당 구매건 선택 → "구매탭에 불러오기"
2. 구매 조사 탭: "수정 모드" 표시, 기존 데이터 로드
3. 수정 후 "문서 재생성" → 기존 폴더에 덮어쓰기, DB 업데이트

∴ 3단계, 자동 처리
```

---

### Expert 1: CTO / 기술 총괄

**설계 결정**:

| 결정사항 | 확정안 | 이유 |
|----------|--------|------|
| 모드 구분 | "신규 모드" vs "수정 모드" | UI에서 명확히 구분 필요 |
| 문서 저장 | **기존 폴더에 덮어쓰기** | 폴더 중복 방지 |
| DB 처리 | **UPDATE** (기존 레코드) | INSERT(새 레코드) 아님 |
| 폴더명 | **변경하지 않음** — 기안명이 폴더명인 시스템 유지 [D4] | 외부 참조 안정성 |
| 검수 기록 | **경고 + 자동 삭제 + 재검수 안내** [D3] | 구매-검수 불일치 원천 차단 |

---

### Expert 3: 백엔드 아키텍트

**현재 `_load_to_purchase` 콜백 분석**:

`tab_history.py` → `app.py` → `tab_purchase.py`

```python
# app.py에서 콜백 연결
def _on_load_purchase(self, record, items):
    self.notebook.select(0)  # 구매 조사 탭으로 전환
    self.tab_purchase.load_purchase(record, items)
```

**현재 `tab_purchase.py`에 `load_purchase()` 존재 여부**: 있음 (불러오기 기능)
- 하지만 현재는 폼만 채우고 **신규 INSERT** 수행
- `_editing_purchase_id` 같은 수정 모드 상태 변수 없음

**필요한 변경**:

```python
class PurchaseTab:
    def __init__(self, ...):
        self._editing_purchase_id = None   # None = 신규, int = 수정 모드
        self._editing_doc_folder = None    # 기존 폴더 경로

    def load_purchase(self, record, items):
        """수정 모드로 기존 구매건 로드"""
        self._editing_purchase_id = record["id"]
        self._editing_doc_folder = record.get("doc_folder")
        self._fill_form(record, items)
        self._update_mode_indicator()  # "수정 모드" UI 표시

    def _generate_documents(self):
        if self._editing_purchase_id:
            self._regenerate_documents()  # UPDATE 경로
        else:
            self._create_new_documents()  # INSERT 경로 (기존)

    def _regenerate_documents(self):
        """기존 구매건 수정 + 문서 재생성"""
        # 1. 검수 기록 확인 → 경고 + 자동 삭제 [D3]
        # 2. purchase_repo.update(self._editing_purchase_id, data)
        # 3. purchase_repo.update_items(self._editing_purchase_id, items)
        # 4. 기존 폴더에 문서 덮어쓰기 [D4 폴더명 유지]
        # 5. purchase_repo.update_docs(...)
```

**purchase_repo.py 추가 함수**:
```python
def update(purchase_id: int, data: PurchaseData):
    """기존 구매건 UPDATE"""

def update_items(purchase_id: int, items: list[PurchaseItem]):
    """기존 품목 삭제 후 재삽입 (CASCADE 활용)"""
    conn.execute("DELETE FROM purchase_items WHERE purchase_id=?", (purchase_id,))
    _insert_items(conn, purchase_id, items)
```

**검수 삭제 연동 [D3]**:
```python
def _check_and_delete_inspection(self, purchase_id: int) -> bool:
    """검수 완료 건 확인 → 경고 → 자동 삭제"""
    inspections = inspection_repo.select_by_purchase(purchase_id)
    if not inspections:
        return True  # 검수 없음, 진행

    # 경고 다이얼로그
    result = messagebox.askyesno(
        "검수 기록 삭제 경고",
        "이 구매건은 검수가 완료되었습니다.\n\n"
        "수정을 진행하면 기존 검수 기록과 문서가\n"
        "자동으로 삭제됩니다.\n\n"
        "수정 후 검수 입력 탭에서 재검수하세요.\n\n"
        "계속하시겠습니까?",
        icon="warning"
    )
    if result:
        # 검수 기록 + 파일 삭제
        for insp in inspections:
            _delete_inspection_files(insp)
            inspection_repo.delete(insp["id"])
        return True
    return False
```

---

### Expert 4: 프론트엔드 아키텍트

**수정 모드 UI**:

```
┌─ 구매 조사 ─────────────────────────────────────────────┐
│ ⚠️ 수정 모드: "토너 구매" (2026-03-11) [수정 취소]       │ ← 노란색 배너
│ ─────────────────────────────────────────────────────── │
│ (기존 폼 그대로)                                         │
│ ...                                                      │
│ [산출기초조사서 재생성]  [기안서 재작성]                    │ ← 버튼 텍스트 변경
└──────────────────────────────────────────────────────────┘
```

**구현 요소**:
1. **모드 배너**: `ttk.Frame` (노란 배경), 품명 + 날짜 + "수정 취소" 버튼
2. **버튼 텍스트**: 수정 모드일 때 "생성" → "재생성"으로 변경
3. **"수정 취소"**: `_editing_purchase_id = None`, 폼 초기화, 배너 숨김
4. **폼 초기화 버튼**: 수정 모드에서는 "수정 취소"와 동일 동작
5. **폴더명 유지** [D4]: 기안명을 변경해도 기존 폴더 경로(`_editing_doc_folder`) 사용

---

### Expert 5: QA / 테스트 전략가

**테스트 케이스 (Issue 2)**:

| # | 시나리오 | 기대 결과 | 위험도 |
|---|----------|-----------|--------|
| T10 | 수정 모드 진입 | 기존 데이터 정확히 로드, 배너 표시 | 중간 |
| T11 | 단일 품목 수정 + 재생성 | 기존 폴더에 덮어쓰기, DB UPDATE | 높음 |
| T12 | 다중 품목 수정 (품목 추가) | 기존 품목 삭제→재삽입, 문서 정확 | **최고** |
| T13 | 다중 품목 수정 (품목 삭제) | 삭제된 품목 반영, grand_total 정확 | **최고** |
| T14 | 수정 취소 | 폼 초기화, 신규 모드 복귀 | 낮음 |
| T15 | 검수 완료 건 수정 | 경고 다이얼로그 → 검수 자동 삭제 [D3] | **최고** |
| T16 | 검수 삭제 후 재검수 | 검수 입력 탭에서 재검수 정상 동작 | 높음 |
| T17 | 수정 후 기안서 재작성 | 기존 업체 정보 유지, 기존 폴더에 저장 | 높음 |
| T18 | 수정 후 이력 조회 반영 | 수정된 데이터가 이력에 즉시 반영 | 중간 |
| T19 | 기안명 변경 + 폴더명 유지 | 기안명 변경해도 폴더 경로 불변 [D4] | 중간 |
| T20 | 캡처 이미지 수정 | 기존 캡처 유지 or 새 캡처로 교체 | 중간 |

---

### Expert 6: 리스크 매니저

**Issue 2 리스크**:

| # | 리스크 | 확률 | 영향 | 등급 | 대응 |
|---|--------|------|------|------|------|
| R5 | 검수 완료 건 수정으로 검수-구매 불일치 | ~~높~~ **제거** | - | - | [D3] 수정 시 검수 자동 삭제로 원천 차단 |
| R6 | 문서 덮어쓰기 실패 (파일 열려있음) | 중 | 중 | Medium | 기존 `_delete_folder_with_retry` 패턴 활용 |
| R7 | 기안명 변경 시 폴더와 불일치 | ~~중~~ **제거** | - | - | [D4] 폴더명 변경 안 함 |
| R8 | 수정 모드에서 앱 종료 시 상태 유실 | 낮 | 낮 | Low | 수정 모드는 메모리 상태만 (DB 미변경) |
| R9 | UPDATE 쿼리에서 purchase_items 불일치 | 중 | 높 | High | DELETE + re-INSERT 패턴 (CASCADE 활용) |
| R10 | 검수 삭제 시 파일 잔존 | 낮 | 중 | Medium | 기존 `_delete_inspection` 패턴 재활용 (파일→DB 순서) |

---

## 통합 작업 계획 (Step-by-Step)

> **개발 순서 [D5]**: Issue 2 (수정 모드) 먼저 → Issue 1 (총액 입력 모드) 통합

### Phase 1: 수정 모드 — DB 계층 (Issue 2)

| Step | 작업 | 파일 | 위험도 |
|------|------|------|--------|
| 1.1 | `purchase_repo.py`에 `update()` 함수 추가 (purchases 테이블 UPDATE) | db/purchase_repo.py | 중간 |
| 1.2 | `purchase_repo.py`에 `update_items()` 함수 추가 (DELETE + re-INSERT) | db/purchase_repo.py | 중간 |
| 1.3 | `purchase_repo.py`에 `update_docs()` 함수 수정 (문서 경로 UPDATE 지원 확인) | db/purchase_repo.py | 낮음 |

### Phase 2: 수정 모드 — UI 계층 (Issue 2)

| Step | 작업 | 파일 | 위험도 |
|------|------|------|--------|
| 2.1 | `_editing_purchase_id`, `_editing_doc_folder` 상태 변수 추가 | ui/tab_purchase.py | 낮음 |
| 2.2 | `load_purchase()` 메서드에 수정 모드 플래그 설정 | ui/tab_purchase.py | 중간 |
| 2.3 | 수정 모드 배너 UI 추가 (노란색 프레임 + 수정 취소 버튼) | ui/tab_purchase.py | 중간 |
| 2.4 | 버튼 텍스트 동적 변경 ("생성" ↔ "재생성") | ui/tab_purchase.py | 낮음 |
| 2.5 | "수정 취소" 버튼 동작 구현 (폼 초기화 + 배너 숨김) | ui/tab_purchase.py | 낮음 |
| 2.6 | 캡처 이미지 수정 모드 대응 (기존 유지 or 새로 캡처) | ui/tab_purchase.py | 중간 |

### Phase 3: 수정 모드 — 문서 재생성 (Issue 2, 핵심)

| Step | 작업 | 파일 | 위험도 |
|------|------|------|--------|
| 3.1 | `_generate_documents()` 분기: 신규 vs 수정 | ui/tab_purchase.py | 중간 |
| 3.2 | `_regenerate_documents()` 구현 — UPDATE + 기존 폴더 덮어쓰기 [D4] | ui/tab_purchase.py | **높음** |
| 3.3 | 검수 완료 건 수정 시 경고 + 검수 자동 삭제 [D3] | ui/tab_purchase.py | **높음** |
| 3.4 | 검수 삭제 시 파일도 함께 삭제 (기존 `_delete_inspection` 패턴 재활용) | ui/tab_purchase.py | 중간 |
| 3.5 | 재생성 완료 후 이력 조회 탭 refresh 연동 | ui/tab_purchase.py, ui/app.py | 낮음 |

### Phase 4: 총액 입력 모드 — 데이터 계층 (Issue 1)

| Step | 작업 | 파일 | 위험도 |
|------|------|------|--------|
| 4.1 | `PurchaseItem`에 `price_input_mode` 필드 추가 | core/models.py | 낮음 |
| 4.2 | `purchase_items` 테이블에 `price_input_mode` 컬럼 추가 (마이그레이션) | db/database.py | 낮음 |
| 4.3 | `calc_total()` 로직 수정 (총액 모드 대응) | core/models.py | 중간 |
| 4.4 | `purchase_repo.py`의 insert/update에 `price_input_mode` 반영 | db/purchase_repo.py | 낮음 |

### Phase 5: 총액 입력 모드 — UI 계층 (Issue 1)

| Step | 작업 | 파일 | 위험도 |
|------|------|------|--------|
| 5.1 | ItemRow에 "총액입력" 체크박스 추가 | ui/tab_purchase.py | 중간 |
| 5.2 | `_recalc()` 양방향 계산 로직 구현 | ui/tab_purchase.py | **높음** |
| 5.3 | 총액 Entry readonly ↔ normal 전환, 단가 Entry 반대 전환 | ui/tab_purchase.py | 중간 |
| 5.4 | 나머지 표시 라벨 추가 ("절사 N원") | ui/tab_purchase.py | 낮음 |
| 5.5 | VAT 자동 비활성화 연동 [D1] (총액 모드 ON → inclusive 강제) | ui/tab_purchase.py | 중간 |
| 5.6 | `get_data()`에서 모드별 값 추출 (`price_input_mode` 포함) | ui/tab_purchase.py | 중간 |
| 5.7 | 수정 모드에서 총액 입력 모드 복원 (불러오기 시 `price_input_mode` 반영) | ui/tab_purchase.py | 중간 |

### Phase 6: 문서 엔진 대응 (Issue 1)

| Step | 작업 | 파일 | 위험도 |
|------|------|------|--------|
| 6.1 | HWP 생성 시 총액 모드 단가/합계 처리 (총액 고정) | documents/hwp_generator.py | 중간 |
| 6.2 | Excel 생성 시 총액 모드 단가/합계 처리 | documents/excel_generator.py | 중간 |

### Phase 7: 검증 및 정리

| Step | 작업 | 위험도 |
|------|------|--------|
| 7.1 | T10~T20 테스트 (수정 모드) | - |
| 7.2 | T1~T9 테스트 (총액 입력 모드) | - |
| 7.3 | 수정 모드 + 총액 모드 통합 테스트 | - |
| 7.4 | CLAUDE.md 업데이트 | 없음 |
| 7.5 | EXE 재빌드 | 낮음 |

---

## 변경 파일 목록

| 파일 | Issue 2 (수정) | Issue 1 (총액) | 변경 유형 | Phase |
|------|:--------------:|:--------------:|-----------|-------|
| db/purchase_repo.py | ✅ | ✅ | 수정 (`update`, `update_items`, `price_input_mode`) | 1, 4 |
| ui/tab_purchase.py | ✅ | ✅ | **주요 수정** (수정 모드 + 총액 모드) | 2, 3, 5 |
| core/models.py | - | ✅ | 수정 (`price_input_mode`, `calc_total`) | 4 |
| db/database.py | - | ✅ | 수정 (마이그레이션) | 4 |
| documents/hwp_generator.py | - | ✅ | 수정 (총액 모드 대응) | 6 |
| documents/excel_generator.py | - | ✅ | 수정 (총액 모드 대응) | 6 |
| ui/app.py | ✅ | - | 수정 (재생성 후 refresh 연동) | 3 |
| CLAUDE.md | ✅ | ✅ | 문서 업데이트 | 7 |

---

## 예상 일정

| Phase | 내용 | 난이도 |
|-------|------|--------|
| Phase 1-3 | 수정 모드 전체 (DB + UI + 문서 재생성) | ★★★☆☆ |
| Phase 4-6 | 총액 입력 모드 전체 (데이터 + UI + 문서 엔진) | ★★★★☆ |
| Phase 7 | 통합 검증 + 빌드 | ★★☆☆☆ |

---

## 확정 의사결정 상세

### D1: VAT 자동 비활성화
- **시점**: 총액 입력 체크박스 ON
- **동작**: VAT 모드 → `inclusive` 강제, VAT 체크박스 disabled
- **복원**: 총액 입력 체크박스 OFF → VAT 체크박스 enabled, 이전 상태 복원
- **UI**: VAT 체크박스에 툴팁 "총액 입력 시 VAT 별도 계산 불가"

### D2: 비고 미기재
- **동작**: 시스템은 "할인 적용가" 등 비고를 자동 기재하지 않음
- **사용자**: 비고란에 필요한 내용을 직접 입력
- **코드 영향**: `hwp_generator.py`의 비고 치환 로직 변경 없음

### D3: 경고 + 검수 삭제 연동
- **시점**: 수정 모드에서 "재생성" 클릭 시 (검수 기록 존재할 때)
- **다이얼로그**:
  ```
  ⚠️ 검수 기록 삭제 경고

  이 구매건은 검수가 완료되었습니다.

  수정을 진행하면 기존 검수 기록과 문서가
  자동으로 삭제됩니다.

  수정 후 검수 입력 탭에서 재검수하세요.

  [예]  [아니오]
  ```
- **삭제 순서**: 검수 파일 삭제 → DB 삭제 (기존 `_delete_inspection` 패턴)
- **후처리**: 이력 조회 탭의 검수 상태 자동 갱신

### D4: 폴더명 유지
- **현재 시스템**: 기안명(draft title)이 폴더명으로 사용됨
- **수정 모드**: 기안명을 변경해도 `_editing_doc_folder` (기존 폴더 경로) 유지
- **문서 저장**: 기존 폴더에 덮어쓰기
- **신규 모드**: 기존과 동일 — 기안명으로 새 폴더 생성

### D5: 개발 순서
```
Phase 1-3: Issue 2 (수정 모드)
  ↓ 완료 후
Phase 4-6: Issue 1 (총액 입력 모드) — 수정 모드 위에 통합
  ↓ 완료 후
Phase 7: 통합 검증 + EXE 빌드
```
- Issue 1의 `price_input_mode`는 수정 모드의 `load_purchase()`에서도 복원해야 하므로 통합 시점이 자연스러움
