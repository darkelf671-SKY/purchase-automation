"""탭 1: 구매 조사 — 사이트 바로가기 + 다중 품목 입력 + 문서 생성"""
import shutil
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime
from config import SCREENSHOT_DIR, make_output_dir_named, get_department, PAYMENT_METHODS
from ui.design_system import COLORS, SPACING, FONTS, BTN_ACTION_PAD
from core.models import PurchaseData, PurchaseItem, VendorQuote
from core.semi_auto import SemiAutoHelper
from core.screenshot import make_screenshot_name, cleanup, capture, capture_region, grab_clean_screen
from documents.hwp_generator import HwpGenerator
import db.purchase_repo as repo
import db.vendor_repo as vendor_repo
import db.sole_contract_repo as scr_repo
import db.draft_template_repo as tpl_repo
from ui.tab_vendor import VendorDialog
from ui.base_dialog import BaseDialog

MAX_ITEMS = 15
UNIT_OPTIONS = ["개", "EA", "세트", "식", "권", "본", "대", "통", "박스", "롤", "장"]


class ItemRow:
    """동적 품목 입력 행

    _items_container 에 직접 grid 배치 → 헤더와 동일한 컨테이너 공유로 열 정렬 보장
    컬럼: # | 품명 | 규격 | 단위 | 수량 | 견적1단가 | 견적1금액 | 견적2단가 | 견적2금액 | 비고 | -
    """
    _W = [3, 14, 12, 5, 4, 9, 9, 9, 9, 9, 2]

    def __init__(self, container: tk.Frame, seq: int, on_change, on_delete,
                 vat_mode_var: tk.StringVar = None,
                 on_total_mode_change=None):
        self._seq = seq
        self._on_change = on_change
        self._container = container
        self._vat_mode_var = vat_mode_var
        self._on_total_mode_change = on_total_mode_change
        self._v1_total_mode = tk.BooleanVar(value=False)
        self._v2_total_mode = tk.BooleanVar(value=False)
        self._widgets = []   # (widget, col, padx, pady)
        self._updating = False  # 재진입 방지 플래그
        self._build(seq, on_delete)

    # ── 내부 구성 ──────────────────────────────────────────────────

    def _grid(self, widget, col, padx=SPACING["xs"], pady=SPACING["xs"], **kw):
        widget.grid(row=self._seq, column=col, padx=padx, pady=pady, **kw)
        self._widgets.append((widget, col, padx, pady))
        return widget

    def _build(self, seq, on_delete):
        w = self._W

        self._seq_label = self._grid(
            ttk.Label(self._container, text=str(seq), width=w[0], anchor="center"), 0)

        self.item_name_var = tk.StringVar()
        self._grid(ttk.Entry(self._container, textvariable=self.item_name_var, width=w[1]), 1)

        self.spec_var = tk.StringVar()
        self._grid(ttk.Entry(self._container, textvariable=self.spec_var, width=w[2]), 2)

        # 단위: 자유 입력 + 드롭다운 (state="normal")
        self.unit_var = tk.StringVar(value="개")
        self._grid(ttk.Combobox(self._container, textvariable=self.unit_var,
                                values=UNIT_OPTIONS, width=w[3], state="normal"), 3)

        self.qty_var = tk.IntVar(value=1)
        self._grid(ttk.Spinbox(self._container, textvariable=self.qty_var,
                               from_=1, to=9999, width=w[4]), 4)

        self.price_var = tk.StringVar()
        self._price_entry = self._grid(
            ttk.Entry(self._container, textvariable=self.price_var, width=w[5]), 5)

        self.total_var = tk.StringVar(value="0")
        self._total_entry = self._grid(
            ttk.Entry(self._container, textvariable=self.total_var,
                      width=w[6], state="readonly"), 6)

        self.v2_price_var = tk.StringVar()
        self._v2_price_entry = self._grid(
            ttk.Entry(self._container, textvariable=self.v2_price_var, width=w[7]), 7)

        self.v2_total_var = tk.StringVar(value="0")
        self._v2_total_entry = self._grid(
            ttk.Entry(self._container, textvariable=self.v2_total_var,
                      width=w[8], state="readonly"), 8)

        self.remark_var = tk.StringVar()
        self._grid(ttk.Entry(self._container, textvariable=self.remark_var, width=w[9]), 9)

        self._del_btn = ttk.Button(self._container, text="\u00D7", width=3, command=on_delete,
                                    style="Small.TButton")
        self._del_btn.grid(row=self._seq, column=10, padx=(SPACING["xs"], 0), pady=SPACING["xs"])
        self._widgets.append((self._del_btn, 10, (SPACING["xs"], 0), SPACING["xs"]))

        self.price_var.trace_add("write", self._recalc_v1)
        self.v2_price_var.trace_add("write", self._recalc_v2)
        self.qty_var.trace_add("write", self._on_qty_change)
        self.total_var.trace_add("write", self._recalc_v1_reverse)
        self.v2_total_var.trace_add("write", self._recalc_v2_reverse)

    # ── 공개 메서드 ────────────────────────────────────────────────

    def regrid(self, new_seq: int):
        """행 순서 변경 시 그리드 위치 업데이트"""
        self._seq = new_seq
        for widget, col, padx, pady in self._widgets:
            widget.grid(row=new_seq, column=col, padx=padx, pady=pady)
        self._seq_label.config(text=str(new_seq))

    def _on_qty_change(self, *_):
        """수량 변경 시 현재 모드에 따라 적절한 재계산 호출"""
        if self._updating:
            return
        self._updating = True
        try:
            if self._v1_total_mode.get():
                self._do_reverse_v1()
            else:
                self._do_calc_v1()
            if self._v2_total_mode.get():
                self._do_reverse_v2()
            else:
                self._do_calc_v2()
            self._on_change()
        finally:
            self._updating = False

    def _recalc_v1(self, *_):
        """견적1: 단가 → 금액"""
        if self._updating or self._v1_total_mode.get():
            return
        self._updating = True
        try:
            self._do_calc_v1()
            self._on_change()
        finally:
            self._updating = False

    def _recalc_v2(self, *_):
        """견적2: 단가 → 금액"""
        if self._updating or self._v2_total_mode.get():
            return
        self._updating = True
        try:
            self._do_calc_v2()
            self._on_change()
        finally:
            self._updating = False

    def _recalc_v1_reverse(self, *_):
        """견적1: 금액 → 단가 역산"""
        if self._updating or not self._v1_total_mode.get():
            return
        self._updating = True
        try:
            self._do_reverse_v1()
            self._on_change()
        finally:
            self._updating = False

    def _recalc_v2_reverse(self, *_):
        """견적2: 금액 → 단가 역산"""
        if self._updating or not self._v2_total_mode.get():
            return
        self._updating = True
        try:
            self._do_reverse_v2()
            self._on_change()
        finally:
            self._updating = False

    def _do_calc_v1(self):
        vat = self._vat_mode_var.get() if self._vat_mode_var else "inclusive"
        mul = 1.1 if vat == "exclusive" else 1.0
        try:
            price = int(self.price_var.get().replace(",", ""))
            qty = self.qty_var.get()
            self.total_var.set(f"{round(price * mul) * qty:,}")
        except (ValueError, tk.TclError):
            self.total_var.set("0")

    def _do_calc_v2(self):
        vat = self._vat_mode_var.get() if self._vat_mode_var else "inclusive"
        mul = 1.1 if vat == "exclusive" else 1.0
        try:
            v2p = int(self.v2_price_var.get().replace(",", ""))
            qty = self.qty_var.get()
            self.v2_total_var.set(f"{round(v2p * mul) * qty:,}")
        except (ValueError, tk.TclError):
            self.v2_total_var.set("0")

    def _do_reverse_v1(self):
        try:
            total = int(self.total_var.get().replace(",", ""))
            qty = self.qty_var.get() or 1
            self.price_var.set(f"{total // qty:,}" if qty > 0 else "0")
        except (ValueError, tk.TclError):
            self.price_var.set("0")

    def _do_reverse_v2(self):
        try:
            v2_total = int(self.v2_total_var.get().replace(",", ""))
            qty = self.qty_var.get() or 1
            self.v2_price_var.set(f"{v2_total // qty:,}" if qty > 0 else "0")
        except (ValueError, tk.TclError):
            self.v2_price_var.set("0")

    def set_v1_total_mode(self, enabled: bool):
        """견적1 총액 입력 모드 전환"""
        self._v1_total_mode.set(enabled)
        self._total_entry.config(state="normal" if enabled else "readonly")
        self._price_entry.config(state="readonly" if enabled else "normal")
        if not enabled:
            # 해제 시 현재 단가 기준으로 금액 재계산
            self._updating = True
            try:
                self._do_calc_v1()
            finally:
                self._updating = False
        if self._on_total_mode_change:
            self._on_total_mode_change()

    def set_v2_total_mode(self, enabled: bool):
        """견적2 총액 입력 모드 전환"""
        self._v2_total_mode.set(enabled)
        self._v2_total_entry.config(state="normal" if enabled else "readonly")
        self._v2_price_entry.config(state="readonly" if enabled else "normal")
        if not enabled:
            # 해제 시 현재 단가 기준으로 금액 재계산
            self._updating = True
            try:
                self._do_calc_v2()
            finally:
                self._updating = False
        if self._on_total_mode_change:
            self._on_total_mode_change()

    def get_total(self) -> int:
        try:
            return int(self.total_var.get().replace(",", ""))
        except ValueError:
            return 0

    def get_v2_total(self) -> int:
        try:
            return int(self.v2_total_var.get().replace(",", ""))
        except ValueError:
            return 0

    def get_data(self) -> dict:
        try:
            qty = self.qty_var.get()
        except (ValueError, tk.TclError):
            qty = 1

        vat = self._vat_mode_var.get() if self._vat_mode_var else "inclusive"
        mul = 1.1 if vat == "exclusive" else 1.0
        v1_total_mode = self._v1_total_mode.get()
        v2_total_mode = self._v2_total_mode.get()

        # 견적1: 모드별 계산
        if v1_total_mode:
            try:
                total = int(self.total_var.get().replace(",", ""))
            except (ValueError, tk.TclError):
                total = 0
            unit = total // qty if qty > 0 else 0
        else:
            try:
                price = int(self.price_var.get().replace(",", ""))
            except (ValueError, tk.TclError):
                price = 0
            unit = round(price * mul)
            total = unit * qty

        # 견적2: 모드별 계산
        if v2_total_mode:
            try:
                v2_total = int(self.v2_total_var.get().replace(",", ""))
            except (ValueError, tk.TclError):
                v2_total = 0
            v2_unit = v2_total // qty if qty > 0 else 0
        else:
            try:
                v2_price = int(self.v2_price_var.get().replace(",", ""))
            except (ValueError, tk.TclError):
                v2_price = 0
            v2_unit = round(v2_price * mul)

        # price_input_mode 결정
        if v1_total_mode and v2_total_mode:
            mode = "total"
        elif v1_total_mode:
            mode = "v1_total"
        elif v2_total_mode:
            mode = "v2_total"
        else:
            mode = "unit"

        return {
            "seq":              self._seq,
            "item_name":        self.item_name_var.get().strip(),
            "spec":             self.spec_var.get().strip(),
            "unit":             self.unit_var.get(),
            "quantity":         qty,
            "unit_price":       unit,
            "total_price":      total,
            "v2_unit_price":    v2_unit,
            "remark":           self.remark_var.get().strip(),
            "price_input_mode": mode,
        }

    def destroy(self):
        for widget, *_ in self._widgets:
            widget.destroy()
        self._widgets.clear()


class PurchaseTab(ttk.Frame):
    def __init__(self, parent, status_var: tk.StringVar):
        super().__init__(parent)
        self.status_var = status_var
        self._semi = SemiAutoHelper()
        self._screenshot_paths = ["", ""]
        self._ss_labels        = [None, None]
        self._name_combos      = [None, None]
        self._all_vendors      = []
        self._vendor_records   = [None, None]
        self._item_rows: list[ItemRow] = []
        self._items_container  = None
        self._grand_total_var  = tk.StringVar(value="0")
        self._v1_total_var     = tk.StringVar(value="0")
        self._v2_total_var     = tk.StringVar(value="0")
        self._vat_mode_var     = tk.StringVar(value="inclusive")
        self._sole_quote_var   = tk.BooleanVar(value=False)
        self._v2_frame         = None
        self._draft_title_var  = tk.StringVar()
        self._title_edited     = False
        self._search_field_var = tk.StringVar(value="item")
        self._editing_purchase_id: int | None = None
        self._editing_doc_folder: str | None = None

        # ── 탭 전체 스크롤 래퍼 ─────────────────────────────────
        _canvas = tk.Canvas(self, highlightthickness=0)
        _vsb    = ttk.Scrollbar(self, orient="vertical", command=_canvas.yview)
        _canvas.configure(yscrollcommand=_vsb.set)
        _vsb.pack(side="right", fill="y")
        _canvas.pack(side="left", fill="both", expand=True)

        self._content = ttk.Frame(_canvas, padding=SPACING["lg"])
        _win = _canvas.create_window((0, 0), window=self._content, anchor="nw")

        def _fit_width(e):
            _canvas.itemconfig(_win, width=e.width)
        def _update_scroll(e):
            _canvas.configure(scrollregion=_canvas.bbox("all"))
        _canvas.bind("<Configure>", _fit_width)
        self._content.bind("<Configure>", _update_scroll)

        def _on_wheel(e):
            _canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        self.bind_all("<MouseWheel>", _on_wheel)

        self._build_ui()

    # ── UI 구성 ──────────────────────────────────────────────────

    def _build_ui(self):
        # 수정 모드 배너 (초기 숨김)
        self._build_edit_banner()

        # ① 품목 및 가격 입력 (VAT 포함)
        self._build_items_section()

        # 첫 번째 품명 → 기안제목 자동 채움
        if self._item_rows:
            self._item_rows[0].item_name_var.trace_add("write", self._auto_fill_title)

        # ② 시장 조사 및 견적 비교
        self._build_quote_section()

        # ③ 계약 업체 및 결제
        self._build_vendor_payment_section()

        # ④ 기안 작성
        self._build_draft_section()

        # 액션 버튼
        act_frame = ttk.Frame(self._content)
        act_frame.pack(fill="x", pady=SPACING["md"])
        ttk.Button(act_frame, text="입력 초기화",
                   command=self._reset_form).pack(side="left", padx=SPACING["md"])
        self._gen_btn = ttk.Button(act_frame, text="문서 생성",
                                    style="Primary.TButton",
                                    command=self._generate_documents)
        self._gen_btn.pack(side="right", padx=SPACING["md"], **BTN_ACTION_PAD)
        ttk.Label(act_frame,
                  text="※ 내부기안(HWP) + 산출기초조사서(HWP) 생성",
                  foreground=COLORS["text_muted"]).pack(side="right", padx=SPACING["sm"])

    def _build_edit_banner(self):
        """모드 배너 — 수정/복사 상태 표시 (grid row=0, 초기 숨김)"""
        # _content 내부에 grid 기반 배너 영역 (row 0)
        self._banner_frame = tk.Frame(self._content)
        self._banner_frame.pack(fill="x", pady=(0, SPACING["md"]))
        self._banner_frame.pack_forget()  # 초기 숨김

        self._edit_banner_label = tk.Label(
            self._banner_frame, text="", font=FONTS["body"])
        self._edit_banner_label.pack(side="left", padx=SPACING["md"])
        self._edit_cancel_btn = tk.Button(
            self._banner_frame, text="수정 취소", bg="#FFC107", fg="#000",
            relief="flat", padx=8, command=self._cancel_edit
        )
        self._edit_cancel_btn.pack(side="right", padx=SPACING["md"])

    def _show_banner(self, bg_color: str, fg_color: str, text: str, show_cancel: bool):
        """배너 표시 공통"""
        self._banner_frame.configure(bg=bg_color)
        self._edit_banner_label.config(text=text, bg=bg_color, fg=fg_color)
        if show_cancel:
            self._edit_cancel_btn.pack(side="right", padx=SPACING["md"])
        else:
            self._edit_cancel_btn.pack_forget()
        # pack_forget 후 맨 앞에 다시 pack
        self._banner_frame.pack_forget()
        # packed 상태인 첫 번째 자식을 찾아서 그 앞에 배치
        packed = [w for w in self._content.winfo_children()
                  if w != self._banner_frame and w.winfo_manager() == "pack"]
        if packed:
            self._banner_frame.pack(fill="x", pady=(0, SPACING["md"]),
                                    before=packed[0])
        else:
            self._banner_frame.pack(fill="x", pady=(0, SPACING["md"]))

    def _show_edit_banner(self, record: dict):
        item = record.get("item_name", "")
        date = record.get("created_at", "")[:10]
        self._show_banner("#FFF3CD", "#856404",
                          f"  수정 모드: \"{item}\" ({date})", show_cancel=True)

    def _show_copy_banner(self, record: dict):
        item = record.get("item_name", "")
        self._show_banner("#D1ECF1", "#0C5460",
                          f"  복사 모드: \"{item}\" → 새 기안 작성", show_cancel=False)

    def _hide_edit_banner(self):
        self._banner_frame.pack_forget()

    def _cancel_edit(self):
        self._editing_purchase_id = None
        self._editing_doc_folder = None
        self._hide_edit_banner()
        self._reset_form()
        self._update_gen_button_text()

    def _update_gen_button_text(self):
        if self._editing_purchase_id:
            self._gen_btn.config(text="문서 재생성")
        else:
            self._gen_btn.config(text="문서 생성")

    def _build_items_section(self):
        """① 품목 및 가격 입력 — VAT 설정 + 품목 테이블"""
        items_frame = ttk.LabelFrame(self._content, text=" ① 품목 및 가격 입력 ", padding=SPACING["lg"])
        items_frame.pack(fill="x", pady=(0, SPACING["md"]))

        # VAT 설정 (기존 survey에서 이동)
        vat_frame = ttk.Frame(items_frame)
        vat_frame.pack(fill="x", pady=(0, SPACING["md"]))
        ttk.Label(vat_frame, text="VAT:").pack(side="left", padx=(0, SPACING["md"]))
        self._vat_radios = []
        for val, lbl in [("exclusive", "VAT 별도 (입력가 × 1.1)"),
                         ("inclusive", "VAT 포함 (입력가 그대로)")]:
            rb = ttk.Radiobutton(vat_frame, text=lbl, variable=self._vat_mode_var, value=val,
                                 command=self._on_vat_change)
            rb.pack(side="left", padx=SPACING["sm"])
            self._vat_radios.append(rb)
        self._vat_hint_label = ttk.Label(vat_frame, text="",
                                         foreground=COLORS["danger"])
        self._vat_hint_label.pack(side="left", padx=(SPACING["md"], 0))

        ttk.Separator(items_frame, orient="horizontal").pack(fill="x", pady=SPACING["sm"])

        _MAX_CANVAS_H = 200   # 헤더 + 약 5행 데이터

        scroll_frame = ttk.Frame(items_frame)
        scroll_frame.pack(fill="x")

        self._items_canvas = tk.Canvas(scroll_frame, highlightthickness=0)
        self._items_vscroll = ttk.Scrollbar(
            scroll_frame, orient="vertical", command=self._items_canvas.yview)
        self._items_canvas.configure(yscrollcommand=self._items_vscroll.set)
        self._items_canvas.pack(side="left", fill="both", expand=True)

        self._items_container = ttk.Frame(self._items_canvas)
        _win = self._items_canvas.create_window(
            (0, 0), window=self._items_container, anchor="nw")

        def _on_canvas_w(event):
            self._items_canvas.itemconfig(_win, width=event.width)

        def _on_frame_h(event):
            self._items_container.update_idletasks()
            content_h = self._items_container.winfo_reqheight()
            canvas_h = min(content_h, _MAX_CANVAS_H)
            self._items_canvas.configure(
                height=canvas_h,
                scrollregion=self._items_canvas.bbox("all"))
            # 내용이 작으면 스크롤바 숨김
            if content_h <= _MAX_CANVAS_H:
                self._items_vscroll.pack_forget()
            else:
                if not self._items_vscroll.winfo_ismapped():
                    self._items_vscroll.pack(side="right", fill="y")

        self._items_canvas.bind("<Configure>", _on_canvas_w)
        self._items_container.bind("<Configure>", _on_frame_h)

        def _on_mousewheel(event):
            # 스크롤 필요 없으면 무시
            content_h = self._items_container.winfo_reqheight()
            if content_h > _MAX_CANVAS_H:
                self._items_canvas.yview_scroll(
                    int(-1 * (event.delta / 120)), "units")
        self._items_canvas.bind("<MouseWheel>", _on_mousewheel)
        self._items_container.bind("<MouseWheel>", _on_mousewheel)

        # 헤더 행 (row 0 — 데이터와 동일 컨테이너로 열 정렬 보장)
        for col, (text, w) in enumerate([
            ("#", 3), ("품명 (필수)", 14), ("규격/사양", 12), ("단위", 5),
            ("수량", 4), ("견적1 단가", 9), ("견적1 금액", 9),
            ("견적2 단가", 9), ("견적2 금액", 9), ("비고", 9), ("", 2),
        ]):
            ttk.Label(self._items_container, text=text, width=w, anchor="center",
                      foreground=COLORS["text_secondary"]).grid(row=0, column=col, padx=SPACING["xs"], pady=(0, SPACING["xs"]))

        # + 추가 버튼 / 총액 입력 토글 / 견적1·2 합계
        bottom = ttk.Frame(items_frame)
        bottom.pack(fill="x", pady=(SPACING["sm"], 0))
        ttk.Button(bottom, text="+ 품목 추가", style="Primary.TButton",
                   command=self._add_item_row).pack(side="left")

        self._v1_total_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text="견적1 총액입력(할인가 역산)",
                        variable=self._v1_total_mode_var,
                        command=self._on_v1_total_toggle).pack(
            side="left", padx=(SPACING["lg"], 0))

        self._v2_total_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text="견적2 총액입력(할인가 역산)",
                        variable=self._v2_total_mode_var,
                        command=self._on_v2_total_toggle).pack(
            side="left", padx=(SPACING["sm"], 0))

        # ⓘ 툴팁 아이콘
        info_label = ttk.Label(bottom, text="ⓘ", foreground=COLORS["info"],
                               cursor="hand2", font=FONTS["body"])
        info_label.pack(side="left", padx=(SPACING["xs"], 0))
        self._total_mode_tooltip = None
        _tip_text = (
            "인터넷 할인가로 구매할 때 결제 총액을 직접 입력하면\n"
            "단가가 자동 역산(총액÷수량)됩니다.\n\n"
            "• 견적1, 견적2를 각각 독립 설정 가능\n"
            "• 체크 시: [금액] 입력 → [단가] 자동 계산\n"
            "• 해제 시: [단가] 입력 → [금액] 자동 계산\n"
            "• 총액입력 시 VAT는 'VAT포함'으로 고정\n\n"
            "예) 토너 3개, 결제금액 42,000원\n"
            "    → 단가 14,000원 자동 표시"
        )
        info_label.bind("<Enter>", lambda e: self._show_total_tip(e, _tip_text))
        info_label.bind("<Leave>", lambda e: self._hide_total_tip())

        self._remainder_label = ttk.Label(bottom, text="",
                                          foreground=COLORS["danger"])
        self._remainder_label.pack(side="left", padx=(SPACING["sm"], 0))

        # 견적2 합계 (오른쪽부터 역순 pack)
        self._v2_unit_label = ttk.Label(bottom, text="원")
        self._v2_unit_label.pack(side="right", padx=(0, SPACING["sm"]))
        self._v2_total_label = ttk.Label(bottom, textvariable=self._v2_total_var,
            foreground=COLORS["text_secondary"], font=FONTS["heading"])
        self._v2_total_label.pack(side="right")
        self._v2_total_prefix = ttk.Label(bottom, text="견적2 합계:")
        self._v2_total_prefix.pack(side="right", padx=(SPACING["lg"], SPACING["sm"]))

        # 견적1 합계
        ttk.Label(bottom, text="원").pack(side="right", padx=(0, SPACING["sm"]))
        self._v1_total_label = ttk.Label(bottom, textvariable=self._v1_total_var,
            foreground=COLORS["total"], font=FONTS["heading"])
        self._v1_total_label.pack(side="right")
        ttk.Label(bottom, text="견적1 합계:").pack(side="right", padx=(0, SPACING["sm"]))

        # 초기 1행
        self._add_item_row()

    def _build_quote_section(self):
        """② 시장 조사 및 견적 비교 — 검색키워드 + 사이트 + 견적1/2 + 최저가 선택"""
        quote_frame = ttk.LabelFrame(self._content, text=" ② 시장 조사 및 견적 비교 ", padding=SPACING["lg"])
        quote_frame.pack(fill="x", pady=(0, SPACING["md"]))

        # 검색 키워드 (기존 survey에서 이동)
        kw_row = ttk.Frame(quote_frame)
        kw_row.pack(fill="x", pady=(0, SPACING["sm"]))
        ttk.Label(kw_row, text="검색 키워드:").pack(side="left", padx=(0, SPACING["md"]))
        ttk.Radiobutton(kw_row, text="첫 번째 품명",
                        variable=self._search_field_var, value="item").pack(side="left", padx=(0, SPACING["md"]))
        ttk.Radiobutton(kw_row, text="규격/사양",
                        variable=self._search_field_var, value="spec").pack(side="left")
        self._kw_preview = ttk.Label(kw_row, text="", foreground=COLORS["total"])
        self._kw_preview.pack(side="left", padx=(SPACING["lg"], 0))
        self._search_field_var.trace_add("write", self._update_kw_preview)

        # 사이트 바로가기 (기존 survey에서 이동)
        ttk.Label(quote_frame,
                  text="버튼 클릭 → 브라우저에서 조사 후 아래 견적란에 입력",
                  foreground=COLORS["text_muted"]).pack(anchor="w", pady=(0, SPACING["sm"]))
        btn_row = ttk.Frame(quote_frame)
        btn_row.pack(fill="x")
        for site, label in [("naver", "네이버쇼핑"), ("coupang", "쿠팡"),
                             ("lotteon", "롯데온"), ("gmarket", "G마켓"),
                             ("auction", "옥션"), ("s2b", "S2B")]:
            ttk.Button(btn_row, text=label,
                       command=lambda s=site: self._open_site(s)).pack(side="left", padx=SPACING["xs"])

        ttk.Separator(quote_frame, orient="horizontal").pack(fill="x", pady=SPACING["sm"])

        # 견적 2개
        quotes_frame = ttk.Frame(quote_frame)
        quotes_frame.pack(fill="x", pady=(0, SPACING["md"]))
        self._build_quote_frame(quotes_frame, "견적 1", 1)
        self._build_quote_frame(quotes_frame, "견적 2", 2)
        quotes_frame.columnconfigure(0, weight=1)
        quotes_frame.columnconfigure(1, weight=1)

        # 최저가 선택
        sel_frame = ttk.Frame(quote_frame)
        sel_frame.pack(fill="x")
        self._selected_var = tk.IntVar(value=1)
        ttk.Radiobutton(sel_frame, text="견적 1 선택",
                        variable=self._selected_var, value=1).pack(side="left", padx=SPACING["xxl"])
        ttk.Radiobutton(sel_frame, text="견적 2 선택",
                        variable=self._selected_var, value=2).pack(side="left", padx=SPACING["xxl"])
        self._price_info_label = ttk.Label(sel_frame, text="", foreground=COLORS["total"])
        self._price_info_label.pack(side="left", padx=SPACING["xxl"])
        ttk.Checkbutton(sel_frame, text="단독견적 (견적2 없음, 산출조사서 미생성)",
                        variable=self._sole_quote_var,
                        command=self._on_sole_toggle).pack(side="right", padx=SPACING["xxl"])

    def _build_vendor_payment_section(self):
        """③ 계약 업체 및 결제 — 구매업체 선택 + 업체 정보 + 결제방법 + 은행 정보"""
        vendor_frame = ttk.LabelFrame(self._content, text=" ③ 계약 업체 및 결제 ", padding=SPACING["lg"])
        vendor_frame.pack(fill="x", pady=(0, SPACING["md"]))

        # 구매업체
        ttk.Label(vendor_frame, text="구매업체 *:").grid(row=0, column=0, sticky="w", pady=SPACING["sm"], padx=(0, SPACING["md"]))
        self._draft_vendor_var = tk.StringVar()
        self._draft_vendor_combo = ttk.Combobox(
            vendor_frame, textvariable=self._draft_vendor_var,
            width=28, state="readonly")
        self._draft_vendor_combo.grid(row=0, column=1, sticky="w", pady=SPACING["sm"])
        self._draft_vendor_combo.bind("<<ComboboxSelected>>", self._on_draft_vendor_select)

        ttk.Button(vendor_frame, text="신규 등록",
                   command=self._add_draft_vendor).grid(
            row=0, column=2, sticky="w", padx=(SPACING["md"], 0), pady=SPACING["sm"])

        # 업체 정보 표시
        vendor_info = ttk.LabelFrame(vendor_frame, text=" 업체 정보 (자동 입력) ", padding=SPACING["lg"])
        vendor_info.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(SPACING["sm"], 0))

        self._dv_ceo_var  = tk.StringVar()
        self._dv_biz_var  = tk.StringVar()
        self._dv_addr_var = tk.StringVar()

        for r, (lbl, var) in enumerate([
            ("대표자:", self._dv_ceo_var),
            ("사업자번호:", self._dv_biz_var),
            ("주소:", self._dv_addr_var),
        ]):
            ttk.Label(vendor_info, text=lbl).grid(
                row=r, column=0, sticky="w", padx=(0, SPACING["md"]), pady=SPACING["xs"])
            ttk.Label(vendor_info, textvariable=var, foreground=COLORS["text_primary"]).grid(
                row=r, column=1, sticky="w", pady=SPACING["xs"])

        # 기본 결제방법 표시 (읽기전용)
        self._dv_pay_var = tk.StringVar()
        ttk.Label(vendor_info, text="기본 결제:").grid(
            row=3, column=0, sticky="w", padx=(0, SPACING["md"]), pady=SPACING["xs"])
        ttk.Label(vendor_info, textvariable=self._dv_pay_var,
                  foreground=COLORS["primary"],
                  font=("맑은 고딕", 10, "bold")).grid(
            row=3, column=1, sticky="w", pady=SPACING["xs"])

        vendor_info.columnconfigure(1, weight=1)

        # ── 결제방법 선택 (건별 오버라이드) ─────────────────────
        ttk.Label(vendor_frame, text="결제방법 *:").grid(
            row=2, column=0, sticky="w", pady=SPACING["sm"], padx=(0, SPACING["md"]))
        pay_f = ttk.Frame(vendor_frame)
        pay_f.grid(row=2, column=1, columnspan=3, sticky="w")
        self._pay_method_var = tk.StringVar(value="card")
        for text, value in [("법인카드 결제", "card"), ("무통장입금", "transfer"),
                            ("자동 이체 납부", "auto_transfer")]:
            ttk.Radiobutton(pay_f, text=text, variable=self._pay_method_var,
                            value=value, command=self._on_pay_method_change
                            ).pack(side="left", padx=(0, SPACING["xl"]))

        # 은행 정보 프레임 (무통장입금 시 표시)
        self._bank_info_frame = ttk.LabelFrame(
            vendor_frame, text=" 은행 정보 ", padding=SPACING["lg"])
        self._bank_info_frame.grid(
            row=3, column=0, columnspan=4, sticky="ew", pady=(SPACING["sm"], 0))
        self._dv_bank_var = tk.StringVar()
        self._dv_holder_var = tk.StringVar()
        self._dv_account_var = tk.StringVar()
        ttk.Label(self._bank_info_frame,
                  text="업체 기본값이 채워집니다. 이 건에서만 변경하려면 직접 수정하세요.",
                  foreground=COLORS["text_secondary"],
                  font=FONTS["small"]).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, SPACING["sm"]))
        for r, (lbl, var, w) in enumerate([
            ("은행명:", self._dv_bank_var, 16),
            ("예금주:", self._dv_holder_var, 16),
            ("계좌번호:", self._dv_account_var, 24),
        ], start=1):
            ttk.Label(self._bank_info_frame, text=lbl).grid(
                row=r, column=0, sticky="w", padx=(0, SPACING["md"]), pady=SPACING["xs"])
            ttk.Entry(self._bank_info_frame, textvariable=var, width=w).grid(
                row=r, column=1, sticky="w", pady=SPACING["xs"])
        self._bank_info_frame.columnconfigure(1, weight=1)
        self._bank_info_frame.grid_remove()  # 초기: 숨김

        vendor_frame.columnconfigure(1, weight=1)

    def _build_draft_section(self):
        """④ 기안 작성 — 템플릿, 제목, 기안일, 부서, 내용, 비고, 포함항목"""
        draft_frame = ttk.LabelFrame(self._content, text=" ④ 기안 작성 ", padding=SPACING["lg"])
        draft_frame.pack(fill="x", pady=(0, SPACING["md"]))

        # 템플릿 불러오기
        tpl_frame = ttk.Frame(draft_frame)
        tpl_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, SPACING["sm"]))
        ttk.Label(tpl_frame, text="템플릿:").pack(side="left", padx=(0, SPACING["md"]))
        self._template_records = tpl_repo.select_all()
        tpl_labels = ["(선택안함)"] + [r["label"] for r in self._template_records]
        self._template_var = tk.StringVar(value="(선택안함)")
        self._template_combo = ttk.Combobox(
            tpl_frame, textvariable=self._template_var,
            values=tpl_labels, width=28, state="readonly")
        self._template_combo.pack(side="left", padx=(0, SPACING["sm"]))
        ttk.Button(tpl_frame, text="템플릿 적용",
                   command=self._load_draft_template).pack(side="left", padx=(0, SPACING["sm"]))
        ttk.Button(tpl_frame, text="현재 내용 저장",
                   command=self._save_as_template).pack(side="left", padx=(0, SPACING["md"]))
        ttk.Label(tpl_frame, text="※ 기안 템플릿 탭에서 관리",
                  foreground=COLORS["text_muted"]).pack(side="left")

        ttk.Separator(draft_frame, orient="horizontal").grid(
            row=1, column=0, columnspan=4, sticky="ew", pady=SPACING["sm"])

        # 기안제목
        ttk.Label(draft_frame, text="기안제목 *:").grid(
            row=2, column=0, sticky="w", pady=SPACING["xs"], padx=(0, SPACING["md"]))
        title_entry = ttk.Entry(draft_frame, textvariable=self._draft_title_var, width=50)
        title_entry.grid(row=2, column=1, columnspan=2, sticky="ew", pady=SPACING["xs"])
        title_entry.bind("<Key>", lambda e: setattr(self, '_title_edited', True) if e.char else None)
        ttk.Label(draft_frame, text="※ 폴더명으로 사용", foreground=COLORS["text_muted"]).grid(
            row=2, column=3, sticky="w", padx=(SPACING["md"], 0))

        # 기안일
        self._draft_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Label(draft_frame, text="기안일:").grid(
            row=3, column=0, sticky="w", pady=SPACING["xs"], padx=(0, SPACING["md"]))
        ttk.Entry(draft_frame, textvariable=self._draft_date_var, width=20).grid(
            row=3, column=1, sticky="w", pady=SPACING["xs"])
        ttk.Label(draft_frame, text="※ YYYY-MM-DD (비워두면 오늘)",
                  foreground=COLORS["text_muted"]).grid(
            row=3, column=2, columnspan=2, sticky="w", padx=(SPACING["md"], 0))

        # 부서명 (설정에서 자동 로드)
        self._department_var = tk.StringVar(value=get_department())
        ttk.Label(draft_frame, text="부서명:").grid(
            row=4, column=0, sticky="w", pady=SPACING["xs"], padx=(0, SPACING["md"]))
        dept_label = ttk.Label(draft_frame, textvariable=self._department_var,
                               foreground=COLORS["text_primary"])
        dept_label.grid(row=4, column=1, sticky="w", pady=SPACING["xs"])
        dept_hint = self._department_var.get() or "(미설정)"
        ttk.Label(draft_frame, text="※ [설정]에서 변경",
                  foreground=COLORS["text_muted"]).grid(
            row=4, column=2, columnspan=2, sticky="w", padx=(SPACING["md"], 0))

        # 내용
        ttk.Label(draft_frame, text="내용 *:").grid(row=5, column=0, sticky="nw", pady=SPACING["sm"], padx=(0, SPACING["md"]))
        self._draft_content_text = tk.Text(draft_frame, width=48, height=4, wrap="word",
                                           font=FONTS["body"], relief="flat", bd=1,
                                           highlightbackground=COLORS["border"],
                                           highlightcolor=COLORS["primary_light"],
                                           highlightthickness=1, padx=SPACING["sm"], pady=SPACING["sm"])
        self._draft_content_text.grid(row=5, column=1, columnspan=3, sticky="ew", pady=SPACING["sm"])

        # 비고
        ttk.Label(draft_frame, text="비고:").grid(row=6, column=0, sticky="w", pady=SPACING["sm"], padx=(0, SPACING["md"]))
        self._draft_remark_var = tk.StringVar()
        ttk.Entry(draft_frame, textvariable=self._draft_remark_var, width=48).grid(
            row=6, column=1, columnspan=3, sticky="ew", pady=SPACING["sm"])

        ttk.Separator(draft_frame, orient="horizontal").grid(
            row=7, column=0, columnspan=4, sticky="ew", pady=SPACING["md"])

        # 포함 항목 선택
        opt_frame = ttk.LabelFrame(draft_frame, text=" 포함 항목 선택 ", padding=SPACING["lg"])
        opt_frame.grid(row=8, column=0, columnspan=4, sticky="ew", pady=(0, SPACING["sm"]))

        self._has_payment_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="계약방법 포함",
                        variable=self._has_payment_var).grid(row=0, column=0, sticky="w", pady=SPACING["xs"])

        self._has_sole_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="수의계약 사유 포함",
                        variable=self._has_sole_var,
                        command=self._toggle_sole_reason).grid(
            row=0, column=1, sticky="w", padx=(SPACING["xxl"], SPACING["sm"]), pady=SPACING["xs"])

        self._sole_records = scr_repo.select_all()
        sole_labels = ["(해당없음)"] + [
            r.get("label") or r["reason"][:20] for r in self._sole_records]
        self._sole_reason_var = tk.StringVar(value="(해당없음)")
        self._sole_reason_combo = ttk.Combobox(
            opt_frame, textvariable=self._sole_reason_var,
            values=sole_labels, width=36, state="readonly")
        self._sole_reason_combo.grid(row=0, column=2, sticky="w", padx=(0, SPACING["sm"]), pady=SPACING["xs"])

        draft_frame.columnconfigure(1, weight=1)

    def _add_item_row(self):
        if len(self._item_rows) >= MAX_ITEMS:
            messagebox.showwarning("제한", f"품목은 최대 {MAX_ITEMS}개까지 입력 가능합니다.")
            return
        row = ItemRow(
            self._items_container,
            seq=len(self._item_rows) + 1,
            on_change=self._update_grand_total,
            on_delete=lambda: None,
            vat_mode_var=self._vat_mode_var,
            on_total_mode_change=self._check_total_mode_vat,
        )
        # 기존 총액 모드 상태 적용
        if hasattr(self, '_v1_total_mode_var') and self._v1_total_mode_var.get():
            row.set_v1_total_mode(True)
        if hasattr(self, '_v2_total_mode_var') and self._v2_total_mode_var.get():
            row.set_v2_total_mode(True)
        self._item_rows.append(row)
        self._rebind_delete_buttons()
        self._update_kw_preview()

    def _rebind_delete_buttons(self):
        for i, row in enumerate(self._item_rows):
            row.regrid(i + 1)
            row._del_btn.config(command=lambda r=row: self._remove_item_row_by_ref(r))

    def _remove_item_row_by_ref(self, row: ItemRow):
        if len(self._item_rows) <= 1:
            messagebox.showwarning("제한", "최소 1개 품목이 필요합니다.")
            return
        row.destroy()
        self._item_rows.remove(row)
        self._rebind_delete_buttons()
        self._update_grand_total()

    def _on_v1_total_toggle(self):
        """견적1 총액 입력 모드 토글"""
        enabled = self._v1_total_mode_var.get()
        for row in self._item_rows:
            row.set_v1_total_mode(enabled)
        self._check_total_mode_vat()
        self._update_remainder_info()

    def _on_v2_total_toggle(self):
        """견적2 총액 입력 모드 토글"""
        enabled = self._v2_total_mode_var.get()
        for row in self._item_rows:
            row.set_v2_total_mode(enabled)
        self._check_total_mode_vat()
        self._update_remainder_info()

    def _check_total_mode_vat(self):
        """총액 모드 시 VAT 자동 비활성화 [D1]"""
        v1 = self._v1_total_mode_var.get() if hasattr(self, '_v1_total_mode_var') else False
        v2 = self._v2_total_mode_var.get() if hasattr(self, '_v2_total_mode_var') else False
        if v1 or v2:
            self._vat_mode_var.set("inclusive")
            for rb in self._vat_radios:
                rb.config(state="disabled")
            self._vat_hint_label.config(text="※ 총액 입력 시 VAT 별도 계산 불가")
        else:
            for rb in self._vat_radios:
                rb.config(state="normal")
            self._vat_hint_label.config(text="")

    def _show_total_tip(self, event, text):
        if self._total_mode_tooltip:
            self._total_mode_tooltip.destroy()
        self._total_mode_tooltip = tk.Toplevel(self)
        self._total_mode_tooltip.wm_overrideredirect(True)
        self._total_mode_tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root - 120}")
        lbl = tk.Label(self._total_mode_tooltip, text=text,
                       background=COLORS["tooltip_bg"], foreground=COLORS["tooltip_fg"],
                       relief="solid", borderwidth=1, wraplength=350,
                       justify="left", padx=SPACING["md"], pady=SPACING["sm"])
        lbl.pack()

    def _hide_total_tip(self):
        if self._total_mode_tooltip:
            self._total_mode_tooltip.destroy()
            self._total_mode_tooltip = None

    def _update_remainder_info(self):
        """총액 모드 절사 정보 표시"""
        if not hasattr(self, '_remainder_label'):
            return
        v1 = self._v1_total_mode_var.get() if hasattr(self, '_v1_total_mode_var') else False
        v2 = self._v2_total_mode_var.get() if hasattr(self, '_v2_total_mode_var') else False
        if not v1 and not v2:
            self._remainder_label.config(text="")
            return
        remainders = []
        for i, row in enumerate(self._item_rows, 1):
            try:
                qty = row.qty_var.get() or 1
                if v1:
                    total = int(row.total_var.get().replace(",", ""))
                    rem = total - (total // qty * qty)
                    if rem > 0:
                        remainders.append(f"품목{i}견적1: 절사 {rem}원")
                if v2:
                    v2_total = int(row.v2_total_var.get().replace(",", ""))
                    rem = v2_total - (v2_total // qty * qty)
                    if rem > 0:
                        remainders.append(f"품목{i}견적2: 절사 {rem}원")
            except (ValueError, tk.TclError):
                pass
        self._remainder_label.config(
            text=" | ".join(remainders) if remainders else "")

    def _on_vat_change(self):
        for row in self._item_rows:
            row._recalc_v1()
            row._recalc_v2()

    def _update_grand_total(self):
        v1_total = sum(row.get_total() for row in self._item_rows)
        v2_total = sum(row.get_v2_total() for row in self._item_rows)
        self._grand_total_var.set(f"{v1_total:,}")
        self._v1_total_var.set(f"{v1_total:,}")
        self._v2_total_var.set(f"{v2_total:,}")

        # 최저가 강조 색상 적용
        if hasattr(self, '_v1_total_label'):
            if v1_total > 0 and v2_total > 0:
                if v1_total <= v2_total:
                    self._v1_total_label.config(foreground=COLORS["total"])
                    self._v2_total_label.config(foreground=COLORS["text_secondary"])
                else:
                    self._v1_total_label.config(foreground=COLORS["text_secondary"])
                    self._v2_total_label.config(foreground=COLORS["total"])
            else:
                self._v1_total_label.config(foreground=COLORS["total"])
                self._v2_total_label.config(foreground=COLORS["text_secondary"])

        self._update_price_info()
        v1t = hasattr(self, '_v1_total_mode_var') and self._v1_total_mode_var.get()
        v2t = hasattr(self, '_v2_total_mode_var') and self._v2_total_mode_var.get()
        if v1t or v2t:
            self._update_remainder_info()

    def _build_quote_frame(self, parent, title: str, slot: int):
        col = slot - 1
        frame = ttk.LabelFrame(parent, text=f" {title} ", padding=SPACING["lg"])
        if slot == 2:
            self._v2_frame = frame
        frame.grid(row=0, column=col, sticky="nsew",
                   padx=(0, SPACING["sm"]) if col == 0 else (SPACING["sm"], 0))

        name_var = tk.StringVar()
        url_var  = tk.StringVar()

        # 구매처명
        ttk.Label(frame, text="구매처명:").grid(row=0, column=0, sticky="w", pady=SPACING["xs"])
        name_combo = ttk.Combobox(frame, textvariable=name_var, width=24)
        name_combo.grid(row=0, column=1, columnspan=2, sticky="ew", pady=SPACING["xs"])
        self._name_combos[col] = name_combo

        def on_vendor_selected(event, c=col):
            name = name_var.get()
            self._vendor_records[c] = next(
                (v for v in self._all_vendors if v["name"] == name), None)
            # 최저가 업체 → 기안서 구매업체 자동 연동
            sel = self._selected_var.get()
            if c == sel - 1 and self._vendor_records[c]:
                self._draft_vendor_var.set(self._vendor_records[c]["name"])
                self._on_draft_vendor_select()

        name_combo.bind("<<ComboboxSelected>>", on_vendor_selected)

        if slot == 1:
            ttk.Label(frame, text="합계금액:").grid(row=1, column=0, sticky="w", pady=SPACING["xs"])
            ttk.Entry(frame, textvariable=self._v1_total_var, width=16,
                      state="readonly").grid(row=1, column=1, columnspan=2, sticky="ew", pady=SPACING["xs"])
            ttk.Label(frame, text="※ 품목 합산 자동", foreground=COLORS["text_muted"]).grid(
                row=2, column=0, columnspan=3, sticky="w", pady=0)
        else:
            ttk.Label(frame, text="합계금액:").grid(row=1, column=0, sticky="w", pady=SPACING["xs"])
            ttk.Entry(frame, textvariable=self._v2_total_var, width=16,
                      state="readonly").grid(row=1, column=1, columnspan=2, sticky="ew", pady=SPACING["xs"])
            ttk.Label(frame, text="※ 품목 견적2 단가 자동합산", foreground=COLORS["text_muted"]).grid(
                row=2, column=0, columnspan=3, sticky="w", pady=0)

        # URL
        ttk.Label(frame, text="URL:").grid(row=3, column=0, sticky="w", pady=SPACING["xs"])
        ttk.Entry(frame, textvariable=url_var, width=20).grid(
            row=3, column=1, sticky="ew", pady=SPACING["xs"])

        def open_url(uvar=url_var, s=slot):
            u = uvar.get().strip()
            if not u:
                messagebox.showinfo("URL 없음", f"견적{s} URL이 비어있습니다.")
                return
            if not u.startswith(("http://", "https://")):
                u = "https://" + u
            webbrowser.open(u)

        ttk.Button(frame, text="열기", width=4, command=open_url).grid(
            row=3, column=2, sticky="w", padx=(SPACING["xs"], 0), pady=SPACING["xs"])

        # 스크린샷
        ttk.Label(frame, text="스크린샷:").grid(row=4, column=0, sticky="w", pady=SPACING["xs"])
        ss_label = ttk.Label(frame, text="없음", foreground=COLORS["text_muted"])
        ss_label.grid(row=4, column=1, columnspan=2, sticky="w", pady=SPACING["xs"])
        self._ss_labels[col] = ss_label

        def _set_file(c, lbl, path):
            old = self._screenshot_paths[c]
            if old and Path(old).parent == SCREENSHOT_DIR and Path(old).exists():
                cleanup(old)
            self._screenshot_paths[c] = path
            lbl.config(text=Path(path).name, foreground=COLORS["success"])

        def select_file(c=col, s=slot, lbl=ss_label):
            path = filedialog.askopenfilename(
                title=f"{title} 파일 선택",
                filetypes=[("이미지/문서", "*.png *.jpg *.jpeg *.bmp *.pdf"),
                           ("모든 파일", "*.*")]
            )
            if path:
                _set_file(c, lbl, path)

        def full_capture(c=col, s=slot, lbl=ss_label):
            top = self.winfo_toplevel()
            top.withdraw()          # 메인 윈도우 숨김
            top.update_idletasks()
            try:
                temp_path = SCREENSHOT_DIR / f"temp_capture_{s}.png"
                path = capture(save_path=temp_path)
                _set_file(c, lbl, path)
                lbl.config(foreground=COLORS["total"])
                self.status_var.set(f"견적{s} 전체캡처 완료")
            finally:
                top.deiconify()     # 메인 윈도우 복원

        def region_capture(c=col, s=slot, lbl=ss_label):
            top = self.winfo_toplevel()
            top.withdraw()          # 메인 윈도우 숨김
            top.update_idletasks()
            try:
                clean_img = grab_clean_screen()  # 깨끗한 화면 먼저 캡처
                temp_path = SCREENSHOT_DIR / f"temp_capture_region_{s}.png"
                path = capture_region(clean_img, parent=self, save_path=temp_path)
                if path:
                    _set_file(c, lbl, path)
                    lbl.config(foreground=COLORS["total"])
                    self.status_var.set(f"견적{s} 구역캡처 완료")
                else:
                    self.status_var.set("캡처 취소됨")
            finally:
                top.deiconify()     # 메인 윈도우 복원

        def reset_ss(c=col, s=slot, lbl=ss_label):
            src = self._screenshot_paths[c]
            if src and Path(src).parent == SCREENSHOT_DIR and Path(src).exists():
                cleanup(src)
            self._screenshot_paths[c] = ""
            lbl.config(text="없음", foreground=COLORS["text_muted"])
            self.status_var.set(f"견적{s} 캡처 초기화됨")

        btn_f = ttk.Frame(frame)
        btn_f.grid(row=5, column=0, columnspan=3, sticky="w", pady=(SPACING["sm"], 0))
        ttk.Button(btn_f, text="파일선택", command=select_file).pack(side="left", padx=(0, SPACING["xs"]))
        ttk.Button(btn_f, text="전체캡처", command=full_capture).pack(side="left", padx=(0, SPACING["xs"]))
        ttk.Button(btn_f, text="구역캡처", command=region_capture).pack(side="left", padx=(0, SPACING["xs"]))
        ttk.Button(btn_f, text="초기화",   command=reset_ss,
                   style="Danger.TButton").pack(side="left")

        frame.columnconfigure(1, weight=1)

        if slot == 1:
            self._v = [{"name": name_var, "url": url_var}]
        else:
            self._v.append({"name": name_var, "url": url_var})

    # ── 기안서 관련 메서드 ─────────────────────────────────────────

    def _toggle_sole_reason(self, _event=None):
        state = "readonly" if self._has_sole_var.get() else "disabled"
        self._sole_reason_combo.config(state=state)
        if not self._has_sole_var.get():
            self._sole_reason_var.set("(해당없음)")

    def _on_draft_vendor_select(self, _event=None):
        name = self._draft_vendor_var.get()
        v = next((x for x in self._all_vendors if x["name"] == name), None)
        if not v:
            return
        self._dv_ceo_var.set(v["ceo"] or "-")
        self._dv_biz_var.set(v["business_no"] or "-")
        self._dv_addr_var.set(v["address"] or "-")

        # 결제방법 + 은행 정보 자동 채움
        pay_code = v.get("payment_method", "card")
        self._dv_pay_var.set(PAYMENT_METHODS.get(pay_code, pay_code))
        self._pay_method_var.set(pay_code)
        self._dv_bank_var.set(v.get("bank_name", "") or "")
        self._dv_holder_var.set(v.get("account_holder", "") or "")
        self._dv_account_var.set(v.get("account_no", "") or "")
        self._on_pay_method_change()

    def _on_pay_method_change(self):
        """결제방법 라디오 변경 → 은행 정보 프레임 표시/숨김"""
        if self._pay_method_var.get() in ("transfer", "auto_transfer"):
            self._bank_info_frame.grid()
        else:
            self._bank_info_frame.grid_remove()
            # 은행 정보 클리어하지 않음 (업체 DB 값 보존)

    def _add_draft_vendor(self):
        def on_saved():
            self.refresh_vendors()
            names = [v["name"] for v in self._all_vendors]
            if names:
                self._draft_vendor_var.set(names[-1])
                self._on_draft_vendor_select()
        VendorDialog(self, title="신규 업체 등록", on_save=on_saved)

    def _load_draft_template(self):
        """기안 템플릿 불러오기"""
        label = self._template_var.get()
        if label == "(선택안함)":
            return
        record = next((r for r in self._template_records if r["label"] == label), None)
        if not record:
            messagebox.showwarning("오류", f"'{label}' 템플릿을 찾을 수 없습니다.")
            return
        first_name = self._item_rows[0].item_name_var.get().strip() if self._item_rows else ""
        title = record["title"].replace("{{품명}}", first_name) if first_name else record["title"]
        content = record["content"].replace("{{품명}}", first_name) if first_name else record["content"]
        if title:
            self._draft_title_var.set(title)
            self._title_edited = True
        if content:
            self._draft_content_text.delete("1.0", "end")
            self._draft_content_text.insert("1.0", content)
        if record.get("remark"):
            self._draft_remark_var.set(record["remark"])
        self.status_var.set(f"템플릿 '{label}' 불러오기 완료")

    def _save_as_template(self):
        """현재 기안폼 내용을 템플릿으로 저장"""
        content = self._draft_content_text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("저장 불가",
                "기안 내용이 비어있습니다.\n내용을 입력한 후 저장하세요.")
            return

        title = self._draft_title_var.get().strip()
        remark = self._draft_remark_var.get().strip()
        first_name = (self._item_rows[0].item_name_var.get().strip()
                      if self._item_rows else "")

        def on_saved():
            # Combobox 갱신
            self._template_records = tpl_repo.select_all()
            tpl_labels = ["(선택안함)"] + [r["label"] for r in self._template_records]
            self._template_combo["values"] = tpl_labels
            self.status_var.set("기안 템플릿 저장 완료")
            # 기안 템플릿 탭 동기화
            try:
                notebook = self.master
                for tab_id in notebook.tabs():
                    tab_widget = notebook.nametowidget(tab_id)
                    if type(tab_widget).__name__ == 'DraftTemplateTab':
                        tab_widget.refresh()
                        break
            except Exception:
                pass

        SaveAsTemplateDialog(
            self,
            title_text=title,
            content_text=content,
            remark_text=remark,
            first_item_name=first_name,
            on_save=on_saved,
        )

    def _auto_fill_title(self, *_):
        if not self._title_edited:
            name = self._item_rows[0].item_name_var.get().strip() if self._item_rows else ""
            if name:
                self._draft_title_var.set(f"{name} 구매 기안")

    # ── 업체 목록 새로고침 ───────────────────────────────────────

    def refresh_vendors(self):
        self._all_vendors = vendor_repo.select_all()
        names = [v["name"] for v in self._all_vendors]
        for combo in self._name_combos:
            if combo:
                combo["values"] = names
        if hasattr(self, '_draft_vendor_combo') and self._draft_vendor_combo:
            self._draft_vendor_combo["values"] = names

        # 수의계약 사유도 함께 갱신
        self._sole_records = scr_repo.select_all()
        sole_labels = ["(해당없음)"] + [
            r.get("label") or r["reason"][:20] for r in self._sole_records]
        if hasattr(self, '_sole_reason_combo') and self._sole_reason_combo:
            self._sole_reason_combo["values"] = sole_labels

        # 기안 템플릿 갱신
        self._template_records = tpl_repo.select_all()
        tpl_labels = ["(선택안함)"] + [r["label"] for r in self._template_records]
        if hasattr(self, '_template_combo') and self._template_combo:
            self._template_combo["values"] = tpl_labels

        # 부서명 설정값 갱신
        if hasattr(self, '_department_var'):
            self._department_var.set(get_department())

    # ── 폼 초기화 ────────────────────────────────────────────────

    def _reset_form(self):
        self._draft_title_var.set("")
        self._title_edited = False
        self._department_var.set(get_department())
        self._draft_date_var.set(datetime.now().strftime("%Y-%m-%d"))
        self._template_var.set("(선택안함)")

        # 품목 행 초기화 (1행만 남기기)
        for row in self._item_rows[1:]:
            row.destroy()
        self._item_rows = self._item_rows[:1]
        if self._item_rows:
            r = self._item_rows[0]
            r.item_name_var.set("")
            r.spec_var.set("")
            r.unit_var.set("개")
            r.qty_var.set(1)
            r.price_var.set("")
            r.total_var.set("0")
            r.v2_price_var.set("")
            r.v2_total_var.set("0")
            r.remark_var.set("")

        self._grand_total_var.set("0")
        self._v1_total_var.set("0")
        self._v2_total_var.set("0")
        self._vat_mode_var.set("inclusive")

        # 총액 모드 초기화
        if hasattr(self, '_v1_total_mode_var'):
            self._v1_total_mode_var.set(False)
            self._v2_total_mode_var.set(False)
            self._on_v1_total_toggle()
            self._on_v2_total_toggle()
            self._check_total_mode_vat()

        # 합계 색상 초기화
        if hasattr(self, '_v1_total_label'):
            self._v1_total_label.config(foreground=COLORS["total"])
            self._v2_total_label.config(foreground=COLORS["text_secondary"])

        for i, v in enumerate(self._v):
            v["name"].set("")
            v["url"].set("")
            src = self._screenshot_paths[i]
            if src and Path(src).parent == SCREENSHOT_DIR and Path(src).exists():
                cleanup(src)
            self._screenshot_paths[i] = ""
            if self._ss_labels[i]:
                self._ss_labels[i].config(text="없음", foreground=COLORS["text_muted"])

        self._selected_var.set(1)
        self._price_info_label.config(text="")
        self._vendor_records = [None, None]

        # 단독견적 초기화 (M-2)
        self._sole_quote_var.set(False)
        if self._v2_frame:
            self._v2_frame.grid()
        # 견적2 합계 위젯 복원
        if hasattr(self, '_v2_total_label'):
            if not self._v2_total_prefix.winfo_ismapped():
                self._v2_unit_label.pack(side="right", padx=(0, SPACING["sm"]))
                self._v2_total_label.pack(side="right")
                self._v2_total_prefix.pack(side="right", padx=(SPACING["lg"], SPACING["sm"]))

        # 기안서 정보 초기화
        self._draft_content_text.delete("1.0", "end")
        self._draft_remark_var.set("")
        self._has_payment_var.set(True)
        self._has_sole_var.set(True)
        self._sole_reason_var.set("(해당없음)")
        self._sole_reason_combo.config(state="readonly")
        self._draft_vendor_var.set("")
        self._dv_ceo_var.set("")
        self._dv_biz_var.set("")
        self._dv_addr_var.set("")
        self._pay_method_var.set("card")
        self._dv_pay_var.set("")
        self._dv_bank_var.set("")
        self._dv_holder_var.set("")
        self._dv_account_var.set("")
        if hasattr(self, '_bank_info_frame'):
            self._bank_info_frame.grid_remove()

        # 수의계약 사유 최신 데이터 로드
        self._sole_records = scr_repo.select_all()
        sole_labels = ["(해당없음)"] + [
            r.get("label") or r["reason"][:20] for r in self._sole_records]
        self._sole_reason_combo["values"] = sole_labels

        # 검색 키워드 초기화 (L-3)
        self._search_field_var.set("item")

        # 수정 모드 초기화
        self._editing_purchase_id = None
        self._editing_doc_folder = None
        if hasattr(self, '_banner_frame'):
            self._hide_edit_banner()
        if hasattr(self, '_gen_btn'):
            self._update_gen_button_text()

        self.status_var.set("입력 초기화 완료")

    # ── 검색 키워드 ──────────────────────────────────────────────

    def _get_search_query(self) -> str:
        if self._item_rows:
            first_item = self._item_rows[0].item_name_var.get().strip()
            first_spec  = self._item_rows[0].spec_var.get().strip()
            if self._search_field_var.get() == "spec":
                return first_spec or first_item
            return first_item
        return ""

    def _update_kw_preview(self, *_):
        q = self._get_search_query()
        if hasattr(self, '_kw_preview'):
            self._kw_preview.config(text=f"→ 검색어: {q}" if q else "")

    def _open_site(self, site: str):
        query = self._get_search_query()
        if not query:
            messagebox.showwarning("입력 오류", "첫 번째 품명을 먼저 입력하세요.")
            return
        name = self._semi.open_site(site, query)
        self.status_var.set(f"{name} 열림 — [{query}] 검색 중")

    def _update_price_info(self):
        try:
            t1 = int(self._v1_total_var.get().replace(",", "") or 0)
            t2 = int(self._v2_total_var.get().replace(",", "") or 0)
            if t1 == 0 and t2 == 0:
                return
            if t1 == t2:
                self._selected_var.set(1)
                self._price_info_label.config(text="동일 금액 — 견적1 자동 선택")
            else:
                cheaper = 1 if t1 <= t2 else 2
                self._selected_var.set(cheaper)
                diff = abs(t1 - t2)
                self._price_info_label.config(
                    text=f"견적{cheaper}이 {diff:,}원 저렴 (자동 선택)")
            # 기안서 업체 자동 연동
            sel = self._selected_var.get()
            vr = self._vendor_records[sel - 1]
            if vr and hasattr(self, '_draft_vendor_combo'):
                self._draft_vendor_var.set(vr["name"])
                self._on_draft_vendor_select()
        except ValueError:
            pass

    def _on_sole_toggle(self):
        sole = self._sole_quote_var.get()
        if sole:
            if self._v2_frame:
                self._v2_frame.grid_remove()
            self._v[1]["name"].set("단독견적")
            self._v[1]["url"].set("")
            # 견적2 스크린샷 초기화 (M-1)
            src = self._screenshot_paths[1]
            if src and Path(src).parent == SCREENSHOT_DIR and Path(src).exists():
                cleanup(src)
            self._screenshot_paths[1] = ""
            if self._ss_labels[1]:
                self._ss_labels[1].config(text="없음", foreground=COLORS["text_muted"])
        else:
            if self._v2_frame:
                self._v2_frame.grid()
            self._v[1]["name"].set("")

        # 견적2 합계 표시/숨김
        if hasattr(self, '_v2_total_label'):
            if sole:
                self._v2_total_prefix.pack_forget()
                self._v2_total_label.pack_forget()
                self._v2_unit_label.pack_forget()
            else:
                self._v2_unit_label.pack(side="right", padx=(0, SPACING["sm"]))
                self._v2_total_label.pack(side="right")
                self._v2_total_prefix.pack(side="right", padx=(SPACING["lg"], SPACING["sm"]))

    def load_purchase(self, record: dict, items: list):
        """이력에서 구매 데이터 불러오기 — 폼 전체 채우기"""
        self._reset_form()
        dept = record.get("department", "")
        if dept:
            self._department_var.set(dept)
        # 기안일 복원
        draft_date = record.get("draft_date", "")
        if draft_date:
            self._draft_date_var.set(draft_date)

        # 기안제목 복원
        draft_title = record.get("doc_draft_title", "")
        if draft_title:
            self._draft_title_var.set(draft_title)
            self._title_edited = True

        # VAT 모드 먼저 설정 (legacy "none" → "inclusive" 매핑)
        vat_mode = record.get("vat_mode", "inclusive")
        if vat_mode == "none":
            vat_mode = "inclusive"
        self._vat_mode_var.set(vat_mode)
        div = 1.1 if vat_mode == "exclusive" else 1.0

        # 품목 행 채우기
        for _ in items[1:]:
            self._add_item_row()
        for row, item in zip(self._item_rows, items):
            row.item_name_var.set(item.get("item_name", ""))
            row.spec_var.set(item.get("spec") or "")
            row.unit_var.set(item.get("unit", "개"))
            row.qty_var.set(item.get("quantity", 1))
            raw_price = round(item.get("unit_price", 0) / div) if div != 1.0 else item.get("unit_price", 0)
            raw_v2 = round(item.get("v2_unit_price", 0) / div) if div != 1.0 else item.get("v2_unit_price", 0)
            row.price_var.set(str(raw_price))
            row.v2_price_var.set(str(raw_v2))
            row.remark_var.set(item.get("remark") or "")

        # 총액 입력 모드 복원 (4가지: unit, total, v1_total, v2_total)
        has_v1_total = any(
            item.get("price_input_mode") in ("total", "v1_total") for item in items)
        has_v2_total = any(
            item.get("price_input_mode") in ("total", "v2_total") for item in items)
        if has_v1_total:
            self._v1_total_mode_var.set(True)
        if has_v2_total:
            self._v2_total_mode_var.set(True)
        for row, item in zip(self._item_rows, items):
            mode = item.get("price_input_mode", "unit")
            if mode in ("total", "v1_total"):
                row.total_var.set(str(item.get("total_price", 0)))
                row.set_v1_total_mode(True)
            if mode in ("total", "v2_total"):
                v2_qty = item.get("quantity", 1) or 1
                v2_unit = item.get("v2_unit_price", 0)
                row.v2_total_var.set(str(v2_unit * v2_qty))
                row.set_v2_total_mode(True)
        if has_v1_total or has_v2_total:
            self._check_total_mode_vat()

        self._v[0]["name"].set(record.get("vendor1_name", ""))
        self._v[0]["url"].set(record.get("vendor1_url", ""))
        self._v[1]["name"].set(record.get("vendor2_name", ""))
        self._v[1]["url"].set(record.get("vendor2_url", ""))
        self._selected_var.set(record.get("selected_vendor", 1))
        self._update_grand_total()

        # 스크린샷 경로 복원
        for idx, key in enumerate(("vendor1_screenshot", "vendor2_screenshot")):
            ss_path = record.get(key, "")
            if ss_path and Path(ss_path).exists():
                self._screenshot_paths[idx] = ss_path
                if self._ss_labels[idx]:
                    self._ss_labels[idx].config(
                        text=Path(ss_path).name,
                        foreground=COLORS["success"])
            elif ss_path:
                # DB에 경로 있으나 파일 삭제됨
                self._screenshot_paths[idx] = ""
                if self._ss_labels[idx]:
                    self._ss_labels[idx].config(
                        text="파일 없음 (재캡처 필요)",
                        foreground=COLORS["warning"])

        # 기안서 내용 복원
        draft_content = record.get("doc_draft_content", "")
        if draft_content:
            self._draft_content_text.delete("1.0", "end")
            self._draft_content_text.insert("1.0", draft_content)

        # 기안서 업체 자동 매칭
        sel = record.get("selected_vendor", 1)
        sel_name = record.get(f"vendor{sel}_name", "")
        if sel_name:
            vendor_names = [v["name"] for v in self._all_vendors]
            if sel_name in vendor_names:
                self._draft_vendor_var.set(sel_name)
                self._on_draft_vendor_select()

        # 결제방법 복원
        pay_m = record.get("payment_method", "") or "card"
        if pay_m:
            self._pay_method_var.set(pay_m)
            self._dv_bank_var.set(record.get("payment_bank", "") or "")
            self._dv_holder_var.set(record.get("payment_holder", "") or "")
            self._dv_account_var.set(record.get("payment_account", "") or "")
            self._dv_pay_var.set(PAYMENT_METHODS.get(pay_m, pay_m))
            self._on_pay_method_change()

        self._show_copy_banner(record)
        self.status_var.set(f"'{record.get('item_name', '')}' 복사 완료 — 새 기안 작성")

    def load_purchase_for_edit(self, record: dict, items: list):
        """이력에서 구매 데이터를 수정 모드로 불러오기"""
        self.load_purchase(record, items)
        # 복사 배너 → 수정 배너로 교체
        self._hide_edit_banner()
        self._editing_purchase_id = record["id"]
        self._editing_doc_folder = record.get("doc_folder", "")
        self._show_edit_banner(record)
        self._update_gen_button_text()
        self.status_var.set(f"'{record.get('item_name', '')}' 수정 모드")

    # ── 유효성 검사 ──────────────────────────────────────────────

    def _validate(self) -> bool:
        if not self._draft_title_var.get().strip():
            messagebox.showwarning("입력 오류", "기안제목을 입력하세요.")
            return False
        for i, row in enumerate(self._item_rows, 1):
            if not row.item_name_var.get().strip():
                messagebox.showwarning("입력 오류", f"품목 {i}의 품명을 입력하세요.")
                return False
            # 수량 >= 1 검사 (C-1)
            try:
                qty = row.qty_var.get()
                if qty < 1:
                    raise ValueError
            except (ValueError, tk.TclError):
                messagebox.showwarning("입력 오류", f"품목 {i}의 수량을 1 이상 입력하세요.")
                return False
            # 견적1 검증: 모드별
            if self._v1_total_mode_var.get():
                try:
                    total = int(row.total_var.get().replace(",", ""))
                    if total <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showwarning("입력 오류", f"품목 {i}의 견적1 금액을 올바르게 입력하세요.")
                    return False
            else:
                try:
                    price = int(row.price_var.get().replace(",", ""))
                    if price <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showwarning("입력 오류", f"품목 {i}의 견적1 단가를 올바르게 입력하세요.")
                    return False
        for i, v in enumerate(self._v, 1):
            if i == 2 and self._sole_quote_var.get():
                continue
            if not v["name"].get().strip():
                messagebox.showwarning("입력 오류", f"견적 {i}의 구매처명을 입력하세요.")
                return False
        # 견적1·2 동일 업체 방지 (C-4)
        if not self._sole_quote_var.get():
            v1 = self._v[0]["name"].get().strip()
            v2 = self._v[1]["name"].get().strip()
            if v1 and v2 and v1 == v2:
                messagebox.showwarning("입력 오류",
                    f"견적 1과 견적 2의 구매처가 동일합니다: '{v1}'\n"
                    "서로 다른 업체를 입력하세요.")
                return False
        # 견적2 단가/금액 0 경고 (C-2) — 총액 모드 구분
        if not self._sole_quote_var.get():
            if self._v2_total_mode_var.get():
                all_v2_zero = all(
                    int(row.v2_total_var.get().replace(",", "") or "0") == 0
                    for row in self._item_rows
                )
                zero_label = "견적2 금액이 모두 0원입니다."
            else:
                all_v2_zero = all(
                    int(row.v2_price_var.get().replace(",", "") or "0") == 0
                    for row in self._item_rows
                )
                zero_label = "견적2 단가가 모두 0원입니다."
            if all_v2_zero:
                if not messagebox.askyesno("확인",
                    f"{zero_label}\n계속 진행하시겠습니까?"):
                    return False
        # 기안서 내용 필수
        if not self._draft_content_text.get("1.0", "end-1c").strip():
            messagebox.showwarning("입력 오류", "기안서 내용을 입력하세요.")
            return False
        # 기안서 구매업체 필수
        if not self._draft_vendor_var.get():
            messagebox.showwarning("입력 오류", "기안서 구매업체를 선택하세요.")
            return False
        # 결제방법이 무통장입금인 경우 은행 정보 검증
        if self._pay_method_var.get() == "transfer":
            if not self._dv_bank_var.get().strip() or not self._dv_account_var.get().strip():
                messagebox.showwarning("입력 오류",
                    "무통장입금 시 은행명과 계좌번호는 필수입니다.")
                return False
        return True

    # ── 문서 생성 ─────────────────────────────────────────────────

    def _build_purchase_data(self) -> PurchaseData:
        items = []
        for row in self._item_rows:
            d = row.get_data()
            items.append(PurchaseItem(
                seq=d["seq"],
                item_name=d["item_name"],
                spec=d["spec"],
                unit=d["unit"],
                quantity=d["quantity"],
                unit_price=d["unit_price"],
                total_price=d["total_price"],
                v2_unit_price=d["v2_unit_price"],
                remark=d["remark"],
                price_input_mode=d.get("price_input_mode", "unit"),
            ))
        grand    = sum(item.total_price for item in items)
        # v2 합계: UI에서 직접 합산 (총액 모드에서 역산 오차 방지)
        v2_grand = sum(row.get_v2_total() for row in self._item_rows)

        data = PurchaseData(
            department=self._department_var.get().strip() or get_department(),
            items=items,
            vendor1=VendorQuote(
                name=self._v[0]["name"].get().strip(),
                unit_price=grand,
                total_price=grand,
                url=self._v[0]["url"].get().strip(),
                screenshot_path=self._screenshot_paths[0],
            ),
            vendor2=VendorQuote(
                name=self._v[1]["name"].get().strip(),
                unit_price=v2_grand,
                total_price=v2_grand,
                url=self._v[1]["url"].get().strip(),
                screenshot_path=self._screenshot_paths[1],
            ),
            selected_vendor=self._selected_var.get(),
            vat_mode=self._vat_mode_var.get(),
            draft_date=self._draft_date_var.get().strip(),
        )

        # 결제방법 정보 첨부
        data.payment_method = self._pay_method_var.get()
        data.payment_bank = self._dv_bank_var.get().strip()
        data.payment_account = self._dv_account_var.get().strip()
        data.payment_holder = self._dv_holder_var.get().strip()

        return data

    def _generate_documents(self):
        if not self._validate():
            return
        if self._editing_purchase_id:
            self._regenerate_documents()
        else:
            self._create_new_documents()

    def _build_docs_common(self, data: PurchaseData, out_dir: Path) -> tuple:
        """문서 생성 공통 로직 — (doc_calc, doc_draft, attachment_files) 반환"""
        # 스크린샷 복사
        vendor_names = [data.vendor1.name, data.vendor2.name]
        attachment_files = []
        for slot, (src, vname) in enumerate(
                zip(self._screenshot_paths, vendor_names), start=1):
            if src and Path(src).exists():
                ext   = Path(src).suffix.lower() or ".png"
                fname = make_screenshot_name(slot, vname, ext)
                perm  = SCREENSHOT_DIR / fname
                if Path(src).resolve() != perm.resolve():
                    if perm.exists():
                        perm.unlink()
                    shutil.copy2(src, perm)
                dest = out_dir / fname
                if perm.resolve() != dest.resolve():
                    shutil.copy2(perm, dest)
                self._screenshot_paths[slot - 1] = str(perm)
                attachment_files.append(str(dest))

        sole_mode = self._sole_quote_var.get()
        doc_calc = ""
        doc_draft = ""
        draft_title = self._draft_title_var.get().strip()

        root = self.winfo_toplevel()
        root.withdraw()
        self.update_idletasks()
        try:
            gen = HwpGenerator()

            if not sole_mode:
                doc_calc = gen.generate_calculation(data, out_dir)
                attachment_files.append(doc_calc)

            draft_content = self._draft_content_text.get("1.0", "end-1c").strip()
            draft_info = {
                "title":   draft_title,
                "content": draft_content,
                "remark":  self._draft_remark_var.get().strip(),
            }
            vendor_name = self._draft_vendor_var.get()
            vendor = next(
                (v for v in self._all_vendors if v["name"] == vendor_name), None)

            sole_reason = ""
            if self._has_sole_var.get():
                sole_label = self._sole_reason_var.get()
                if sole_label and sole_label != "(해당없음)":
                    match = next(
                        (r for r in self._sole_records
                         if (r.get("label") or r["reason"][:20]) == sole_label),
                        None)
                    sole_reason = match["reason"] if match else sole_label

            # 결제방법 오버라이드
            payment_override = {
                "method": self._pay_method_var.get(),
                "bank": self._dv_bank_var.get().strip(),
                "account": self._dv_account_var.get().strip(),
                "holder": self._dv_holder_var.get().strip(),
            }

            doc_draft = gen.generate_draft(
                data, draft_info, vendor, out_dir,
                has_payment=self._has_payment_var.get(),
                sole_reason=sole_reason,
                attachment_files=attachment_files,
                payment_override=payment_override,
            )
        finally:
            root.deiconify()
            root.lift()
            root.focus_force()
            self.update_idletasks()

        return doc_calc, doc_draft

    def _save_db_meta(self, purchase_id: int, out_dir: Path,
                      doc_draft: str, doc_calc: str):
        """DB 메타 정보 저장 (신규/수정 공통)"""
        repo.update_folder(purchase_id, str(out_dir))
        if doc_calc and doc_draft:
            repo.update_docs(purchase_id, doc_draft, doc_calc)
        elif doc_draft:
            repo.update_docs(purchase_id, doc_draft, "")
        elif doc_calc:
            repo.update_docs(purchase_id, "", doc_calc)
        draft_title = self._draft_title_var.get().strip()
        draft_content = self._draft_content_text.get("1.0", "end-1c").strip()
        draft_remark = self._draft_remark_var.get().strip()
        repo.update_draft_meta(purchase_id, draft_title, draft_content, draft_remark)

    def _create_new_documents(self):
        """신규 문서 생성 (기존 로직)"""
        if not self._check_screenshot_missing():
            return
        data = self._build_purchase_data()
        draft_title = self._draft_title_var.get().strip()

        try:
            out_dir = make_output_dir_named(draft_title)
        except FileExistsError:
            messagebox.showerror("폴더 중복",
                f"'{draft_title}' 폴더가 이미 존재합니다.\n다른 기안제목을 입력하세요.")
            return
        except Exception as e:
            messagebox.showerror("오류", f"폴더 생성 실패: {e}")
            return

        self.status_var.set("문서 생성 중...")
        self._gen_btn.configure(state="disabled", text="생성 중...")
        self.config(cursor="wait")
        self.update()

        try:
            doc_calc, doc_draft = self._build_docs_common(data, out_dir)

            purchase_id = repo.insert(data)
            self._save_db_meta(purchase_id, out_dir, doc_draft, doc_calc)

            files_created = []
            if doc_calc:
                files_created.append(f"산출기초조사서: {Path(doc_calc).name}")
            if doc_draft:
                files_created.append(f"기안서: {Path(doc_draft).name}")
            files_str = "\n".join(files_created)

            self.status_var.set(f"문서 생성 완료: {out_dir.name}/")
            messagebox.showinfo("생성 완료",
                f"문서가 생성되었습니다.\n\n폴더: {out_dir}\n{files_str}")

            self._reset_form()

        except Exception as e:
            self.status_var.set("오류 발생")
            messagebox.showerror("오류", str(e))
        finally:
            self._gen_btn.configure(state="normal")
            self._update_gen_button_text()
            self.config(cursor="")

    def _check_screenshot_missing(self) -> bool:
        """스크린샷 누락 확인 — False 반환 시 중단"""
        missing = []
        sole = self._sole_quote_var.get()
        if not self._screenshot_paths[0]:
            missing.append("견적1")
        if not sole and not self._screenshot_paths[1]:
            missing.append("견적2")
        if not missing:
            return True
        result = messagebox.askyesnocancel("견적파일 확인",
            f"{', '.join(missing)}의 견적파일(스크린샷)이 없습니다.\n\n"
            "견적파일 없이 진행하면 기안서에 첨부파일이\n"
            "누락됩니다.\n\n"
            "• [예] 견적파일 없이 계속 진행\n"
            "• [아니오] 돌아가서 견적파일 추가")
        if result is None or result is False:
            return False
        return True

    def _regenerate_documents(self):
        """수정 모드 — 기존 구매건 UPDATE + 문서 재생성"""
        if not self._check_screenshot_missing():
            return

        import db.inspection_repo as insp_repo

        purchase_id = self._editing_purchase_id

        # 검수 완료 건 확인 + 삭제 [D3]
        insp = insp_repo.select_by_purchase(purchase_id)
        if insp:
            if not messagebox.askyesno("검수 기록 삭제 경고",
                "이 구매건은 검수가 완료되었습니다.\n\n"
                "수정을 진행하면 기존 검수 기록과 문서가\n"
                "자동으로 삭제됩니다.\n\n"
                "수정 후 검수 입력 탭에서 재검수하세요.\n\n"
                "계속하시겠습니까?", icon="warning"):
                return
            # 검수 파일 삭제
            for key in ("doc_inspection_list", "doc_inspection_rpt"):
                path = insp.get(key, "")
                if path and Path(path).exists():
                    try:
                        Path(path).unlink()
                    except OSError:
                        pass
            insp_repo.delete(insp["id"])

        data = self._build_purchase_data()

        # 기존 문서 파일 삭제 (제목 변경 시 구 파일 잔여 방지)
        from config import get_output_dir
        allowed_base = Path(get_output_dir()).resolve()
        old_record = repo.select_by_id(purchase_id)
        if old_record:
            for key in ("doc_draft", "doc_calculation"):
                old_path = old_record.get(key, "")
                if not old_path:
                    continue
                p = Path(old_path).resolve()
                # 출력 디렉토리 범위 내 파일만 삭제 (경로 검증)
                if p.exists() and str(p).startswith(str(allowed_base)):
                    try:
                        p.unlink()
                    except OSError:
                        pass

        # 기존 폴더 사용 [D4]
        out_dir = Path(self._editing_doc_folder) if self._editing_doc_folder else None
        if not out_dir or not out_dir.exists():
            # 폴더가 없으면 새로 생성
            draft_title = self._draft_title_var.get().strip()
            try:
                out_dir = make_output_dir_named(draft_title)
            except FileExistsError:
                out_dir = Path(self._editing_doc_folder)
                out_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("오류", f"폴더 생성 실패: {e}")
                return

        self.status_var.set("문서 재생성 중...")
        self._gen_btn.configure(state="disabled", text="재생성 중...")
        self.config(cursor="wait")
        self.update()

        try:
            doc_calc, doc_draft = self._build_docs_common(data, out_dir)

            # DB UPDATE
            repo.update(purchase_id, data)
            repo.update_items(purchase_id, data.items)
            self._save_db_meta(purchase_id, out_dir, doc_draft, doc_calc)

            files_created = []
            if doc_calc:
                files_created.append(f"산출기초조사서: {Path(doc_calc).name}")
            if doc_draft:
                files_created.append(f"기안서: {Path(doc_draft).name}")
            files_str = "\n".join(files_created)

            self.status_var.set(f"문서 재생성 완료: {out_dir.name}/")
            messagebox.showinfo("재생성 완료",
                f"문서가 재생성되었습니다.\n\n폴더: {out_dir}\n{files_str}")

            self._reset_form()

        except Exception as e:
            self.status_var.set("오류 발생")
            messagebox.showerror("오류", str(e))
        finally:
            self._gen_btn.configure(state="normal")
            self._update_gen_button_text()
            self.config(cursor="")


class SaveAsTemplateDialog(BaseDialog):
    """기안폼 현재 내용을 템플릿으로 저장하는 경량 다이얼로그"""

    def __init__(self, parent, *, title_text: str, content_text: str,
                 remark_text: str, first_item_name: str = "",
                 on_save=None):
        self._title_text = title_text
        self._content_text_val = content_text
        self._remark_text = remark_text
        self._first_item_name = first_item_name
        self._label_var = tk.StringVar()
        self._reverse_var = tk.BooleanVar(value=bool(first_item_name))
        super().__init__(parent, "템플릿으로 저장", on_save=on_save)

    def _build_content(self, f: ttk.Frame):
        ttk.Label(f, text="별칭 *:").grid(
            row=0, column=0, sticky="w",
            pady=SPACING["sm"], padx=(0, SPACING["md"]))
        entry = ttk.Entry(f, textvariable=self._label_var, width=30)
        entry.grid(row=0, column=1, sticky="ew", pady=SPACING["sm"])
        entry.focus_set()

        # 미리보기
        preview = ttk.LabelFrame(f, text=" 저장될 내용 ", padding=SPACING["sm"])
        preview.grid(row=1, column=0, columnspan=2, sticky="ew",
                     pady=SPACING["sm"])
        ttk.Label(preview, text=f"기안제목: {self._title_text[:60]}",
                  wraplength=350).pack(anchor="w")
        content_preview = self._content_text_val[:80].replace("\n", " ")
        if len(self._content_text_val) > 80:
            content_preview += "..."
        ttk.Label(preview, text=f"내용: {content_preview}",
                  wraplength=350).pack(anchor="w")
        if self._remark_text:
            ttk.Label(preview, text=f"비고: {self._remark_text}",
                      wraplength=350).pack(anchor="w")

        # 역치환 체크박스
        if self._first_item_name:
            ttk.Checkbutton(
                f, text=f"'{self._first_item_name}' → {{{{품명}}}}으로 치환 (범용 템플릿)",
                variable=self._reverse_var
            ).grid(row=2, column=0, columnspan=2, sticky="w",
                   pady=(SPACING["sm"], 0))

        f.columnconfigure(1, weight=1)

    def _on_save(self):
        label = self._label_var.get().strip()
        if not label:
            messagebox.showwarning("입력 오류", "별칭을 입력하세요.", parent=self)
            return

        title = self._title_text
        content = self._content_text_val
        remark = self._remark_text

        # 역치환
        if self._reverse_var.get() and self._first_item_name:
            title = title.replace(self._first_item_name, "{{품명}}")
            content = content.replace(self._first_item_name, "{{품명}}")

        # 중복 검사
        existing = tpl_repo.select_by_label(label)
        if existing:
            if not messagebox.askyesno("중복 확인",
                    f"'{label}' 별칭이 이미 존재합니다.\n덮어쓰시겠습니까?",
                    parent=self):
                return
            tpl_repo.update(existing["id"], label, title, content, remark)
        else:
            tpl_repo.insert(label, title, content, remark)

        self._fire_save_callback()
        self.destroy()
