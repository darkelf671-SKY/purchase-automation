"""디자인 시스템 — 컬러, 폰트, 간격, ttk 테마 설정 일원화"""
from tkinter import ttk

# ── 컬러 토큰 ──────────────────────────────────────────────────
COLORS = {
    # Primary (네이비 — 공공기관 신뢰감)
    "primary":        "#1A3A5C",
    "primary_light":  "#2A5F9E",
    "primary_dark":   "#0F2540",

    # Neutral
    "bg_window":      "#F4F6F8",
    "bg_surface":     "#FFFFFF",
    "border":         "#C8D3DD",
    "border_light":   "#E2E8F0",

    # Text
    "text_primary":   "#1A2332",
    "text_secondary": "#4A5568",
    "text_muted":     "#8A9BB0",

    # Semantic
    "total":          "#003A70",
    "success":        "#2E7D32",
    "danger":         "#B71C1C",
    "warning":        "#E65100",
    "info":           "#0072CE",

    # Treeview
    "row_even":       "#F7F9FC",
    "row_odd":        "#FFFFFF",
    "row_selected":   "#D6E4F0",

    # Tooltip
    "tooltip_bg":     "#1A2332",
    "tooltip_fg":     "#FFFFFF",
}

# ── 간격 체계 (8px 기반) ───────────────────────────────────────
SPACING = {
    "xs":  2,
    "sm":  4,
    "md":  8,
    "lg":  12,
    "xl":  16,
    "xxl": 24,
}

# ── 타이포그래피 ───────────────────────────────────────────────
FONT_FAMILY = "Malgun Gothic"

FONTS = {
    "small":     (FONT_FAMILY, 8),
    "body":      (FONT_FAMILY, 9),
    "body_bold": (FONT_FAMILY, 9, "bold"),
    "heading":   (FONT_FAMILY, 10, "bold"),
    "total":     (FONT_FAMILY, 11, "bold"),
    "title":     (FONT_FAMILY, 13, "bold"),
}

# ── 버튼 패딩 ─────────────────────────────────────────────────
BTN_PAD = {"padx": SPACING["md"], "pady": SPACING["sm"]}
BTN_PRIMARY_PAD = {"ipadx": 24, "ipady": 8}
BTN_ACTION_PAD = {"ipadx": 20, "ipady": 6}


def apply_theme(style: ttk.Style):
    """전역 ttk 테마 설정 — app.py에서 1회 호출"""
    style.theme_use("clam")

    # ── 전역 기본 ──────────────────────────────────────────────
    style.configure(".",
                    font=FONTS["body"],
                    background=COLORS["bg_window"],
                    foreground=COLORS["text_primary"],
                    borderwidth=0)

    # ── TFrame ─────────────────────────────────────────────────
    style.configure("TFrame", background=COLORS["bg_window"])
    style.configure("Surface.TFrame", background=COLORS["bg_surface"])

    # ── TLabel ─────────────────────────────────────────────────
    style.configure("TLabel",
                    background=COLORS["bg_window"],
                    foreground=COLORS["text_primary"])
    style.configure("Secondary.TLabel",
                    foreground=COLORS["text_secondary"])
    style.configure("Muted.TLabel",
                    foreground=COLORS["text_muted"])
    style.configure("Total.TLabel",
                    font=FONTS["total"],
                    foreground=COLORS["total"])
    style.configure("Heading.TLabel",
                    font=FONTS["heading"],
                    foreground=COLORS["primary"])
    style.configure("Info.TLabel",
                    foreground=COLORS["info"])
    style.configure("Success.TLabel",
                    foreground=COLORS["success"])

    # ── TEntry ─────────────────────────────────────────────────
    style.configure("TEntry",
                    fieldbackground=COLORS["bg_surface"],
                    borderwidth=1)
    style.map("TEntry",
              fieldbackground=[("focus", "#FFFFFF"), ("disabled", "#EAECEF")],
              bordercolor=[("focus", COLORS["primary_light"])])

    # ── TCombobox ──────────────────────────────────────────────
    style.configure("TCombobox",
                    fieldbackground=COLORS["bg_surface"])
    style.map("TCombobox",
              fieldbackground=[("disabled", "#EAECEF")])

    # ── TButton ────────────────────────────────────────────────
    style.configure("TButton",
                    font=FONTS["body"],
                    padding=(SPACING["md"], SPACING["sm"]))
    style.map("TButton",
              background=[("active", "#E2E8F0"), ("pressed", "#CBD5E0")],
              relief=[("pressed", "flat")])

    # Primary — 네이비 배경 + 흰 텍스트
    style.configure("Primary.TButton",
                    font=FONTS["body_bold"],
                    background=COLORS["primary"],
                    foreground="#FFFFFF",
                    padding=(SPACING["xl"], SPACING["md"]))
    style.map("Primary.TButton",
              background=[("active", COLORS["primary_light"]),
                          ("pressed", COLORS["primary_dark"]),
                          ("disabled", "#A0AEC0")],
              foreground=[("disabled", "#FFFFFF")])

    # Danger — 빨강 텍스트
    style.configure("Danger.TButton",
                    foreground=COLORS["danger"])
    style.map("Danger.TButton",
              foreground=[("active", "#D32F2F")],
              background=[("active", "#FFEBEE")])

    # Small — 인라인 삭제 버튼
    style.configure("Small.TButton",
                    font=(FONT_FAMILY, 8),
                    padding=(SPACING["sm"], 0))

    # ── TNotebook ──────────────────────────────────────────────
    style.configure("TNotebook",
                    background=COLORS["bg_window"],
                    borderwidth=0)
    style.configure("TNotebook.Tab",
                    font=FONTS["body"],
                    padding=[SPACING["lg"], SPACING["md"]],
                    background="#E2E8F0",
                    foreground=COLORS["text_secondary"])
    style.map("TNotebook.Tab",
              background=[("selected", COLORS["bg_surface"])],
              foreground=[("selected", COLORS["primary"])],
              font=[("selected", FONTS["body_bold"])])

    # ── Treeview ───────────────────────────────────────────────
    style.configure("Treeview",
                    font=FONTS["body"],
                    rowheight=26,
                    fieldbackground=COLORS["bg_surface"],
                    background=COLORS["bg_surface"],
                    borderwidth=1)
    style.configure("Treeview.Heading",
                    font=FONTS["body_bold"],
                    background="#E2E8F0",
                    foreground=COLORS["primary"],
                    borderwidth=1,
                    relief="flat")
    style.map("Treeview",
              background=[("selected", COLORS["row_selected"])],
              foreground=[("selected", COLORS["text_primary"])])

    # ── TLabelframe ────────────────────────────────────────────
    style.configure("TLabelframe",
                    background=COLORS["bg_window"],
                    bordercolor=COLORS["border"],
                    borderwidth=1,
                    relief="solid")
    style.configure("TLabelframe.Label",
                    font=FONTS["body_bold"],
                    foreground=COLORS["primary"],
                    background=COLORS["bg_window"])

    # Card 스타일 — 상세 패널 카드형 그룹
    style.configure("Card.TFrame",
                    background=COLORS["row_even"],
                    relief="groove",
                    borderwidth=1)
    style.configure("Card.TLabel",
                    background=COLORS["row_even"],
                    foreground=COLORS["text_primary"])
    style.configure("CardKey.TLabel",
                    background=COLORS["row_even"],
                    foreground=COLORS["text_secondary"],
                    font=FONTS["body_bold"])
    style.configure("CardVal.TLabel",
                    background=COLORS["row_even"],
                    foreground=COLORS["text_primary"],
                    font=FONTS["body"])
    style.configure("CardValInfo.TLabel",
                    background=COLORS["row_even"],
                    foreground=COLORS["info"],
                    font=FONTS["body_bold"])
    style.configure("CardTitle.TLabel",
                    background=COLORS["row_even"],
                    foreground=COLORS["primary"],
                    font=FONTS["body_bold"])
    # Input Card — 흰 배경
    style.configure("InputCard.TFrame",
                    background=COLORS["bg_surface"],
                    relief="groove",
                    borderwidth=1)
    style.configure("InputCard.TLabel",
                    background=COLORS["bg_surface"],
                    foreground=COLORS["text_secondary"],
                    font=FONTS["body_bold"])
    style.configure("InputCardVal.TLabel",
                    background=COLORS["bg_surface"],
                    foreground=COLORS["text_primary"],
                    font=FONTS["body"])

    # ── TSeparator ─────────────────────────────────────────────
    style.configure("TSeparator",
                    background=COLORS["border_light"])

    # ── TCheckbutton / TRadiobutton ────────────────────────────
    style.configure("TCheckbutton",
                    background=COLORS["bg_window"])
    style.map("TCheckbutton",
              indicatorcolor=[("selected", COLORS["primary"]),
                              ("!selected", COLORS["bg_surface"])],
              indicatorrelief=[("selected", "flat"), ("!selected", "sunken")],
              background=[("active", COLORS["bg_window"])])
    style.configure("TRadiobutton",
                    background=COLORS["bg_window"])
    style.map("TRadiobutton",
              background=[("active", COLORS["bg_window"])])

    # ── TSpinbox ───────────────────────────────────────────────
    style.configure("TSpinbox",
                    fieldbackground=COLORS["bg_surface"])

    # ── TScrollbar ─────────────────────────────────────────────
    style.configure("TScrollbar",
                    background="#E2E8F0",
                    troughcolor=COLORS["bg_window"])


def configure_treeview_tags(tree):
    """Treeview 교대 행 색상 + 상태 태그 적용"""
    tree.tag_configure("evenrow", background=COLORS["row_even"])
    tree.tag_configure("oddrow",  background=COLORS["row_odd"])
    tree.tag_configure("complete", foreground=COLORS["info"])
    tree.tag_configure("partial",  foreground=COLORS["warning"])
    tree.tag_configure("missing",  foreground=COLORS["text_muted"])


def insert_with_alternating(tree, parent, index, **kwargs):
    """교대 행 색상이 적용된 insert"""
    existing = len(tree.get_children(parent))
    tag = "evenrow" if existing % 2 == 0 else "oddrow"
    tags = kwargs.get("tags", ())
    if isinstance(tags, str):
        tags = (tags,)
    kwargs["tags"] = (tag,) + tuple(tags)
    return tree.insert(parent, index, **kwargs)
