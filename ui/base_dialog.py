"""다이얼로그 기본 클래스 — 중앙 정렬, 패딩, grab 순서 표준화"""
import tkinter as tk
from tkinter import ttk
from ui.design_system import SPACING, FONTS


class BaseDialog(tk.Toplevel):
    """모든 다이얼로그의 기본 클래스

    사용법:
        class MyDialog(BaseDialog):
            def _build_content(self, frame):
                # frame 안에 위젯 배치
                ...
            def _build_buttons(self, frame):
                # frame 안에 버튼 배치 (선택, 기본 제공: 저장/취소)
                ...
    """
    def __init__(self, parent, title: str, *, on_save=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self._on_save_cb = on_save

        # 콘텐츠 영역
        content = ttk.Frame(self, padding=SPACING["xl"])
        content.pack(fill="both", expand=True)
        self._build_content(content)

        # 버튼 영역
        btn_frame = ttk.Frame(self, padding=(SPACING["xl"], 0, SPACING["xl"], SPACING["lg"]))
        btn_frame.pack(fill="x")
        self._build_buttons(btn_frame)

        # 중앙 정렬 + focus
        self.transient(parent)
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"+{px}+{py}")
        self.wait_visibility()
        self.focus_set()

    def _build_content(self, frame: ttk.Frame):
        """서브클래스에서 오버라이드"""
        pass

    def _build_buttons(self, frame: ttk.Frame):
        """서브클래스에서 오버라이드 (기본: 저장/취소)"""
        ttk.Button(frame, text="저장", style="Primary.TButton",
                   command=self._on_save).pack(side="right", padx=SPACING["sm"])
        ttk.Button(frame, text="취소",
                   command=self.destroy).pack(side="right", padx=SPACING["sm"])

    def _on_save(self):
        """서브클래스에서 오버라이드"""
        pass

    def _fire_save_callback(self):
        if self._on_save_cb:
            self._on_save_cb()
