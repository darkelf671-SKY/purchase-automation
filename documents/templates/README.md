# HWP/Excel 템플릿 파일 배치 안내

이 폴더에 다음 양식 파일을 복사해 주세요.

## 필요한 파일

| 파일명 | 형식 | 용도 |
|--------|------|------|
| 기안서.hwp | HWP | 구매 기안서 |
| 산출기초조사서.hwp | HWP | 비교견적 산출 근거 |
| 물품검수조서.hwp | HWP | 검수 완료 조서 |
| 물품검수내역서.xlsx | Excel | 검수 내역 목록 |

## HWP 자리표시자 (Placeholder)

HWP 양식 파일 안에 아래 문자열을 삽입하면 자동으로 값이 채워집니다.

### 기안서.hwp
| 자리표시자 | 내용 |
|-----------|------|
| {{PURPOSE}} | 구매 목적 |
| {{ITEM_NAME}} | 구매품명 |
| {{SPEC}} | 규격/사양 |
| {{QUANTITY}} | 수량 |
| {{UNIT_PRICE}} | 단가 숫자 (예: 45,000) |
| {{UNIT_PRICE_KR}} | 단가 한글 (예: 사만오천원) |
| {{UNIT_PRICE_FORMAL}} | 단가 공식표기 (예: 一金일금사만오천원(₩45,000)) |
| {{TOTAL_PRICE}} | 총액 숫자 (예: 45,000) |
| {{TOTAL_PRICE_KR}} | 총액 한글 (예: 사만오천원) |
| {{TOTAL_PRICE_FORMAL}} | 총액 공식표기 (예: 一金일금사만오천원(₩45,000)) |
| {{VENDOR_NAME}} | 구매처명 |
| {{VENDOR_URL}} | 구매처 URL |
| {{TODAY}} | 작성일 (YYYY년 MM월 DD일) |

### 산출기초조사서.hwp
| 자리표시자 | 내용 | 예시 |
|-----------|------|------|
| {{ITEM_NAME}} | 품명 | 기계식 키보드 |
| {{SPEC}} | 규격/사양 | USB, 기계식 |
| {{UNIT}} | 단위 | 개 |
| {{QUANTITY}} | 수량 | 2 |
| {{VENDOR1_NAME}} | 비교견적 1 업체명 | 삼성전자 |
| {{VENDOR1_TOTAL}} | 견적1 총가격 | 90,000 |
| {{VENDOR2_NAME}} | 비교견적 2 업체명 | LG전자 |
| {{VENDOR2_TOTAL}} | 견적2 총가격 | 76,000 |
| {{SEL_VENDOR}} | 최저가 업체명 | LG전자 |
| {{SEL_TOTAL}} | 최저가 산출가격 | 76,000 |
| {{TODAY}} | 작성일 | 2026년 03월 06일 |

### 물품검수조서.hwp
| 자리표시자 | 내용 |
|-----------|------|
| {{ITEM_NAME}} | 품명 |
| {{SPEC}} | 규격/사양 |
| {{QUANTITY}} | 구매수량 |
| {{VENDOR_NAME}} | 구매처 |
| {{INSPECTION_DATE}} | 검수일 |
| {{INSPECTOR}} | 검수자 |
| {{INSPECTED_QTY}} | 검수수량 |
| {{DEFECT_STATUS}} | 이상 유무 ("이상 없음" 또는 이상 내용) |
| {{REMARK}} | 비고 |
| {{TODAY}} | 작성일 |

## Excel 셀 매핑 (물품검수내역서.xlsx)

템플릿 없을 경우 기본 양식이 자동 생성됩니다.
기존 양식이 있는 경우 `documents/excel_generator.py`의
`INSPECTION_LIST_CELLS` 딕셔너리에서 셀 주소를 수정하세요.
