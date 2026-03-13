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
DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
REQUEST_TIMEOUT = 30  # seconds

# 무료 모델 목록 (model_id → 표시명)
FREE_MODELS: dict[str, str] = {
    "gemini-3.1-flash-lite-preview": "Gemini 3.1 Flash Lite — 분당 15회, 하루 500회",
    "gemini-2.5-flash-lite":         "Gemini 2.5 Flash Lite — 분당 10회, 하루 20회",
    "gemini-2.5-flash":              "Gemini 2.5 Flash — 분당 5회, 하루 20회",
}

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
        """공공기관 기안 문서에 특화된 프롬프트 조합"""
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
        """Gemini REST API 호출 및 응답 파싱"""
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
