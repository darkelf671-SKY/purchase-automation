---
name: purchase-tab-ui-restructure 플랜
description: 구매 조사 탭 섹션 순서 재편 및 항목 그룹화 개선 플랜 완료, CTO 검토 대기 (2026-03-12)
type: project
---

## 기능명
purchase-tab-ui-restructure

## 현재 단계
Plan (Draft) — CTO 검토 대기

## 플랜 문서 위치
`docs/01-plan/features/purchase-tab-ui-restructure.plan.md`

## 핵심 변경 방향

### AS-IS (현재 순서)
1. 기안 정보 (12개 항목 — 업체/결제 포함)
2. 구매 조사 (VAT + 사이트 바로가기)
3. 품목 목록
4. 견적 비교
5. 액션 버튼

### TO-BE (목표 순서)
1. 품목 및 가격 입력 (VAT 통합)
2. 시장 조사 (사이트 바로가기만)
3. 견적 비교 및 선택
4. 업체·결제 정보 (신규 분리)
5. 기안 작성 (슬림화 — 7개 항목)
6. 액션 버튼

## 식별된 주요 리스크

| # | 리스크 | 영향도 |
|---|--------|-------|
| R-02 | Combobox 이벤트·vendor_records 연동 깨짐 | High |
| R-03 | load_purchase() 위젯 초기화 타이밍 문제 | High |
| R-04 | 수정/복사 모드 배너 위치 오작동 | Medium |
| R-05 | VAT 비활성화 로직과 위젯 위치 불일치 | Medium |
| R-06 | 은행 정보 프레임 grid_remove 부모 변경 | Medium |

## 생성일
2026-03-12
