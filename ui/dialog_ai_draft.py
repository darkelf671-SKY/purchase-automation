"""AI 기안 내용 생성 다이얼로그"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from ui.base_dialog import BaseDialog
from ui.design_system import COLORS, SPACING, FONTS
from core.gemini_api import GeminiDraftAPI, GeminiAPIError, FREE_MODELS
from config import get_gemini_api_key, get_gemini_model, open_gemini_guide


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
        self.bind("<Return>", lambda e: self._on_generate()
                  if e.widget != self._input_text else None)
        self.bind("<Control-Return>",
                  lambda e: self._on_apply())
        self.bind("<Escape>", lambda e: self.destroy())

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

    # ── 품목 컨텍스트 ────────────────────────────────────────

    def _format_context_summary(self) -> str:
        """품목 컨텍스트를 요약 문자열로 변환"""
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

    # ── API 호출 ──────────────────────────────────────────────

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

        model = get_gemini_model()
        api = GeminiDraftAPI(api_key, model=model)
        context = self._purchase_context
        self._set_loading(True)

        def _worker():
            try:
                result = api.generate_draft_content(
                    user_input, context)
                self.after(0, lambda r=result: self._on_result(r))
            except GeminiAPIError as e:
                err = e  # except 블록 밖에서 e가 삭제되므로 복사
                self.after(0, lambda ex=err: self._on_error(ex))
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

    def _on_result(self, text: str):
        """API 성공 시 미리보기 영역에 결과 표시"""
        if not text or not text.strip():
            self._status_var.set("[오류] 생성된 내용이 비어 있습니다. 다시 시도하세요.")
            self._status_label.configure(foreground=COLORS["danger"])
            self._retry_btn.configure(state="normal")
            return
        self._generated_text = text
        self._preview_text.configure(state="normal")
        self._preview_text.delete("1.0", "end")
        self._preview_text.insert("1.0", text)
        self._preview_text.configure(state="disabled")
        self._apply_btn.configure(state="normal")
        self._retry_btn.configure(state="normal")
        model_id = get_gemini_model()
        model_name = FREE_MODELS.get(model_id, model_id)
        self._status_var.set(f"생성 완료 | 모델: {model_name}")
        self._status_label.configure(
            foreground=COLORS["success"])

    def _on_error(self, error: GeminiAPIError):
        """API 실패 시 에러 메시지 표시"""
        msg = str(error) if str(error) and str(error) != "None" else "알 수 없는 오류가 발생했습니다."
        self._status_var.set(f"[오류] {msg}")
        self._status_label.configure(
            foreground=COLORS["danger"])
        if self._generated_text:
            self._apply_btn.configure(state="normal")
            self._retry_btn.configure(state="normal")
        else:
            self._retry_btn.configure(state="normal")

    # ── 적용 / 안내 ──────────────────────────────────────────

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
            "[아니오] 닫기",
            parent=self)
        if result is True:
            open_gemini_guide()
        elif result is False:
            self.destroy()
