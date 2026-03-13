# Feature Plan: vendor-excel-bulk-upload

> 업체 Excel 일괄 업로드 기능

| 항목 | 내용 |
|------|------|
| **문서 ID** | PLAN-FEAT-vendor-excel-bulk-upload |
| **작성일** | 2026-03-12 |
| **상태** | Implemented |

---

## 1. Executive Summary

| 구분 | 내용 |
|------|------|
| **Problem** | 업체를 1건씩 수동 등록(VendorDialog)해야 하므로, 수십~수백 건의 업체 마스터 초기 세팅 시 과도한 시간 소요 |
| **Solution** | Excel 양식 다운로드 → 작성 → 일괄 업로드 흐름 제공. 중복 업체 자동 감지 및 처리(건너뛰기/덮어쓰기) 선택 |
| **Function UX Effect** | 업체 관리 탭에 "양식 다운로드" + "Excel 일괄 업로드" 버튼 2개 추가. 업로드 시 미리보기 다이얼로그에서 중복 확인 후 일괄 등록 |
| **Core Value** | 대량 업체 등록 시간을 N분 → 수 초로 단축. 기존 업체와의 중복 충돌 방지 |

---

## 2. AS-IS / TO-BE

### 2.1 AS-IS

- 업체 등록은 `VendorDialog` 를 통해 **1건씩 수동 입력**
- 업체가 많을 경우 반복 작업 필요 (상호, 대표자, 사업자번호, 주소, 결제방법, 계좌정보 등)
- 중복 업체 검사 없음 (UNIQUE 제약 위반 시 에러 메시지만 표시)
- 타 시스템에서 업체 목록을 가져올 방법 없음

### 2.2 TO-BE

1. **양식 다운로드**: "양식 다운로드" 버튼 클릭 → 2시트 구성 Excel 파일 저장
   - 시트1 "업체목록": 헤더 + 예제 3행 (스타일 적용)
   - 시트2 "설명": 필드별 설명, 중복 처리 규칙, 주의사항
2. **Excel 일괄 업로드**: "Excel 일괄 업로드" 버튼 클릭 → 파일 선택 → 파싱
   - 헤더 자동 매핑 (한글/영문 모두 지원)
   - 결제방법 정규화 (한글 ↔ 영문 코드)
3. **미리보기 다이얼로그** (`BulkUploadPreviewDialog`):
   - 중복 검사 결과를 Treeview로 표시 (신규=초록, 중복=노랑)
   - 중복 건별 건너뛰기/덮어쓰기 선택 라디오
   - "모두 건너뛰기" / "모두 덮어쓰기" 일괄 버튼
   - "일괄 등록 실행" → `bulk_insert()` 호출 → 결과 요약 표시
4. **구매 조사 탭 연동**: 등록 완료 후 구매 조사 탭의 업체 Combobox 자동 갱신

---

## 3. Implementation Scope

### 3.1 수정 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `db/vendor_repo.py` | `find_by_business_no()`, `find_by_name()`, `bulk_insert()` 함수 추가 |
| `ui/tab_vendor.py` | `_download_template()`, `_excel_upload()`, `_on_bulk_save()` 메서드 추가. `BulkUploadPreviewDialog` 클래스 추가 |

### 3.2 신규 클래스/함수 상세

#### db/vendor_repo.py

| 함수 | 시그니처 | 설명 |
|------|---------|------|
| `find_by_business_no` | `(biz_no: str) -> dict \| None` | 사업자등록번호로 업체 1건 조회 |
| `find_by_name` | `(name: str) -> dict \| None` | 상호명으로 업체 1건 조회 |
| `bulk_insert` | `(rows: list[dict]) -> dict` | 중복 처리 포함 일괄 등록. 반환: `{inserted, updated, skipped, details}` |

#### ui/tab_vendor.py

| 메서드/클래스 | 설명 |
|--------------|------|
| `VendorTab._download_template()` | openpyxl로 2시트 Excel 양식 생성 (헤더 스타일 + 예제 3행 + 설명 시트) |
| `VendorTab._excel_upload()` | Excel 파일 로드 → 헤더 매핑 → 결제방법 정규화 → `BulkUploadPreviewDialog` 호출 |
| `VendorTab._on_bulk_save()` | 업체 탭 refresh + 구매 조사 탭 `refresh_vendors()` 연동 |
| `BulkUploadPreviewDialog` | Toplevel 다이얼로그. 중복 검사 + Treeview 미리보기 + 처리 선택 + 일괄 등록 실행 |

---

## 4. Risk Analysis

| 리스크 | 영향 | 대응 |
|--------|------|------|
| **중복 업체 충돌** | 기존 업체 데이터 의도치 않은 덮어쓰기 | 미리보기 다이얼로그에서 건별 skip/update 선택. 기본값=건너뛰기 |
| **Excel 양식 오류** | 헤더 누락/변경 시 파싱 실패 | "상호" 헤더 필수 검증. 헤더 매핑에 "상호 *"/"상호" 모두 지원 |
| **대용량 파일** | 수천 건 업로드 시 UI 블로킹 | SQLite 단일 트랜잭션(`with get_connection()`)으로 일괄 처리. 현 규모에서는 문제 없음 |
| **결제방법 표기 불일치** | 사용자가 한글/영문 혼용 입력 | 정규화 로직으로 한글("법인카드") → 코드("card") 자동 변환. 미인식 값은 "card" 기본값 |
| **빈 행/상호 누락** | 불필요한 레코드 삽입 | `name` 빈 행 자동 스킵. `bulk_insert`에서도 이중 검증 |

---

## 5. Tasks

| ID | 작업 | 대상 파일 | 설명 |
|----|------|----------|------|
| T-01 | `find_by_business_no()` 구현 | `db/vendor_repo.py` | 사업자등록번호 기반 SELECT 쿼리 |
| T-02 | `find_by_name()` 구현 | `db/vendor_repo.py` | 상호명 기반 SELECT 쿼리 |
| T-03 | `bulk_insert()` 구현 | `db/vendor_repo.py` | 중복 검사 + insert/update/skip 분기 로직 |
| T-04 | `_download_template()` 구현 | `ui/tab_vendor.py` | 2시트 Excel 양식 생성 (openpyxl) |
| T-05 | `_excel_upload()` 구현 | `ui/tab_vendor.py` | Excel 파싱 + 헤더 매핑 + 결제방법 정규화 |
| T-06 | `BulkUploadPreviewDialog` 구현 | `ui/tab_vendor.py` | 미리보기 Treeview + 중복 처리 UI + 일괄 등록 실행 |
