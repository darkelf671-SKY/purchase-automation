---
name: project_context
description: 구매기안 자동화 시스템 QA 전략 맥락 — v1.2 총액 입력 모드 및 수정/복사 분리 변경 사항
type: project
---

# 구매기안 자동화 시스템 QA 컨텍스트

## 프로젝트
- Python/tkinter 데스크톱 앱, SQLite3, HWP COM 자동화
- 공공기관 물품 비교견적 수집 후 HWP 기안서 자동 생성

## v1.2 주요 변경 (QA 전략 수립 완료)
- 총액 입력 모드: 견적1/2 독립 제어 (4케이스: unit/v1_total/v2_total/total)
- 이력 조회 "복사하여 새 기안" vs "수정하기" 버튼 분리
- 수정 모드 배너: 복사=파란(#D1ECF1), 수정=노란(#FFF3CD)
- 수정 시 기존 폴더 덮어쓰기 + 검수 자동 삭제 연동
- VAT 비활성화 조건: 어느 한쪽이라도 총액 모드이면 inclusive 강제

## QA 전략 문서 위치
`docs/03-analysis/qa_strategy.md`

## 알려진 위험
- `PurchaseItem.calc_total()`에서 "v2_total" 모드 미처리 — 검토 필요
- 기존 통합 테스트(`test_integration.py`)에 총액 모드 및 UPDATE 테스트 미포함
