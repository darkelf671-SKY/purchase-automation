# 결제 수단 개선 기획 문서

> **Summary**: 업체별 복수 계좌 등록 + 건별 결제수단 오버라이드로 오입력 방지 및 실무 효율 개선
>
> **Project**: 구매기안 자동화 시스템 v1.0
> **Version**: v1.2
> **Author**: 전산팀 장길섭
> **Date**: 2026-03-12
> **Status**: Draft (실무자 피드백 반영 — v0.2)

---

## Executive Summary

| 관점 | 내용 |
|------|------|
| **문제** | 같은 업체라도 건마다 결제방법이 달라 매번 수동 입력하면 계좌번호 오입력 위험이 있고, 자동이체 납부 방식이 시스템에 없어 처리 불가 |
| **해결책** | 자동이체 납부 추가 + 업체별 복수 계좌 등록(최대 3개) + 구매 시 드롭다운 선택 — 직접 타이핑 경로 최소화 |
| **기능/UX 효과** | 결제수단 변경 시 등록된 계좌 드롭다운 선택, 건별 오버라이드는 DB에 기록되어 감사 추적 가능, 업체 기본값 자동 제안 |
| **핵심 가치** | 계좌번호 오입력 사고 예방 + 반복 구매 업체 결제 처리 속도 향상 + 감사 추적성 확보 |

---

## 1. 개요

### 1.1 목적

공공기관 물품 구매 시 사용되는 결제 수단 유형을 확장하고, 동일 업체라도 구매 건별로 다른 결제 수단을 선택할 수 있도록 한다. 생성되는 HWP 문서(기안서)의 `{{PAYMENT_METHOD}}` 자리표시자에 선택한 결제 수단에 맞는 형식의 텍스트가 삽입되어야 한다.

### 1.2 배경

- 현재 결제 수단은 업체 마스터(vendors 테이블)의 `payment_method` 컬럼에 등록된 법인카드/무통장입금 두 가지만 지원
- 일부 구매 건은 자동 이체 납부 방식으로 처리되나 현재 시스템에서 선택 불가
- 같은 업체와 거래해도 구매 건에 따라 결제 수단이 달라질 수 있으므로, 구매 건 단위의 결제 수단 지정이 필요
- **실무자 피드백**: "같은 업체가 건마다 결제방법을 다양하게 사용한다" — 무통장 전환 시 계좌번호 직접 타이핑이 오입력 위험을 야기

### 1.3 실무 시나리오 분석

| 시나리오 | 내용 | 빈도 | 현재 문제 |
|---------|------|------|-----------|
| A | 두인시스템 토너 구매 → 법인카드 (업체 기본값) | 높음 | 없음 |
| B | 두인시스템 서버 구매 → 무통장입금 (고가 장비, 기본값과 다름) | 중간 | 계좌번호 직접 입력 필요 |
| C | 동일 업체, 용도별 계좌가 다른 경우 | 낮음 | 계좌번호 직접 입력 필요 |
| D | 업체 기본값 카드 → 이번 건만 무통장 변경 | 높음 | 계좌번호 직접 입력 필요 |

**핵심 인사이트**: 결제방법 변경 빈도는 높으나 계좌 자체가 바뀌는 경우는 드물다. 업체별 복수 계좌를 미리 등록하면 드롭다운 선택으로 타이핑 없이 처리 가능.

### 1.3 관련 문서

- CLAUDE.md: 기안서 자리표시자 `{{PAYMENT_METHOD}}`, `{{PAYMENT_SECTION}}` 정의
- `documents/hwp_generator.py`: `generate_draft()` 내 결제 수단 치환 로직
- `db/vendor_repo.py`, `db/purchase_repo.py`: 업체 및 구매 데이터 저장소
- `ui/tab_purchase.py`: 구매 조사 탭 UI (기안 다이얼로그 포함)

---

## 2. 범위

### 2.1 포함 범위

- [ ] 결제 수단 Enum/상수에 "자동 이체 납부" 추가 (법인카드 / 무통장입금 / 자동 이체 납부)
- [ ] `vendor_accounts` 신규 테이블: 업체별 복수 계좌 등록 (최대 3개, 별칭 + 은행명 + 계좌번호)
- [ ] `purchases` 테이블에 `payment_method_override`, `vendor_account_id`, `bank_account_memo` 컬럼 추가
- [ ] 업체 관리 다이얼로그: 계좌 목록 UI (최대 3개, 별칭/은행명/계좌번호, 기본 계좌 지정)
- [ ] 기안 다이얼로그(DraftDialog): 결제 수단 Combobox + 무통장/자동이체 선택 시 계좌 드롭다운 표시
- [ ] `{{PAYMENT_METHOD}}` 자리표시자 치환 로직 수정:
  - 무통장입금: `"무통장입금, {은행명}, {계좌번호}, {예금주(대표자)}"`
  - 법인카드: `"법인카드 결제"`
  - 자동 이체 납부: `"자동 이체 납부"`
- [ ] 이력 조회(tab_history.py) 상세 패널에 사용된 결제 수단 표시
- [ ] 기존 데이터 하위 호환: `payment_method_override IS NULL` 인 경우 업체 기본값으로 폴백
- [ ] 기존 `vendors.bank_name`, `vendors.account_number` → `vendor_accounts` 마이그레이션

### 2.2 제외 범위

- 카드번호, 유효기간 등 법인카드 상세 정보 저장 (보안 위험)
- 계좌 3개 초과 등록 (실무 충분성 및 UI 단순성 유지)
- `{{PAYMENT_SECTION}}` 자리표시자 변경 (수의계약 고정 텍스트이므로 결제 수단과 무관)
- 모바일/웹 UI 변경
- 결제 프로필(N개) 시스템 (복잡도 대비 효용 낮음)

---

## 3. 요구사항

### 3.1 기능 요구사항

| ID | 요구사항 | 우선순위 | 상태 |
|----|----------|----------|------|
| FR-01 | 결제 수단 목록에 "자동 이체 납부" 추가 (업체 관리 탭 포함) | Must | 미완 |
| FR-02 | 기안 다이얼로그에서 결제 수단을 건별로 선택/변경 가능 | Must | 미완 |
| FR-03 | 업체 선택 시 해당 업체의 기본 결제 수단이 자동으로 Combobox에 채워짐 | Must | 미완 |
| FR-04 | `purchases` 테이블에 `payment_method_override`, `vendor_account_id` 컬럼 저장 | Must | 미완 |
| FR-05 | HWP 기안서의 `{{PAYMENT_METHOD}}` 치환 시 결제 수단별 포맷 적용 | Must | 미완 |
| FR-06 | 이력 조회 상세 패널에 구매 건에 적용된 결제 수단 표시 | Should | 미완 |
| FR-07 | 기존 `payment_method_override IS NULL` 레코드는 업체 기본 결제 수단으로 폴백 | Must | 미완 |
| FR-08 | 업체 관리 다이얼로그: 계좌 정보 최대 3개 등록/수정/삭제 (별칭, 은행명, 계좌번호) | Must | 미완 |
| FR-09 | 무통장/자동이체 선택 시 등록 계좌 드롭다운 표시, 법인카드 선택 시 숨김 | Must | 미완 |
| FR-10 | 등록된 계좌 없을 경우 직접 입력 폴백 허용 (신규 업체 또는 임시 계좌) | Should | 미완 |
| FR-11 | 기존 단일 계좌 데이터 `vendor_accounts` 테이블로 자동 마이그레이션 | Must | 미완 |

### 3.2 비기능 요구사항

| 범주 | 기준 | 측정 방법 |
|------|------|-----------|
| 하위 호환성 | 기존 purchases 레코드에서 override가 NULL일 때 문서 생성 시 오류 없음 | 기존 데이터로 HWP 생성 테스트 |
| DB 마이그레이션 | app 최초 실행 시 신규 컬럼 및 `vendor_accounts` 테이블 자동 생성 | `database.py` 마이그레이션 로직 |
| UI 일관성 | 결제 수단 Combobox가 업체 관리 탭과 기안 다이얼로그 양쪽에서 동일한 선택지 제공 | 직접 확인 |
| 오입력 방지 | 등록된 계좌가 있으면 드롭다운 선택 경로를 우선, 직접 타이핑은 폴백으로만 | UI 플로우 확인 |
| 감사 추적성 | 건별 선택된 결제수단·계좌 DB 영구 보존 | purchases 테이블 컬럼 확인 |

---

## 4. DB 설계 (추가)

### 4.1 신규 테이블: `vendor_accounts`

```sql
CREATE TABLE vendor_accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id   INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    alias       TEXT,                    -- 별칭 (예: "물품대금용")
    bank_name   TEXT,                    -- 은행명
    account_no  TEXT NOT NULL,           -- 계좌번호
    is_default  INTEGER DEFAULT 0,       -- 기본 계좌 여부 (1=기본)
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 `purchases` 테이블 추가 컬럼

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `payment_method_override` | TEXT | NULL이면 업체 기본값 폴백 |
| `vendor_account_id` | INTEGER | `vendor_accounts.id` 참조 (NULL 허용) |
| `bank_account_memo` | TEXT | 드롭다운에 없을 때 직접 입력값 저장 |

### 4.3 마이그레이션 전략

- 기존 `vendors.bank_name`, `vendors.account_number` 데이터를 `vendor_accounts` 테이블로 자동 복사
- 기존 컬럼은 삭제하지 않고 deprecated 유지 (EXE 배포 환경 하위 호환)

---

## 5. 사용자 스토리

### US-00: 업체 복수 계좌 등록

> 구매담당자로서, 업체 관리 탭에서 동일 업체에 여러 계좌를 등록하고 각 계좌에 별칭을 붙여 구분할 수 있다.

**인수 기준**:
- [ ] 업체 추가/수정 다이얼로그에서 계좌를 최대 3개 등록할 수 있다.
- [ ] 계좌별 별칭(예: "물품대금용"), 은행명, 계좌번호를 입력할 수 있다.
- [ ] 기본 계좌를 지정할 수 있으며, 무통장 선택 시 기본 계좌가 자동 선택된다.
- [ ] 3개 초과 시 "추가" 버튼이 비활성화된다.

### US-01: 자동 이체 납부 업체 등록

> 구매담당자로서, 업체 관리 탭에서 업체의 기본 결제 수단으로 "자동 이체 납부"를 선택하고 저장할 수 있다.

**인수 기준**:
- [ ] 업체 추가/수정 다이얼로그의 결제 수단 Combobox에 "자동 이체 납부" 선택지가 표시된다.
- [ ] "자동 이체 납부"로 저장된 업체가 업체 목록에 정상 표시된다.

### US-02: 구매 건별 결제 수단 오버라이드

> 구매담당자로서, 기안서 작성 시 업체에 등록된 기본 결제 수단 대신 다른 결제 수단을 선택하여 해당 구매 건에만 적용할 수 있다.

**인수 기준**:
- [ ] 기안 다이얼로그에 결제 수단 Combobox가 표시된다.
- [ ] 업체를 선택하면 해당 업체의 기본 결제 수단이 자동으로 선택된다.
- [ ] 무통장/자동이체 선택 시 해당 업체의 등록 계좌 드롭다운이 표시된다.
- [ ] 법인카드 선택 시 계좌 드롭다운이 숨겨진다.
- [ ] 사용자가 다른 결제 수단으로 변경하면 그 값이 `payment_method_override`에 저장된다.
- [ ] 변경된 결제 수단은 해당 구매 건의 기안서에만 적용되고, 업체 마스터 데이터는 변경되지 않는다.

### US-03: HWP 문서에 결제 수단 자동 반영

> 구매담당자로서, HWP 기안서를 생성하면 선택한 결제 수단에 맞는 형식의 텍스트가 `{{PAYMENT_METHOD}}` 위치에 자동으로 삽입된다.

**인수 기준**:
- [ ] 무통장입금 선택 시: `"무통장입금, {은행명}, {계좌번호}, {예금주(대표자)}"` 형식으로 삽입된다.
- [ ] 법인카드 선택 시: `"법인카드 결제"` 로 삽입된다.
- [ ] 자동 이체 납부 선택 시: `"자동 이체 납부"` 로 삽입된다.
- [ ] `payment_method_override`가 NULL인 구매 건은 업체 기본 결제 수단을 사용하여 정상 생성된다.

### US-04: 이력 조회에서 결제 수단 확인

> 구매담당자로서, 이력 조회 탭에서 과거 구매 건의 상세 정보를 확인할 때 해당 건에 적용된 결제 수단을 볼 수 있다.

**인수 기준**:
- [ ] 이력 조회 상세 패널에 "결제 수단" 항목이 표시된다.
- [ ] 표시 값은 `payment_method_override`가 있으면 그 값, 없으면 업체 기본값을 보여준다.

---

## 6. 성공 기준

### 6.1 완료 정의

- [ ] FR-01~FR-11 모든 기능 요구사항 구현 완료
- [ ] 업체관리에서 계좌 최대 3개 등록/수정/삭제 동작 확인
- [ ] 무통장 선택 시 계좌 드롭다운, 법인카드 선택 시 계좌 드롭다운 숨김 확인
- [ ] 기존 데이터로 HWP 생성 시 오류 없음 (하위 호환 검증)
- [ ] `python main.py`로 UI 실행 및 기안 다이얼로그에서 결제 수단 변경 후 저장 확인
- [ ] 결제 수단별 3가지 `{{PAYMENT_METHOD}}` 치환 결과 확인
- [ ] 건별 선택된 계좌가 DB에 저장되고 이력 조회에서 확인 가능

### 6.2 품질 기준

- [ ] DB 마이그레이션 자동 적용 (수동 SQL 실행 불필요)
- [ ] 결제 수단 상수/Enum이 단일 위치에서 관리되어 향후 추가 시 한 곳만 수정
- [ ] 계좌번호 직접 타이핑 경로 최소화 (드롭다운 선택 경로 우선)

---

## 7. 위험 및 대응

| 위험 | 영향도 | 발생 가능성 | 대응 방안 |
|------|--------|-------------|-----------|
| DB 마이그레이션 누락으로 기존 DB에서 컬럼 없음 오류 | 높음 | 중간 | `database.py`의 `_migrate()` 함수에 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 추가 |
| 기존 단일 계좌 데이터 마이그레이션 오류 | 높음 | 낮음 | 마이그레이션 스크립트 사전 테스트, 기존 컬럼 deprecated 유지 |
| 업체 기본 결제 수단이 NULL인 레코드에서 폴백 처리 미흡 | 중간 | 낮음 | `hwp_generator.py`에서 None 체크 후 기본값("무통장입금") 적용 |
| 자동 이체 납부 선택 시 은행 계좌 정보 입력을 요구하는 혼동 | 낮음 | 중간 | UI에 "자동 이체 납부는 별도 계좌 정보 없이 출력됩니다" 안내 툴팁 추가 (Could) |
| `{{PAYMENT_SECTION}}`과의 혼동 (계약방법과 결제 수단을 다른 개념으로 명확히 구분) | 중간 | 낮음 | 코드 주석 및 문서에 명확히 구분: `PAYMENT_METHOD`=결제 수단, `PAYMENT_SECTION`=계약방법(수의계약 고정) |
| 계좌 3개 초과 등록 시도 | 낮음 | 중간 | UI에서 3개 초과 시 "추가" 버튼 비활성화 |

---

## 8. 아키텍처 고려사항

### 8.1 영향 받는 컴포넌트

| 레이어 | 파일 | 변경 내용 |
|--------|------|-----------|
| DB 스키마 | `db/database.py` | `vendor_accounts` 테이블 생성 + `purchases` 컬럼 마이그레이션 |
| 데이터 모델 | `core/models.py` | `VendorAccount` 모델 추가, `PurchaseData` 필드 추가 |
| 저장소 | `db/vendor_repo.py` | 계좌 CRUD 추가 + 결제 수단 Enum 상수 추가 |
| 저장소 | `db/purchase_repo.py` | INSERT/UPDATE/SELECT 시 `payment_method_override`, `vendor_account_id` 처리 |
| 문서 생성 | `documents/hwp_generator.py` | `{{PAYMENT_METHOD}}` 치환 로직 수정 (3-way 분기) |
| UI | `ui/tab_vendor.py` | 계좌 목록 UI 추가 (최대 3개, 별칭/은행명/계좌번호) |
| UI | `ui/tab_purchase.py` (DraftDialog) | 결제 수단 Combobox + 계좌 드롭다운 연동 |
| UI | `ui/tab_history.py` | 상세 패널에 결제 수단 행 추가 |

### 8.2 결제 수단 상수 관리

```python
# config.py 또는 core/models.py 에 단일 정의 권장
PAYMENT_METHODS = ["법인카드", "무통장입금", "자동 이체 납부"]
```

### 8.3 `{{PAYMENT_METHOD}}` 치환 로직

```python
# hwp_generator.py 변경 로직 (의사 코드)
method = data.payment_method_override or vendor.payment_method or "무통장입금"

if method == "무통장입금":
    payment_text = f"무통장입금, {vendor.bank_name}, {vendor.account_number}, {vendor.ceo_name}"
elif method == "법인카드":
    payment_text = "법인카드 결제"
elif method == "자동 이체 납부":
    payment_text = "자동 이체 납부"
else:
    payment_text = method  # 알 수 없는 값은 그대로 출력
```

### 8.4 DB 마이그레이션 방식

기존 `database.py`의 `_migrate()` 패턴 사용:

```sql
-- 신규 테이블
CREATE TABLE IF NOT EXISTS vendor_accounts (...);

-- purchases 컬럼 추가
ALTER TABLE purchases ADD COLUMN payment_method_override TEXT;
ALTER TABLE purchases ADD COLUMN vendor_account_id INTEGER;
ALTER TABLE purchases ADD COLUMN bank_account_memo TEXT;

-- 기존 단일 계좌 데이터 마이그레이션
INSERT INTO vendor_accounts (vendor_id, bank_name, account_no, is_default)
SELECT id, bank_name, account_number, 1
FROM vendors
WHERE account_number IS NOT NULL AND account_number != '';
```

---

## 9. 우선순위 (MoSCoW)

| 우선순위 | 항목 |
|----------|------|
| Must | FR-01, FR-02, FR-03, FR-04, FR-05, FR-07, FR-08, FR-09, FR-11 (핵심 기능, 복수 계좌, 하위 호환) |
| Should | FR-06 (이력 조회 결제 수단 표시), FR-10 (직접 입력 폴백) |
| Could | 자동 이체 납부 선택 시 UI 안내 툴팁, 계좌별 별칭 |
| Won't | 카드번호/유효기간 등 법인카드 상세 정보 저장, 결제 프로필 N개 시스템 |

---

## 10. 미해결 질문 (CTO 검토 요청)

1. **자동 이체 납부의 은행 계좌 정보 필요 여부**: 현재 계획은 단순 텍스트 `"자동 이체 납부"` 출력. 실제 문서 양식에서 계좌 정보가 필요한지 확인 필요.
2. **결제 수단 상수 위치**: `config.py` vs `core/models.py` 중 어디에 정의할지 팀 합의 필요.
3. **업체 기본 결제 수단 NULL 처리**: 현재 일부 업체 레코드에 `payment_method`가 NULL일 수 있음. 기본값을 "무통장입금"으로 강제할지, 기안 다이얼로그에서 필수 선택으로 할지 결정 필요.
4. **계좌 드롭다운 표시 형식**: `"물품대금용 - 신한은행 110-123-456789"` vs `"신한은행 / 110-123-456789"` 중 어느 포맷이 선호되는지 확인 필요.
5. **`vendor_accounts` 별칭 필수 여부**: 별칭 없이 은행명+계좌번호만으로도 충분한지, 또는 별칭을 필수로 요구할지 결정 필요.

---

## 11. 다음 단계

1. [ ] CTO(팀 리드) 검토 및 승인
2. [ ] 미해결 질문 10.1~10.5 확인 후 설계 문서 작성
3. [ ] `vendor_accounts` 테이블 및 마이그레이션 구현
4. [ ] 업체 다이얼로그 계좌 목록 UI 구현
5. [ ] 구매조사 탭 계좌 드롭다운 연동
6. [ ] HWP 치환 로직 업데이트
7. [ ] 통합 테스트 (`python main.py`)

---

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 0.1 | 2026-03-12 | 최초 작성 | Product Manager |
| 0.2 | 2026-03-12 | 실무자 피드백 반영 — 복수 계좌 등록(최대 3개), 계좌 드롭다운 선택, 오입력 방지 방안 추가 | Product Manager |
