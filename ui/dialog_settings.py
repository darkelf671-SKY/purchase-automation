"""설정 다이얼로그 — 저장 경로 등 환경 설정"""
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from config import (OUTPUT_DIR, SCREENSHOT_DIR, get_output_dir, set_output_dir,
                    get_department, set_department,
                    get_inspector, set_inspector, get_witness, set_witness)
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

        dept = self._dept_var.get().strip() or "(미설정)"
        insp = self._inspector_var.get().strip() or "(미설정)"
        witn = self._witness_var.get().strip() or "(미설정)"
        messagebox.showinfo("저장 완료",
            f"설정이 저장되었습니다.\n\n"
            f"부서명: {dept}\n검수자: {insp}\n입회자: {witn}\n산출 폴더: {out}",
            parent=self)
        if self._on_save_callback:
            self._on_save_callback()
        self.destroy()
