"""탭 3: 이력 조회"""
import gc
import os
import shutil
import subprocess
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import db.purchase_repo as repo
import db.inspection_repo as inspection_repo
from db.purchase_repo import select_items
from config import PAYMENT_METHODS
from ui.design_system import COLORS, SPACING, FONTS, configure_treeview_tags, insert_with_alternating


class HistoryTab(ttk.Frame):
    def __init__(self, parent, status_var: tk.StringVar,
                 on_load_purchase=None, on_edit_purchase=None):
        super().__init__(parent)
        self.status_var = status_var
        self._on_load_purchase = on_load_purchase
        self._on_edit_purchase = on_edit_purchase
        self._records  = []
        self._insp_map = {}

        # ── 탭 전체 스크롤 래퍼 ─────────────────────────────────
        self._canvas = tk.Canvas(self, highlightthickness=0,
                                 background=COLORS["bg_window"])
        _vsb = ttk.Scrollbar(self, orient="vertical",
                              command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=_vsb.set)
        _vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._content = ttk.Frame(self._canvas, padding=SPACING["lg"])
        _win = self._canvas.create_window((0, 0), window=self._content,
                                          anchor="nw")

        def _fit_width(e):
            self._canvas.itemconfig(_win, width=e.width)
        def _update_scroll(e):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._canvas.bind("<Configure>", _fit_width)
        self._content.bind("<Configure>", _update_scroll)

        def _on_wheel(e):
            try:
                w = e.widget
                while w:
                    if w is self:
                        break
                    w = w.master
                else:
                    return
            except Exception:
                return
            self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        self.bind_all("<MouseWheel>", _on_wheel)

        self._build_ui()

    def _build_ui(self):
        # ── 검색바 ──────────────────────────────────────────────
        search_frame = ttk.Frame(self._content)
        search_frame.pack(fill="x", pady=(0, SPACING["md"]))

        ttk.Label(search_frame, text="검색:").pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        ttk.Entry(search_frame, textvariable=self._search_var,
                  width=22).pack(side="left", padx=SPACING["sm"])

        ttk.Label(search_frame, text="대상:").pack(side="left", padx=(SPACING["md"], SPACING["xs"]))
        self._chk_item    = self._chkvar(search_frame, "품명",    True)
        self._chk_dept    = self._chkvar(search_frame, "부서명",  True)
        self._chk_draft   = self._chkvar(search_frame, "기안제목", True)
        self._chk_content = self._chkvar(search_frame, "기안내용", True)

        ttk.Button(search_frame, text="새로고침",
                   command=self.refresh).pack(side="left", padx=(SPACING["md"], 0))

        # ── 목록 ────────────────────────────────────────────────
        list_frame = ttk.LabelFrame(self._content, text=" 구매 이력 ", padding=SPACING["sm"])
        list_frame.pack(fill="x", pady=(0, SPACING["md"]))

        # 버튼 행 (하단 2줄)
        # Row 1: 관리 (아래쪽)
        btn_row1 = ttk.Frame(list_frame)
        btn_row1.pack(side="bottom", fill="x", pady=(SPACING["xs"], 0))
        ttk.Button(btn_row1, text="복사하여 새 기안",
                   command=self._load_to_purchase).pack(side="left", padx=SPACING["sm"])
        ttk.Button(btn_row1, text="수정하기",
                   command=self._edit_purchase).pack(side="left", padx=SPACING["sm"])
        ttk.Button(btn_row1, text="폴더 열기",
                   command=self._open_folder).pack(side="right", padx=SPACING["sm"])
        ttk.Button(btn_row1, text="선택 항목 삭제",
                   command=self._delete_selected).pack(side="right", padx=SPACING["sm"])

        # Row 2: 문서 열기 (위쪽)
        btn_row2 = ttk.Frame(list_frame)
        btn_row2.pack(side="bottom", fill="x", pady=(SPACING["sm"], 0))
        _doc_btn_w = 10
        ttk.Button(btn_row2, text="기안서", width=_doc_btn_w,
                   command=lambda: self._open_doc("draft")).pack(side="left", padx=SPACING["sm"])
        ttk.Button(btn_row2, text="산출조사서", width=_doc_btn_w,
                   command=lambda: self._open_doc("calc")).pack(side="left", padx=SPACING["sm"])
        ttk.Button(btn_row2, text="검수내역서", width=_doc_btn_w,
                   command=lambda: self._open_inspection_doc("list")).pack(side="left", padx=SPACING["sm"])
        ttk.Button(btn_row2, text="검수조서", width=_doc_btn_w,
                   command=lambda: self._open_inspection_doc("rpt")).pack(side="left", padx=SPACING["sm"])
        ttk.Button(btn_row2, text="견적서1", width=_doc_btn_w,
                   command=lambda: self._open_quote_file(1)).pack(side="left", padx=SPACING["sm"])
        ttk.Button(btn_row2, text="견적서2", width=_doc_btn_w,
                   command=lambda: self._open_quote_file(2)).pack(side="left", padx=SPACING["sm"])

        # Treeview
        cols = ("기안제목", "품명", "부서명", "구매처", "금액", "기안일", "검수")
        self._tree = ttk.Treeview(list_frame, columns=cols,
                                  show="headings", height=9)
        for col, w, anchor in [
            ("기안제목", 170, "center"),
            ("품명",    150, "center"),
            ("부서명",   85, "center"),
            ("구매처",  120, "center"),
            ("금액",     90, "e"),
            ("기안일",   90, "center"),
            ("검수",     50, "center"),
        ]:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, anchor=anchor, minwidth=40)

        configure_treeview_tags(self._tree)

        # 세로 + 가로 스크롤바
        sb_y = ttk.Scrollbar(list_frame, orient="vertical",   command=self._tree.yview)
        sb_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        sb_x.pack(side="bottom", fill="x")
        self._tree.pack(side="left", fill="both", expand=True)
        sb_y.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda _: self._open_doc("draft"))

        # ── 상세 패널 ────────────────────────────────────────────
        detail_frame = ttk.LabelFrame(self._content, text=" 선택 항목 상세 ", padding=SPACING["lg"])
        detail_frame.pack(fill="x")

        self._detail_hint = ttk.Label(
            detail_frame,
            text="항목을 선택하면 기안제목, 견적 URL 등 상세 정보가 표시됩니다.",
            foreground=COLORS["text_muted"])
        self._detail_hint.pack(fill="x")

        self._detail_rows = ttk.Frame(detail_frame)
        self._detail_rows.pack(fill="x")
        self._detail_rows.pack_forget()

        _K = 10   # 라벨 폭 (키)
        _kpad = (SPACING["md"], SPACING["sm"])
        _vpad = SPACING["xs"]

        # ═══════════════════════════════════════════════════════════
        # 카드 1: 기안 정보
        # ═══════════════════════════════════════════════════════════
        card1 = ttk.Frame(self._detail_rows, style="Card.TFrame", padding=SPACING["md"])
        card1.pack(fill="x", pady=(0, SPACING["sm"]))
        ttk.Label(card1, text="기안 정보", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, SPACING["sm"]))

        self._ddraft_ttl = tk.StringVar()
        self._ddept = tk.StringVar()
        self._ddraft_content = tk.StringVar()
        self._ddraft_remark = tk.StringVar()

        for r, (key, var) in enumerate([
            ("기안제목", self._ddraft_ttl),
            ("부서명",   self._ddept),
            ("기안내용", self._ddraft_content),
            ("기안비고", self._ddraft_remark),
        ], start=1):
            ttk.Label(card1, text=key, width=_K, anchor="e",
                      style="CardKey.TLabel").grid(
                row=r, column=0, sticky="e", pady=_vpad, padx=_kpad)
            ttk.Label(card1, textvariable=var, style="CardVal.TLabel",
                      wraplength=550 if key == "기안내용" else 0,
                      justify="left").grid(
                row=r, column=1, columnspan=3, sticky="w", pady=_vpad)
        card1.columnconfigure(1, weight=1)

        # ═══════════════════════════════════════════════════════════
        # 카드 2: 구매 정보 + 견적
        # ═══════════════════════════════════════════════════════════
        card2 = ttk.Frame(self._detail_rows, style="Card.TFrame", padding=SPACING["md"])
        card2.pack(fill="x", pady=(0, SPACING["sm"]))
        ttk.Label(card2, text="구매 / 견적 정보", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, SPACING["sm"]))

        self._ditem = tk.StringVar()
        self._dspec = tk.StringVar()
        self._dqty = tk.StringVar()
        self._dpayment = tk.StringVar()

        # 품명 / 수량
        ttk.Label(card2, text="품명", width=_K, anchor="e",
                  style="CardKey.TLabel").grid(
            row=1, column=0, sticky="e", pady=_vpad, padx=_kpad)
        ttk.Label(card2, textvariable=self._ditem,
                  style="CardVal.TLabel").grid(
            row=1, column=1, sticky="w", pady=_vpad)
        ttk.Label(card2, text="수량", width=6, anchor="e",
                  style="CardKey.TLabel").grid(
            row=1, column=2, sticky="e", pady=_vpad, padx=_kpad)
        ttk.Label(card2, textvariable=self._dqty,
                  style="CardVal.TLabel").grid(
            row=1, column=3, sticky="w", pady=_vpad)

        # 규격/사양
        ttk.Label(card2, text="규격/사양", width=_K, anchor="e",
                  style="CardKey.TLabel").grid(
            row=2, column=0, sticky="e", pady=_vpad, padx=_kpad)
        ttk.Label(card2, textvariable=self._dspec,
                  style="CardVal.TLabel").grid(
            row=2, column=1, columnspan=5, sticky="w", pady=_vpad)

        # 결제방법
        ttk.Label(card2, text="결제방법", width=_K, anchor="e",
                  style="CardKey.TLabel").grid(
            row=3, column=0, sticky="e", pady=_vpad, padx=_kpad)
        ttk.Label(card2, textvariable=self._dpayment,
                  style="CardVal.TLabel").grid(
            row=3, column=1, columnspan=5, sticky="w", pady=_vpad)

        # 견적 1, 2
        self._d1_name  = tk.StringVar()
        self._d1_price = tk.StringVar()
        self._d1_url   = tk.StringVar()
        self._d2_name  = tk.StringVar()
        self._d2_price = tk.StringVar()
        self._d2_url   = tk.StringVar()

        for row, (label, name_v, price_v, url_v) in enumerate([
            ("견적 1", self._d1_name, self._d1_price, self._d1_url),
            ("견적 2", self._d2_name, self._d2_price, self._d2_url),
        ], start=4):
            ttk.Label(card2, text=label, width=_K, anchor="e",
                      style="CardKey.TLabel").grid(
                row=row, column=0, sticky="e", pady=_vpad, padx=_kpad)
            ttk.Label(card2, textvariable=name_v, width=14, anchor="w",
                      style="CardVal.TLabel").grid(
                row=row, column=1, sticky="w", padx=(0, SPACING["md"]))
            ttk.Label(card2, textvariable=price_v,
                      style="CardValInfo.TLabel", width=12, anchor="e").grid(
                row=row, column=2, sticky="w", padx=(0, SPACING["md"]))
            url_entry = ttk.Entry(card2, textvariable=url_v,
                                  width=28, state="readonly")
            url_entry.grid(row=row, column=3, sticky="ew",
                          padx=(0, SPACING["sm"]), columnspan=2)

            def make_open(uv=url_v):
                def _open():
                    u = uv.get().strip()
                    if u:
                        import webbrowser
                        webbrowser.open(u)
                    else:
                        messagebox.showinfo("URL 없음", "등록된 URL이 없습니다.")
                return _open

            ttk.Button(card2, text="URL 열기",
                       command=make_open()).grid(row=row, column=5, padx=SPACING["xs"])

        card2.columnconfigure(3, weight=1)

        # ═══════════════════════════════════════════════════════════
        # 카드 3: 검수 정보
        # ═══════════════════════════════════════════════════════════
        card3 = ttk.Frame(self._detail_rows, style="Card.TFrame", padding=SPACING["md"])
        card3.pack(fill="x")
        ttk.Label(card3, text="검수 정보", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, SPACING["sm"]))

        self._dinsp_memo = tk.StringVar()
        ttk.Label(card3, text="검수메모", width=_K, anchor="e",
                  style="CardKey.TLabel").grid(
            row=1, column=0, sticky="e", pady=_vpad, padx=_kpad)
        ttk.Label(card3, textvariable=self._dinsp_memo,
                  style="CardVal.TLabel").grid(
            row=1, column=1, columnspan=3, sticky="w", pady=_vpad)
        card3.columnconfigure(1, weight=1)

        detail_frame.columnconfigure(0, weight=1)

    # ── 헬퍼 ─────────────────────────────────────────────────────
    def _chkvar(self, parent, text: str, default: bool) -> tk.BooleanVar:
        var = tk.BooleanVar(value=default)
        ttk.Checkbutton(parent, text=text, variable=var,
                        command=self._apply_filter).pack(side="left", padx=SPACING["xs"])
        return var

    # ── 데이터 ──────────────────────────────────────────────────
    def refresh(self):
        self._records = repo.select_all()
        # 검수 맵 구성 (N+1 방지)
        all_insp = inspection_repo.select_all_grouped()
        self._insp_map = {i["purchase_id"]: i for i in all_insp}
        self._apply_filter()

    def _apply_filter(self):
        kw = self._search_var.get().strip().lower()
        self._tree.delete(*self._tree.get_children())

        for r in self._records:
            if kw:
                targets = []
                if self._chk_item.get():
                    targets.append(r.get("item_name", "").lower())
                if self._chk_dept.get():
                    targets.append(r.get("department", "").lower())
                if self._chk_draft.get():
                    targets.append(r.get("doc_draft_title", "").lower())
                if self._chk_content.get():
                    targets.append(r.get("doc_draft_content", "").lower())
                if not any(kw in t for t in targets):
                    continue

            sv          = r["selected_vendor"]
            vendor_name = r[f"vendor{sv}_name"]
            total       = r[f"vendor{sv}_total"]
            has_draft   = bool(r["doc_draft"])
            has_calc    = bool(r["doc_calculation"])
            insp        = self._insp_map.get(r["id"])
            insp_txt    = "완료" if insp else "-"

            if has_draft and has_calc:
                tag = "complete"
            elif has_draft or has_calc:
                tag = "partial"
            else:
                tag = "missing"

            insert_with_alternating(self._tree, "", "end", values=(
                r.get("doc_draft_title") or "-",
                r["item_name"],
                r.get("department") or "-",
                vendor_name,
                f"{total:,}원",
                r["created_at"][:10],
                insp_txt,
            ), iid=str(r["id"]), tags=(tag,))

    def _get_selected_record(self) -> dict | None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("선택 오류", "항목을 선택하세요.")
            return None
        record_id = int(sel[0])
        return next((r for r in self._records if r["id"] == record_id), None)

    # ── 선택 이벤트 ─────────────────────────────────────────────
    def _on_select(self, _event=None):
        if not self._tree.selection():
            self._detail_rows.pack_forget()
            self._detail_hint.pack(fill="x")
            return
        r = self._get_selected_record() if self._tree.selection() else None
        if not r:
            return

        self._detail_hint.pack_forget()
        self._detail_rows.pack(fill="x")

        # 공통 블록: 기안제목
        self._ddraft_ttl.set(r.get("doc_draft_title") or "(기안서 미생성)")

        # 공통 블록: 부서명 / 품명 / 수량
        self._ddept.set(r.get("department") or "-")
        items = select_items(r["id"])
        if len(items) <= 1:
            item = items[0] if items else {}
            self._ditem.set(item.get("item_name", r["item_name"]))
            self._dspec.set(item.get("spec", r.get("spec", "")) or "-")
            qty = item.get("quantity", r.get("quantity", 1))
            unit = item.get("unit", r.get("unit", "개"))
            self._dqty.set(f"{qty}{unit}")
        else:
            self._ditem.set(f"{r['item_name']} ({len(items)}종)")
            summary = ", ".join(
                f"{i['item_name']}({i['quantity']}{i['unit']})" for i in items)
            self._dspec.set(summary)
            total_qty = sum(i["quantity"] for i in items)
            self._dqty.set(f"{len(items)}종 (총 {total_qty}개)")

        # 공통 블록: 기안내용
        content = r.get("doc_draft_content") or "-"
        if len(content) > 200:
            content = content[:200] + "..."
        self._ddraft_content.set(content)

        # 공통 블록: 기안비고
        self._ddraft_remark.set(r.get("doc_draft_remark") or "-")

        # 이력탭 전용: 견적1/2
        self._d1_name.set(r["vendor1_name"] or "-")
        self._d1_price.set(f"{r['vendor1_total']:,}원")
        self._d1_url.set(r.get("vendor1_url") or "")

        self._d2_name.set(r["vendor2_name"] or "-")
        self._d2_price.set(f"{r['vendor2_total']:,}원")
        self._d2_url.set(r.get("vendor2_url") or "")

        # 이력탭 전용: 결제정보
        pay_code = r.get("payment_method") or ""
        pay_label = PAYMENT_METHODS.get(pay_code, pay_code) or "-"
        pay_bank = r.get("payment_bank") or ""
        pay_account = r.get("payment_account") or ""
        pay_holder = r.get("payment_holder") or ""
        if pay_code in ("transfer", "auto_transfer") and pay_bank:
            pay_detail = f"{pay_label} ({pay_bank} {pay_account} {pay_holder})".strip()
        else:
            pay_detail = pay_label
        self._dpayment.set(pay_detail)

        # 이력탭 전용: 검수메모
        insp = self._insp_map.get(r["id"])
        if insp:
            self._dinsp_memo.set(insp.get("remark") or "-")
        else:
            self._dinsp_memo.set("(검수 미등록)")

    # ── 문서/폴더 열기 ──────────────────────────────────────────
    def _open_doc(self, doc_type: str):
        r = self._get_selected_record()
        if not r:
            return
        path = r["doc_draft"] if doc_type == "draft" else r["doc_calculation"]
        if not path or not Path(path).exists():
            messagebox.showwarning("파일 없음", "해당 문서 파일을 찾을 수 없습니다.")
            return
        os.startfile(path)

    def _open_folder(self):
        r = self._get_selected_record()
        if not r:
            return
        folder = r.get("doc_folder", "")
        if folder and Path(folder).exists():
            subprocess.Popen(["explorer", folder])
        else:
            messagebox.showwarning("폴더 없음", "산출 폴더를 찾을 수 없습니다.")

    def _open_inspection_doc(self, doc_type: str):
        """검수 문서 열기: doc_type = 'list'(내역서) | 'rpt'(조서)"""
        r = self._get_selected_record()
        if not r:
            return
        insp = self._insp_map.get(r["id"])
        if not insp:
            messagebox.showwarning("검수 없음", "등록된 검수 기록이 없습니다.")
            return
        key  = "doc_inspection_list" if doc_type == "list" else "doc_inspection_rpt"
        name = "물품검수내역서" if doc_type == "list" else "물품검수조서"
        path = insp.get(key, "")
        if not path or not Path(path).exists():
            messagebox.showwarning("파일 없음", f"{name} 파일을 찾을 수 없습니다.")
            return
        os.startfile(path)

    def _open_quote_file(self, slot: int):
        """견적서 파일 열기: slot = 1 | 2"""
        r = self._get_selected_record()
        if not r:
            return
        path = r.get(f"vendor{slot}_screenshot", "")
        if not path or not Path(path).exists():
            messagebox.showwarning("파일 없음", f"견적서{slot} 파일을 찾을 수 없습니다.")
            return
        os.startfile(path)

    # ── 삭제 ────────────────────────────────────────────────────
    def _delete_selected(self):
        r = self._get_selected_record()
        if not r:
            return
        insp         = self._insp_map.get(r["id"])
        folder       = r.get("doc_folder", "")
        folder_exists = folder and Path(folder).exists()

        msg = f"'{r['item_name']}' 이력을 삭제하시겠습니까?"
        if insp:
            msg += "\n• 연결된 검수 기록도 함께 삭제됩니다."
        if folder_exists:
            msg += f"\n• 산출 폴더({Path(folder).name})와 모든 파일이 삭제됩니다."
        msg += "\n\n이 작업은 되돌릴 수 없습니다."

        if not messagebox.askyesno("삭제 확인", msg):
            return

        if folder_exists:
            if not self._delete_folder_with_retry(folder):
                return   # 완전 취소 — DB도 삭제 안 함

        # 파일 삭제 성공 후 DB 삭제
        inspection_repo.delete_by_purchase(r["id"])
        repo.delete(r["id"])
        self._detail_rows.pack_forget()
        self._detail_hint.pack(fill="x")
        self.refresh()
        self.status_var.set(f"'{r['item_name']}' 삭제 완료")

    def _delete_folder_with_retry(self, folder_path: str) -> bool:
        """폴더 삭제 재시도 헬퍼 — PermissionError 시 팝업 + 재시도/완전취소"""
        path = Path(folder_path)
        while True:
            try:
                gc.collect()
                time.sleep(0.5)
                shutil.rmtree(path)
                return True
            except PermissionError as e:
                locked = getattr(e, 'filename', str(path))
                retry = messagebox.askyesno(
                    "파일 잠금 오류",
                    f"아래 파일이 열려 있어 삭제할 수 없습니다.\n\n"
                    f"  {locked}\n\n"
                    f"[예] 파일을 닫은 후 다시 시도합니다.\n"
                    f"[아니오] 작업을 취소합니다.",
                    parent=self
                )
                if not retry:
                    messagebox.showinfo(
                        "작업 취소됨",
                        "모든 관련 파일을 닫은 후 다시 삭제를 시도해 주세요.",
                        parent=self
                    )
                    return False
            except Exception as e:
                messagebox.showwarning("폴더 삭제 실패", f"오류:\n{e}", parent=self)
                return False

    def _load_to_purchase(self):
        """선택한 구매 이력을 구매 조사탭에 복사 (새 기안 작성용)"""
        r = self._get_selected_record()
        if not r:
            return
        if not self._on_load_purchase:
            messagebox.showwarning("기능 없음", "불러오기 기능이 연결되지 않았습니다.")
            return
        from db.purchase_repo import select_items
        items = select_items(r["id"])
        self._on_load_purchase(r, items)

    def _edit_purchase(self):
        """선택한 구매 이력을 수정 모드로 불러오기"""
        r = self._get_selected_record()
        if not r:
            return
        if not self._on_edit_purchase:
            messagebox.showwarning("기능 없음", "수정 기능이 연결되지 않았습니다.")
            return
        from db.purchase_repo import select_items
        items = select_items(r["id"])
        self._on_edit_purchase(r, items)
