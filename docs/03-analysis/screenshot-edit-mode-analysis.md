# 견적파일(스크린샷) 수정 모드 문제 — CTO팀 종합 분석 보고서

> **작성일**: 2026-03-12
> **심각도**: Critical (데이터 영구 손실 가능)
> **대상**: 이력조회 → 수정 모드 → 문서 재생성 시 견적파일 처리

---

## Executive Summary

| 관점 | 내용 |
|------|------|
| **문제** | 수정 모드에서 기존 견적파일(스크린샷) 경로가 복원되지 않아 기안서 첨부파일 누락 + DB 경로 영구 손실 |
| **해결** | load_purchase()에서 스크린샷 경로 복원 + 파일 존재 검증 + 사용자 선택 팝업 |
| **기능 UX 효과** | 수정 시 기존 견적파일 자동 유지, 신규 캡처 선택적 교체 가능 |
| **핵심 가치** | 데이터 무결성 보장 + 문서 품질 유지 + 사용자 재작업 최소화 |

---

## 1. 문제 상세 분석 (6 전문가 관점)

### 1.1 아키텍트 관점 — 데이터 흐름 단절

```
[정상] 신규 생성:
  캡처 → _screenshot_paths → _build_purchase_data → _build_docs_common → attachment_files → HWP
                                                  → repo.insert() → DB 저장

[문제] 수정 모드:
  DB record (vendor1_screenshot="path1")
    → load_purchase() ← 여기서 _screenshot_paths에 복원 안 함!
    → _screenshot_paths = ["", ""]
    → _build_purchase_data → VendorQuote.screenshot_path = ""
    → _build_docs_common → src="" → 첨부 없음
    → repo.update() → DB 덮어쓰기: vendor1_screenshot = "" ← 영구 손실!
```

**근본 원인**: `load_purchase()` 메서드가 vendor1_screenshot, vendor2_screenshot 필드를 복원하지 않음.

### 1.2 보안 아키텍트 관점 — 데이터 무결성 위험

| 위험 | 심각도 | 설명 |
|------|--------|------|
| DB 경로 영구 손실 | Critical | 수정 1회만으로 스크린샷 경로가 "" 으로 덮어씌워짐 |
| 복구 불가 | Critical | 2차 수정 시 record["vendor1_screenshot"]="" → 원본 추적 불가 |
| 파일 고아화 | Medium | SCREENSHOT_DIR에 파일은 남아있지만 DB 참조 끊어짐 |
| 출력폴더 사본 유실 | Low | out_dir의 견적파일도 재생성 시 복사되지 않음 |

### 1.3 QA 전략가 관점 — 경우의 수 매트릭스

| # | 견적1 파일 | 견적2 파일 | 시나리오 | 현재 동작 | 기대 동작 |
|---|-----------|-----------|---------|----------|----------|
| A | DB에 있음 + 파일 존재 | DB에 있음 + 파일 존재 | 일반적 수정 | 둘 다 누락 | 둘 다 자동 복원 |
| B | DB에 있음 + 파일 존재 | DB에 없음 | 견적2 미캡처 상태 수정 | 둘 다 누락 | 견적1만 복원 |
| C | DB에 있음 + 파일 삭제됨 | DB에 있음 + 파일 존재 | 견적1 파일 수동 삭제 후 수정 | 둘 다 누락 | 견적2 복원 + 견적1 경고 |
| D | DB에 없음 | DB에 없음 | 최초 캡처 없이 저장된 건 | 둘 다 누락 | 변경 없음 (정상) |
| E | DB에 있음 + 파일 존재 | 사용자가 새로 캡처 | 견적2만 교체 | 견적1 누락 | 견적1 유지 + 견적2 교체 |
| F | 사용자가 새로 캡처 | DB에 있음 + 파일 존재 | 견적1만 교체 | 견적2 누락 | 견적1 교체 + 견적2 유지 |
| G | 단독견적 | N/A | 수의계약 | 견적1 누락 | 견적1 복원 |

### 1.4 프로덕트 매니저 관점 — 사용자 시나리오

**현재 UX 문제**:
1. 사용자가 이력에서 "수정하기" 클릭
2. 폼에 모든 데이터가 채워지지만 견적파일 상태는 "없음"으로 표시
3. 사용자는 견적파일이 이미 있다는 것을 인지하지 못함
4. "재생성" 클릭 → 첨부파일 없는 기안서 생성
5. DB에서 스크린샷 경로도 소실 → 재수정해도 복구 불가

**기대 UX**:
1. "수정하기" 클릭 → 기존 견적파일 자동 복원 (파일명 표시)
2. 파일이 삭제된 경우 → 경고 아이콘 + "재캡처 필요" 안내
3. 사용자가 원하면 새 파일로 교체 가능
4. 교체하지 않으면 기존 파일 그대로 사용

### 1.5 프론트엔드 아키텍트 관점 — UI 상태 관리

**현재 UI 상태 흐름**:
```
_reset_form() → _screenshot_paths = ["", ""]
                _ss_labels = "없음" (회색)

load_purchase() → 업체명/URL/품목 복원
                  스크린샷: 복원 안 함 ← 문제
```

**필요한 UI 상태**:
```
load_purchase() → 스크린샷 경로 복원
                  파일 존재 확인
                  ├─ 존재: 라벨에 파일명 표시 (녹색)
                  └─ 미존재: 라벨에 "파일 없음 (재캡처 필요)" (주황색)
```

### 1.6 코드 분석가 관점 — 영향 범위

| 파일 | 수정 필요 | 수정 내용 |
|------|----------|----------|
| `ui/tab_purchase.py` | YES | load_purchase()에 스크린샷 복원 추가 |
| `core/models.py` | NO | VendorQuote 구조 변경 없음 |
| `db/purchase_repo.py` | NO | 이미 vendor1/2_screenshot 저장/조회 |
| `ui/tab_history.py` | NO | record에 이미 screenshot 포함 |
| `documents/hwp_generator.py` | NO | attachment_files 처리 정상 |
| `core/screenshot.py` | NO | 캡처 함수 변경 없음 |

---

## 2. 개선 대안 비교

### 대안 A: 자동 복원 (권장)
- load_purchase()에서 DB 스크린샷 경로 자동 복원
- 파일 존재 시 → 라벨에 파일명 표시
- 파일 미존재 시 → 라벨에 경고 표시
- 사용자 개입 없이 자동 처리

**장점**: 코드 변경 최소, 기존 UX 흐름 유지, 데이터 무결성 보장
**단점**: 없음

### 대안 B: 팝업 확인 방식
- 수정 모드 진입 시 견적파일 상태 팝업
- "기존 파일 사용" / "새로 캡처" / "파일 없이 진행" 선택

**장점**: 사용자에게 명시적 선택 기회
**단점**: 매번 팝업이 뜨면 UX 방해, 대부분 "기존 파일 사용" 선택할 것

### 대안 C: 재생성 시점 확인 방식
- load 시에는 자동 복원 (대안 A)
- "재생성" 클릭 시 스크린샷이 없으면 팝업 확인

**장점**: 불필요한 팝업 최소화, 필요할 때만 경고
**단점**: 약간 더 복잡한 로직

### 최종 선택: 대안 A + C 하이브리드

1. **load 시**: 자동 복원 (대안 A)
2. **재생성 시**: 스크린샷 없으면 경고 팝업 (대안 C의 안전장치)

---

## 3. 상세 구현 계획

### 3.1 load_purchase() 스크린샷 복원 추가

```python
# load_purchase() 메서드 내 — 견적 정보 복원 블록 뒤에 추가
# 스크린샷 경로 복원
for idx, key in enumerate(("vendor1_screenshot", "vendor2_screenshot")):
    ss_path = record.get(key, "")
    if ss_path and Path(ss_path).exists():
        self._screenshot_paths[idx] = ss_path
        if self._ss_labels[idx]:
            self._ss_labels[idx].config(
                text=Path(ss_path).name,
                foreground=COLORS["success"])
    elif ss_path:
        # DB에 경로 있으나 파일 없음
        self._screenshot_paths[idx] = ""
        if self._ss_labels[idx]:
            self._ss_labels[idx].config(
                text="파일 없음 (재캡처 필요)",
                foreground=COLORS["warning"])
    # ss_path가 빈 문자열이면 기본값 "없음" 유지
```

### 3.2 _regenerate_documents() 안전장치

```python
# _regenerate_documents() 시작 부분 — _validate() 통과 후
# 스크린샷 누락 확인
missing = []
if not self._sole_quote_var.get():
    for idx, slot in enumerate([1, 2]):
        if not self._screenshot_paths[idx]:
            missing.append(f"견적{slot}")
else:
    if not self._screenshot_paths[0]:
        missing.append("견적1")
if missing:
    result = messagebox.askyesnocancel("견적파일 확인",
        f"{', '.join(missing)}의 견적파일(스크린샷)이 없습니다.\n\n"
        "• [예] 견적파일 없이 계속 진행\n"
        "• [아니오] 돌아가서 견적파일 추가\n"
        "• [취소] 재생성 취소")
    if result is None:  # 취소
        return
    if result is False:  # 아니오 → 돌아감
        return
    # True → 진행
```

### 3.3 _create_new_documents() 동일 안전장치

신규 생성에도 동일한 견적파일 누락 확인 추가 (일관성).

### 3.4 리스크 분석

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| 복원된 파일이 다른 건의 스크린샷과 이름 충돌 | Low | Low | make_screenshot_name()이 업체명 기반으로 고유 이름 생성 |
| SCREENSHOT_DIR 파일 수동 삭제 후 수정 | Medium | Low | 파일 미존재 시 "파일 없음" 표시 + 재캡처 유도 |
| 복사 모드에서 스크린샷 공유 | Low | Low | 복사 시에도 복원되므로 원본 파일 참조 공유 → _build_docs_common에서 새 파일로 복사 |
| load_purchase trace 경합 | Low | Low | 스크린샷 복원은 trace 콜백과 무관 (UI 라벨만 변경) |
| 단독견적 모드에서 견적2 복원 | Low | None | 단독견적 toggle 시 견적2 초기화 로직이 이미 존재 |

---

## 4. 테스트 케이스

| TC | 시나리오 | 검증 항목 |
|----|---------|----------|
| T1 | 견적1+2 스크린샷 있는 건 수정 | 라벨에 파일명 표시, 재생성 시 첨부 포함, DB 경로 유지 |
| T2 | 견적1만 스크린샷 있는 건 수정 | 견적1만 복원, 견적2 "없음" |
| T3 | 스크린샷 파일 삭제된 건 수정 | "파일 없음" 경고 표시 |
| T4 | 수정 중 견적1 새로 캡처 | 기존 파일 교체, 새 파일로 DB 갱신 |
| T5 | 수정 중 캡처 안 하고 재생성 | 기존 스크린샷으로 첨부 생성 |
| T6 | 복사 모드에서 스크린샷 복원 | 복사 시에도 기존 파일명 표시, 새 기안에 첨부 |
| T7 | 단독견적 건 수정 | 견적1만 복원, 견적2 무시 |
| T8 | 재생성 시 스크린샷 없음 팝업 | "예" → 진행, "아니오" → 돌아감, "취소" → 취소 |
| T9 | 2차 수정 (수정→재생성→재수정) | DB 경로 보존, 재수정 시에도 복원 |

---

## 5. 구현 우선순위

| 순서 | 작업 | 파일 | 위험도 |
|------|------|------|--------|
| 1 | load_purchase() 스크린샷 복원 | tab_purchase.py | Critical — 데이터 손실 방지 |
| 2 | 재생성 시 스크린샷 누락 팝업 | tab_purchase.py | High — 사용자 실수 방지 |
| 3 | 신규 생성 시에도 동일 팝업 | tab_purchase.py | Medium — 일관성 |
