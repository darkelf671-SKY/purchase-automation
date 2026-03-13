---
name: payment-method-enhancement 플랜
description: 결제 수단 개선 기능(자동 이체 납부 추가, 건별 결제 수단 선택) 플랜 문서 생성 완료
type: project
---

## 기능명
payment-method-enhancement

## 현재 단계
Plan (Draft) — CTO 검토 대기

## 플랜 문서 위치
`docs/01-plan/features/payment-method-enhancement.plan.md`

## 핵심 결정사항 (v0.2 — 실무자 피드백 반영)
- 결제 수단 3종: 법인카드 / 무통장입금 / 자동 이체 납부
- **신규**: `vendor_accounts` 테이블 — 업체별 복수 계좌 등록 (최대 3개, 별칭+은행명+계좌번호)
- `purchases` 테이블: `payment_method_override`, `vendor_account_id`, `bank_account_memo` 컬럼 추가
- `{{PAYMENT_METHOD}}` 치환 로직 3-way 분기
- `{{PAYMENT_SECTION}}`은 변경 없음 (수의계약 고정 텍스트)
- 무통장/자동이체 선택 시 등록 계좌 드롭다운, 법인카드 선택 시 계좌 드롭다운 숨김
- 기존 단일 계좌 → `vendor_accounts` 자동 마이그레이션 (기존 컬럼 deprecated 유지)

## 선택 근거 (Option B + 경량 복수 계좌)
- 순수 기본값+건별편집(Option B)은 계좌번호 직접 타이핑 위험 존재
- 복잡한 프로필 시스템(Option C)은 업체 등록 진입장벽 증가
- 최대 3개 계좌 드롭다운이 오입력 방지와 복잡도 사이 균형점

## 미해결 질문 (CTO 확인 필요)
1. 자동 이체 납부 문서에 계좌 정보 필요 여부
2. 결제 수단 상수 위치 (config.py vs core/models.py)
3. 업체 payment_method NULL 기본값 처리 방식
4. 계좌 드롭다운 표시 형식
5. vendor_accounts 별칭 필수 여부

## 생성일 / 업데이트
2026-03-12 최초 / 2026-03-12 v0.2 실무자 피드백 반영
