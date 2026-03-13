# Gemini AI 기안내용 생성 기능 Planning Document

> **Summary**: Gemini API를 활용하여 공공기관 기안서 "내용" 필드를 자동 생성하는 기능
>
> **Project**: 구매기안 자동화 시스템 v1.0
> **Version**: v1.4
> **Author**: 전산팀 장길섭
> **Date**: 2026-03-13
> **Status**: Draft

---

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | 기안서 "내용" 작성 시 매번 유사한 문장을 수동으로 입력해야 하며, 공공기관 문서 형식을 기억하고 따라야 하는 부담이 있음 |
| **Solution** | Google Gemini API(무료 티어)를 연동하여 키워드/간략 설명 입력만으로 공공기관 양식에 맞는 기안 내용을 자동 생성 |
| **Function/UX Effect** | "AI 활용하기" 버튼 클릭 -> 키워드 입력 다이얼로그 -> 생성 결과 미리보기 -> "적용" 또는 "다시 생성"으로 빠른 반복 |
| **Core Value** | 기안 내용 작성 시간 단축(3~5분 -> 30초), 일관된 공공기관 문서 품질 유지, 무료 API 활용으로 비용 부담 없음 |

---

## 1. Overview

### 1.1 Purpose

기안서 "내용" 필드 작성 과정을 AI로 자동화하여, 사용자가 간단한 키워드나 설명만 입력하면 공공기관 물품구매 기안에 적합한 형식의 본문을 자동 생성한다.

### 1.2 Background

- 현재 기안 내용은 사용자가 직접 `tk.Text` 위젯에 수동 입력하거나, 기안 템플릿(`draft_templates` 테이블)에서 불러와 편집하는 방식
- 템플릿이 없는 새로운 유형의 구매 건에서는 매번 처음부터 작성해야 함
- 공공기관 기안 문서는 특유의 격식체와 항목 나열 방식이 있어 초안 작성에도 시간 소요
- Google Gemini API 무료 티어(RPM 5~15, RPD 250~1000)로 별도 비용 없이 LLM 활용 가능

### 1.3 Related Documents

- 프로젝트 CLAUDE.md: `E:\ClaudeCode\purchase-automation\CLAUDE.md`
- 기안 템플릿 관리: `ui/tab_draft_template.py`
- 설정 시스템: `config.py` (load_settings / save_settings)
- 기존 API 연동 참고: `core/naver_api.py`

---

## 2. Scope

### 2.1 In Scope

- [x] Gemini API 연동 모듈 (`core/gemini_api.py`)
- [x] AI 기안 생성 다이얼로그 UI (`ui/dialog_ai_draft.py`)
- [x] 공공기관 기안에 특화된 프롬프트 템플릿 설계
- [x] API 키 설정 UI (설정 다이얼로그에 Gemini API 키 입력란 추가)
- [x] "AI 활용하기" 버튼을 기안 내용 필드 영역에 추가
- [x] 생성 결과 미리보기 및 "적용" / "다시 생성" 기능
- [x] 에러 처리 (네트워크 오류, API 한도, 타임아웃)
- [x] PyInstaller EXE 빌드 호환성 확인
- [x] API 키 발급 가이드 프로그램 내장 (HTML, 브라우저 열기)
- [x] 설정/에러 화면에서 가이드 열기 버튼 제공

### 2.2 Out of Scope

- Gemini 유료 티어 연동 (무료 티어만 사용)
- 다른 LLM 서비스 연동 (Claude, GPT 등)
- 기안 내용 외 다른 필드(제목, 비고 등)의 AI 생성
- 프롬프트 히스토리/즐겨찾기 관리
- 오프라인 AI 모델 (로컬 LLM)

---

## 3. Requirements

### 3.1 Expert Team Composition

| # | Role | Name | Responsibilities |
|---|------|------|-----------------|
| 1 | **Product Manager** | PM | 요구사항 분석, 사용자 스토리, UX 플로우 정의, 우선순위 |
| 2 | **Frontend Architect** | FE-Arch | tkinter 다이얼로그 설계, UI/UX 레이아웃, 디자인 시스템 통합 |
| 3 | **Backend Expert** | BE-Expert | Gemini API 연동, 프롬프트 엔지니어링, 비동기 호출, 응답 파싱 |
| 4 | **Security Architect** | Sec-Arch | API 키 보안 저장, 전송 보안, 데이터 프라이버시 |
| 5 | **QA Strategist** | QA | 테스트 전략, 네트워크 에러 시나리오, 경계값 테스트 |
| 6 | **Code Analyzer** | CA | 기존 코드 구조 분석, 통합 지점 파악, 의존성 충돌 검토 |
| 7 | **User** | 사용자 | 실사용 관점 피드백, 공공기관 문서 형식 검증 |

### 3.2 Functional Requirements

| ID | Requirement | Priority | Status | Expert |
|----|-------------|----------|--------|--------|
| FR-01 | "AI 활용하기" 버튼을 기안 "내용 *:" 필드 하단에 배치 | High | Pending | FE-Arch |
| FR-02 | 버튼 클릭 시 AI 기안 생성 다이얼로그를 모달로 표시 | High | Pending | FE-Arch |
| FR-03 | 다이얼로그에서 간략 설명/키워드 입력 영역 제공 (tk.Text, 3줄) | High | Pending | FE-Arch |
| FR-04 | "생성" 버튼 클릭 시 Gemini API 호출하여 기안 내용 생성 | High | Pending | BE-Expert |
| FR-05 | 생성 중 로딩 표시 (버튼 비활성화 + "생성 중..." 텍스트) | Medium | Pending | FE-Arch |
| FR-06 | 생성 결과를 다이얼로그 내 미리보기 영역에 표시 (tk.Text, 읽기 전용) | High | Pending | FE-Arch |
| FR-07 | "적용" 버튼: 생성 결과를 기안 내용 필드에 반영 후 다이얼로그 닫기 | High | Pending | FE-Arch |
| FR-08 | "다시 생성" 버튼: 동일 입력으로 재호출하여 새로운 결과 생성 | High | Pending | BE-Expert |
| FR-09 | 기존 기안 내용이 있을 경우 덮어쓰기 전 확인 다이얼로그 표시 | Medium | Pending | PM |
| FR-10 | API 키가 미설정 시 설정 안내 메시지 표시 | High | Pending | FE-Arch |
| FR-11 | 설정 다이얼로그에 Gemini API 키 입력란 추가 | High | Pending | FE-Arch, Sec-Arch |
| FR-12 | 품명/규격/수량 등 현재 입력된 구매 정보를 프롬프트 컨텍스트로 활용 | Medium | Pending | BE-Expert |
| FR-13 | 생성된 내용에 `{{품명}}` 등 템플릿 치환자 포함 옵션 제공 | Low | Pending | BE-Expert |
| FR-14 | API 키 발급 가이드를 프로그램에 내장하여 사용자가 직접 보고 세팅 가능 | High | Pending | FE-Arch, PM |
| FR-15 | 설정 다이얼로그 AI 섹션에 "발급 가이드 보기" 버튼 추가 | High | Pending | FE-Arch |
| FR-16 | API 키 미설정 안내 메시지에서도 가이드 열기 옵션 제공 | Medium | Pending | FE-Arch |
| FR-17 | PyInstaller EXE 빌드 시 가이드 HTML 파일 번들 포함 | High | Pending | CA |
| FR-18 | 설정에서 무료 AI 모델을 선택할 수 있는 Combobox 제공 | High | Pending | FE-Arch |
| FR-19 | 모델별 사용 한도(분당/하루)를 표시명에 포함하여 사용자가 판단 가능 | Medium | Pending | PM |
| FR-20 | 한도 초과 시 다른 모델로 변경하여 계속 사용 가능 | High | Pending | BE-Expert |
| FR-21 | AI 생성 완료 시 사용된 모델명을 상태바에 표시 | Low | Pending | FE-Arch |

### 3.3 Non-Functional Requirements

| Category | Criteria | Measurement Method | Expert |
|----------|----------|-------------------|--------|
| **Performance** | API 응답 시간 15초 이내, 타임아웃 20초 | requests 타임아웃 설정 | BE-Expert |
| **Reliability** | 네트워크 오류 시 사용자 친화적 에러 메시지 | 수동 테스트 (오프라인 모드) | QA |
| **Security** | API 키 settings.json 저장 (평문, 로컬 전용) | 코드 리뷰 | Sec-Arch |
| **Usability** | 3클릭 이내 기안 내용 생성 완료 | UX 워크스루 | PM |
| **Compatibility** | Python 3.8+, PyInstaller --onefile 빌드 호환 | EXE 빌드 테스트 | CA |
| **Rate Limit** | 무료 티어 한도 초과 시 안내 메시지 | API 429 응답 처리 | BE-Expert |
| **Accessibility** | 키보드 탐색 가능 (Tab, Enter, Escape) | 수동 테스트 | FE-Arch |

---

## 4. Technical Design

### 4.1 Architecture Overview

```
tab_purchase.py                    dialog_ai_draft.py
┌──────────────────────┐          ┌──────────────────────────────┐
│  기안 내용 *:         │          │  AI 기안 내용 생성            │
│  ┌──────────────────┐│          │                              │
│  │ (tk.Text)        ││   click  │  설명/키워드: ___________     │
│  └──────────────────┘│ ───────> │                              │
│  [AI 활용하기]       │          │  [생성]                       │
│                      │          │                              │
│                      │  apply   │  ── 미리보기 ──               │
│  (내용 필드 갱신)     │ <─────── │  │ 생성된 기안 내용... │       │
│                      │          │  ──────────────               │
└──────────────────────┘          │  [적용]  [다시 생성]  [취소]  │
                                  └──────────────────────────────┘
                                           │
                                           │ API 호출
                                           v
                                  ┌──────────────────────┐
                                  │  core/gemini_api.py  │
                                  │  GeminiDraftAPI      │
                                  │  - generate_content()│
                                  │  - _build_prompt()   │
                                  └──────────┬───────────┘
                                             │ HTTPS
                                             v
                                  ┌──────────────────────┐
                                  │  Google Gemini API   │
                                  │  (Free Tier)         │
                                  │  gemini-2.5-flash    │
                                  └──────────────────────┘
```

### 4.2 Module Structure

#### 4.2.1 `core/gemini_api.py` (신규)

```python
"""Google Gemini API 연동 — 기안 내용 자동 생성"""
import requests
from typing import Optional

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
REQUEST_TIMEOUT = 30  # seconds

# 무료 모델 목록 (model_id → 표시명)
FREE_MODELS: dict[str, str] = {
    "gemini-3.1-flash-lite-preview": "Gemini 3.1 Flash Lite — 분당 15회, 하루 500회",
    "gemini-2.5-flash-lite":         "Gemini 2.5 Flash Lite — 분당 10회, 하루 20회",
    "gemini-2.5-flash":              "Gemini 2.5 Flash — 분당 5회, 하루 20회",
}


class GeminiDraftAPI:
    """기안 내용 생성 전용 Gemini API 클라이언트"""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate_draft_content(
        self,
        user_input: str,
        context: Optional[dict] = None,  # {item_name, spec, quantity, unit, ...}
    ) -> str:
        """기안 내용 생성 API 호출

        Args:
            user_input: 사용자가 입력한 간략 설명/키워드
            context: 현재 품목 정보 (선택, 프롬프트 보강용)

        Returns:
            생성된 기안 내용 텍스트

        Raises:
            GeminiAPIError: API 호출 실패
        """
        prompt = self._build_prompt(user_input, context)
        return self._call_api(prompt)

    def _build_prompt(self, user_input: str, context: Optional[dict]) -> str:
        """공공기관 기안 문서에 특화된 프롬프트 생성"""
        ...

    def _call_api(self, prompt: str) -> str:
        """Gemini REST API 호출"""
        ...


class GeminiAPIError(Exception):
    """Gemini API 호출 에러"""
    pass
```

**[BE-Expert 의견]**: REST API를 직접 호출(requests)하는 방식을 권장한다. `google-generativeai` 패키지는 의존성이 무거우며(`grpcio`, `proto-plus` 등) PyInstaller 빌드 시 크기가 크게 증가한다. 기안 내용 생성이라는 단일 용도에는 REST 직접 호출이 가볍고 충분하다. 기존 `naver_api.py`와 동일한 패턴(requests + timeout)을 따르면 코드 일관성도 유지된다.

#### 4.2.2 `ui/dialog_ai_draft.py` (신규)

```python
"""AI 기안 내용 생성 다이얼로그"""
from ui.base_dialog import BaseDialog


class AIDraftDialog(BaseDialog):
    """키워드 입력 -> Gemini 호출 -> 미리보기 -> 적용"""

    def __init__(self, parent, *, on_apply=None, purchase_context=None):
        self._on_apply_cb = on_apply           # 적용 콜백(생성된 텍스트 전달)
        self._purchase_context = purchase_context  # 현재 품목 정보
        super().__init__(parent, "AI 기안 내용 생성")

    def _build_content(self, frame):
        # 1) 키워드/설명 입력 영역
        # 2) [생성] 버튼
        # 3) 미리보기 영역 (읽기전용 tk.Text)
        # 4) 상태 표시 라벨
        ...

    def _build_buttons(self, frame):
        # [적용] [다시 생성] [취소]
        ...
```

**[FE-Arch 의견]**: `BaseDialog`를 상속하되, 기본 버튼 레이아웃을 오버라이드하여 3개 버튼("적용", "다시 생성", "취소")으로 구성한다. "적용" 버튼은 생성 결과가 없을 때 비활성화해야 한다. 다이얼로그 크기는 width=520, 미리보기 영역 height=8로 충분한 가독성을 확보한다.

#### 4.2.3 `config.py` 변경

```python
# 추가할 함수
def get_gemini_api_key() -> str:
    """설정된 Gemini API 키 반환"""
    return load_settings().get("gemini_api_key", "")

def set_gemini_api_key(value: str) -> None:
    s = load_settings()
    s["gemini_api_key"] = value
    save_settings(s)
```

**[Sec-Arch 의견]**: API 키를 `settings.json`에 평문 저장하는 것은 로컬 데스크톱 앱의 특성상 수용 가능하다. 이미 네이버 API 키가 동일한 방식(`naver_client_id`, `naver_client_secret`)으로 저장되고 있어 일관성을 유지한다. 다만 파일 권한(600)을 설정하면 좋지만, Windows 환경에서는 사용자 프로필 폴더 내에 있으므로 기본 ACL로 충분하다.

#### 4.2.4 `ui/tab_purchase.py` 변경

기안 내용 필드(`row=5`) 하단(`row=6` 이전)에 "AI 활용하기" 버튼 추가:

```python
# 806행 이후, row=5 -> 내용 Text 위젯과 같은 행, 또는 별도 행에 버튼 배치
ai_btn = ttk.Button(draft_frame, text="AI 활용하기",
                    command=self._open_ai_draft_dialog)
ai_btn.grid(row=5, column=1, sticky="e", ...)
# 기존 row 6(비고) 이하의 row 번호를 +1 조정 필요
```

**[CA 의견]**: `tab_purchase.py`의 기안 섹션 grid 레이아웃에서 row 5가 "내용 *:" 필드이다. "AI 활용하기" 버튼은 내용 Text 위젯 바로 아래(row 6)에 배치하고, 기존 "비고"(row 6) 이하를 row 7~로 밀어야 한다. 또는 내용 Text 위젯과 같은 셀의 우측 하단에 작은 버튼으로 배치하는 방법도 있다. grid 행 번호 조정 시 하위 위젯(`opt_frame`, `Separator` 등)의 row 값도 모두 업데이트해야 한다.

#### 4.2.5 `ui/dialog_settings.py` 변경

설정 다이얼로그에 "AI 설정" 섹션 추가:

```python
# Gemini API 키 입력
ttk.Label(frame, text="AI 설정", font=FONTS["heading"]).grid(...)
ttk.Label(frame, text="Gemini API 키:").grid(...)
self._gemini_key_var = tk.StringVar(value=get_gemini_api_key())
ttk.Entry(frame, textvariable=self._gemini_key_var, show="*", width=44).grid(...)
# show="*" 로 마스킹, 토글 버튼으로 표시/숨기기 전환 가능
```

### 4.3 Gemini API Integration Details

#### 4.3.1 API Endpoint & Configuration

| 항목 | 값 |
|------|-----|
| **Endpoint** | `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent` |
| **Auth** | Query parameter `key={API_KEY}` |
| **Model** | `gemini-3.1-flash-lite-preview` (기본), 사용자 선택 가능 (3종) |
| **Timeout** | 30초 |
| **Content-Type** | `application/json` |

#### 4.3.2 Request Format

```json
{
  "contents": [
    {
      "parts": [
        {
          "text": "{system_prompt}\n\n{user_input}"
        }
      ]
    }
  ],
  "generationConfig": {
    "temperature": 0.7,
    "maxOutputTokens": 1024,
    "topP": 0.9
  }
}
```

#### 4.3.3 Response Parsing

```python
response_json = resp.json()
text = response_json["candidates"][0]["content"]["parts"][0]["text"]
```

에러 응답 처리:
- `candidates` 없음: 안전 필터 차단 가능성 -> "내용을 생성할 수 없습니다" 안내
- HTTP 429: 한도 초과 -> "API 호출 한도에 도달했습니다. 잠시 후 다시 시도하세요."
- HTTP 400: 잘못된 API 키 -> "API 키를 확인하세요."
- HTTP 5xx: 서버 오류 -> "서버 오류가 발생했습니다. 잠시 후 다시 시도하세요."

#### 4.3.4 Prompt Design

**[BE-Expert 의견]**: 공공기관 기안 문서의 특성을 반영한 시스템 프롬프트를 설계한다. 핵심은 격식체, 항목 나열, 간결한 문장이다.

```
시스템 프롬프트:
────────────────────────────────────────
당신은 공공기관 물품구매 기안서 작성 도우미입니다.
다음 규칙을 따라 기안 내용을 작성하세요:

1. 공공기관 공문서 격식체를 사용합니다 (예: "~하고자 합니다", "~바랍니다")
2. 간결하고 명확한 문장으로 작성합니다
3. 구매 목적, 필요성, 구매 내역을 포함합니다
4. 2~4개 단락으로 구성합니다
5. 마지막에 "위와 같이 구매하고자 하오니 결재 바랍니다." 등의 맺음말을 포함합니다
6. 제목이나 머리말 없이 본문 내용만 작성합니다
────────────────────────────────────────

사용자 프롬프트 (컨텍스트 있을 때):
────────────────────────────────────────
[구매 정보]
- 품명: {item_name}
- 규격: {spec}
- 수량: {quantity}{unit}

[요청]
{user_input}

위 정보를 바탕으로 물품구매 기안 내용을 작성해주세요.
────────────────────────────────────────

사용자 프롬프트 (컨텍스트 없을 때):
────────────────────────────────────────
[요청]
{user_input}

위 내용을 바탕으로 물품구매 기안 내용을 작성해주세요.
────────────────────────────────────────
```

생성 예시:
```
업무용 노트북 10대를 관내 직원 업무환경 개선을 위해 구매하고자 합니다.

현재 사용 중인 노트북의 노후화로 인해 업무 처리 속도가 저하되어
업무 효율성이 감소하고 있어 교체가 시급한 상황입니다.

이에 시장조사를 통해 비교견적 2개를 확보하였으며,
최저가 업체를 선정하여 수의계약으로 구매하고자 합니다.

위와 같이 구매하고자 하오니 결재 바랍니다.
```

### 4.4 API Key Management

**[Sec-Arch 종합 의견]**:

| 항목 | 방안 | 비고 |
|------|------|------|
| **저장 위치** | `data/settings.json` | 기존 네이버 API 키와 동일 패턴 |
| **저장 형식** | 평문 (JSON) | 로컬 데스크톱 앱, 서버 미전송 |
| **UI 표시** | `show="*"` 마스킹 | 설정 다이얼로그에서 입력 시 |
| **전송 보안** | HTTPS 전용 | googleapis.com은 HTTPS만 지원 |
| **키 범위** | Gemini API 전용 | 다른 Google 서비스 접근 불가 |
| **EXE 배포 시** | 사용자가 직접 API 키 발급/입력 | EXE에 키 하드코딩 금지 |

추가 보안 고려사항:
- API 키는 Google AI Studio (aistudio.google.com)에서 무료 발급
- 키 노출 시 Google Cloud Console에서 즉시 재발급 가능
- `settings.json` 파일은 `.gitignore`에 포함 (이미 `data/` 폴더 전체가 제외됨)
- 프롬프트에 개인정보(주민번호, 계좌번호 등)를 포함하지 않도록 안내 문구 표시

---

## 5. UI/UX Detailed Design

### 5.1 User Flow

```
[사용자]
    │
    ├─1─ 구매 조사 탭에서 기안 정보 입력 중
    │    (품명, 규격, 수량 등 이미 입력 상태)
    │
    ├─2─ "내용 *:" 필드 하단의 [AI 활용하기] 버튼 클릭
    │
    │    ┌─────── API 키 확인 ───────┐
    │    │ 미설정? → 안내 메시지     │
    │    │ "설정에서 Gemini API 키를  │
    │    │  먼저 입력하세요."        │
    │    │ [설정 열기] [취소]        │
    │    └───────────────────────────┘
    │
    ├─3─ AI 기안 생성 다이얼로그 표시 (모달)
    │    ┌─────────────────────────────────────┐
    │    │  AI 기안 내용 생성                   │
    │    │                                     │
    │    │  현재 품목: 노트북(i7/16GB) 10대     │
    │    │                                     │
    │    │  설명/키워드:                        │
    │    │  ┌─────────────────────────────────┐│
    │    │  │ 직원 업무환경 개선을 위한       ││
    │    │  │ 노후 장비 교체 구매             ││
    │    │  └─────────────────────────────────┘│
    │    │                                     │
    │    │  [생성하기]                          │
    │    │                                     │
    │    │  ── 생성 결과 ──────────────────────│
    │    │  │ (생성 전: 안내 텍스트)           ││
    │    │  │ (생성 후: AI 생성 결과)          ││
    │    │  ────────────────────────────────────│
    │    │                                     │
    │    │        [적용]  [다시 생성]  [취소]   │
    │    └─────────────────────────────────────┘
    │
    ├─4─ 키워드 입력 → [생성하기] 클릭
    │    (버튼 비활성화 + "생성 중..." 표시)
    │
    ├─5─ 생성 결과 미리보기 확인
    │    ├── 만족 → [적용] 클릭 → 내용 필드에 반영, 다이얼로그 닫힘
    │    └── 불만족 → [다시 생성] 클릭 → 4로 돌아감
    │
    └─6─ 기안 내용 필드에 생성된 텍스트 적용됨
         (기존 내용이 있었다면 덮어쓰기 확인 후 적용)
```

### 5.2 Dialog Layout Detail

**[FE-Arch 종합 의견]**:

```
┌─ AI 기안 내용 생성 ──────────────────────── [X] ─┐
│                                                   │
│  현재 품목: 노트북(i7/16GB/512SSD) 10대           │
│  ─────────────────────────────────────────────    │
│                                                   │
│  설명/키워드 *:                                    │
│  ┌───────────────────────────────────────────┐    │
│  │                                           │    │
│  │ (3줄 높이, wrap=word)                     │    │
│  │                                           │    │
│  └───────────────────────────────────────────┘    │
│  ※ 구매 목적, 배경 등을 간략히 입력하세요          │
│                                                   │
│  [생성하기]                    (Primary 스타일)     │
│                                                   │
│  ── 생성 결과 ────────────────────────────────    │
│  ┌───────────────────────────────────────────┐    │
│  │                                           │    │
│  │ (8줄 높이, 읽기전용, 스크롤바)             │    │
│  │                                           │    │
│  │                                           │    │
│  │                                           │    │
│  └───────────────────────────────────────────┘    │
│                                                   │
│  ─────────────────────────────────────────────    │
│          [적용]    [다시 생성]    [취소]            │
│                                                   │
└───────────────────────────────────────────────────┘
```

디자인 규칙:
- `BaseDialog` 상속, 디자인 시스템 `COLORS`, `SPACING`, `FONTS` 적용
- "현재 품목" 정보는 `Info.TLabel` 스타일 (파란색, 읽기전용)
- "생성하기" 버튼: `Primary.TButton` 스타일
- "적용" 버튼: `Primary.TButton`, 생성 결과 없을 때 `state="disabled"`
- "다시 생성" 버튼: 일반 `TButton`, 생성 결과 없을 때 `state="disabled"`
- 미리보기 영역: 스크롤바 포함, `bg=COLORS["bg_surface"]`, `relief="flat"`
- 키보드 단축키: Enter(생성), Ctrl+Enter(적용), Escape(취소)

### 5.3 "AI 활용하기" Button Placement

**[CA 의견 보충]**: `tab_purchase.py`의 기안 섹션 grid에서 "내용 *:" 라벨(row=5, col=0)과 tk.Text(row=5, col=1~3) 사이에 버튼을 넣으면 레이아웃이 복잡해진다. 권장 방안:

**방안 A (채택)**: 내용 tk.Text 위젯 바로 아래에 별도 행으로 버튼 배치
```python
# row=5: 내용 tk.Text (기존)
# row=6: [AI 활용하기] 버튼 (신규, 우측 정렬)
ttk.Button(draft_frame, text="AI 활용하기",
           command=self._open_ai_draft_dialog).grid(
    row=6, column=1, columnspan=3, sticky="e", pady=(0, SPACING["sm"]))
# row=7: 비고 (기존 row=6에서 이동)
# row=8: Separator (기존 row=7에서 이동)
# row=9: 포함 항목 선택 (기존 row=8에서 이동)
```

**방안 B (대안)**: 내용 라벨 옆에 작은 버튼
```python
# "내용 *:" 라벨과 같은 row, 다른 column에 소형 버튼
# 단점: 라벨 영역이 좁아 레이아웃 불안정
```

---

## 6. Error Handling Strategy

**[QA 의견]**:

### 6.1 Error Scenarios & Responses

| # | Scenario | HTTP Code | User Message | Action |
|---|----------|-----------|-------------|--------|
| E1 | API 키 미설정 | - | "Gemini API 키가 설정되지 않았습니다.\n[설정]에서 API 키를 먼저 입력하세요." | 설정 다이얼로그 열기 옵션 |
| E2 | 네트워크 오류 | ConnectionError | "인터넷 연결을 확인하세요." | 재시도 유도 |
| E3 | API 키 오류 | 400 / 403 | "API 키가 올바르지 않습니다.\n[설정]에서 확인하세요." | 설정 열기 옵션 |
| E4 | 한도 초과 | 429 | "API 호출 한도에 도달했습니다.\n잠시 후(1분) 다시 시도하세요." | 자동 재시도 안 함 |
| E5 | 서버 오류 | 500 / 503 | "Google 서버 오류가 발생했습니다.\n잠시 후 다시 시도하세요." | 재시도 유도 |
| E6 | 타임아웃 | Timeout | "응답 시간이 초과되었습니다.\n네트워크 상태를 확인 후 다시 시도하세요." | 재시도 유도 |
| E7 | 안전 필터 차단 | 200 (no candidates) | "해당 내용은 생성할 수 없습니다.\n설명을 다르게 입력해보세요." | 입력 수정 유도 |
| E8 | 빈 입력 | - | "설명/키워드를 입력하세요." | 입력 필드 포커스 |
| E9 | 응답 파싱 오류 | 200 (unexpected format) | "응답을 처리할 수 없습니다.\n다시 시도하세요." | 재시도 유도 |

### 6.2 Error Handling Code Pattern

```python
class GeminiAPIError(Exception):
    def __init__(self, message: str, code: str = "UNKNOWN", status_code: int = 0):
        super().__init__(message)
        self.code = code
        self.status_code = status_code

# 에러 코드 매핑
ERROR_MESSAGES = {
    "NOT_CONFIGURED": "Gemini API 키가 설정되지 않았습니다.\n[설정]에서 API 키를 먼저 입력하세요.",
    "NETWORK_ERROR":  "인터넷 연결을 확인하세요.",
    "INVALID_KEY":    "API 키가 올바르지 않습니다.\n[설정]에서 확인하세요.",
    "RATE_LIMIT":     "API 호출 한도에 도달했습니다.\n잠시 후(1분) 다시 시도하세요.",
    "SERVER_ERROR":   "Google 서버 오류가 발생했습니다.\n잠시 후 다시 시도하세요.",
    "TIMEOUT":        "응답 시간이 초과되었습니다.\n네트워크 상태를 확인 후 다시 시도하세요.",
    "BLOCKED":        "해당 내용은 생성할 수 없습니다.\n설명을 다르게 입력해보세요.",
    "PARSE_ERROR":    "응답을 처리할 수 없습니다.\n다시 시도하세요.",
}
```

### 6.3 Threading Strategy

**[BE-Expert 의견]**: tkinter는 단일 스레드이므로 API 호출 시 `threading.Thread`를 사용하여 UI 블로킹을 방지한다.

```python
import threading

def _on_generate(self):
    """생성 버튼 클릭 핸들러"""
    self._set_loading(True)

    def _worker():
        try:
            result = self._api.generate_draft_content(user_input, context)
            self.after(0, lambda: self._on_result(result))
        except GeminiAPIError as e:
            self.after(0, lambda: self._on_error(e))
        finally:
            self.after(0, lambda: self._set_loading(False))

    threading.Thread(target=_worker, daemon=True).start()

def _set_loading(self, loading: bool):
    """로딩 상태 UI 전환"""
    if loading:
        self._generate_btn.configure(state="disabled", text="생성 중...")
        self._apply_btn.configure(state="disabled")
        self._retry_btn.configure(state="disabled")
    else:
        self._generate_btn.configure(state="normal", text="생성하기")
```

---

## 7. Implementation Roadmap

### Phase 1: Core Infrastructure (Priority: Critical)

| # | Task | File | Estimated |
|---|------|------|-----------|
| 1-1 | `core/gemini_api.py` 모듈 생성 (GeminiDraftAPI 클래스) | 신규 | 1시간 |
| 1-2 | 프롬프트 템플릿 구현 (`_build_prompt`) | gemini_api.py | 30분 |
| 1-3 | API 호출 + 응답 파싱 (`_call_api`) | gemini_api.py | 30분 |
| 1-4 | 에러 처리 (GeminiAPIError, 에러 코드 매핑) | gemini_api.py | 30분 |
| 1-5 | `config.py`에 `get_gemini_api_key` / `set_gemini_api_key` 추가 | config.py | 10분 |

### Phase 2: Settings UI (Priority: High)

| # | Task | File | Estimated |
|---|------|------|-----------|
| 2-1 | 설정 다이얼로그에 "AI 설정" 섹션 추가 | dialog_settings.py | 30분 |
| 2-2 | Gemini API 키 입력란 (마스킹 + 저장) | dialog_settings.py | 20분 |

### Phase 3: AI Draft Dialog (Priority: High)

| # | Task | File | Estimated |
|---|------|------|-----------|
| 3-1 | `ui/dialog_ai_draft.py` 다이얼로그 생성 (BaseDialog 상속) | 신규 | 1시간 |
| 3-2 | 키워드 입력 + 생성 버튼 + 미리보기 영역 레이아웃 | dialog_ai_draft.py | 30분 |
| 3-3 | Threading 기반 API 호출 + 로딩 상태 관리 | dialog_ai_draft.py | 30분 |
| 3-4 | "적용" / "다시 생성" / "취소" 버튼 동작 | dialog_ai_draft.py | 20분 |
| 3-5 | 기존 내용 덮어쓰기 확인 로직 | dialog_ai_draft.py | 10분 |

### Phase 4: Integration (Priority: High)

| # | Task | File | Estimated |
|---|------|------|-----------|
| 4-1 | `tab_purchase.py`에 "AI 활용하기" 버튼 추가 + grid 행 조정 | tab_purchase.py | 30분 |
| 4-2 | 버튼 클릭 시 다이얼로그 열기 + 품목 컨텍스트 전달 | tab_purchase.py | 20분 |
| 4-3 | 적용 콜백: 생성 결과를 내용 tk.Text에 삽입 | tab_purchase.py | 10분 |

### Phase 5: Polish & Test (Priority: Medium)

| # | Task | File | Estimated |
|---|------|------|-----------|
| 5-1 | API 키 미설정 시 안내 + 설정 열기 연동 | dialog_ai_draft.py | 20분 |
| 5-2 | 키보드 단축키 (Enter, Ctrl+Enter, Escape) | dialog_ai_draft.py | 15분 |
| 5-3 | PyInstaller EXE 빌드 테스트 | build_exe.py | 30분 |
| 5-4 | 통합 테스트 (정상 흐름 + 에러 시나리오) | 수동 | 1시간 |

**총 예상 소요시간**: 약 8시간

---

## 8. Test Plan

**[QA 종합 전략]**:

### 8.1 Unit Tests

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| T-01 | API 키 미설정 시 `is_configured()` | api_key="" | False |
| T-02 | 프롬프트 빌드 (컨텍스트 있음) | item_name="노트북", user_input="업무용" | 프롬프트에 "노트북", "업무용" 포함 |
| T-03 | 프롬프트 빌드 (컨텍스트 없음) | user_input="사무용품 구매" | 기본 프롬프트만 포함 |
| T-04 | 응답 파싱 정상 | 정상 JSON | 텍스트 추출 성공 |
| T-05 | 응답 파싱 실패 (candidates 없음) | 빈 candidates | GeminiAPIError(BLOCKED) |
| T-06 | HTTP 429 처리 | 429 응답 | GeminiAPIError(RATE_LIMIT) |
| T-07 | HTTP 400 처리 | 400 응답 | GeminiAPIError(INVALID_KEY) |
| T-08 | 타임아웃 처리 | Timeout 예외 | GeminiAPIError(TIMEOUT) |
| T-09 | 네트워크 오류 처리 | ConnectionError | GeminiAPIError(NETWORK_ERROR) |

### 8.2 Integration Tests (Manual)

| # | Scenario | Steps | Expected Result |
|---|----------|-------|-----------------|
| IT-01 | 정상 생성 흐름 | API 키 설정 -> 품목 입력 -> AI 버튼 -> 키워드 입력 -> 생성 -> 적용 | 내용 필드에 생성 텍스트 반영 |
| IT-02 | 다시 생성 | IT-01 후 "다시 생성" 클릭 | 새로운 결과 표시, 이전 결과와 다름 |
| IT-03 | 기존 내용 덮어쓰기 | 내용 필드에 텍스트 입력 후 AI 생성 -> 적용 | 덮어쓰기 확인 후 반영 |
| IT-04 | API 키 미설정 | API 키 없이 AI 버튼 클릭 | 안내 메시지 표시 |
| IT-05 | 네트워크 오류 | Wi-Fi 끊기 -> 생성 클릭 | 에러 메시지 표시, UI 정상 복귀 |
| IT-06 | 잘못된 API 키 | 임의 문자열 입력 후 생성 | "API 키를 확인하세요" 메시지 |
| IT-07 | 빈 입력 생성 | 키워드 미입력 -> 생성 클릭 | "설명/키워드를 입력하세요" 안내 |
| IT-08 | 수정 모드 호환 | 수정 모드에서 AI 생성 -> 적용 -> 재생성 | 정상 동작 |
| IT-09 | EXE 빌드 동작 | PyInstaller 빌드 후 EXE에서 AI 기능 실행 | 정상 동작 |

### 8.3 Edge Cases

| # | Case | Expected |
|---|------|----------|
| EC-01 | 매우 긴 키워드 입력 (1000자+) | 프롬프트 자르기 또는 그대로 전송 (API가 처리) |
| EC-02 | 특수문자만 입력 | 정상 API 호출 (결과 품질은 낮을 수 있음) |
| EC-03 | 연속 빠른 클릭 (더블 클릭) | 중복 호출 방지 (버튼 비활성화로 처리됨) |
| EC-04 | 생성 중 다이얼로그 닫기 | 스레드 daemon=True로 자동 정리 |
| EC-05 | 여러 품목(다중 품목) 컨텍스트 | 첫 품목 + "외 N종" 형태로 표시 |

---

## 9. Risk Analysis

### 9.1 Risk Matrix

| # | Risk | Impact | Likelihood | Mitigation | Owner |
|---|------|--------|------------|------------|-------|
| R1 | Gemini 무료 티어 중단/변경 | High | Low | 코드 구조를 추상화하여 다른 LLM으로 교체 용이하게 설계 | BE-Expert |
| R2 | API 응답 품질 불안정 | Medium | Medium | 프롬프트 최적화, "다시 생성" 기능으로 UX 보완 | BE-Expert |
| R3 | 한도 초과 (15 RPM) | Low | Low | 단일 사용자 데스크톱 앱이므로 한도 초과 가능성 낮음; 429 처리 구현 | QA |
| R4 | PyInstaller 빌드 시 requests 호환성 | Low | Low | 이미 naver_api.py에서 requests 사용 중, 검증됨 | CA |
| R5 | API 키 유출 (EXE 배포 시) | Medium | Low | 사용자 직접 발급/입력, EXE에 키 미포함 | Sec-Arch |
| R6 | 공공기관 보안 정책으로 외부 API 차단 | High | Medium | 기능 비활성화(graceful degradation), 기존 수동 입력/템플릿 유지 | PM |
| R7 | 생성 내용의 부정확성/부적절성 | Medium | Medium | 미리보기 단계에서 사용자 확인 필수, 자동 적용 없음 | PM |

### 9.2 Mitigation Details

**R6 (방화벽 차단) 대응**:
- 기능은 완전히 선택적(optional)이며, API 키가 없으면 "AI 활용하기" 버튼만 보이고 기존 워크플로우에 영향 없음
- 오프라인/차단 환경에서는 기존 템플릿 시스템(`draft_templates`)과 수동 입력을 계속 사용
- 버튼 tooltip에 "인터넷 연결 필요" 안내

**R1 (무료 티어 변경) 대응**:
- `GeminiDraftAPI` 클래스를 교체 가능한 구조로 설계
- API URL, 모델명을 상수로 분리하여 설정 변경만으로 모델 교체 가능
- 향후 `google-generativeai` 패키지 또는 다른 LLM API로 전환 시 `_call_api` 메서드만 수정

---

## 10. Dependencies

### 10.1 New Dependencies

| Package | Version | Purpose | Size Impact |
|---------|---------|---------|-------------|
| (없음) | - | requests 패키지 이미 설치됨 | 0 |

**[CA 의견]**: 신규 의존성이 없다. `requests`는 이미 `naver_api.py`에서 사용 중이며, `threading`은 Python 표준 라이브러리다. PyInstaller 빌드 크기에 영향 없음.

### 10.2 External Dependencies

| Service | Tier | Rate Limit | Cost |
|---------|------|-----------|------|
| Google Gemini API (3.1 Flash Lite) | Free | 15 RPM, 500 RPD | 무료 (기본) |
| Google Gemini API (2.5 Flash Lite) | Free | 10 RPM, 20 RPD | 무료 |
| Google Gemini API (2.5 Flash) | Free | 5 RPM, 20 RPD | 무료 |

### 10.3 Integration Points (Existing Code)

| File | Change Type | Description |
|------|------------|-------------|
| `config.py` | Add functions | `get_gemini_api_key()`, `set_gemini_api_key()`, `get_gemini_model()`, `set_gemini_model()` |
| `ui/tab_purchase.py` | Add button + handler | "AI 활용하기" 버튼, grid row 조정 |
| `ui/dialog_settings.py` | Add section | "AI 설정" 섹션 + API 키 입력란 + 모델 선택 Combobox |
| `core/gemini_api.py` | New file | GeminiDraftAPI 클래스 |
| `ui/dialog_ai_draft.py` | New file | AIDraftDialog 클래스 |

---

## 11. Success Criteria

### 11.1 Definition of Done

- [x] Gemini API 호출로 기안 내용 생성 가능
- [x] 생성된 내용을 기안 내용 필드에 적용 가능
- [x] "다시 생성"으로 재호출 가능
- [x] 에러 시 사용자 친화적 메시지 표시
- [x] API 키 설정/관리 UI 제공
- [x] 기존 기능(수동 입력, 템플릿)에 영향 없음
- [x] PyInstaller EXE 빌드 정상 동작
- [x] API 키 발급 가이드를 프로그램 내에서 열람 가능
- [x] API 키 미설정 시 가이드 열기 옵션 제공

### 11.2 Quality Criteria

- [x] 에러 시나리오 9종(E1~E9) 모두 처리
- [x] UI 블로킹 없음 (Threading 사용)
- [x] 디자인 시스템 일관성 유지 (COLORS, SPACING, FONTS)
- [x] BaseDialog 패턴 준수

---

## 12. Next Steps

1. [ ] Design 문서 작성 (`gemini-draft-content.design.md`)
2. [ ] Phase 1 구현: `core/gemini_api.py`
3. [ ] Phase 2 구현: 설정 UI 변경
4. [ ] Phase 3 구현: AI 다이얼로그
5. [ ] Phase 4 구현: 통합
6. [ ] Phase 5: 테스트 및 빌드 검증

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-13 | Initial draft - Expert team plan | CTO Lead |
| 0.2 | 2026-03-13 | FR-14~17 추가 (API 키 발급 가이드 프로그램 내장) | PM |
| 0.3 | 2026-03-13 | FR-18~21 추가 (무료 모델 선택 기능), 모델 변경(2.0→3.1 Flash Lite 기본), 타임아웃 30초, threading 클로저 버그 수정 | BE-Expert |
