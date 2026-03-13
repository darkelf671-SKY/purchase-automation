# 결제방법 3종 확장 + 건별 오버라이드 — 종합 설계서

> **작성일**: 2026-03-12
> **Phase**: Design
> **심각도**: High (데이터 모델 + UI + 문서 생성 동시 변경)
> **검토팀**: CTO + 프론트엔드 아키텍트 + 보안 아키텍트 + 코드 분석가 + QA 전략가 + 제품 관리자

---

## Executive Summary

| 관점 | 내용 |
|------|------|
| **문제** | 결제방법이 법인카드/무통장입금 2종만 지원, 자동이체 미지원. 구매건별 결제방법 지정 불가 (업체 고정값만 사용) |
| **해결책** | 결제방법 enum에 `auto_transfer` 추가, `purchases` 테이블에 스냅샷 컬럼 4개 추가, 기안서 작성 시 건별 결제방법 선택 UI |
| **기능/UX 효과** | 기안서 작성 시 결제방법 3종 선택 가능, HWP 문서에 은행 정보 포함 자동 삽입 |
| **핵심 가치** | 결제방법 다양성 지원으로 문서 자동화 적용 범위 확대, 과거 구매건의 결제 정보 불변성 보장 |

---

## 1. 현재 상태 분석

### 1.1 데이터 흐름

```
[업체 관리 (tab_vendor.py)]
  vendors.payment_method = "card" | "transfer"
        │
        ▼
[구매 조사 (tab_purchase.py)]
  _draft_vendor_var → vendor dict 조회
  vendor dict를 그대로 generate_draft()에 전달
        │
        ▼  ★ 스냅샷 없이 vendor dict 직접 사용
[HWP 생성기 (hwp_generator.py)]
  vendor.get("payment_method", "card") → "법인카드" / "무통장입금"
  {{PAYMENT_METHOD}} 치환
```

### 1.2 핵심 문제점

| # | 문제 | 영향 |
|---|------|------|
| 1 | `payment_method`가 2값(card/transfer)만 지원 | 자동이체 구매건 처리 불가 |
| 2 | `purchases` 테이블에 결제방법 컬럼 없음 | 업체 정보 변경 시 과거 기안서 정합성 깨짐 |
| 3 | 건별 결제방법 오버라이드 불가 | 같은 업체에 다른 결제방법 적용 불가 |
| 4 | `{{PAYMENT_METHOD}}`가 단순 라벨만 출력 | 무통장입금 시 은행 정보 미포함 |
| 5 | 모든 분기가 if/else (binary) | 3번째 값 추가 시 오류 발생 지점 다수 |

---

## 2. 전문가 분석 종합

### 2.1 CTO 아키텍처 결정

**결정 A: purchases 테이블에 결제 스냅샷 4개 컬럼 추가**

```sql
ALTER TABLE purchases ADD COLUMN payment_method  TEXT DEFAULT '';
ALTER TABLE purchases ADD COLUMN payment_bank    TEXT DEFAULT '';
ALTER TABLE purchases ADD COLUMN payment_account TEXT DEFAULT '';
ALTER TABLE purchases ADD COLUMN payment_holder  TEXT DEFAULT '';
```

- 빈 문자열(`''`) = vendor에서 폴백 → **하위 호환 100% 보장**
- 공공기관 문서의 법적 정합성: 구매 시점의 결제 정보 불변 보장

**결정 B: generate_draft() 시그니처 확장**

```python
def generate_draft(self, data, draft_info, vendor, out_dir,
                   has_payment, sole_reason, attachment_files,
                   payment_override=None)
# payment_override = {"method": "transfer", "bank": "...", "account": "...", "holder": "..."}
# None이면 vendor에서 상속 (하위 호환)
```

**결정 C: 결제방법 상수 중앙화**

```python
# config.py 에 추가
PAYMENT_METHODS = {
    "card":          "법인카드 결제",
    "transfer":      "무통장입금",
    "auto_transfer": "자동 이체 납부",
}
```

### 2.2 프론트엔드 아키텍트 UI 설계

#### VendorDialog 변경 (row 4)

```
결제방법:  [o] 법인카드   [o] 무통장입금   [o] 자동 이체 납부
```

- `_toggle_transfer()`: `"transfer"` OR `"auto_transfer"` → 은행 필드 활성화
- `_apply_filter()`: 3값 매핑 dict 사용

#### PurchaseTab 추가 (row 11~12)

```
row 10 │ [업체 정보 LabelFrame — 대표자/사업자번호/주소/기본결제]    ← 기본결제 행 추가
row 11 │ 결제방법 *:  [o] 법인카드  [o] 무통장입금  [o] 자동 이체 납부
row 12 │ [은행 정보 LabelFrame — 은행명/예금주/계좌번호]             ← 조건부 표시
```

- 업체 선택 시 → 업체 기본 결제방법으로 자동 선택
- 사용자가 건별 오버라이드 가능
- 무통장입금/자동이체 시 은행 정보 프레임 표시
- 법인카드 시 `grid_remove()` 숨김

### 2.3 보안 아키텍트 평가

| 위험 | 심각도 | 완화 방안 |
|------|--------|-----------|
| build_exe.py 시드 DB에 은행 계좌 정보 포함 | **High** | 시드 DB 복사 시 bank_name/account_holder/account_no 공백 처리 |
| DB 내 계좌번호 평문 저장 | Medium | 로컬 앱 특성상 수용. OS BitLocker 권장 |
| 스크린샷 캡처 시 계좌 정보 노출 가능 | Medium | UI에서 별도 토글/섹션 분리 고려 |
| SQL Injection | Low (양호) | 파라미터 바인딩 적용됨 |
| HWP 템플릿 인젝션 | Low (양호) | clean 정제 로직 적용됨 |

### 2.4 코드 분석가 — 수정 대상 전수 조사

**총 수정 파일: 5개, 수정 지점: 8곳**

| # | 파일 | 행 | 수정 유형 | 난이도 |
|---|------|----|-----------|--------|
| 1 | `db/database.py` | `_migrate()` | purchases 4개 컬럼 마이그레이션 추가 | 쉬움 |
| 2 | `db/purchase_repo.py` | insert/update | payment 4개 컬럼 저장 | 쉬움 |
| 3 | `ui/tab_vendor.py:66` | `_apply_filter` | if/else → dict 매핑 | 쉬움 |
| 4 | `ui/tab_vendor.py:131-134` | VendorDialog | 라디오버튼 1개 추가 | 쉬움 |
| 5 | `ui/tab_vendor.py:155-156` | `_toggle_transfer` | 조건 확장 | 쉬움 |
| 6 | `ui/tab_purchase.py:767-784` | draft_frame | 결제방법 UI 추가 (row 11~12) | 보통 |
| 7 | `ui/tab_purchase.py:1070-1077` | `_on_draft_vendor_select` | 결제방법/은행 자동 채움 | 보통 |
| 8 | `documents/hwp_generator.py:531-534` | `{{PAYMENT_METHOD}}` | 3값 포맷팅 + 은행 정보 | 보통 |

**수정 불필요 확인 완료:**
- `db/vendor_repo.py` — 바인드 파라미터 사용, 변경 불필요
- `ui/tab_history.py` — payment 관련 코드 없음
- `ui/tab_inspection.py` — payment 관련 코드 없음
- `core/models.py` — payment_method 필드 없음 (dict 전달)
- `build_exe.py` — 보안 조치만 필요 (은행 정보 제거)

### 2.5 QA 전략가 — 테스트 매트릭스 (44개 케이스)

| 카테고리 | 케이스 수 | 우선순위 분포 |
|----------|-----------|---------------|
| 업체 관리 (VM) | 12 | 필수 5, 높음 4, 중간 3 |
| 구매 조사 (PT) | 10 | 필수 6, 높음 1, 중간 3 |
| HWP 생성 (HG) | 10 | 필수 3, 높음 3, 중간 3, 낮음 1 |
| 수정 모드 (EM) | 4 | 필수 3, 높음 1 |
| 마이그레이션 (MG) | 5 | 필수 4, 중간 1 |
| 엣지 케이스 (EC) | 6 | 높음 3, 중간 2, 낮음 1 |

**Critical 위험 4건 (반드시 수정):**
1. `tab_vendor.py:66` — binary 분기 → `auto_transfer` 시 "무통장입금"으로 오표시
2. `hwp_generator.py:531-534` — binary 분기 → `auto_transfer` 미처리
3. `database.py` — purchases 테이블에 payment_method 컬럼 누락
4. `purchase_repo.py` — INSERT/UPDATE에 payment_method 미포함

### 2.6 제품 관리자 — MoSCoW 우선순위

| Must (반드시) | Should (해야) | Could (가능하면) | Won't (안 함) |
|---------------|---------------|------------------|----------------|
| 자동이체 3번째 옵션 추가 | 이력조회 결제방법 표시 | 자동이체 선택 시 UI 툴팁 | 자동이체용 별도 계좌 입력 |
| 건별 결제방법 선택 UI | | | |
| DB 저장 (스냅샷) | | | |
| HWP `{{PAYMENT_METHOD}}` 포맷팅 | | | |
| 하위 호환 (기존 데이터 무결) | | | |

---

## 3. `{{PAYMENT_METHOD}}` 출력 형식 정의

| 결제방법 코드 | HWP 출력 텍스트 | 예시 |
|--------------|-----------------|------|
| `"card"` | `"법인카드 결제"` | 법인카드 결제 |
| `"transfer"` | `"무통장입금, {은행명}, {계좌번호}, {예금주(대표자)}"` | 무통장입금, 신한은행, 140-014-029895, 두인시스템(원희수) |
| `"auto_transfer"` | `"자동 이체 납부"` | 자동 이체 납부 |

### 무통장입금 포맷팅 로직

```python
def _format_payment_method(pay_code: str, vendor: dict) -> str:
    if pay_code == "card":
        return "법인카드 결제"
    elif pay_code == "transfer":
        bank   = vendor.get("bank_name", "")
        acct   = vendor.get("account_no", "")
        holder = vendor.get("account_holder", "")
        ceo    = vendor.get("ceo", "")
        # 예금주(대표자) 형식
        holder_part = f"{holder}({ceo})" if holder and ceo else holder or ceo or ""
        parts = [p for p in ["무통장입금", bank, acct, holder_part] if p]
        return ", ".join(parts)
    elif pay_code == "auto_transfer":
        return "자동 이체 납부"
    else:
        return "법인카드 결제"  # 폴백
```

---

## 4. 구현 순서 (5 Phase)

### Phase 1: DB 계층 (하위 호환 보장)

| 순서 | 작업 | 파일 | 난이도 |
|------|------|------|--------|
| 1-1 | `config.py`에 `PAYMENT_METHODS` 상수 추가 | config.py | 쉬움 |
| 1-2 | `_migrate()`에 purchases 4컬럼 추가 | database.py | 쉬움 |
| 1-3 | `insert()`/`update()`에 payment 컬럼 반영 | purchase_repo.py | 쉬움 |

### Phase 2: 업체 관리 UI

| 순서 | 작업 | 파일 | 난이도 |
|------|------|------|--------|
| 2-1 | 라디오버튼 3개 확장 | tab_vendor.py | 쉬움 |
| 2-2 | `_toggle_transfer()` 조건 확장 | tab_vendor.py | 쉬움 |
| 2-3 | Treeview 표시 3값 매핑 | tab_vendor.py | 쉬움 |

### Phase 3: 구매 조사 UI

| 순서 | 작업 | 파일 | 난이도 |
|------|------|------|--------|
| 3-1 | row 10 업체정보에 "기본결제" 행 추가 | tab_purchase.py | 쉬움 |
| 3-2 | row 11 결제방법 라디오 3종 추가 | tab_purchase.py | 보통 |
| 3-3 | row 12 은행 정보 프레임 (조건부) | tab_purchase.py | 보통 |
| 3-4 | `_on_draft_vendor_select()` 연동 | tab_purchase.py | 보통 |
| 3-5 | `_on_pay_method_change()` 신규 | tab_purchase.py | 쉬움 |
| 3-6 | `_reset_form()` 초기화 항목 추가 | tab_purchase.py | 쉬움 |
| 3-7 | `load_purchase()` 결제방법 복원 | tab_purchase.py | 보통 |
| 3-8 | `_build_purchase_data()` 결제방법 전달 | tab_purchase.py | 보통 |

### Phase 4: HWP 문서 생성

| 순서 | 작업 | 파일 | 난이도 |
|------|------|------|--------|
| 4-1 | `_format_payment_method()` 함수 추가 | hwp_generator.py | 보통 |
| 4-2 | `generate_draft()` payment_override 파라미터 | hwp_generator.py | 보통 |
| 4-3 | `{{PAYMENT_METHOD}}` 치환 로직 교체 | hwp_generator.py | 쉬움 |

### Phase 5: 보안 + 테스트

| 순서 | 작업 | 파일 | 난이도 |
|------|------|------|--------|
| 5-1 | 시드 DB 은행 정보 제거 | build_exe.py | 쉬움 |
| 5-2 | 통합 테스트 케이스 추가 | test_integration.py | 보통 |

---

## 5. 리스크 분석

| 리스크 | 확률 | 영향 | 완화 |
|--------|------|------|------|
| 기존 DB 레코드 호환 깨짐 | Low | High | 빈 문자열 폴백으로 vendor 참조 유지 |
| HWP 출력 형식 변경으로 기존 문서 영향 | None | None | 자리표시자 동일, 기존 생성 문서 불변 |
| 수정 모드에서 결제방법 미복원 | Medium | Medium | `load_purchase()`에서 purchases.payment_method 읽기 |
| EXE 빌드 시 은행 정보 유출 | High | High | build_exe.py에서 은행 필드 공백 처리 |
| 무통장입금 은행 정보 빈값 | Medium | Low | 빈 필드 제외 후 join (graceful fallback) |
| 긴 은행정보 → HWP 셀 넘침 | Low | Low | AllReplace는 길이 제한 없음, 시각적 확인만 |
| 업체 재선택 시 오버라이드 초기화 | Medium | Low | 새 업체 기본값으로 자동 갱신 (의도된 동작) |

---

## 6. 변경 영향 범위 요약

```
수정 대상 (5개 파일):
  ├── config.py              ← PAYMENT_METHODS 상수 추가
  ├── db/database.py         ← purchases 4컬럼 마이그레이션
  ├── db/purchase_repo.py    ← insert/update payment 컬럼
  ├── ui/tab_vendor.py       ← 라디오 3종 + Treeview 표시
  ├── ui/tab_purchase.py     ← 결제방법 선택 UI + 연동
  └── documents/hwp_generator.py ← 3값 포맷팅

수정 불필요 (확인 완료):
  ├── db/vendor_repo.py      ← 파라미터 바인딩, 변경 불필요
  ├── ui/tab_history.py      ← payment 관련 코드 없음
  ├── ui/tab_inspection.py   ← payment 관련 코드 없음
  ├── core/models.py         ← dict 전달, 모델 변경 불필요
  └── build_exe.py           ← 보안 조치만 (선택적)
```
