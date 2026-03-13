"""메인 윈도우 — tkinter Notebook"""
import tkinter as tk
from tkinter import ttk
from config import APP_TITLE, APP_VERSION, APP_AUTHOR, APP_WIDTH, APP_HEIGHT
from ui.design_system import apply_theme, COLORS, FONTS, SPACING
from ui.tab_purchase      import PurchaseTab
from ui.tab_inspection    import InspectionTab
from ui.tab_history       import HistoryTab
from ui.tab_vendor        import VendorTab
from ui.tab_sole_contract import SoleContractTab
from ui.tab_draft_template import DraftTemplateTab


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE}  {APP_VERSION}")
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.resizable(False, False)
        self.configure(background=COLORS["bg_window"])

        self._status_var = tk.StringVar(value="준비 완료")

        # 디자인 시스템 테마 적용
        style = ttk.Style(self)
        apply_theme(style)

        # Notebook
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True,
                      padx=SPACING["md"], pady=(SPACING["md"], SPACING["sm"]))

        self._tab_purchase      = PurchaseTab(notebook, self._status_var)
        self._tab_inspection    = InspectionTab(notebook, self._status_var)
        self._tab_history       = HistoryTab(notebook, self._status_var,
                                             on_load_purchase=self._handle_load_purchase,
                                             on_edit_purchase=self._handle_edit_purchase)
        self._tab_vendor        = VendorTab(notebook, self._status_var)
        self._tab_sole_contract   = SoleContractTab(notebook, self._status_var)
        self._tab_draft_template  = DraftTemplateTab(notebook, self._status_var)

        notebook.add(self._tab_purchase,        text="구매 조사")
        notebook.add(self._tab_inspection,      text="검수 입력")
        notebook.add(self._tab_history,         text="이력 조회")
        notebook.add(self._tab_vendor,          text="업체 관리")
        notebook.add(self._tab_sole_contract,   text="수의계약 사유")
        notebook.add(self._tab_draft_template,  text="기안 템플릿")

        notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)
        self._tab_purchase.refresh_vendors()

        # 하단 바 — flat 스타일 + 상단 구분선
        ttk.Separator(self, orient="horizontal").pack(side="bottom", fill="x")
        bottom = ttk.Frame(self)
        bottom.pack(side="bottom", fill="x")

        ttk.Label(bottom, textvariable=self._status_var,
                  anchor="w",
                  padding=(SPACING["md"], SPACING["sm"])).pack(
            side="left", fill="x", expand=True)
        ttk.Separator(bottom, orient="vertical").pack(
            side="left", fill="y", pady=SPACING["xs"])
        ttk.Label(bottom,
                  text=f"제작: {APP_AUTHOR}   |   {APP_VERSION}",
                  style="Muted.TLabel",
                  anchor="e",
                  padding=(SPACING["md"], SPACING["sm"])).pack(side="right")
        ttk.Separator(bottom, orient="vertical").pack(
            side="right", fill="y", pady=SPACING["xs"])
        ttk.Button(bottom, text="설정",
                   command=self._open_settings).pack(
            side="right", padx=SPACING["md"], pady=SPACING["xs"])

    def _handle_load_purchase(self, record: dict, items: list):
        """이력 조회탭 → 구매 조사탭 데이터 복사 (새 기안 작성)"""
        self._tab_purchase.load_purchase(record, items)
        self._switch_to_purchase_tab()

    def _handle_edit_purchase(self, record: dict, items: list):
        """이력 조회탭 → 구매 조사탭 수정 모드"""
        self._tab_purchase.load_purchase_for_edit(record, items)
        self._switch_to_purchase_tab()

    def _switch_to_purchase_tab(self):
        """구매 조사 탭으로 전환"""
        for child in self.winfo_children():
            if hasattr(child, 'index'):
                try:
                    child.select(0)
                except Exception:
                    pass
        self._tab_purchase.refresh_vendors()

    def _open_settings(self):
        from ui.dialog_settings import OutputSettingsDialog
        OutputSettingsDialog(self, on_save_callback=self._on_settings_saved)

    def _on_settings_saved(self):
        """설정 저장 후 모든 탭의 설정 의존 필드 즉시 갱신"""
        self._tab_purchase.refresh_vendors()
        self._tab_inspection.reload_settings()

    def _on_tab_change(self, event):
        tab = event.widget.index("current")
        if tab == 0:
            self._tab_purchase.refresh_vendors()
        elif tab == 1:
            self._tab_inspection.refresh()
        elif tab == 2:
            self._tab_history.refresh()
        elif tab == 3:
            self._tab_vendor.refresh()
        elif tab == 4:
            self._tab_sole_contract.refresh()
        elif tab == 5:
            self._tab_draft_template.refresh()
