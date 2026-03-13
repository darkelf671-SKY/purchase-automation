"""설정 다이얼로그 — 저장 경로 등 환경 설정"""
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from config import (OUTPUT_DIR, SCREENSHOT_DIR, get_output_dir, set_output_dir,
                    get_department, set_department,
                    get_inspector, set_inspector, get_witness, set_witness,
                    get_gemini_api_key, set_gemini_api_key, open_gemini_guide)
from ui.base_dialog import BaseDialog
from ui.design_system import COLORS, SPACING, FONTS


class OutputSettingsDialog(BaseDialog):
    def __init__(self, parent, on_save_callback=None):
        self._on_save_callback = on_save_callback
        super().__init__(parent, "환경 설정")

    def _build_content(self, frame):
        # 부서명 설정
        ttk.Label(frame, text="기본 설정", font=FONTS["heading"]).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, SPACING["lg"]))

        ttk.Label(frame, text="부서명:").grid(
            row=1, column=0, sticky="w", pady=SPACING["sm"], padx=(0, SPACING["md"]))
        self._dept_var = tk.StringVar(value=get_department())
        ttk.Entry(frame, textvariable=self._dept_var, width=44).grid(
            row=1, column=1, sticky="ew", pady=SPACING["sm"])
        ttk.Label(frame, text="※ 기안서에 자동 입력",
                  foreground=COLORS["text_muted"]).grid(
            row=1, column=2, sticky="w", padx=(SPACING["md"], 0))

        # 검수자
        ttk.Label(frame, text="검수자:").grid(
            row=2, column=0, sticky="w", pady=SPACING["sm"], padx=(0, SPACING["md"]))
        self._inspector_var = tk.StringVar(value=get_inspector())
        ttk.Entry(frame, textvariable=self._inspector_var, width=44).grid(
            row=2, column=1, sticky="ew", pady=SPACING["sm"])
        ttk.Label(frame, text="※ 검수 입력에 자동 입력",
                  foreground=COLORS["text_muted"]).grid(
            row=2, column=2, sticky="w", padx=(SPACING["md"], 0))

        # 입회자
        ttk.Label(frame, text="입회자:").grid(
            row=3, column=0, sticky="w", pady=SPACING["sm"], padx=(0, SPACING["md"]))
        self._witness_var = tk.StringVar(value=get_witness())
        ttk.Entry(frame, textvariable=self._witness_var, width=44).grid(
            row=3, column=1, sticky="ew", pady=SPACING["sm"])
        ttk.Label(frame, text="※ 검수 입력에 자동 입력",
                  foreground=COLORS["text_muted"]).grid(
            row=3, column=2, sticky="w", padx=(SPACING["md"], 0))

        ttk.Separator(frame, orient="horizontal").grid(
            row=4, column=0, columnspan=3, sticky="ew", pady=SPACING["lg"])

        # 파일 저장 경로
        ttk.Label(frame, text="파일 저장 경로", font=FONTS["heading"]).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(0, SPACING["lg"]))

        # 산출 폴더 (구매건별 HWP/Excel 저장)
        ttk.Label(frame, text="산출 폴더:").grid(
            row=6, column=0, sticky="w", pady=SPACING["sm"], padx=(0, SPACING["md"]))
        self._out_var = tk.StringVar(value=str(get_output_dir()))
        ttk.Entry(frame, textvariable=self._out_var, width=44,
                  state="readonly").grid(row=6, column=1, sticky="ew", pady=SPACING["sm"])
        ttk.Button(frame, text="변경", width=6,
                   command=self._browse_output).grid(
            row=6, column=2, padx=(SPACING["md"], 0), pady=SPACING["sm"])

        # 스크린샷 폴더 (정보 표시 + 열기)
        ttk.Label(frame, text="스크린샷 폴더:").grid(
            row=7, column=0, sticky="w", pady=SPACING["sm"], padx=(0, SPACING["md"]))
        ttk.Label(frame, text=str(SCREENSHOT_DIR),
                  foreground=COLORS["text_muted"]).grid(
            row=7, column=1, sticky="w", pady=SPACING["sm"])
        ttk.Button(frame, text="열기", width=6,
                   command=lambda: subprocess.Popen(["explorer", str(SCREENSHOT_DIR)])
                   ).grid(row=7, column=2, padx=(SPACING["md"], 0), pady=SPACING["sm"])

        ttk.Label(frame, text="※ 스크린샷 폴더는 프로그램 내부 경로로 고정됩니다.",
                  foreground=COLORS["text_muted"]).grid(
            row=8, column=0, columnspan=3, sticky="w", pady=(0, SPACING["sm"]))

        # ── AI 설정 ──────────────────────────────────────────
        ttk.Separator(frame, orient="horizontal").grid(
            row=9, column=0, columnspan=3, sticky="ew", pady=SPACING["lg"])

        ttk.Label(frame, text="AI 설정", font=FONTS["heading"]).grid(
            row=10, column=0, columnspan=3, sticky="w", pady=(0, SPACING["lg"]))

        # Gemini API 키
        ttk.Label(frame, text="Gemini API 키:").grid(
            row=11, column=0, sticky="w", pady=SPACING["sm"], padx=(0, SPACING["md"]))

        key_frame = ttk.Frame(frame)
        key_frame.grid(row=11, column=1, sticky="ew", pady=SPACING["sm"])

        self._gemini_key_var = tk.StringVar(value=get_gemini_api_key())
        self._gemini_key_entry = ttk.Entry(
            key_frame, textvariable=self._gemini_key_var, width=36, show="*")
        self._gemini_key_entry.pack(side="left", fill="x", expand=True)

        self._show_key = False
        self._toggle_key_btn = ttk.Button(
            key_frame, text="보기", width=4,
            command=self._toggle_key_visibility)
        self._toggle_key_btn.pack(side="left", padx=(SPACING["sm"], 0))

        ttk.Label(frame, text="※ Google AI Studio에서 무료 발급",
                  foreground=COLORS["text_muted"]).grid(
            row=11, column=2, sticky="w", padx=(SPACING["md"], 0))

        # 발급 가이드 보기 버튼
        ttk.Button(frame, text="발급 가이드 보기",
                   command=self._open_api_guide).grid(
            row=12, column=1, sticky="w", pady=SPACING["sm"])

        frame.columnconfigure(1, weight=1)

    def _build_buttons(self, frame):
        ttk.Button(frame, text="기본값으로",
                   command=self._reset_default).pack(side="left", padx=(0, SPACING["md"]))
        ttk.Button(frame, text="산출 폴더 열기",
                   command=self._open_output).pack(side="left", padx=(0, SPACING["lg"]))
        ttk.Button(frame, text="저장", style="Primary.TButton",
                   command=self._on_save).pack(side="right", padx=(SPACING["sm"], 0))
        ttk.Button(frame, text="취소",
                   command=self.destroy).pack(side="right", padx=(SPACING["sm"], 0))

    def _browse_output(self):
        path = filedialog.askdirectory(
            title="산출 폴더 선택 — 구매 문서(HWP, Excel)가 저장될 위치",
            initialdir=self._out_var.get(),
        )
        if path:
            self._out_var.set(path)

    def _reset_default(self):
        self._out_var.set(str(OUTPUT_DIR))

    def _open_output(self):
        p = Path(self._out_var.get())
        p.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(p)])

    def _on_save(self):
        out = self._out_var.get().strip()
        if not out:
            messagebox.showwarning("입력 오류", "산출 폴더를 지정하세요.", parent=self)
            return
        try:
            Path(out).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("오류", f"폴더를 생성할 수 없습니다:\n{e}", parent=self)
            return
        set_output_dir(out)
        set_department(self._dept_var.get().strip())
        set_inspector(self._inspector_var.get().strip())
        set_witness(self._witness_var.get().strip())
        set_gemini_api_key(self._gemini_key_var.get().strip())

        dept = self._dept_var.get().strip() or "(미설정)"
        insp = self._inspector_var.get().strip() or "(미설정)"
        witn = self._witness_var.get().strip() or "(미설정)"
        gemini = "설정됨" if self._gemini_key_var.get().strip() else "(미설정)"
        messagebox.showinfo("저장 완료",
            f"설정이 저장되었습니다.\n\n"
            f"부서명: {dept}\n검수자: {insp}\n입회자: {witn}\n"
            f"산출 폴더: {out}\nGemini API: {gemini}",
            parent=self)
        if self._on_save_callback:
            self._on_save_callback()
        self.destroy()

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
