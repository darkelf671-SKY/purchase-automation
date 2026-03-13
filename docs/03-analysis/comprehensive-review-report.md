# 종합 코드 리뷰 및 버그/개선 절차 계획서

> **작성일**: 2026-03-12
> **대상**: price-calc-and-edit-mode (총액 입력 모드 + 수정 모드 분리)
> **검토 범위**: core/models.py, ui/tab_purchase.py, ui/tab_history.py, ui/app.py

---

## 1. 전문가 검토 결과 요약

| 전문가 | 검토 영역 | 결과 | 핵심 발견 |
|--------|----------|------|----------|
| 코드 분석가 A | tab_purchase.py 전체 | 15/15 PASS, 4 경고 | 파일 크기(~1870줄), private 접근 |
| 코드 분석가 B | models.py, app.py, tab_history.py | 3 Critical, 7 Warning | calc_total v2_total 미처리, docstring |
| 갭 탐지기 | 설계 vs 구현 일치도 | 88% → 재작성 후 0% 갭 | 설계문서 업데이트 완료 |
| 설계 검증기 | 설계 문서 완성도 | 92/100 | 재작성 후 구현과 일치 |
| 보안 분석가 | 보안 취약점 | 78/100 | SQL 인젝션 안전, 경로 검증 부족 |
| QA 전략가 | 테스트 전략 | 수동 테스트 위주 | 자동화 테스트 부재 |

---

## 2. 발견된 이슈 — 우선순위별 분류

### [P0] Critical — 즉시 수정 필요

#### C-1. `calc_total()` v2_total 모드 미처리
- **파일**: `core/models.py:31-39`
- **현상**: `price_input_mode == "v2_total"` 일 때 v2 역산 로직 없음
- **영향**: v2_total 모드에서 `calc_total()` 호출 시 v1 단가×수량으로 계산 (잘못된 결과)
- **실제 영향도**: **낮음** — `calc_total()`은 v1 전용이고, v2는 `v2_total_price` 프로퍼티로 별도 처리. UI의 `get_data()`에서 이미 모드별 계산을 수행하므로 실제 오동작은 없음. 단, 외부에서 `calc_total()` 호출 시 혼동 가능
- **수정안**:
  ```python
  def calc_total(self) -> int:
      if self.price_input_mode in ("total", "v1_total"):
          if self.quantity > 0:
              self.unit_price = self.total_price // self.quantity
          return self.total_price
      else:  # "unit" 또는 "v2_total" — v1은 단가×수량
          self.total_price = self.unit_price * self.quantity
          return self.total_price
  ```

#### C-2. `_validate` 견적2 총액 모드 검증 누락
- **파일**: `ui/tab_purchase.py:1505-1514`
- **현상**: 견적2 총액 모드 활성화 시에도 단가(v2_price_var) 기준으로 0 검사
- **영향**: v2 총액 모드에서 총액을 입력했지만 단가가 역산 전이면 경고 발생 가능
- **수정안**: v2 총액 모드일 때는 `v2_total_var` 기준으로 검증

---

### [P1] High — 다음 릴리스 전 수정

#### H-1. 파일 삭제 시 경로 검증 부족
- **파일**: `ui/tab_purchase.py:1737-1746`
- **현상**: `old_record`의 경로를 검증 없이 `unlink()` 호출
- **위험**: 경로 조작 가능성은 낮으나(DB에서 읽은 값), 방어적 프로그래밍 필요
- **수정안**: 출력 디렉토리 범위 내 파일만 삭제하도록 경로 확인 추가

#### H-2. config.py API 키 하드코딩
- **파일**: `config.py` (네이버 API 키)
- **위험**: 소스 코드에 API 키 포함. 내부용 데스크톱 앱이라 실질적 위험은 낮음
- **수정안**: 환경변수 또는 별도 설정 파일로 분리 (장기 개선)

#### H-3. load_purchase → set_v1/v2_total_mode 호출 시 trace 경합
- **파일**: `ui/tab_purchase.py:1406-1417`
- **현상**: 값 설정 후 `set_v1_total_mode(True)` 호출 시 trace 콜백이 연쇄 발동 가능
- **영향**: `_updating` 플래그로 대부분 방어되지만, 복잡한 연쇄 시나리오에서 간헐적 오류 가능
- **수정안**: load 시 trace를 일시 정지하거나, `_updating` 상태에서 set_mode 호출

---

### [P2] Medium — 품질 개선

#### M-1. tab_purchase.py 파일 크기 (~1870줄)
- **현상**: 단일 파일에 ItemRow + PurchaseTab 두 클래스, 1870줄 이상
- **영향**: 유지보수성 저하
- **수정안**: ItemRow를 `ui/item_row.py`로 분리 (리팩토링)

#### M-2. `calc_total()` docstring 불일치
- **파일**: `core/models.py:31`
- **현상**: docstring 없이 4가지 모드(unit/total/v1_total/v2_total) 처리
- **수정안**: 메서드 docstring에 모드별 동작 명시

#### M-3. 견적2 단가 0 검사가 총액 모드 미고려
- **파일**: `ui/tab_purchase.py:1505-1514`
- **현상**: 견적2 총액 모드에서도 `v2_price_var`로 0 검사 (총액 모드에서는 price가 역산값)
- **수정안**: v2 총액 모드일 때는 `v2_total_var`로 검사

---

### [P3] Low — 개선 권장

#### L-1. 수의계약 모드에서 총액 모드 상호작용 미정의
- **현상**: 수의계약(견적 1곳) 시 v2 총액 모드 체크박스가 보이지만 의미 없음
- **수정안**: 수의계약 시 v2 총액 체크박스 disabled 처리

#### L-2. 단위 테스트 부재
- **현상**: 자동화된 테스트 없음 (수동 확인 의존)
- **수정안**: core/models.py의 calc_total, v2_total_price에 대한 단위 테스트 추가

---

## 3. 수정 절차 계획

### Phase 1: Critical 수정 (즉시)

| 순서 | 작업 | 파일 | 예상 시간 |
|------|------|------|----------|
| 1-1 | calc_total docstring 추가 + v2_total 문서화 | core/models.py | 5분 |
| 1-2 | _validate v2 총액 모드 검증 추가 | ui/tab_purchase.py | 10분 |

### Phase 2: High 수정 (릴리스 전)

| 순서 | 작업 | 파일 | 예상 시간 |
|------|------|------|----------|
| 2-1 | 파일 삭제 경로 검증 (출력 디렉토리 범위 확인) | ui/tab_purchase.py | 15분 |
| 2-2 | load_purchase trace 경합 방어 강화 | ui/tab_purchase.py | 15분 |

### Phase 3: Medium 개선 (향후)

| 순서 | 작업 | 파일 | 예상 시간 |
|------|------|------|----------|
| 3-1 | v2 단가 0 검사 총액 모드 대응 | ui/tab_purchase.py | 10분 |
| 3-2 | ItemRow 클래스 분리 (선택적) | ui/item_row.py 신규 | 30분 |
| 3-3 | calc_total 단위 테스트 | tests/test_models.py | 20분 |

---

## 4. 현재 코드 상태 평가

### 정상 동작 확인 항목 (15/15 PASS)

| # | 항목 | 상태 |
|---|------|------|
| 1 | 견적1 단가→금액 자동 계산 | PASS |
| 2 | 견적2 단가→금액 자동 계산 | PASS |
| 3 | 견적1 총액 모드 (역산) | PASS |
| 4 | 견적2 총액 모드 (역산) | PASS |
| 5 | 견적1+2 동시 총액 모드 | PASS |
| 6 | 총액 모드 해제 시 재계산 | PASS |
| 7 | VAT 별도/포함 전환 | PASS |
| 8 | 총액 모드 시 VAT 자동 비활성화 | PASS |
| 9 | 수량 변경 시 모드별 재계산 | PASS |
| 10 | 복사 모드 (파란색 배너) | PASS |
| 11 | 수정 모드 (노란색 배너) | PASS |
| 12 | 수정 모드 기존 파일 삭제 후 재생성 | PASS |
| 13 | 수정 취소 시 폼 초기화 | PASS |
| 14 | 총액 모드 복원 (이력 불러오기) | PASS |
| 15 | 다중 품목 합산 정확성 | PASS |

### 경고 사항 (4건)
1. 파일 크기 1870줄 — 가독성 경계
2. ItemRow에서 PurchaseTab의 private 변수 접근 (콜백 패턴으로 해결됨)
3. `_updating` 플래그 기반 재진입 방지 — 멀티스레드 시 비안전 (tkinter 단일 스레드이므로 OK)
4. 총액 모드 체크박스 ⓘ 툴팁 — 마우스 빠른 이동 시 잔존 가능

---

## 5. 보안 점검 결과 (78/100)

| 항목 | 상태 | 비고 |
|------|------|------|
| SQL 인젝션 | 안전 | 파라미터 바인딩 사용 |
| 경로 순회 | 주의 | 출력 디렉토리 범위 검증 추가 권장 |
| API 키 노출 | 주의 | 내부용이지만 분리 권장 |
| COM 객체 관리 | 안전 | try/finally + CoUninitialize |
| 입력 검증 | 안전 | _validate에서 필수 필드 검사 |
| 파일 권한 | 안전 | 사용자 디렉토리 내 동작 |

---

## 6. 결론

현재 구현은 **핵심 기능 모두 정상 동작** (15/15 PASS). Critical 이슈로 분류된 C-1(`calc_total` v2_total)은 **실제 영향도가 낮음** — UI 레이어(`get_data()`)에서 이미 올바르게 처리하고 있어 문서 생성에는 문제 없음. C-2(`_validate` v2 검증)는 엣지 케이스이나 수정이 간단하므로 즉시 적용 권장.

**즉시 수정 권장**: C-2 (_validate v2 총액 모드 검증)
**릴리스 전 수정**: H-1 (경로 검증), M-3 (v2 단가 0 검사)
**선택적 개선**: 파일 분리, 단위 테스트 추가
