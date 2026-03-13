---
name: purchase_automation_project
description: 물품구매 자동화 시스템 — 공공기관 비교견적 수집 및 HWP 기안서 자동 생성 데스크톱 앱 프로젝트 개요
type: project
---

## 프로젝트 성격
- Python 3 + tkinter 데스크톱 앱 (웹 프레임워크 아님)
- UI는 tkinter grid/pack 레이아웃 — React/Next.js 패턴 적용 불가
- "design_system.py"가 CSS 변수 역할 (COLORS, SPACING, FONTS, apply_theme)
- BaseDialog 패턴이 컴포넌트 합성 역할

## 핵심 UI 파일
- `ui/tab_purchase.py` — 탭1, 기안 정보 섹션(grid row 0~10), 품목 목록, 견적 비교
- `ui/tab_vendor.py` — 탭4 + VendorDialog (업체 추가/수정)
- `ui/design_system.py` — COLORS, SPACING, FONTS, BTN_ACTION_PAD

## 현재 결제방법 값 목록
- `"card"` — 법인카드
- `"transfer"` — 무통장입금
- (신규) `"auto_transfer"` — 자동 이체 납부 (추가 예정)

## tab_purchase.py — _build_draft_section 레이아웃 (grid)
- row 0: 템플릿 선택 (columnspan=4)
- row 1: Separator
- row 2: 기안제목
- row 3: 기안일
- row 4: 부서명
- row 5: 내용
- row 6: 비고
- row 7: Separator
- row 8: 포함 항목 선택 LabelFrame (columnspan=4)
- row 9: 구매업체 Combobox + 신규 등록 버튼
- row 10: 업체 정보 LabelFrame (대표자/사업자번호/주소)
- row 11~: (추가 예정) 결제방법 선택 + 은행 정보

## _on_draft_vendor_select() 현재 동작
- 업체 선택 시 _dv_ceo_var, _dv_biz_var, _dv_addr_var만 채움
- 결제방법/은행 정보는 표시 안 함 (추가 필요)
