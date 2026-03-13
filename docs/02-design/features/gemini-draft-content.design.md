# Gemini AI 기안내용 생성 기능 Design Document

> **Summary**: Google Gemini API를 활용하여 공공기관 기안서 "내용" 필드를 자동 생성하는 기능의 상세 설계
>
> **Project**: 구매기안 자동화 시스템 v1.0
> **Version**: v1.3
> **Author**: 전산팀 장길섭
> **Date**: 2026-03-13
> **Status**: Draft
> **Planning Doc**: [gemini-draft-content.plan.md](../../01-plan/features/gemini-draft-content.plan.md)

---

## 1. Overview

### 1.1 Design Goals

1. Gemini REST API 직접 호출로 기안 내용 자동 생성 (SDK 미사용, requests 패키지 활용)
2. BaseDialog 패턴 준수 + 디자인 시스템 일관성 유지
3. threading 기반 비동기 호출로 UI 블로킹 방지
4. 기존 코드(config.py, tab_purchase.py, dialog_settings.py)의 최소 변경
5. API 키 발급 가이드 HTML 내장으로 사용자 셀프 설정 지원
6. PyInstaller EXE 빌드 호환성 보장

### 1.2 Design Principles

- **최소 의존성**: 신규 패키지 없음 (requests, threading은 기존/표준 라이브러리)
- **기존 패턴 준수**: config.py의 get/set 패턴, BaseDialog 상속, COLORS/SPACING/FONTS 적용
- **선택적 기능**: API 키 미설정 시 기존 워크플로우에 영향 없음 (graceful degradation)
- **사용자 확인 필수**: 생성 결과는 반드시 미리보기 후 수동 적용 (자동 적용 없음)

---

## 2. Architecture

### 2.1 Component Diagram

```
tab_purchase.py                      dialog_ai_draft.py
+----------------------------+       +----------------------------------+
|  [section] 기안 작성        |       |  AIDraftDialog (BaseDialog)      |
|                            |       |                                  |
|  내용 *: [tk.Text]         |       |  품목 컨텍스트 표시               |
|  [AI 활용하기] ─── click ──+──>    |  키워드 입력 [tk.Text, 3줄]      |
|                            |       |  [생성하기] (Primary.TButton)     |
|                            |       |  미리보기 [tk.Text, 8줄, readonly]|
|  (내용 필드 갱신) <── apply ─+──    |  [적용] [다시 생성] [취소]        |
+----------------------------+       +--------+-------------------------+
                                              |
                                              | threading.Thread
                                              v
                                     +----------------------------------+
                                     |  core/gemini_api.py              |
                                     |  GeminiDraftAPI                  |
                                     |  - generate_draft_content()      |
                                     |  - _build_prompt()               |
                                     |  - _call_api()                   |
                                     +--------+-------------------------+
                                              | HTTPS (requests)
                                              v
                                     +----------------------------------+
                                     |  Google Gemini API               |
                                     |  generativelanguage.googleapis   |
                                     |  .com/v1beta                     |
                                     |  Model: gemini-2.5-flash (Free)  |
                                     +----------------------------------+

config.py                            dialog_settings.py
+----------------------------+       +----------------------------------+
|  get_gemini_api_key()      | <──── |  AI 설정 섹션                    |
|  set_gemini_api_key()      |       |  Gemini API 키: [****] [보기]    |
|  GUIDE_DIR (경로 상수)      |       |  [발급 가이드 보기]              |
+----------------------------+       +----------------------------------+
                                              |
                                              | webbrowser.open()
                                              v
                                     +----------------------------------+
                                     |  docs/manual/                    |
                                     |  gemini-api-key-guide.html       |
                                     +----------------------------------+
```

### 2.2 Data Flow

```
[사용자]
  |
  +--(1) "AI 활용하기" 클릭
  |      tab_purchase._open_ai_draft_dialog()
  |        +-- API 키 확인: config.get_gemini_api_key()
  |        +-- 미설정 시: 안내 메시지 + "가이드 보기" / "설정 열기" 옵션
  |        +-- 설정 완료 시: AIDraftDialog 생성
  |
  +--(2) AIDraftDialog 생성
  |      purchase_context = {items, item_name, spec, quantity, unit} 전달
  |
  +--(3) 키워드 입력 + [생성하기] 클릭
  |      _on_generate()
  |        +-- 입력 검증 (빈 문자열 체크)
  |        +-- _set_loading(True)
  |        +-- threading.Thread(target=_worker) 시작
  |
  +--(4) _worker (백그라운드 스레드)
  |      GeminiDraftAPI.generate_draft_content(user_input, context)
  |        +-- _build_prompt(user_input, context) -> prompt 문자열
  |        +-- _call_api(prompt) -> requests.post() -> response text
  |      self.after(0, _on_result) 또는 self.after(0, _on_error)
  |
  +--(5) 결과 표시
  |      _on_result(text): 미리보기 tk.Text에 표시
  |      _on_error(e): 에러 메시지 표시 (상태 라벨)
  |
  +--(6) [적용] 클릭
  |      _on_apply()
  |        +-- 기존 내용 확인 -> 덮어쓰기 확인 다이얼로그
  |        +-- on_apply 콜백 호출 (생성 텍스트 전달)
  |        +-- 다이얼로그 닫기
  |
  +--(7) tab_purchase._apply_ai_draft(text)
         self._draft_content_text.delete("1.0", "end")
         self._draft_content_text.insert("1.0", text)
```

### 2.3 가이드 HTML 열기 흐름

```
[설정 다이얼로그]                      [AI 다이얼로그]
"발급 가이드 보기" 버튼                 API 키 미설정 에러 메시지
       |                                      |
       +--- _open_guide() ----+--- _open_guide() ---+
                               |
                               v
                    config.GUIDE_DIR / "gemini-api-key-guide.html"
                               |
                               v
                    webbrowser.open(str(guide_path))
                               |
                               v
                    시스템 기본 브라우저에서 HTML 렌더링
```

### 2.4 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `dialog_ai_draft.py` | `core/gemini_api.py` | API 호출 |
| `dialog_ai_draft.py` | `ui/base_dialog.py` | 다이얼로그 기본 클래스 |
| `dialog_ai_draft.py` | `config.py` | API 키 조회, 가이드 경로 |
| `tab_purchase.py` | `dialog_ai_draft.py` | 다이얼로그 생성 |
| `tab_purchase.py` | `config.py` | API 키 확인 |
| `dialog_settings.py` | `config.py` | API 키 저장/로드, 가이드 열기 |
| `core/gemini_api.py` | `requests` (기존) | HTTP 호출 |
| `build_exe.py` | `docs/manual/` | 가이드 HTML 번들 |

---

## 3. Module Detail Design

### 3.1 `core/gemini_api.py` (신규 파일)

```python
"""Google Gemini API 연동 -- 기안 내용 자동 생성

REST API 직접 호출 방식 (google-generativeai SDK 미사용).
기존 naver_api.py와 동일한 패턴(requests + timeout).
"""
import requests
from typing import Optional

# ── 상수 ──────────────────────────────────────────────────────
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta"
    "/models/{model}:generateContent"
)
DEFAULT_MODEL = "gemini-2.5-flash"
REQUEST_TIMEOUT = 20  # seconds

# ── 에러 코드 & 메시지 ───────────────────────────────────────
ERROR_MESSAGES: dict[str, str] = {
    "NOT_CONFIGURED": (
        "Gemini API 키가 설정되지 않았습니다.\n"
        "[설정]에서 API 키를 먼저 입력하세요."
    ),
    "NETWORK_ERROR": "인터넷 연결을 확인하세요.",
    "INVALID_KEY": (
        "API 키가 올바르지 않습니다.\n"
        "[설정]에서 확인하세요."
    ),
    "RATE_LIMIT": (
        "API 호출 한도에 도달했습니다.\n"
        "잠시 후(1분) 다시 시도하세요."
    ),
    "SERVER_ERROR": (
        "Google 서버 오류가 발생했습니다.\n"
        "잠시 후 다시 시도하세요."
    ),
    "TIMEOUT": (
        "응답 시간이 초과되었습니다.\n"
        "네트워크 상태를 확인 후 다시 시도하세요."
    ),
    "BLOCKED": (
        "해당 내용은 생성할 수 없습니다.\n"
        "설명을 다르게 입력해보세요."
    ),
    "PARSE_ERROR": (
        "응답을 처리할 수 없습니다.\n"
        "다시 시도하세요."
    ),
}

# ── 시스템 프롬프트 ───────────────────────────────────────────
SYSTEM_PROMPT = (
    "당신은 공공기관 물품구매 기안서 작성 도우미입니다.\n"
    "다음 규칙을 따라 기안 내용을 작성하세요:\n\n"
    "1. 공공기관 공문서 격식체를 사용합니다 "
    '(예: "~하고자 합니다", "~바랍니다")\n'
    "2. 간결하고 명확한 문장으로 작성합니다\n"
    "3. 구매 목적, 필요성, 구매 내역을 포함합니다\n"
    "4. 2~4개 단락으로 구성합니다\n"
    '5. 마지막에 "위와 같이 구매하고자 하오니 '
    '결재 바랍니다." 등의 맺음말을 포함합니다\n'
    "6. 제목이나 머리말 없이 본문 내용만 작성합니다"
)

USER_PROMPT_WITH_CONTEXT = (
    "[구매 정보]\n"
    "- 품명: {item_name}\n"
    "- 규격: {spec}\n"
    "- 수량: {quantity}{unit}\n\n"
    "[요청]\n"
    "{user_input}\n\n"
    "위 정보를 바탕으로 물품구매 기안 내용을 작성해주세요."
)

USER_PROMPT_WITHOUT_CONTEXT = (
    "[요청]\n"
    "{user_input}\n\n"
    "위 내용을 바탕으로 물품구매 기안 내용을 작성해주세요."
)


class GeminiAPIError(Exception):
    """Gemini API 호출 에러"""
    def __init__(self, message: str, code: str = "UNKNOWN",
                 status_code: int = 0):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class GeminiDraftAPI:
    """기안 내용 생성 전용 Gemini API 클라이언트"""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        """API 키 설정 여부 확인"""
        return bool(self.api_key and self.api_key.strip())

    def generate_draft_content(
        self,
        user_input: str,
        context: Optional[dict] = None,
    ) -> str:
        """기안 내용 생성 API 호출

        Args:
            user_input: 사용자가 입력한 간략 설명/키워드
            context: 현재 품목 정보 dict
                     {item_name, spec, quantity, unit} (선택)

        Returns:
            생성된 기안 내용 텍스트

        Raises:
            GeminiAPIError: API 호출 실패 시
        """
        if not self.is_configured():
            raise GeminiAPIError(
                ERROR_MESSAGES["NOT_CONFIGURED"],
                code="NOT_CONFIGURED"
            )

        prompt = self._build_prompt(user_input, context)
        return self._call_api(prompt)

    def _build_prompt(self, user_input: str,
                      context: Optional[dict]) -> str:
        """공공기관 기안 문서에 특화된 프롬프트 조합

        Returns:
            "{SYSTEM_PROMPT}\n\n{USER_PROMPT}" 형태의 전체 프롬프트
        """
        if context and context.get("item_name"):
            user_part = USER_PROMPT_WITH_CONTEXT.format(
                item_name=context.get("item_name", ""),
                spec=context.get("spec", ""),
                quantity=context.get("quantity", ""),
                unit=context.get("unit", ""),
                user_input=user_input,
            )
        else:
            user_part = USER_PROMPT_WITHOUT_CONTEXT.format(
                user_input=user_input,
            )

        return f"{SYSTEM_PROMPT}\n\n{user_part}"

    def _call_api(self, prompt: str) -> str:
        """Gemini REST API 호출 및 응답 파싱

        Request Body:
            {
              "contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
                "topP": 0.9
              }
            }

        Response Parsing:
            response["candidates"][0]["content"]["parts"][0]["text"]

        Raises:
            GeminiAPIError: HTTP 에러, 타임아웃, 파싱 실패 등
        """
        url = GEMINI_API_URL.format(model=self.model)
        params = {"key": self.api_key}
        body = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
                "topP": 0.9,
            },
        }

        try:
            resp = requests.post(
                url, params=params, json=body,
                timeout=REQUEST_TIMEOUT
            )
        except requests.exceptions.Timeout:
            raise GeminiAPIError(
                ERROR_MESSAGES["TIMEOUT"],
                code="TIMEOUT"
            )
        except requests.exceptions.ConnectionError:
            raise GeminiAPIError(
                ERROR_MESSAGES["NETWORK_ERROR"],
                code="NETWORK_ERROR"
            )
        except requests.exceptions.RequestException as e:
            raise GeminiAPIError(str(e), code="NETWORK_ERROR")

        # HTTP 에러 코드 처리
        if resp.status_code in (400, 403):
            raise GeminiAPIError(
                ERROR_MESSAGES["INVALID_KEY"],
                code="INVALID_KEY",
                status_code=resp.status_code,
            )
        if resp.status_code == 429:
            raise GeminiAPIError(
                ERROR_MESSAGES["RATE_LIMIT"],
                code="RATE_LIMIT",
                status_code=429,
            )
        if resp.status_code >= 500:
            raise GeminiAPIError(
                ERROR_MESSAGES["SERVER_ERROR"],
                code="SERVER_ERROR",
                status_code=resp.status_code,
            )
        if resp.status_code != 200:
            raise GeminiAPIError(
                f"HTTP {resp.status_code}: {resp.text[:200]}",
                code="UNKNOWN",
                status_code=resp.status_code,
            )

        # 응답 파싱
        try:
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise GeminiAPIError(
                    ERROR_MESSAGES["BLOCKED"],
                    code="BLOCKED",
                    status_code=200,
                )
            text = candidates[0]["content"]["parts"][0]["text"]
            return text.strip()
        except (KeyError, IndexError, TypeError):
            raise GeminiAPIError(
                ERROR_MESSAGES["PARSE_ERROR"],
                code="PARSE_ERROR",
                status_code=200,
            )
```

**메서드 시그니처 요약:**

| Method | Signature | Returns |
|--------|-----------|---------|
| `__init__` | `(api_key: str, model: str = DEFAULT_MODEL)` | None |
| `is_configured` | `() -> bool` | API 키 존재 여부 |
| `generate_draft_content` | `(user_input: str, context: Optional[dict]) -> str` | 생성된 텍스트 |
| `_build_prompt` | `(user_input: str, context: Optional[dict]) -> str` | 전체 프롬프트 |
| `_call_api` | `(prompt: str) -> str` | 응답 텍스트 |

---

### 3.2 `config.py` 변경

**추가할 상수 (line 23 이후, TEMPLATE_DIR 아래):**

```python
GUIDE_DIR = _BUNDLE_DIR / "docs" / "manual"
```

**추가할 함수 (기존 get_witness/set_witness 이후):**

```python
def get_gemini_api_key() -> str:
    """설정된 Gemini API 키 반환"""
    return load_settings().get("gemini_api_key", "")


def set_gemini_api_key(value: str) -> None:
    """Gemini API 키를 settings.json에 저장"""
    s = load_settings()
    s["gemini_api_key"] = value
    save_settings(s)
```

**settings.json 구조 변경 (before/after):**

```json
// Before
{
  "output_dir": "...",
  "department": "...",
  "inspector": "...",
  "witness": "...",
  "naver_client_id": "...",
  "naver_client_secret": "..."
}

// After (gemini_api_key 추가)
{
  "output_dir": "...",
  "department": "...",
  "inspector": "...",
  "witness": "...",
  "naver_client_id": "...",
  "naver_client_secret": "...",
  "gemini_api_key": "AIza..."
}
```

---

### 3.3 `ui/dialog_ai_draft.py` (신규 파일)

#### 3.3.1 클래스 구조

```python
"""AI 기안 내용 생성 다이얼로그"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from pathlib import Path

from ui.base_dialog import BaseDialog
from ui.design_system import COLORS, SPACING, FONTS
from core.gemini_api import GeminiDraftAPI, GeminiAPIError
from config import get_gemini_api_key, GUIDE_DIR


class AIDraftDialog(BaseDialog):
    """키워드 입력 -> Gemini 호출 -> 미리보기 -> 적용

    Args:
        parent: 부모 윈도우
        on_apply: 적용 콜백 (생성된 텍스트를 인자로 전달)
        purchase_context: 현재 품목 정보 dict (선택)
            {item_name, spec, quantity, unit, items: list[dict]}
    """

    def __init__(self, parent, *, on_apply=None,
                 purchase_context=None):
        self._on_apply_cb = on_apply
        self._purchase_context = purchase_context
        self._generated_text: str = ""
        self._is_loading: bool = False
        super().__init__(parent, "AI 기안 내용 생성")

    # ... (메서드 상세 아래)
```

#### 3.3.2 Grid 레이아웃 상세

`_build_content(self, frame)` 내부 grid 구성:

| Row | Col 0 | Col 1 | Widget | Notes |
|-----|-------|-------|--------|-------|
| 0 | colspan=2 | | `ttk.Label` "현재 품목: ..." | Info.TLabel 스타일, 품목 요약 |
| 1 | colspan=2 | | `ttk.Separator` | horizontal |
| 2 | colspan=2 | | `ttk.Label` "설명/키워드 *:" | 일반 TLabel |
| 3 | colspan=2 | | `tk.Text` (입력) | height=3, wrap="word" |
| 4 | colspan=2 | | `ttk.Label` 힌트 | text_muted 색상 |
| 5 | colspan=2 | | `ttk.Button` "생성하기" | Primary.TButton, sticky="w" |
| 6 | colspan=2 | | `ttk.Separator` | horizontal |
| 7 | colspan=2 | | `ttk.Label` "생성 결과" | heading 폰트 |
| 8 | colspan=2 | | `tk.Text` (미리보기) + Scrollbar | height=8, state="disabled" |
| 9 | colspan=2 | | `ttk.Label` 상태 | 에러/성공 메시지 표시 |

**frame.columnconfigure(0, weight=1)** 적용.

```python
def _build_content(self, frame):
    frame.columnconfigure(0, weight=1)

    # Row 0: 현재 품목 정보
    ctx_text = self._format_context_summary()
    if ctx_text:
        ttk.Label(frame, text=ctx_text,
                  style="Info.TLabel").grid(
            row=0, column=0, columnspan=2,
            sticky="w", pady=(0, SPACING["sm"]))
        ttk.Separator(frame, orient="horizontal").grid(
            row=1, column=0, columnspan=2,
            sticky="ew", pady=SPACING["sm"])

    # Row 2: 입력 라벨
    ttk.Label(frame, text="설명/키워드 *:").grid(
        row=2, column=0, columnspan=2,
        sticky="w", pady=(SPACING["sm"], SPACING["xs"]))

    # Row 3: 키워드 입력 (tk.Text, 3줄)
    self._input_text = tk.Text(
        frame, width=56, height=3, wrap="word",
        font=FONTS["body"], relief="flat", bd=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["primary_light"],
        highlightthickness=1,
        padx=SPACING["sm"], pady=SPACING["sm"])
    self._input_text.grid(
        row=3, column=0, columnspan=2,
        sticky="ew", pady=SPACING["xs"])

    # Row 4: 힌트
    ttk.Label(
        frame,
        text="※ 구매 목적, 배경 등을 간략히 입력하세요",
        foreground=COLORS["text_muted"]
    ).grid(row=4, column=0, columnspan=2,
           sticky="w", pady=(0, SPACING["sm"]))

    # Row 5: 생성 버튼
    self._generate_btn = ttk.Button(
        frame, text="생성하기",
        style="Primary.TButton",
        command=self._on_generate)
    self._generate_btn.grid(
        row=5, column=0, columnspan=2,
        sticky="w", pady=SPACING["sm"])

    # Row 6: 구분선
    ttk.Separator(frame, orient="horizontal").grid(
        row=6, column=0, columnspan=2,
        sticky="ew", pady=SPACING["sm"])

    # Row 7: 결과 라벨
    ttk.Label(frame, text="생성 결과",
              font=FONTS["heading"]).grid(
        row=7, column=0, sticky="w",
        pady=(SPACING["sm"], SPACING["xs"]))

    # Row 8: 미리보기 (tk.Text, 8줄, 읽기전용)
    preview_frame = ttk.Frame(frame)
    preview_frame.grid(
        row=8, column=0, columnspan=2,
        sticky="nsew", pady=SPACING["xs"])
    preview_frame.columnconfigure(0, weight=1)
    preview_frame.rowconfigure(0, weight=1)

    self._preview_text = tk.Text(
        preview_frame, width=56, height=8,
        wrap="word", font=FONTS["body"],
        relief="flat", bd=1,
        bg=COLORS["bg_surface"],
        highlightbackground=COLORS["border"],
        highlightthickness=1,
        padx=SPACING["sm"], pady=SPACING["sm"],
        state="disabled")
    self._preview_text.grid(
        row=0, column=0, sticky="nsew")

    scrollbar = ttk.Scrollbar(
        preview_frame, orient="vertical",
        command=self._preview_text.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    self._preview_text.configure(
        yscrollcommand=scrollbar.set)

    # Row 9: 상태 메시지
    self._status_var = tk.StringVar()
    self._status_label = ttk.Label(
        frame, textvariable=self._status_var,
        foreground=COLORS["text_muted"],
        wraplength=480)
    self._status_label.grid(
        row=9, column=0, columnspan=2,
        sticky="w", pady=(SPACING["xs"], 0))

    # 키보드 바인딩
    self.bind("<Return>", lambda e: self._on_generate())
    self.bind("<Control-Return>",
              lambda e: self._on_apply())
    self.bind("<Escape>", lambda e: self.destroy())
```

#### 3.3.3 버튼 영역

```python
def _build_buttons(self, frame):
    """[적용] [다시 생성] [취소] 3버튼 구성"""
    self._apply_btn = ttk.Button(
        frame, text="적용",
        style="Primary.TButton",
        command=self._on_apply,
        state="disabled")
    self._apply_btn.pack(
        side="right", padx=SPACING["sm"])

    self._retry_btn = ttk.Button(
        frame, text="다시 생성",
        command=self._on_generate,
        state="disabled")
    self._retry_btn.pack(
        side="right", padx=SPACING["sm"])

    ttk.Button(
        frame, text="취소",
        command=self.destroy
    ).pack(side="right", padx=SPACING["sm"])
```

#### 3.3.4 핵심 메서드

```python
def _format_context_summary(self) -> str:
    """품목 컨텍스트를 요약 문자열로 변환

    단일 품목: "현재 품목: 노트북(i7/16GB) 10대"
    다중 품목: "현재 품목: 노트북(i7/16GB) 10대 외 2종"
    컨텍스트 없음: ""
    """
    ctx = self._purchase_context
    if not ctx or not ctx.get("item_name"):
        return ""
    name = ctx["item_name"]
    spec = ctx.get("spec", "")
    qty = ctx.get("quantity", "")
    unit = ctx.get("unit", "")
    items = ctx.get("items", [])

    base = f"{name}"
    if spec:
        base += f"({spec})"
    if qty:
        base += f" {qty}{unit}"

    if len(items) > 1:
        base += f" 외 {len(items) - 1}종"

    return f"현재 품목: {base}"


def _on_generate(self):
    """생성 버튼 클릭 핸들러 -- threading으로 API 호출"""
    user_input = self._input_text.get("1.0", "end").strip()
    if not user_input:
        self._status_var.set("설명/키워드를 입력하세요.")
        self._status_label.configure(
            foreground=COLORS["warning"])
        self._input_text.focus_set()
        return

    if self._is_loading:
        return  # 중복 호출 방지

    api_key = get_gemini_api_key()
    if not api_key:
        self._show_no_key_message()
        return

    api = GeminiDraftAPI(api_key)
    context = self._purchase_context
    self._set_loading(True)

    def _worker():
        try:
            result = api.generate_draft_content(
                user_input, context)
            self.after(0, lambda: self._on_result(result))
        except GeminiAPIError as e:
            self.after(0, lambda: self._on_error(e))
        finally:
            self.after(0, lambda: self._set_loading(False))

    threading.Thread(target=_worker, daemon=True).start()


def _set_loading(self, loading: bool):
    """로딩 상태 UI 전환"""
    self._is_loading = loading
    if loading:
        self._generate_btn.configure(
            state="disabled", text="생성 중...")
        self._apply_btn.configure(state="disabled")
        self._retry_btn.configure(state="disabled")
        self._status_var.set("Gemini API 호출 중...")
        self._status_label.configure(
            foreground=COLORS["info"])
    else:
        self._generate_btn.configure(
            state="normal", text="생성하기")
        # apply/retry 상태는 _on_result/_on_error에서 관리


def _on_result(self, text: str):
    """API 성공 시 미리보기 영역에 결과 표시"""
    self._generated_text = text
    self._preview_text.configure(state="normal")
    self._preview_text.delete("1.0", "end")
    self._preview_text.insert("1.0", text)
    self._preview_text.configure(state="disabled")
    self._apply_btn.configure(state="normal")
    self._retry_btn.configure(state="normal")
    self._status_var.set("생성 완료")
    self._status_label.configure(
        foreground=COLORS["success"])


def _on_error(self, error: GeminiAPIError):
    """API 실패 시 에러 메시지 표시"""
    self._status_var.set(str(error))
    self._status_label.configure(
        foreground=COLORS["danger"])
    if self._generated_text:
        # 이전 결과가 있으면 버튼 유지
        self._apply_btn.configure(state="normal")
        self._retry_btn.configure(state="normal")
    else:
        self._retry_btn.configure(state="normal")


def _on_apply(self):
    """적용 버튼 -- 생성 결과를 콜백으로 전달"""
    if not self._generated_text:
        return
    if self._on_apply_cb:
        self._on_apply_cb(self._generated_text)
    self.destroy()


def _show_no_key_message(self):
    """API 키 미설정 시 안내 + 가이드 열기 옵션"""
    result = messagebox.askyesnocancel(
        "API 키 미설정",
        "Gemini API 키가 설정되지 않았습니다.\n\n"
        "API 키 발급 가이드를 열까요?\n\n"
        "[예] 발급 가이드 보기\n"
        "[아니오] 다이얼로그 닫기",
        parent=self)
    if result is True:
        _open_guide()
    elif result is False:
        self.destroy()
    # None(Cancel) = 그대로 유지
```

#### 3.3.5 가이드 열기 공용 함수

```python
def _open_guide():
    """API 키 발급 가이드 HTML을 기본 브라우저로 열기"""
    guide_path = GUIDE_DIR / "gemini-api-key-guide.html"
    if guide_path.exists():
        webbrowser.open(str(guide_path))
    else:
        messagebox.showwarning(
            "파일 없음",
            f"가이드 파일을 찾을 수 없습니다:\n{guide_path}")
```

> 이 함수는 `dialog_ai_draft.py` 모듈 레벨에 정의하고,
> `dialog_settings.py`에서도 `from ui.dialog_ai_draft import _open_guide`로 재사용하거나,
> 동일 로직을 `config.py`에 `open_guide()` 함수로 정의하여 양쪽에서 import할 수 있다.
> **설계 결정**: `config.py`에 `open_gemini_guide()` 함수를 두어 중복 방지.

**config.py에 추가:**

```python
def open_gemini_guide():
    """Gemini API 키 발급 가이드 HTML을 기본 브라우저로 열기"""
    import webbrowser
    guide_path = GUIDE_DIR / "gemini-api-key-guide.html"
    if guide_path.exists():
        webbrowser.open(str(guide_path))
        return True
    return False
```

---

### 3.4 `ui/dialog_settings.py` 변경

#### 3.4.1 import 추가

```python
# 기존 import에 추가
from config import (...기존...,
                    get_gemini_api_key, set_gemini_api_key,
                    open_gemini_guide)
```

#### 3.4.2 Grid Row 변경표 (Before/After)

| Row | Before (현재) | After (변경 후) |
|-----|--------------|----------------|
| 0 | "기본 설정" 제목 | "기본 설정" 제목 (동일) |
| 1 | 부서명 | 부서명 (동일) |
| 2 | 검수자 | 검수자 (동일) |
| 3 | 입회자 | 입회자 (동일) |
| 4 | Separator | Separator (동일) |
| 5 | "파일 저장 경로" 제목 | "파일 저장 경로" 제목 (동일) |
| 6 | 산출 폴더 | 산출 폴더 (동일) |
| 7 | 스크린샷 폴더 | 스크린샷 폴더 (동일) |
| 8 | 스크린샷 힌트 | 스크린샷 힌트 (동일) |
| 9 | _(없음)_ | **Separator** (NEW) |
| 10 | _(없음)_ | **"AI 설정" 제목** (NEW) |
| 11 | _(없음)_ | **Gemini API 키 입력란** (NEW) |
| 12 | _(없음)_ | **"발급 가이드 보기" 버튼** (NEW) |

#### 3.4.3 추가 코드 상세

`_build_content()` 메서드 끝 (`frame.columnconfigure(1, weight=1)` 직전)에 추가:

```python
# ── AI 설정 ──────────────────────────────────────────
ttk.Separator(frame, orient="horizontal").grid(
    row=9, column=0, columnspan=3,
    sticky="ew", pady=SPACING["lg"])

ttk.Label(frame, text="AI 설정", font=FONTS["heading"]).grid(
    row=10, column=0, columnspan=3,
    sticky="w", pady=(0, SPACING["lg"]))

# Gemini API 키
ttk.Label(frame, text="Gemini API 키:").grid(
    row=11, column=0, sticky="w",
    pady=SPACING["sm"], padx=(0, SPACING["md"]))

key_frame = ttk.Frame(frame)
key_frame.grid(row=11, column=1, sticky="ew",
               pady=SPACING["sm"])

self._gemini_key_var = tk.StringVar(
    value=get_gemini_api_key())
self._gemini_key_entry = ttk.Entry(
    key_frame, textvariable=self._gemini_key_var,
    width=36, show="*")
self._gemini_key_entry.pack(side="left", fill="x",
                             expand=True)

self._show_key = False
self._toggle_key_btn = ttk.Button(
    key_frame, text="보기", width=4,
    command=self._toggle_key_visibility)
self._toggle_key_btn.pack(side="left",
                           padx=(SPACING["sm"], 0))

ttk.Label(frame, text="※ Google AI Studio에서 무료 발급",
          foreground=COLORS["text_muted"]).grid(
    row=11, column=2, sticky="w",
    padx=(SPACING["md"], 0))

# 발급 가이드 보기 버튼
ttk.Button(frame, text="발급 가이드 보기",
           command=self._open_api_guide).grid(
    row=12, column=1, sticky="w",
    pady=SPACING["sm"])
```

#### 3.4.4 추가 메서드

```python
def _toggle_key_visibility(self):
    """API 키 표시/숨기기 전환"""
    self._show_key = not self._show_key
    if self._show_key:
        self._gemini_key_entry.configure(show="")
        self._toggle_key_btn.configure(text="숨기기")
    else:
        self._gemini_key_entry.configure(show="*")
        self._toggle_key_btn.configure(text="보기")


def _open_api_guide(self):
    """Gemini API 키 발급 가이드 열기"""
    if not open_gemini_guide():
        messagebox.showwarning(
            "파일 없음",
            "가이드 파일을 찾을 수 없습니다.",
            parent=self)
```

#### 3.4.5 `_on_save()` 메서드 변경

기존 `_on_save()` 끝에 Gemini API 키 저장 추가:

```python
def _on_save(self):
    # ... 기존 코드 (output_dir, department, inspector, witness 저장) ...

    # Gemini API 키 저장 (추가)
    set_gemini_api_key(self._gemini_key_var.get().strip())

    # ... 기존 messagebox + callback + destroy ...
```

---

### 3.5 `ui/tab_purchase.py` 변경

#### 3.5.1 import 추가

```python
from config import (...기존..., get_gemini_api_key,
                    open_gemini_guide)
from ui.dialog_ai_draft import AIDraftDialog
```

#### 3.5.2 Grid Row 변경표 (`_build_draft_section` 내부)

| Row | Before (현재) | After (변경 후) |
|-----|--------------|----------------|
| 0 | 템플릿 프레임 | 템플릿 프레임 (동일) |
| 1 | Separator | Separator (동일) |
| 2 | 기안제목 | 기안제목 (동일) |
| 3 | 기안일 | 기안일 (동일) |
| 4 | 부서명 | 부서명 (동일) |
| 5 | 내용 (tk.Text) | 내용 (tk.Text) (동일) |
| 6 | 비고 | **[AI 활용하기] 버튼** (NEW, 우측 정렬) |
| 7 | Separator | 비고 (기존 row=6에서 이동) |
| 8 | 포함 항목 선택 | Separator (기존 row=7에서 이동) |
| - | | 포함 항목 선택 (기존 row=8 -> row=9) |

#### 3.5.3 코드 변경 상세

기존 `_build_draft_section()` 내에서 row=5 (내용 tk.Text) 이후:

```python
# row=5: 내용 tk.Text (기존, 변경 없음)
# ...

# row=6: AI 활용하기 버튼 (NEW)
self._ai_draft_btn = ttk.Button(
    draft_frame, text="AI 활용하기",
    command=self._open_ai_draft_dialog)
self._ai_draft_btn.grid(
    row=6, column=1, columnspan=3,
    sticky="e", pady=(0, SPACING["sm"]))

# row=7: 비고 (기존 row=6 -> row=7)
ttk.Label(draft_frame, text="비고:").grid(
    row=7, column=0, sticky="w",
    pady=SPACING["sm"], padx=(0, SPACING["md"]))
# ... (기존 비고 Entry grid row=6 -> row=7)

# row=8: Separator (기존 row=7 -> row=8)
# row=9: 포함 항목 선택 (기존 row=8 -> row=9)
```

#### 3.5.4 추가 메서드

```python
def _open_ai_draft_dialog(self):
    """AI 기안 내용 생성 다이얼로그 열기"""
    # API 키 확인
    api_key = get_gemini_api_key()
    if not api_key:
        result = messagebox.askyesnocancel(
            "API 키 미설정",
            "Gemini API 키가 설정되지 않았습니다.\n\n"
            "API 키 발급 가이드를 열까요?\n\n"
            "[예] 발급 가이드 보기\n"
            "[아니오] 닫기",
            parent=self._content)
        if result is True:
            open_gemini_guide()
        return

    # 품목 컨텍스트 수집
    context = self._collect_purchase_context()

    # 기존 내용 확인 (적용 시 덮어쓰기 확인용)
    existing = self._draft_content_text.get(
        "1.0", "end").strip()

    def on_apply(text: str):
        """AI 생성 결과를 기안 내용 필드에 적용"""
        if existing:
            confirm = messagebox.askyesno(
                "내용 덮어쓰기",
                "기존 기안 내용이 있습니다.\n"
                "AI 생성 결과로 덮어쓰시겠습니까?",
                parent=self._content)
            if not confirm:
                return
        self._draft_content_text.delete("1.0", "end")
        self._draft_content_text.insert("1.0", text)

    AIDraftDialog(
        self._content.winfo_toplevel(),
        on_apply=on_apply,
        purchase_context=context)


def _collect_purchase_context(self) -> dict:
    """현재 입력된 품목 정보를 dict로 수집

    Returns:
        {
            "item_name": str,  # 첫 품목 이름
            "spec": str,       # 첫 품목 규격
            "quantity": str,   # 첫 품목 수량
            "unit": str,       # 첫 품목 단위
            "items": list[dict],  # 전체 품목 리스트
        }
    """
    items = []
    for row in self._item_rows:
        items.append({
            "item_name": row.item_name_var.get(),
            "spec": row.spec_var.get(),
            "quantity": row.quantity_var.get(),
            "unit": row.unit_var.get(),
        })

    first = items[0] if items else {}
    return {
        "item_name": first.get("item_name", ""),
        "spec": first.get("spec", ""),
        "quantity": first.get("quantity", ""),
        "unit": first.get("unit", ""),
        "items": items,
    }
```

---

### 3.6 `build_exe.py` 변경

#### 3.6.1 가이드 HTML 번들 추가

`build_exe()` 함수 내 `cmd` 리스트에 `--add-data` 항목 추가:

```python
def build_exe():
    seed = create_seed_db()
    template_dir = ROOT / "documents" / "templates"
    guide_dir = ROOT / "docs" / "manual"   # <-- NEW

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "구매기안자동화",
        # 읽기전용 리소스 번들
        "--add-data", f"{template_dir};documents/templates",
        # 가이드 HTML 번들 (NEW)
        "--add-data", f"{guide_dir};docs/manual",
        # 시드 DB 번들
        "--add-data", f"{seed};data",
        "--noconfirm",
        "--clean",
        str(ROOT / "main.py"),
    ]
    # ... 나머지 동일 ...
```

이로써 PyInstaller 빌드 시 `docs/manual/gemini-api-key-guide.html`이
`_MEIPASS/docs/manual/` 경로에 포함되며,
`config.py`의 `GUIDE_DIR = _BUNDLE_DIR / "docs" / "manual"`로 접근 가능.

---

## 4. Threading & Sequence Diagram

### 4.1 정상 흐름 시퀀스

```
  User           AIDraftDialog         GeminiDraftAPI        Google API
   |                  |                     |                    |
   |--[생성하기]----->|                     |                    |
   |                  |--_on_generate()     |                    |
   |                  |  validate input     |                    |
   |                  |  _set_loading(True) |                    |
   |                  |                     |                    |
   |                  |--Thread.start()---->|                    |
   |                  |  (daemon=True)      |                    |
   |                  |                     |                    |
   |   [UI 응답 유지]  |                     |--POST /v1beta/---->|
   |                  |                     |  models/gemini-2.5 |
   |                  |                     |  -flash:generate   |
   |                  |                     |  Content           |
   |                  |                     |                    |
   |                  |                     |<---200 OK----------|
   |                  |                     |  {candidates:[...]}|
   |                  |                     |                    |
   |                  |<--.after(0,         |                    |
   |                  |    _on_result)------|                    |
   |                  |                     |                    |
   |                  |--_set_loading(False) |                    |
   |                  |--미리보기 표시       |                    |
   |                  |--[적용] 활성화      |                    |
   |                  |                     |                    |
   |--[적용]--------->|                     |                    |
   |                  |--on_apply(text)     |                    |
   |<--(내용 반영)----|                     |                    |
   |                  |--destroy()          |                    |
```

### 4.2 에러 흐름 시퀀스

```
  User           AIDraftDialog         GeminiDraftAPI        Google API
   |                  |                     |                    |
   |--[생성하기]----->|                     |                    |
   |                  |--Thread.start()---->|                    |
   |                  |                     |--POST------------>|
   |                  |                     |                    |
   |                  |                     |<---429 Rate Limit--|
   |                  |                     |                    |
   |                  |                     |--raise             |
   |                  |                     |  GeminiAPIError    |
   |                  |                     |  (RATE_LIMIT)      |
   |                  |                     |                    |
   |                  |<--.after(0,         |                    |
   |                  |    _on_error)-------|                    |
   |                  |                     |                    |
   |                  |--_set_loading(False) |                    |
   |                  |--에러 메시지 표시    |                    |
   |                  |--[다시 생성] 활성화  |                    |
```

### 4.3 Thread Safety 설계

| 관점 | 대책 |
|------|------|
| UI 스레드 접근 | `self.after(0, callback)` 으로 메인 스레드에서 위젯 조작 |
| 중복 호출 방지 | `self._is_loading` 플래그 + 버튼 disabled |
| 스레드 정리 | `daemon=True` -- 다이얼로그 닫으면 자동 종료 |
| GeminiDraftAPI 인스턴스 | 호출 시마다 새로 생성 (상태 없음, thread-safe) |

---

## 5. Error Handling

### 5.1 에러 코드 매핑 (core/gemini_api.py)

| Code | HTTP | Trigger | User Message |
|------|------|---------|-------------|
| `NOT_CONFIGURED` | - | api_key 빈 문자열 | "API 키가 설정되지 않았습니다..." |
| `NETWORK_ERROR` | ConnectionError | 네트워크 미연결 | "인터넷 연결을 확인하세요." |
| `INVALID_KEY` | 400, 403 | 잘못된 API 키 | "API 키가 올바르지 않습니다..." |
| `RATE_LIMIT` | 429 | 무료 티어 한도 초과 | "API 호출 한도에 도달했습니다..." |
| `SERVER_ERROR` | 5xx | Google 서버 오류 | "Google 서버 오류가 발생했습니다..." |
| `TIMEOUT` | Timeout | 20초 초과 | "응답 시간이 초과되었습니다..." |
| `BLOCKED` | 200 (no candidates) | 안전 필터 차단 | "해당 내용은 생성할 수 없습니다..." |
| `PARSE_ERROR` | 200 (malformed) | JSON 구조 불일치 | "응답을 처리할 수 없습니다..." |

### 5.2 에러 표시 방식

- 에러 메시지는 다이얼로그 하단 `_status_label`에 `COLORS["danger"]` 색상으로 표시
- API 키 미설정(NOT_CONFIGURED)만 별도 messagebox 팝업 (가이드 열기 옵션 포함)
- 나머지 에러는 인라인 표시 (팝업으로 흐름 끊기지 않도록)

---

## 6. Security Considerations

| 항목 | 대응 | 비고 |
|------|------|------|
| API 키 저장 | `settings.json` 평문 | 기존 네이버 API 키와 동일 패턴 |
| UI 표시 | `show="*"` 마스킹 + 토글 | 설정 다이얼로그에서 |
| 전송 보안 | HTTPS 전용 | googleapis.com은 HTTPS만 지원 |
| 프롬프트 데이터 | 품명/규격/수량만 전송 | 개인정보(주민번호 등) 미포함 |
| EXE 배포 | 사용자 직접 API 키 발급/입력 | EXE에 키 하드코딩 없음 |
| `.gitignore` | `data/` 폴더 전체 제외 | settings.json 포함 |

---

## 7. Test Plan

### 7.1 단위 테스트 (core/gemini_api.py)

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| T-01 | `is_configured()` - 빈 키 | `api_key=""` | `False` |
| T-02 | `is_configured()` - 유효 키 | `api_key="AIza..."` | `True` |
| T-03 | `_build_prompt()` - 컨텍스트 있음 | `context={item_name:"노트북"}` | 프롬프트에 "[구매 정보]" + "노트북" 포함 |
| T-04 | `_build_prompt()` - 컨텍스트 없음 | `context=None` | "[요청]" 섹션만 포함 |
| T-05 | `_call_api()` - 정상 응답 | 200 + candidates | 텍스트 반환 |
| T-06 | `_call_api()` - 429 | HTTP 429 | `GeminiAPIError(RATE_LIMIT)` |
| T-07 | `_call_api()` - 400 | HTTP 400 | `GeminiAPIError(INVALID_KEY)` |
| T-08 | `_call_api()` - 타임아웃 | `Timeout` 예외 | `GeminiAPIError(TIMEOUT)` |
| T-09 | `_call_api()` - 네트워크 오류 | `ConnectionError` | `GeminiAPIError(NETWORK_ERROR)` |
| T-10 | `_call_api()` - candidates 없음 | 200 + `{candidates:[]}` | `GeminiAPIError(BLOCKED)` |

### 7.2 통합 테스트 (수동)

| # | Scenario | Steps | Expected |
|---|----------|-------|----------|
| IT-01 | 정상 생성 | API 키 설정 -> 품목 입력 -> AI 버튼 -> 키워드 -> 생성 -> 적용 | 내용 필드에 텍스트 반영 |
| IT-02 | 다시 생성 | IT-01 후 "다시 생성" | 새 결과 표시 |
| IT-03 | 덮어쓰기 확인 | 기존 내용 있는 상태에서 AI 적용 | 확인 다이얼로그 표시 |
| IT-04 | API 키 미설정 | 키 없이 AI 버튼 클릭 | 안내 + 가이드 열기 옵션 |
| IT-05 | 잘못된 API 키 | 임의 문자열로 생성 | "API 키를 확인하세요" |
| IT-06 | 빈 입력 | 키워드 미입력 -> 생성 | "설명/키워드를 입력하세요" |
| IT-07 | 설정 가이드 | 설정 다이얼로그 -> "발급 가이드 보기" | 브라우저에서 HTML 열림 |
| IT-08 | API 키 마스킹 | 설정 -> API 키 입력 -> "보기" 토글 | show/hide 전환 |
| IT-09 | 수정 모드 호환 | 수정 모드에서 AI 생성 -> 적용 | 정상 동작 |
| IT-10 | EXE 빌드 | PyInstaller 빌드 -> EXE에서 AI + 가이드 | 정상 동작 |
| IT-11 | 다중 품목 컨텍스트 | 3개 품목 입력 -> AI 버튼 | "외 2종" 표시 |

---

## 8. Implementation Order

의존성 기반 구현 순서:

```
Phase 1: config.py 변경
   |  (GUIDE_DIR 상수, get/set_gemini_api_key, open_gemini_guide)
   |  의존성: 없음
   v
Phase 2: core/gemini_api.py 생성
   |  (GeminiDraftAPI, GeminiAPIError, 프롬프트, 에러 매핑)
   |  의존성: config.py (API 키 조회는 호출자가 수행)
   v
Phase 3: ui/dialog_settings.py 변경
   |  (AI 설정 섹션, API 키 입력, 가이드 버튼)
   |  의존성: config.py (get/set_gemini_api_key, open_gemini_guide)
   v
Phase 4: ui/dialog_ai_draft.py 생성
   |  (AIDraftDialog, threading, 미리보기, 적용/다시 생성)
   |  의존성: core/gemini_api.py, config.py, base_dialog.py
   v
Phase 5: ui/tab_purchase.py 변경
   |  ("AI 활용하기" 버튼, grid row 조정, _open_ai_draft_dialog)
   |  의존성: dialog_ai_draft.py, config.py
   v
Phase 6: build_exe.py 변경
   |  (가이드 HTML --add-data 추가)
   |  의존성: docs/manual/ 폴더
   v
Phase 7: 통합 테스트
   (정상 흐름 + 에러 시나리오 + EXE 빌드)
```

---

## 9. File Change Summary

### 9.1 신규 파일

| File | Purpose | Lines (est.) |
|------|---------|-------------|
| `core/gemini_api.py` | Gemini API 클라이언트 + 에러 처리 + 프롬프트 | ~180 |
| `ui/dialog_ai_draft.py` | AI 기안 생성 다이얼로그 | ~200 |

### 9.2 변경 파일

| File | Change Type | Scope |
|------|------------|-------|
| `config.py` | 상수 1개 + 함수 3개 추가 | `GUIDE_DIR`, `get_gemini_api_key`, `set_gemini_api_key`, `open_gemini_guide` |
| `ui/dialog_settings.py` | AI 설정 섹션 추가 (row 9~12) | import 변경, `_build_content` 확장, `_toggle_key_visibility`, `_open_api_guide`, `_on_save` 수정 |
| `ui/tab_purchase.py` | AI 버튼 + 핸들러 추가 | import 변경, `_build_draft_section` grid row 6~9 조정, `_open_ai_draft_dialog`, `_collect_purchase_context` |
| `build_exe.py` | 가이드 HTML 번들 추가 | `--add-data` 1줄 추가 |

### 9.3 변경하지 않는 파일

| File | Reason |
|------|--------|
| `core/models.py` | 데이터 모델 변경 없음 |
| `db/*.py` | DB 스키마 변경 없음 |
| `documents/*.py` | 문서 생성 로직 변경 없음 |
| `ui/base_dialog.py` | 기존 패턴 그대로 사용 |
| `ui/design_system.py` | 기존 스타일 그대로 사용 |

---

## 10. Coding Convention Reference

### 10.1 이 기능에 적용하는 컨벤션

| Item | Convention |
|------|-----------|
| 파일명 | snake_case (`gemini_api.py`, `dialog_ai_draft.py`) |
| 클래스명 | PascalCase (`GeminiDraftAPI`, `AIDraftDialog`, `GeminiAPIError`) |
| 함수/변수명 | snake_case (`generate_draft_content`, `_build_prompt`) |
| 상수 | UPPER_SNAKE_CASE (`GEMINI_API_URL`, `DEFAULT_MODEL`, `SYSTEM_PROMPT`) |
| 한글 주석 | 허용 (공공기관 도메인 특성) |
| 타입힌트 | Python 3 표준 (`Optional[dict]`, `-> str`) |
| 에러 클래스 | `Exception` 상속 + `code`, `status_code` 속성 |
| UI 패턴 | `BaseDialog` 상속, `COLORS`/`SPACING`/`FONTS` 적용 |
| config 패턴 | `get_*()` / `set_*()` 함수 쌍 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-13 | Initial design - Plan 기반 + FR-14(가이드 내장) 반영 | CTO Lead |
