"""탭: 수의계약 사유 관리 — 수의계약 사유 마스터 등록/수정/삭제"""
import tkinter as tk
from tkinter import ttk, messagebox
import db.sole_contract_repo as repo
from ui.design_system import COLORS, SPACING, FONTS, configure_treeview_tags, insert_with_alternating
from ui.base_dialog import BaseDialog


class SoleContractTab(ttk.Frame):
    def __init__(self, parent, status_var: tk.StringVar):
        super().__init__(parent, padding=SPACING["lg"])
        self.status_var = status_var
        self._records = []
        self._build_ui()

    def _build_ui(self):
        # ── 검색바 ──────────────────────────────────────────────
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", pady=(0, SPACING["md"]))
        ttk.Label(search_frame, text="검색:").pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        ttk.Entry(search_frame, textvariable=self._search_var,
                  width=22).pack(side="left", padx=SPACING["sm"])
        ttk.Button(search_frame, text="새로고침",
                   command=self.refresh).pack(side="left", padx=(SPACING["md"], 0))

        # 목록
        list_frame = ttk.LabelFrame(self, text=" 등록된 수의계약 사유 ", padding=SPACING["lg"])
        list_frame.pack(fill="both", expand=True, pady=(0, SPACING["md"]))

        cols = ("별칭", "수의계약 사유", "등록일")
        self._tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)
        self._tree.heading("별칭", text="별칭")
        self._tree.column("별칭", width=120, minwidth=80, stretch=False, anchor="center")
        self._tree.heading("수의계약 사유", text="수의계약 사유")
        self._tree.column("수의계약 사유", width=400, minwidth=200, stretch=True, anchor="center")
        self._tree.heading("등록일", text="등록일")
        self._tree.column("등록일", width=90, minwidth=80, stretch=False, anchor="center")

        configure_treeview_tags(self._tree)

        btn_row = ttk.Frame(list_frame)
        btn_row.pack(side="bottom", fill="x", pady=(SPACING["sm"], 0))
        ttk.Button(btn_row, text="사유 추가", style="Primary.TButton",
                   command=self._add).pack(side="left", padx=SPACING["sm"])
        ttk.Button(btn_row, text="수정",
                   command=self._edit).pack(side="left", padx=SPACING["sm"])
        ttk.Button(btn_row, text="삭제", style="Danger.TButton",
                   command=self._delete).pack(side="right", padx=SPACING["sm"])

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._tree.bind("<Double-1>", lambda _: self._edit())

        # 툴팁 — 긴 사유 텍스트 마우스 호버 시 표시
        self._tooltip = None
        self._tree.bind("<Motion>", self._on_tree_motion)
        self._tree.bind("<Leave>", self._hide_tooltip)

    def _on_tree_motion(self, event):
        item = self._tree.identify_row(event.y)
        col = self._tree.identify_column(event.x)
        if item and col == "#2":  # 수의계약 사유 컬럼
            values = self._tree.item(item, "values")
            if values and len(values) >= 2:
                self._show_tooltip(event, values[1])
                return
        self._hide_tooltip()

    def _show_tooltip(self, event, text):
        if self._tooltip:
            self._tooltip.destroy()
        if len(text) <= 50:
            return
        self._tooltip = tk.Toplevel(self)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        lbl = tk.Label(self._tooltip, text=text, background=COLORS["tooltip_bg"],
                       foreground=COLORS["tooltip_fg"],
                       relief="solid", borderwidth=1, wraplength=400,
                       justify="left", padx=SPACING["md"], pady=SPACING["sm"])
        lbl.pack()

    def _hide_tooltip(self, event=None):
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

    def refresh(self):
        self._records = repo.select_all()
        self._apply_filter()

    def _apply_filter(self):
        kw = self._search_var.get().strip().lower()
        self._tree.delete(*self._tree.get_children())
        for r in self._records:
            if kw and not any(kw in str(r.get(f, "")).lower()
                              for f in ("label", "reason")):
                continue
            insert_with_alternating(self._tree, "", "end", iid=str(r["id"]), values=(
                r.get("label", ""), r["reason"], r["created_at"][:10]
            ))

    def _get_selected(self) -> dict | None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("선택 오류", "사유를 선택하세요.")
            return None
        rid = int(sel[0])
        return next((r for r in self._records if r["id"] == rid), None)

    def _add(self):
        SoleContractDialog(self, title="사유 추가", on_save=self._on_save)

    def _edit(self):
        r = self._get_selected()
        if r:
            SoleContractDialog(self, title="사유 수정", record=r, on_save=self._on_save)

    def _delete(self):
        r = self._get_selected()
        if not r:
            return
        if messagebox.askyesno("삭제 확인", f"'{r['reason']}' 사유를 삭제하시겠습니까?"):
            repo.delete(r["id"])
            self.refresh()
            self.status_var.set(f"'{r['reason']}' 삭제 완료")

    def _on_save(self):
        self.refresh()
        self.status_var.set("수의계약 사유 저장 완료")


class SoleContractDialog(BaseDialog):
    def __init__(self, parent, title: str, record: dict = None, on_save=None):
        self._record = record
        self._vars = {}
        super().__init__(parent, title, on_save=on_save)
        if record:
            self._load(record)

    def _build_content(self, f: ttk.Frame):
        fields = [
            ("별칭 *:", "label", 30),
            ("수의계약 사유 *:", "reason", 50),
        ]
        for r, (lbl, key, w) in enumerate(fields):
            ttk.Label(f, text=lbl).grid(row=r, column=0, sticky="w",
                                        pady=SPACING["sm"], padx=(0, SPACING["md"]))
            var = tk.StringVar()
            ttk.Entry(f, textvariable=var, width=w).grid(row=r, column=1, sticky="ew",
                                                         pady=SPACING["sm"])
            self._vars[key] = var

        f.columnconfigure(1, weight=1)

    def _load(self, r: dict):
        for key, var in self._vars.items():
            var.set(r.get(key, ""))

    def _on_save(self):
        label = self._vars["label"].get().strip()
        if not label:
            messagebox.showwarning("입력 오류", "별칭을 입력하세요.", parent=self)
            return
        reason = self._vars["reason"].get().strip()
        if not reason:
            messagebox.showwarning("입력 오류", "수의계약 사유를 입력하세요.", parent=self)
            return
        try:
            if self._record:
                repo.update(self._record["id"], reason, label)
            else:
                repo.insert(reason, label)
            self._fire_save_callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("저장 오류", str(e), parent=self)
