"""탭 2: 검수 입력 (v2) — 기안 이력에서 선택 후 검수 문서 생성"""
import gc
import time
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from pathlib import Path
from config import make_output_dir, get_inspector, get_witness, PAYMENT_METHODS
from core.models import PurchaseData, PurchaseItem, VendorQuote, InspectionData
import db.purchase_repo as purchase_repo_mod
from documents.hwp_generator import HwpGenerator
from documents.excel_generator import ExcelGenerator
import db.purchase_repo as purchase_repo
import db.inspection_repo as inspection_repo
from ui.design_system import COLORS, SPACING, FONTS, BTN_ACTION_PAD, configure_treeview_tags, insert_with_alternating


class InspectionTab(ttk.Frame):
    def __init__(self, parent, status_var: tk.StringVar):
        super().__init__(parent)
        self.status_var = status_var
        self._purchases = []
        self._filtered_purchases = []
        self._selected_purchase = None
        self._selected_items = []

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
            # 이 탭이 보일 때만 스크롤
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

    def _chkvar(self, parent, text: str, default: bool) -> tk.BooleanVar:
        var = tk.BooleanVar(value=default)
        ttk.Checkbutton(parent, text=text, variable=var,
                        command=self._apply_filter).pack(side="left", padx=SPACING["xs"])
        return var

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

        # 구매건 목록
        list_frame = ttk.LabelFrame(self._content, text=" 구매건 선택 ", padding=SPACING["lg"])
        list_frame.pack(fill="x", pady=(0, SPACING["md"]))

        cols = ("기안제목", "품명", "구매처", "금액", "기안일", "검수")
        self._tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=6)
        for col, w, anchor in [
            ("기안제목", 150, "center"),
            ("품명",    140, "center"),
            ("구매처",  110, "center"),
            ("금액",     90, "e"),
            ("기안일",   90, "center"),
            ("검수",     55, "center"),
        ]:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, anchor=anchor)

        configure_treeview_tags(self._tree)

        btn_row = ttk.Frame(list_frame)
        btn_row.pack(side="bottom", fill="x", pady=(SPACING["sm"], 0))
        ttk.Button(btn_row, text="검수 기록만 삭제", command=self._delete_inspection).pack(side="right", padx=SPACING["md"])
        ttk.Button(btn_row, text="구매건 전체 삭제", command=self._delete_all).pack(side="right", padx=SPACING["sm"])

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # 검수 정보 입력
        input_frame = ttk.LabelFrame(self._content, text=" 검수 정보 입력 ", padding=SPACING["lg"])
        input_frame.pack(fill="x", pady=(0, SPACING["md"]))

        _K = 10   # 라벨 폭 (키)
        _kpad = (SPACING["md"], SPACING["sm"])  # 키 좌우 패딩
        _vpad = SPACING["xs"]                   # 행 상하 패딩

        # ═══════════════════════════════════════════════════════════
        # 카드 1: 기안 정보 (읽기전용, 연한 배경)
        # ═══════════════════════════════════════════════════════════
        card1 = ttk.Frame(input_frame, style="Card.TFrame", padding=SPACING["md"])
        card1.pack(fill="x", pady=(0, SPACING["sm"]))
        ttk.Label(card1, text="기안 정보", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, SPACING["sm"]))

        self._draft_title_var = tk.StringVar(value="(구매건을 선택하세요)")
        self._dept_var = tk.StringVar(value="-")
        self._draft_content_var = tk.StringVar(value="-")
        self._draft_remark_var = tk.StringVar(value="-")

        for r, (key, var) in enumerate([
            ("기안제목", self._draft_title_var),
            ("부서명",   self._dept_var),
            ("기안내용", self._draft_content_var),
            ("기안비고", self._draft_remark_var),
        ], start=1):
            ttk.Label(card1, text=key, width=_K, anchor="e",
                      style="CardKey.TLabel").grid(
                row=r, column=0, sticky="e", pady=_vpad, padx=_kpad)
            lbl = ttk.Label(card1, textvariable=var, style="CardVal.TLabel",
                            wraplength=550 if key == "기안내용" else 0,
                            justify="left")
            lbl.grid(row=r, column=1, columnspan=3, sticky="w", pady=_vpad)

        # 라벨 참조 (선택 시 foreground 변경용)
        self._draft_title_label = card1.grid_slaves(row=1, column=1)[0]
        self._dept_label = card1.grid_slaves(row=2, column=1)[0]
        self._draft_content_label = card1.grid_slaves(row=3, column=1)[0]
        self._draft_remark_label = card1.grid_slaves(row=4, column=1)[0]
        card1.columnconfigure(1, weight=1)

        # ═══════════════════════════════════════════════════════════
        # 카드 2: 구매 정보 (읽기전용, 연한 배경)
        # ═══════════════════════════════════════════════════════════
        card2 = ttk.Frame(input_frame, style="Card.TFrame", padding=SPACING["md"])
        card2.pack(fill="x", pady=(0, SPACING["sm"]))
        ttk.Label(card2, text="구매 정보", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, SPACING["sm"]))

        self._item_var = tk.StringVar(value="-")
        self._spec_var = tk.StringVar(value="-")
        self._qty_var = tk.StringVar(value="-")
        self._vendor_var = tk.StringVar(value="-")
        self._amount_var = tk.StringVar(value="-")
        self._pay_method_var_disp = tk.StringVar(value="-")

        # 품명 / 수량 (같은 행)
        ttk.Label(card2, text="품명", width=_K, anchor="e",
                  style="CardKey.TLabel").grid(
            row=1, column=0, sticky="e", pady=_vpad, padx=_kpad)
        self._item_label = ttk.Label(card2, textvariable=self._item_var,
                                     style="CardVal.TLabel")
        self._item_label.grid(row=1, column=1, sticky="w", pady=_vpad)
        ttk.Label(card2, text="수량", width=6, anchor="e",
                  style="CardKey.TLabel").grid(
            row=1, column=2, sticky="e", pady=_vpad, padx=_kpad)
        self._qty_label = ttk.Label(card2, textvariable=self._qty_var,
                                    style="CardVal.TLabel")
        self._qty_label.grid(row=1, column=3, sticky="w", pady=_vpad)

        # 규격/사양
        ttk.Label(card2, text="규격/사양", width=_K, anchor="e",
                  style="CardKey.TLabel").grid(
            row=2, column=0, sticky="e", pady=_vpad, padx=_kpad)
        self._spec_label = ttk.Label(card2, textvariable=self._spec_var,
                                     style="CardVal.TLabel")
        self._spec_label.grid(row=2, column=1, columnspan=3, sticky="w", pady=_vpad)

        # 구매처 / 금액 (같은 행)
        ttk.Label(card2, text="구매처", width=_K, anchor="e",
                  style="CardKey.TLabel").grid(
            row=3, column=0, sticky="e", pady=_vpad, padx=_kpad)
        self._vendor_label = ttk.Label(card2, textvariable=self._vendor_var,
                                       style="CardVal.TLabel")
        self._vendor_label.grid(row=3, column=1, sticky="w", pady=_vpad)
        ttk.Label(card2, text="금액", width=6, anchor="e",
                  style="CardKey.TLabel").grid(
            row=3, column=2, sticky="e", pady=_vpad, padx=_kpad)
        self._amount_label = ttk.Label(card2, textvariable=self._amount_var,
                                       style="CardValInfo.TLabel")
        self._amount_label.grid(row=3, column=3, sticky="w", pady=_vpad)

        # 결제방법
        ttk.Label(card2, text="결제방법", width=_K, anchor="e",
                  style="CardKey.TLabel").grid(
            row=4, column=0, sticky="e", pady=_vpad, padx=_kpad)
        ttk.Label(card2, textvariable=self._pay_method_var_disp,
                  style="CardVal.TLabel").grid(
            row=4, column=1, columnspan=3, sticky="w", pady=_vpad)

        card2.columnconfigure(1, weight=1)

        # ═══════════════════════════════════════════════════════════
        # 카드 3: 검수 입력 (흰 배경 — 입력 영역 강조)
        # ═══════════════════════════════════════════════════════════
        card3 = ttk.Frame(input_frame, style="InputCard.TFrame", padding=SPACING["md"])
        card3.pack(fill="x")
        ttk.Label(card3, text="검수 입력", style="InputCard.TLabel",
                  font=FONTS["body_bold"],
                  foreground=COLORS["primary"]).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, SPACING["sm"]))

        self._date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self._inspector_var = tk.StringVar(value=get_inspector())
        self._witness_var = tk.StringVar(value=get_witness())
        self._remark_var = tk.StringVar()

        ttk.Label(card3, text="검수일", width=_K, anchor="e",
                  style="InputCard.TLabel").grid(
            row=1, column=0, sticky="e", pady=_vpad, padx=_kpad)
        ttk.Entry(card3, textvariable=self._date_var, width=14).grid(
            row=1, column=1, sticky="w", pady=_vpad)

        ttk.Label(card3, text="검수자", width=_K, anchor="e",
                  style="InputCard.TLabel").grid(
            row=2, column=0, sticky="e", pady=_vpad, padx=_kpad)
        ttk.Entry(card3, textvariable=self._inspector_var, width=20).grid(
            row=2, column=1, sticky="w", pady=_vpad)
        ttk.Label(card3, text="입회자", width=6, anchor="e",
                  style="InputCard.TLabel").grid(
            row=2, column=2, sticky="e", pady=_vpad, padx=_kpad)
        ttk.Entry(card3, textvariable=self._witness_var, width=20).grid(
            row=2, column=3, sticky="w", pady=_vpad)

        ttk.Label(card3, text="검수메모", width=_K, anchor="e",
                  style="InputCard.TLabel").grid(
            row=3, column=0, sticky="e", pady=_vpad, padx=_kpad)
        ttk.Entry(card3, textvariable=self._remark_var, width=45).grid(
            row=3, column=1, columnspan=3, sticky="ew", pady=_vpad)

        card3.columnconfigure(1, weight=1)

        gen_frame = ttk.Frame(self._content)
        gen_frame.pack(fill="x", pady=SPACING["lg"])
        ttk.Label(gen_frame,
                  text="※ 물품검수내역서(Excel) + 물품검수조서(HWP) 생성",
                  foreground=COLORS["text_muted"]).pack(side="right", padx=SPACING["sm"])
        ttk.Button(gen_frame, text="문서 생성",
                   style="Primary.TButton",
                   command=self._generate_documents
                   ).pack(side="right", padx=SPACING["md"], **BTN_ACTION_PAD)

    def reload_settings(self):
        """설정에서 검수자/입회자 값이 변경되었을 때 즉시 반영"""
        saved_inspector = get_inspector()
        saved_witness = get_witness()
        if saved_inspector and not self._inspector_var.get().strip():
            self._inspector_var.set(saved_inspector)
        if saved_witness and not self._witness_var.get().strip():
            self._witness_var.set(saved_witness)

    def refresh(self):
        self._purchases = purchase_repo.select_all()
        self._apply_filter()

    def _apply_filter(self):
        kw = self._search_var.get().strip().lower()
        self._tree.delete(*self._tree.get_children())
        self._filtered_purchases = []
        for p in self._purchases:
            if kw:
                targets = []
                if self._chk_item.get():
                    targets.append(p.get("item_name", "").lower())
                if self._chk_dept.get():
                    targets.append(p.get("department", "").lower())
                if self._chk_draft.get():
                    targets.append(p.get("doc_draft_title", "").lower())
                if self._chk_content.get():
                    targets.append(p.get("doc_draft_content", "").lower())
                if not any(kw in t for t in targets):
                    continue
            insp = inspection_repo.select_by_purchase(p["id"])
            insp_status = "완료" if insp else "대기"
            selected_total = p["vendor1_total"] if p["selected_vendor"] == 1 else p["vendor2_total"]
            insert_with_alternating(self._tree, "", "end", values=(
                p.get("doc_draft_title") or "-",
                p["item_name"],
                p["vendor1_name"] if p["selected_vendor"] == 1 else p["vendor2_name"],
                f"{selected_total:,}원",
                p["created_at"][:10],
                insp_status,
            ))
            self._filtered_purchases.append(p)

    def _delete_folder_with_retry(self, folder_path: str) -> bool:
        """폴더 삭제 재시도 헬퍼 — PermissionError 시 팝업 + 재시도/완전취소"""
        path = Path(folder_path)
        while True:
            try:
                gc.collect()          # COM 참조 해제 유도
                time.sleep(0.5)       # 파일 핸들 해제 대기
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

    def _delete_all(self):
        """구매건 + 검수기록 + 관련 파일 전체 삭제"""
        if not self._selected_purchase:
            messagebox.showwarning("선택 오류", "구매건을 선택하세요.")
            return
        p = self._selected_purchase
        if not messagebox.askyesno("전체 삭제 확인",
                f"'{p['item_name']}' 구매건을 완전히 삭제합니다.\n\n"
                "• 구매 이력\n• 검수 기록\n• 생성된 문서 파일 (HWP, Excel)\n\n"
                "이 작업은 되돌릴 수 없습니다. 계속하시겠습니까?"):
            return

        deleted_files, failed_files = [], []

        # 1. 관련 파일 삭제
        file_fields = ["doc_draft", "doc_calculation"]
        insp = inspection_repo.select_by_purchase(p["id"])
        if insp:
            file_fields += ["doc_inspection_list", "doc_inspection_rpt"]
            for field in ["doc_inspection_list", "doc_inspection_rpt"]:
                path_str = insp.get(field, "")
                if path_str:
                    path = Path(path_str)
                    if path.exists():
                        try:
                            path.unlink()
                            deleted_files.append(path.name)
                        except Exception:
                            failed_files.append(path.name)

        for field in ["doc_draft", "doc_calculation"]:
            path_str = p.get(field, "")
            if path_str:
                path = Path(path_str)
                if path.exists():
                    try:
                        path.unlink()
                        deleted_files.append(path.name)
                    except Exception:
                        failed_files.append(path.name)

        # 2. 산출 폴더 전체 삭제
        folder = p.get("doc_folder", "")
        if folder and Path(folder).exists():
            if self._delete_folder_with_retry(folder):
                deleted_files.append(f"[폴더] {Path(folder).name}")
            else:
                return   # 완전 취소 — DB 삭제 안 함

        # 3. DB 삭제 (검수 먼저, 구매 나중)
        inspection_repo.delete_by_purchase(p["id"])
        purchase_repo.delete(p["id"])

        self._selected_purchase = None
        self.refresh()

        msg = f"'{p['item_name']}' 삭제 완료"
        if deleted_files:
            msg += f"\n삭제된 파일: {', '.join(deleted_files)}"
        if failed_files:
            msg += f"\n삭제 실패 파일: {', '.join(failed_files)}"
        self.status_var.set(f"'{p['item_name']}' 전체 삭제 완료")
        messagebox.showinfo("삭제 완료", msg)

    def _delete_inspection(self):
        if not self._selected_purchase:
            messagebox.showwarning("선택 오류", "구매건을 선택하세요.")
            return
        p = self._selected_purchase
        insp = inspection_repo.select_by_purchase(p["id"])
        if not insp:
            messagebox.showinfo("알림", "해당 구매건의 검수 기록이 없습니다.")
            return

        # 삭제 대상 파일 목록 구성
        file_labels = {"doc_inspection_list": "물품검수내역서(Excel)",
                       "doc_inspection_rpt":  "물품검수조서(HWP)"}
        target_files = []
        for field, label in file_labels.items():
            path_str = insp.get(field, "")
            if path_str and Path(path_str).exists():
                target_files.append((Path(path_str), label))

        msg = f"'{p['item_name']}' 의 검수 기록을 삭제하시겠습니까?\n(구매 이력은 유지됩니다)\n"
        if target_files:
            msg += "\n다음 파일도 함께 삭제됩니다:\n"
            msg += "\n".join(f"  • {label} ({path.name})" for path, label in target_files)
            msg += "\n\n이 작업은 되돌릴 수 없습니다."
        else:
            msg += "\n※ 연결된 파일이 없거나 이미 삭제되었습니다."

        if not messagebox.askyesno("삭제 확인", msg):
            return

        # 파일 삭제
        failed = []
        for path, label in target_files:
            try:
                path.unlink()
            except Exception as e:
                failed.append(f"{label} ({e})")

        # DB 삭제
        inspection_repo.delete(insp["id"])
        self.refresh()

        if failed:
            messagebox.showwarning("일부 삭제 실패",
                f"검수 기록은 삭제되었으나 아래 파일 삭제에 실패했습니다:\n" +
                "\n".join(failed))
            self.status_var.set("검수 기록 삭제 완료 (파일 일부 실패)")
        else:
            self.status_var.set("검수 기록 및 파일 삭제 완료")

    def _on_select(self, _event=None):
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        if idx >= len(self._filtered_purchases):
            return
        p = self._filtered_purchases[idx]
        self._selected_purchase = p

        # 카드 1: 기안 정보
        self._draft_title_var.set(p.get("doc_draft_title") or "-")
        self._dept_var.set(p.get("department") or "-")
        content = p.get("doc_draft_content") or "-"
        if len(content) > 200:
            content = content[:200] + "..."
        self._draft_content_var.set(content)
        self._draft_remark_var.set(p.get("doc_draft_remark") or "-")

        # 다중 품목 로드
        items = purchase_repo_mod.select_items(p["id"])
        self._selected_items = items

        if len(items) <= 1:
            item = items[0] if items else {}
            self._item_var.set(item.get("item_name", p["item_name"]))
            self._spec_var.set(item.get("spec", p.get("spec", "")) or "-")
            qty = item.get("quantity", p["quantity"])
            unit = item.get("unit", p.get("unit", "개"))
            self._qty_var.set(f"{qty}{unit}")
        else:
            self._item_var.set(f"{p['item_name']} ({len(items)}종)")
            summary = ", ".join(
                f"{i['item_name']}({i['quantity']}{i['unit']})" for i in items)
            self._spec_var.set(summary)
            total_qty = sum(i["quantity"] for i in items)
            self._qty_var.set(f"{len(items)}종 (총 {total_qty}개)")
        # 카드 2: 구매 정보
        sv = p["selected_vendor"]
        self._vendor_var.set(p.get(f"vendor{sv}_name") or "-")
        total = p.get(f"vendor{sv}_total", 0)
        self._amount_var.set(f"{total:,}원")

        # 검수탭 전용: 결제방법
        pay_code = p.get("payment_method") or ""
        pay_label = PAYMENT_METHODS.get(pay_code, pay_code) or "-"
        pay_bank = p.get("payment_bank") or ""
        if pay_code in ("transfer", "auto_transfer") and pay_bank:
            pay_acct = p.get("payment_account") or ""
            pay_holder = p.get("payment_holder") or ""
            self._pay_method_var_disp.set(
                f"{pay_label} ({pay_bank} {pay_acct} {pay_holder})".strip())
        else:
            self._pay_method_var_disp.set(pay_label)

    def _generate_documents(self):
        if not self._selected_purchase:
            messagebox.showwarning("선택 오류", "검수할 구매건을 선택하세요.")
            return
        if not self._inspector_var.get().strip():
            messagebox.showwarning("입력 오류", "검수자를 입력하세요.")
            return

        p = self._selected_purchase
        selected_v = p["selected_vendor"]

        # 품목 리스트 (DB에서 로드, 없으면 구버전 단일 품목 폴백)
        db_items = getattr(self, "_selected_items", [])
        if db_items:
            items = purchase_repo_mod.items_to_purchase_items(db_items)
        else:
            items = [PurchaseItem(
                seq=1,
                item_name=p["item_name"],
                spec=p.get("spec", ""),
                unit=p.get("unit", "개"),
                quantity=p["quantity"],
                unit_price=p[f"vendor{selected_v}_price"],
                total_price=p[f"vendor{selected_v}_total"],
            )]

        purchase_data = PurchaseData(
            department=p.get("department", ""),
            items=items,
            vendor1=VendorQuote(p["vendor1_name"], p["vendor1_price"], p["vendor1_total"]),
            vendor2=VendorQuote(p["vendor2_name"], p["vendor2_price"], p["vendor2_total"]),
            selected_vendor=selected_v,
            draft_date=p.get("draft_date", ""),
        )
        insp_data = InspectionData(
            purchase=purchase_data,
            inspection_date=self._date_var.get(),
            inspector=self._inspector_var.get().strip(),
            witness=self._witness_var.get().strip(),
            inspected_qty=purchase_data.quantity,
            has_defect=False,
            defect_note="",
            remark=self._remark_var.get().strip(),
        )
        self.status_var.set("검수 문서 생성 중...")
        # 메인 창 숨김 — HWP 보안 다이얼로그가 전면에 표시되도록
        root = self.winfo_toplevel()
        root.withdraw()
        self.update_idletasks()
        try:
            # 기존 구매건 폴더가 있으면 그 폴더에, 없으면 새 폴더 생성
            folder_str = p.get("doc_folder", "")
            if folder_str and Path(folder_str).exists():
                out_dir = Path(folder_str)
            else:
                out_dir = make_output_dir(p["item_name"])
                purchase_repo.update_folder(p["id"], str(out_dir))

            doc_rpt  = HwpGenerator().generate_inspection_report(insp_data, out_dir)
            doc_list = ExcelGenerator().generate_inspection_list(insp_data, out_dir)
            insp_id = inspection_repo.insert(insp_data, p["id"])
            inspection_repo.update_docs(insp_id, doc_list, doc_rpt)
            self.status_var.set(f"검수 문서 생성 완료: {out_dir.name}/")
            messagebox.showinfo("생성 완료",
                f"검수 문서가 생성되었습니다.\n\n폴더: {out_dir}\n{Path(doc_list).name}\n{Path(doc_rpt).name}")
            self.refresh()
        except Exception as e:
            self.status_var.set("오류")
            messagebox.showerror("오류", str(e))
        finally:
            root.deiconify()
            root.lift()
            root.focus_force()
            self.update_idletasks()
