# HWP COM Cursor Management Bug Fix -- Planning Document

> **Summary**: HWP COM 자동화에서 AllReplace/FindReplace 사용 시 커서 위치 미보장으로 인한 4개 버그 일괄 수정
>
> **Project**: 구매기안 자동화 시스템
> **Version**: 1.1
> **Author**: CTO Team (6-member Expert Panel)
> **Date**: 2026-03-09
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | AllReplace 액션은 커서를 치환 위치로 이동시키지 않으며, FindReplace는 Direction=0(Forward)에서 커서 위치 이후만 검색하여, 빈 행 삭제/단락 삭제/합계 행 삭제/서식 적용이 모두 실패한다 |
| **Solution** | AllReplace를 FindReplace+MoveDocBegin 패턴으로 교체하고, 모든 검색/삭제 작업 전 커서를 문서 시작점으로 초기화하는 공통 유틸리티 도입 |
| **Function/UX Effect** | PUA 마커(\uE010, \uE012) 잔존 제거, {{SOLE_SECTION}} 미삭제 해결, 산출기초조사서 원래 합계 행 정상 삭제, Bold 서식 안정 적용 |
| **Core Value** | 품목 수(1~15개)와 구매방법/수의계약사유 포함 여부에 관계없이 문서가 항상 정확하게 생성되는 신뢰성 확보 |

---

## 1. Overview

### 1.1 Purpose

`hwp_generator.py`의 4개 메서드에서 HWP COM API의 커서 위치 관리 결함을 수정하여, 생성된 HWP 문서에 PUA 마커 잔존, 미삭제 자리표시자, 잔존 합계 행 등의 결함이 없도록 한다.

### 1.2 Background

테스트 데이터 "노트북 컴퓨터 구매 기안3333" (Purchase ID: 37, 품목 1개, 쿠팡/네이버파이낸셜)로 생성한 실제 출력 파일에서 다음 결함이 확인되었다:

**기안서 (노트북 컴퓨터 구매 기안3333.hwp)**
- Row 2~15의 빈 품목 행 중 `\uE010` PUA 마커가 문서에 그대로 보임 (빈 행 삭제 실패)
- `{{SOLE_SECTION}}` 자리표시자가 삭제되지 않고 그대로 노출

**산출기초조사서 (3.산출기초조사서.hwp)**
- N+1 합계 행은 정상 배치되었으나, 원래 합계 행의 `\uE012` 마커가 잔존 (원래 합계 행 삭제 실패)

### 1.3 Related Documents

- 핵심 파일: `E:\ClaudeCode\purchase-automation\documents\hwp_generator.py`
- 프로젝트 설명: `E:\ClaudeCode\purchase-automation\CLAUDE.md`

---

## 2. Scope

### 2.1 In Scope

- [x] Bug 1: `_delete_empty_item_rows()` (L222-241) -- 기안서 빈 품목 행 미삭제 수정
- [x] Bug 2: `_delete_paragraph_with_placeholder()` (L243-262) -- {{SOLE_SECTION}} 미삭제 수정
- [x] Bug 3: `_delete_total_row()` (L264-268) -- 산출기초조사서 합계 행 미삭제 수정
- [x] Bug 4: `_apply_total_row_style()` (L270-284) -- Bold 서식 미적용 수정
- [x] 공통 유틸리티 메서드 `_find_and_move_cursor()` 추출
- [x] 기존 AllReplace 기반 치환(`_allreplace`) 유지 (전체 치환에는 정상 동작)

### 2.2 Out of Scope

- 템플릿 HWP 파일 수정 (양식 레이아웃 변경)
- 물품검수조서 (`_replace_and_save`) -- 행 삭제 없으므로 영향 없음
- Excel 생성기 (`excel_generator.py`) -- 별도 엔진
- UI 레이어 변경
- MAX_ITEM_ROWS 상수 변경

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 품목 1개일 때 기안서 빈 행(Row 2~15) 14개가 모두 정상 삭제되어야 한다 | Critical | Pending |
| FR-02 | 수의계약사유 미포함 시 `{{SOLE_SECTION}}` 자리표시자가 포함된 단락이 완전히 삭제되어야 한다 | Critical | Pending |
| FR-03 | 구매방법 미포함 시 `{{PAYMENT_SECTION}}` 자리표시자가 포함된 단락이 완전히 삭제되어야 한다 | Critical | Pending |
| FR-04 | 산출기초조사서에서 원래 합계 행(`{{VENDOR1_TOTAL}}` 위치)이 정상 삭제되어야 한다 | Critical | Pending |
| FR-05 | 산출기초조사서 N+1 합계 행에 Bold 서식이 적용되어야 한다 | High | Pending |
| FR-06 | 품목 15개(최대)일 때 빈 행 삭제 로직이 실행되지 않아야 한다 (기존 동작 유지) | High | Pending |
| FR-07 | PUA 마커(\uE010, \uE012)가 최종 문서에 잔존하지 않아야 한다 | Critical | Pending |
| FR-08 | 기존 정상 동작(다중 품목 치환, 산출기초조사서 빈 행 유지 등)이 깨지지 않아야 한다 | Critical | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| 안정성 | COM 자동화 중 예외 발생 시 hwp.Quit() 정상 호출 보장 | try/finally 블록 확인 |
| 호환성 | 한/글 2020, 2022, 2024 버전 COM API 호환 | MoveDocBegin, FindReplace는 모든 버전 지원 |
| 성능 | 15개 품목 빈 행 삭제 시 1초 이내 완료 | 실행 시간 측정 |
| 유지보수성 | 커서 관리 로직 공통 메서드 추출, 코드 중복 제거 | 코드 리뷰 |

---

## 4. Root Cause Analysis (6-Expert Panel)

### 4.1 HWP COM Expert -- AllReplace vs FindReplace 커서 동작 분석

#### AllReplace 동작 원리
```
AllReplace("{{SEQ_02}}", "\uE010")
```
- 문서 **전체**를 스캔하여 모든 일치 항목을 한 번에 치환
- **커서를 이동시키지 않음** -- 치환 전 커서 위치 그대로 유지
- 반환값: 치환 횟수 (0이면 미발견)
- 설계 의도: 전역 일괄 치환, 개별 위치 추적 불필요

#### FindReplace 동작 원리
```
FindReplace("합 계")  with Direction=0
```
- 현재 커서 위치부터 **Direction 방향**으로 첫 번째 일치 항목 검색
- **커서를 일치 위치로 이동시킴** -- 이것이 핵심 차이
- Direction=0 (Forward): 커서 이후만 검색
- Direction=1 (Backward): 커서 이전만 검색
- 반환값: bool (찾았으면 True)

#### 신뢰성 있는 커서 이동 전략
```python
# 패턴: MoveDocBegin -> FindReplace -> 커서 기반 액션
hwp.HAction.Run("MoveDocBegin")          # 1. 문서 시작으로 이동
act.FindString = target
act.Direction = 0                         # 2. Forward 검색
found = hwp.HAction.Execute("FindReplace", act.HSet)  # 3. 커서가 대상 위치로 이동
if found:
    hwp.HAction.Run("TableDeleteRow")     # 4. 정확한 위치에서 실행
```

### 4.2 Backend Architect -- 4개 버그 수정 설계

#### Bug 1: `_delete_empty_item_rows()` -- 근본 수정

**Before (L222-241):**
```python
def _delete_empty_item_rows(self, hwp, n_items: int, anchor_prefix: str = "SEQ"):
    _MARKER = "\uE010"
    if n_items >= MAX_ITEM_ROWS:
        return
    for i in range(MAX_ITEM_ROWS, n_items, -1):
        tag = f"{i:02d}"
        self._allreplace(hwp, f"{{{{{anchor_prefix}_{tag}}}}}", _MARKER)  # 커서 미이동!
        hwp.HAction.Run("TableDeleteRow")  # 잘못된 위치
```

**After:**
```python
def _delete_empty_item_rows(self, hwp, n_items: int, anchor_prefix: str = "SEQ"):
    """빈 품목 행 삭제 -- FindReplace로 커서 이동 후 TableDeleteRow"""
    if n_items >= MAX_ITEM_ROWS:
        return
    for i in range(MAX_ITEM_ROWS, n_items, -1):   # 아래 -> 위 순서 유지
        tag = f"{i:02d}"
        target = f"{{{{{anchor_prefix}_{tag}}}}}"
        if self._find_and_move_cursor(hwp, target):
            hwp.HAction.Run("TableDeleteRow")
```

**변경 요점:**
- `_allreplace` + PUA 마커 패턴을 `_find_and_move_cursor` (FindReplace 기반)로 교체
- PUA 마커(\uE010) 불필요 -- FindReplace가 커서를 직접 이동시키므로
- `_find_and_move_cursor`가 내부에서 `MoveDocBegin`을 호출하므로 각 반복이 독립적

#### Bug 2: `_delete_paragraph_with_placeholder()` -- MoveDocBegin 추가

**Before (L243-262):**
```python
def _delete_paragraph_with_placeholder(self, hwp, placeholder: str):
    act = hwp.HParameterSet.HFindReplace
    hwp.HAction.GetDefault("FindReplace", act.HSet)
    act.FindString = placeholder
    act.ReplaceString = ""
    act.Direction = 0          # Forward만 -- 커서 위치 의존!
    act.IgnoreMessage = 1
    found = hwp.HAction.Execute("FindReplace", act.HSet)
    if not found: return
    # ...
```

**After:**
```python
def _delete_paragraph_with_placeholder(self, hwp, placeholder: str):
    """자리표시자가 포함된 단락 전체를 삭제 (빈줄 방지)"""
    hwp.HAction.Run("MoveDocBegin")   # 문서 시작으로 이동 -- 핵심 수정
    act = hwp.HParameterSet.HFindReplace
    hwp.HAction.GetDefault("FindReplace", act.HSet)
    act.FindString = placeholder
    act.ReplaceString = ""
    act.Direction = 0
    act.IgnoreMessage = 1
    found = hwp.HAction.Execute("FindReplace", act.HSet)
    if not found:
        return
    # 단락 전체 선택 -> 삭제 (줄바꿈 포함)
    hwp.HAction.Run("MoveParaBegin")
    hwp.HAction.Run("MoveSelParaEnd")
    hwp.HAction.Run("MoveSelNextChar")   # 줄바꿈 문자까지 포함
    hwp.HAction.Run("Delete")
```

**변경 요점:**
- 메서드 시작 시 `hwp.HAction.Run("MoveDocBegin")` 1줄 추가
- 이전 단계(AllReplace 루프)의 커서 위치에 의존하지 않음

#### Bug 3: `_delete_total_row()` -- FindReplace 기반으로 전면 교체

**Before (L264-268):**
```python
def _delete_total_row(self, hwp, anchor: str):
    _MARKER = "\uE012"
    self._allreplace(hwp, anchor, _MARKER)      # 커서 미이동!
    hwp.HAction.Run("TableDeleteRow")            # 잘못된 위치
```

**After:**
```python
def _delete_total_row(self, hwp, anchor: str):
    """합계 행 삭제 -- FindReplace로 앵커 위치 특정 후 TableDeleteRow"""
    if self._find_and_move_cursor(hwp, anchor):
        hwp.HAction.Run("TableDeleteRow")
```

**변경 요점:**
- PUA 마커(\uE012) 불필요
- `_find_and_move_cursor`로 앵커 위치에 커서 확실히 이동

#### Bug 4: `_apply_total_row_style()` -- MoveDocBegin 추가

**Before (L270-284):**
```python
def _apply_total_row_style(self, hwp):
    try:
        act = hwp.HParameterSet.HFindReplace
        hwp.HAction.GetDefault("FindReplace", act.HSet)
        act.FindString = "합 계"
        act.Direction = 0         # Forward만 -- 커서 위치 의존!
        act.IgnoreMessage = 1
        found = hwp.HAction.Execute("FindReplace", act.HSet)
        if found:
            hwp.HAction.Run("TableCellBlockRow")
            hwp.HAction.Run("CharShapeBold")
    except Exception:
        pass
```

**After:**
```python
def _apply_total_row_style(self, hwp):
    """합계 행('합 계' 텍스트)에 굵은 글씨 적용"""
    try:
        hwp.HAction.Run("MoveDocBegin")   # 문서 시작으로 이동 -- 핵심 수정
        act = hwp.HParameterSet.HFindReplace
        hwp.HAction.GetDefault("FindReplace", act.HSet)
        act.FindString = "합 계"
        act.ReplaceString = ""
        act.Direction = 0
        act.IgnoreMessage = 1
        found = hwp.HAction.Execute("FindReplace", act.HSet)
        if found:
            hwp.HAction.Run("TableCellBlockRow")
            hwp.HAction.Run("CharShapeBold")
    except Exception:
        pass   # 서식 적용 실패해도 데이터는 정상
```

**변경 요점:**
- `hwp.HAction.Run("MoveDocBegin")` 1줄 추가
- `act.ReplaceString = ""` 초기화 추가 (이전 호출의 잔존값 방지)

### 4.3 Code Quality -- 공통 유틸리티 메서드 설계

```python
def _find_and_move_cursor(self, hwp, target: str) -> bool:
    """문서 시작부터 target 텍스트를 검색하여 커서를 해당 위치로 이동.

    Returns:
        True: 찾아서 커서 이동 완료
        False: 대상 텍스트를 찾지 못함
    """
    hwp.HAction.Run("MoveDocBegin")
    act = hwp.HParameterSet.HFindReplace
    hwp.HAction.GetDefault("FindReplace", act.HSet)
    act.FindString = target
    act.ReplaceString = ""
    act.Direction = 0          # Forward
    act.IgnoreMessage = 1
    return bool(hwp.HAction.Execute("FindReplace", act.HSet))
```

**설계 원칙:**
- 매 호출마다 `MoveDocBegin` 실행 -- 이전 커서 위치에 절대 의존하지 않음
- `ReplaceString = ""` 초기화 -- HParameterSet 상태 오염 방지
- 반환값으로 검색 성공 여부 전달 -- 호출자가 후속 액션 결정
- 이 메서드를 사용하는 곳: Bug 1(`_delete_empty_item_rows`), Bug 3(`_delete_total_row`)
- Bug 2, Bug 4는 후속 액션이 다르므로 인라인 `MoveDocBegin` 추가

### 4.4 QA Engineer -- 테스트 시나리오 설계

| # | 시나리오 | 품목 수 | 구매방법 | 수의계약사유 | 검증 포인트 |
|---|---------|--------|---------|------------|-----------|
| T-01 | 최소 품목 | 1개 | 포함 | 미포함 | 14행 삭제, {{SOLE_SECTION}} 단락 삭제, PUA 마커 없음 |
| T-02 | 중간 품목 | 5개 | 포함 | 포함 | 10행 삭제, 두 섹션 모두 존재 |
| T-03 | 최대 품목 | 15개 | 포함 | 포함 | 삭제 없음, 빈 행 삭제 로직 미실행 |
| T-04 | 구매방법 미포함 | 1개 | **미포함** | 미포함 | {{PAYMENT_SECTION}}+{{SOLE_SECTION}} 둘 다 삭제 |
| T-05 | 수의계약사유만 | 3개 | **미포함** | 포함 | {{PAYMENT_SECTION}} 삭제, {{SOLE_SECTION}} 유지 |
| T-06 | 산출기초조사서 1품목 | 1개 | - | - | 원래 합계 행 삭제, N+1 합계 행 Bold, 빈 행 유지 |
| T-07 | 산출기초조사서 5품목 | 5개 | - | - | 원래 합계 행 삭제, 6행째 합계 |
| T-08 | 산출기초조사서 15품목 | 15개 | - | - | 합계 행 삭제 미실행, 원래 합계 행 유지 |

**텍스트 추출 검증 방법:**
```python
# HWP COM으로 텍스트 추출하여 검증
hwp.InitScan()
while True:
    state, text = hwp.GetText()
    if state <= 0: break
    assert "\uE010" not in text   # PUA 마커 없어야 함
    assert "\uE012" not in text
    assert "{{SOLE_SECTION}}" not in text
    assert "{{PAYMENT_SECTION}}" not in text
```

### 4.5 Security Architect -- COM 자동화 안전성 검토

| 위험 항목 | 현재 상태 | 수정 후 영향 | 대책 |
|----------|----------|------------|------|
| FindReplace 무한 루프 | N/A | 같은 텍스트를 반복 검색 시 무한 루프 가능 | `_find_and_move_cursor`는 1회만 호출, 루프 내 사용 시 검색 대상이 매번 다름 ({{SEQ_15}}, {{SEQ_14}}, ...) |
| HParameterSet 상태 오염 | AllReplace 후 FindString 잔존 | FindReplace 사용 시 이전 값 간섭 가능 | `ReplaceString = ""`로 매 호출 초기화 |
| COM 객체 누수 | try/finally로 hwp.Quit() 보장 | 변경 없음 | 기존 패턴 유지 |
| 템플릿 원본 변조 | `_copy_template_to_tmp`로 원본 보호 | 변경 없음 | 기존 패턴 유지 |
| TableDeleteRow 호출 시 빈 테이블 | 삭제할 행이 없으면 HWP 에러 | `_find_and_move_cursor` 반환값으로 분기 | False 반환 시 TableDeleteRow 미실행 |

### 4.6 Risk Analyst -- 사이드 이펙트 분석

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| FindReplace가 테이블 내부 텍스트를 찾지 못할 가능성 | High | Low | HWP COM FindReplace는 표 안 텍스트도 검색 대상에 포함 (AllReplace와 동일 범위) |
| 산출기초조사서 빈 행 유지 기능 손상 | High | Low | `_delete_empty_item_rows`는 산출기초조사서에서 호출되지 않음 (`_replace_and_save_calc`는 별도 경로) |
| MoveDocBegin이 매번 호출되어 성능 저하 | Low | Medium | MoveDocBegin은 경량 액션, 15회 반복해도 무시할 수 있는 오버헤드 |
| 기존 AllReplace 기반 전체 치환 로직 변경 | High | None | `_allreplace` 메서드는 변경하지 않음. main 루프의 전체 치환은 그대로 유지 |
| `_delete_paragraph_with_placeholder` 호출 순서 변경 시 다른 삭제 영향 | Medium | Low | 각 호출이 MoveDocBegin으로 시작하므로 순서 독립적 |
| `act.ReplaceString = ""` 추가로 FindReplace가 치환 모드로 동작 | Medium | Low | FindReplace는 FindString만 검색하고 커서 이동. ReplaceString=""는 치환이 아닌 빈 문자열 대입이므로 검색 모드와 동일 효과. 단, Execute가 치환을 수행하므로, Bug 2/4에서는 찾기 전용으로 `act.ReplaceMode = 0` 설정 또는 찾기 후 별도 삭제 로직 사용 필요 |

**IMPORTANT -- FindReplace 동작 정밀 분석:**

HWP COM의 `FindReplace` 액션은 이름에서 알 수 있듯이 "찾기 및 바꾸기"이다. `Execute` 호출 시 FindString을 ReplaceString으로 **치환**한다. 따라서:

- Bug 1 (`_delete_empty_item_rows`): `_find_and_move_cursor`가 FindReplace를 실행하면 `{{SEQ_02}}`가 빈 문자열로 치환됨. 이후 `TableDeleteRow`로 행 전체를 삭제하므로 문제 없음 -- 행이 삭제되면 셀 내용도 소멸.
- Bug 2 (`_delete_paragraph_with_placeholder`): FindReplace가 placeholder를 빈 문자열로 치환하지만, 이후 단락 전체를 선택/삭제하므로 문제 없음.
- Bug 3 (`_delete_total_row`): `_find_and_move_cursor`가 앵커를 빈 문자열로 치환하지만, 이후 행 전체를 삭제하므로 문제 없음.
- Bug 4 (`_apply_total_row_style`): "합 계" 텍스트가 빈 문자열로 치환되면 **문제 발생**! 합계 행의 텍스트가 사라짐.

**Bug 4 수정 보완 -- 찾기 전용 모드 사용:**

Bug 4에서는 FindReplace 대신 **RepeatFind** 액션을 사용해야 한다. 또는 FindReplace 실행 후 즉시 Undo하거나, 더 안전하게는 FindString = "합 계", ReplaceString = "합 계" (동일 값)로 설정하여 치환 효과 없이 커서만 이동시킨다.

```python
# Bug 4 최종 수정안 -- 치환 없이 커서만 이동
def _apply_total_row_style(self, hwp):
    try:
        hwp.HAction.Run("MoveDocBegin")
        act = hwp.HParameterSet.HFindReplace
        hwp.HAction.GetDefault("FindReplace", act.HSet)
        act.FindString = "합 계"
        act.ReplaceString = "합 계"   # 동일 값 -> 치환 효과 없음
        act.Direction = 0
        act.IgnoreMessage = 1
        found = hwp.HAction.Execute("FindReplace", act.HSet)
        if found:
            hwp.HAction.Run("TableCellBlockRow")
            hwp.HAction.Run("CharShapeBold")
    except Exception:
        pass
```

마찬가지로, `_find_and_move_cursor`도 범용 유틸리티이므로 ReplaceString에 대한 전략이 필요하다:

```python
def _find_and_move_cursor(self, hwp, target: str, consume: bool = True) -> bool:
    """문서 시작부터 target 텍스트를 검색하여 커서를 해당 위치로 이동.

    Args:
        target: 검색할 텍스트
        consume: True면 대상 텍스트를 빈 문자열로 치환 (삭제 전 앵커용)
                 False면 대상 텍스트 유지 (서식 적용용)
    """
    hwp.HAction.Run("MoveDocBegin")
    act = hwp.HParameterSet.HFindReplace
    hwp.HAction.GetDefault("FindReplace", act.HSet)
    act.FindString = target
    act.ReplaceString = "" if consume else target
    act.Direction = 0
    act.IgnoreMessage = 1
    return bool(hwp.HAction.Execute("FindReplace", act.HSet))
```

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| FindReplace가 AllReplace와 다른 검색 범위 | High | Low | HWP COM 문서상 동일 범위 (본문+표+머리글 등). 테스트 T-01~T-08에서 전수 검증 |
| 기존 15품목 정상 동작 손상 | High | Very Low | `n_items >= MAX_ITEM_ROWS` 조건에서 삭제 로직 미실행 (기존과 동일) |
| HParameterSet 공유 인스턴스 상태 오염 | Medium | Medium | 매 호출마다 `GetDefault`로 초기화 + `FindString`/`ReplaceString` 명시적 설정 |
| 품목 삭제 순서(아래->위) 변경 시 인덱스 꼬임 | High | None | 순서 변경 없음. range(MAX_ITEM_ROWS, n_items, -1) 유지 |
| `_replace_and_save_multi` skip_keys 로직 불필요 | Medium | Low | skip_keys는 AllReplace 루프용이므로 유지 필요. FindReplace로 전환된 삭제 메서드에서는 자리표시자를 직접 검색하므로 AllReplace에서 skip된 자리표시자가 문서에 남아있어야 FindReplace로 찾을 수 있음. 기존 skip 로직이 정확히 이 역할을 수행 |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure | Static sites, portfolios | -- |
| **Dynamic** | Feature-based modules, BaaS | Web apps with backend | -- |
| **Enterprise** | Strict layer separation, DI, microservices | High-traffic systems | X |

Enterprise 레벨 선정 이유: 6명 전문가 팀 운영, COM 자동화 안전성/커서 관리의 정밀 분석 필요

### 6.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| 커서 이동 전략 | AllReplace+마커 / FindReplace+MoveDocBegin / RepeatFind | FindReplace+MoveDocBegin | 커서 이동이 보장되며, 검색+치환 동시 수행으로 앵커 자리표시자 자동 제거 |
| 공통 유틸리티 | 인라인 / 메서드 추출 | `_find_and_move_cursor` 추출 | Bug 1, 3에서 동일 패턴 사용; consume 파라미터로 Bug 4 대응 |
| PUA 마커 사용 | 유지 / 제거 | 제거 | FindReplace가 커서를 직접 이동시키므로 마커 불필요 |
| AllReplace 전체 치환 | 유지 / FindReplace 전환 | 유지 | main 루프의 전체 치환은 AllReplace가 적합 (커서 무관) |

### 6.3 수정 영향 범위

```
hwp_generator.py 수정 범위:
  NEW: _find_and_move_cursor()           -- 신규 공통 메서드
  MOD: _delete_empty_item_rows()         -- AllReplace -> _find_and_move_cursor
  MOD: _delete_paragraph_with_placeholder() -- MoveDocBegin 추가
  MOD: _delete_total_row()               -- AllReplace -> _find_and_move_cursor
  MOD: _apply_total_row_style()          -- MoveDocBegin 추가, ReplaceString 수정

  NO CHANGE: _allreplace()               -- 기존 전체 치환 유지
  NO CHANGE: _replace_and_save()         -- 행 삭제 없음
  NO CHANGE: _replace_and_save_multi()   -- 호출 순서/skip_keys 유지
  NO CHANGE: _replace_and_save_calc()    -- 호출 순서 유지
  NO CHANGE: generate_*()                -- 퍼블릭 API 변경 없음
```

---

## 7. Implementation Checklist

### 7.1 수정 순서 (의존성 기반)

1. [ ] `_find_and_move_cursor()` 신규 메서드 추가 (L146 부근, `_allreplace` 바로 뒤)
2. [ ] `_delete_empty_item_rows()` 수정 (Bug 1)
3. [ ] `_delete_paragraph_with_placeholder()` 수정 (Bug 2)
4. [ ] `_delete_total_row()` 수정 (Bug 3)
5. [ ] `_apply_total_row_style()` 수정 (Bug 4)
6. [ ] 테스트 T-01~T-08 실행 및 검증
7. [ ] 기존 정상 출력물과 비교 검증

### 7.2 롤백 계획

- `hwp_generator.py`만 수정하므로 git revert 또는 파일 단위 복원 가능
- 템플릿 파일 미변경, DB 미변경, UI 미변경

---

## 8. Next Steps

1. [ ] Design 문서 작성 (`hwp-cursor-management-bugfix.design.md`)
2. [ ] 코드 수정 구현 (Do phase)
3. [ ] 테스트 시나리오 T-01~T-08 실행 (Check phase)
4. [ ] 결과 보고서 작성 (Report phase)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-09 | Initial draft -- 6-expert panel analysis | CTO Team |
