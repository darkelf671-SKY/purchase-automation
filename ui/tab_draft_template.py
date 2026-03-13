"""탭: 기안 템플릿 관리 — 기안서 제목/내용/비고 템플릿 등록/수정/삭제"""
import tkinter as tk
from tkinter import ttk, messagebox
import db.draft_template_repo as repo
from ui.design_system import COLORS, SPACING, FONTS, configure_treeview_tags, insert_with_alternating
from ui.base_dialog import BaseDialog


class DraftTemplateTab(ttk.Frame):
    def __init__(self, parent, status_var: tk.StringVar):
        super().__init__(parent, padding=SPACING["lg"])
        self.status_var = status_var
        self._records = []
        self._build_ui()

    def _build_ui(self):
        # 검색바
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
        list_frame = ttk.LabelFrame(self, text=" 등록된 기안 템플릿 ", padding=SPACING["lg"])
        list_frame.pack(fill="both", expand=True, pady=(0, SPACING["md"]))

        cols = ("별칭", "기안제목", "내용", "등록일")
        self._tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)
        for col_name, w, minw, stretch, anchor in [
            ("별칭",       120, 80,  False, "center"),
            ("기안제목",   200, 120, True,  "center"),
            ("내용",       250, 150, True,  "center"),
            ("등록일",      90, 80,  False, "center"),
        ]:
            self._tree.heading(col_name, text=col_name if col_name != "내용" else "내용 (일부)")
            self._tree.column(col_name, width=w, minwidth=minw, stretch=stretch, anchor=anchor)

        configure_treeview_tags(self._tree)

        btn_row = ttk.Frame(list_frame)
        btn_row.pack(side="bottom", fill="x", pady=(SPACING["sm"], 0))
        ttk.Button(btn_row, text="템플릿 추가", style="Primary.TButton",
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

        # 툴팁
        self._tooltip = None
        self._tree.bind("<Motion>", self._on_tree_motion)
        self._tree.bind("<Leave>", self._hide_tooltip)

    def _on_tree_motion(self, event):
        item = self._tree.identify_row(event.y)
        col = self._tree.identify_column(event.x)
        if item and col == "#3":  # 내용 컬럼
            values = self._tree.item(item, "values")
            if values and len(values) >= 3:
                # 전체 내용 표시
                rid = int(item)
                rec = next((r for r in self._records if r["id"] == rid), None)
                if rec and len(rec["content"]) > 40:
                    self._show_tooltip(event, rec["content"])
                    return
        self._hide_tooltip()

    def _show_tooltip(self, event, text):
        if self._tooltip:
            self._tooltip.destroy()
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
                              for f in ("label", "title", "content")):
                continue
            content_preview = r["content"][:40] + "..." if len(r["content"]) > 40 else r["content"]
            content_preview = content_preview.replace("\n", " ")
            insert_with_alternating(self._tree, "", "end", iid=str(r["id"]), values=(
                r.get("label", ""), r.get("title", ""), content_preview, r["created_at"][:10]
            ))

    def _get_selected(self) -> dict | None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("선택 오류", "템플릿을 선택하세요.")
            return None
        rid = int(sel[0])
        return next((r for r in self._records if r["id"] == rid), None)

    def _add(self):
        DraftTemplateDialog(self, title="템플릿 추가", on_save=self._on_save)

    def _edit(self):
        r = self._get_selected()
        if r:
            DraftTemplateDialog(self, title="템플릿 수정", record=r, on_save=self._on_save)

    def _delete(self):
        r = self._get_selected()
        if not r:
            return
        if messagebox.askyesno("삭제 확인", f"'{r['label']}' 템플릿을 삭제하시겠습니까?"):
            repo.delete(r["id"])
            self.refresh()
            self.status_var.set(f"'{r['label']}' 삭제 완료")

    def _on_save(self):
        self.refresh()
        self.status_var.set("기안 템플릿 저장 완료")


class DraftTemplateDialog(BaseDialog):
    def __init__(self, parent, title: str, record: dict = None, on_save=None):
        self._record = record
        self._vars = {}
        super().__init__(parent, title, on_save=on_save)
        if record:
            self._load(record)

    def _build_content(self, f: ttk.Frame):
        # 별칭
        ttk.Label(f, text="별칭 *:").grid(row=0, column=0, sticky="w",
                                          pady=SPACING["sm"], padx=(0, SPACING["md"]))
        self._vars["label"] = tk.StringVar()
        ttk.Entry(f, textvariable=self._vars["label"], width=40).grid(
            row=0, column=1, sticky="ew", pady=SPACING["sm"])

        # 기안제목
        ttk.Label(f, text="기안제목:").grid(row=1, column=0, sticky="w",
                                           pady=SPACING["sm"], padx=(0, SPACING["md"]))
        self._vars["title"] = tk.StringVar()
        ttk.Entry(f, textvariable=self._vars["title"], width=40).grid(
            row=1, column=1, sticky="ew", pady=SPACING["sm"])

        # 내용
        ttk.Label(f, text="내용 *:").grid(row=2, column=0, sticky="nw",
                                          pady=SPACING["sm"], padx=(0, SPACING["md"]))
        self._content_text = tk.Text(f, width=40, height=6, wrap="word",
                                     font=FONTS["body"], relief="flat", bd=1,
                                     highlightbackground=COLORS["border"],
                                     highlightcolor=COLORS["primary_light"],
                                     highlightthickness=1,
                                     padx=SPACING["sm"], pady=SPACING["sm"])
        self._content_text.grid(row=2, column=1, sticky="ew", pady=SPACING["sm"])

        # 비고
        ttk.Label(f, text="비고:").grid(row=3, column=0, sticky="w",
                                        pady=SPACING["sm"], padx=(0, SPACING["md"]))
        self._vars["remark"] = tk.StringVar()
        ttk.Entry(f, textvariable=self._vars["remark"], width=40).grid(
            row=3, column=1, sticky="ew", pady=SPACING["sm"])

        # 안내
        ttk.Label(f, text="※ {{품명}}은 첫 품목명으로 자동 치환됩니다.",
                  foreground=COLORS["text_muted"]).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(SPACING["sm"], 0))

        f.columnconfigure(1, weight=1)

    def _load(self, r: dict):
        self._vars["label"].set(r.get("label", ""))
        self._vars["title"].set(r.get("title", ""))
        self._content_text.delete("1.0", "end")
        self._content_text.insert("1.0", r.get("content", ""))
        self._vars["remark"].set(r.get("remark", ""))

    def _on_save(self):
        label = self._vars["label"].get().strip()
        if not label:
            messagebox.showwarning("입력 오류", "별칭을 입력하세요.", parent=self)
            return
        content = self._content_text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("입력 오류", "내용을 입력하세요.", parent=self)
            return
        title = self._vars["title"].get().strip()
        remark = self._vars["remark"].get().strip()
        try:
            if self._record:
                repo.update(self._record["id"], label, title, content, remark)
            else:
                repo.insert(label, title, content, remark)
            self._fire_save_callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("저장 오류", str(e), parent=self)
