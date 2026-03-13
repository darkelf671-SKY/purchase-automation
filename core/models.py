from dataclasses import dataclass, field


@dataclass
class VendorQuote:
    name: str = ""
    unit_price: int = 0
    total_price: int = 0
    url: str = ""
    screenshot_path: str = ""


@dataclass
class PurchaseItem:
    """단일 품목 데이터 (1:N 구조)"""
    seq: int = 1
    item_name: str = ""
    spec: str = ""
    unit: str = "개"
    quantity: int = 1
    unit_price: int = 0       # 견적1(선정업체) 단가
    total_price: int = 0      # = unit_price × quantity
    v2_unit_price: int = 0    # 견적2(비교업체) 단가
    remark: str = ""
    price_input_mode: str = "unit"  # "unit" | "total" | "v1_total" | "v2_total"

    @property
    def v2_total_price(self) -> int:
        return self.v2_unit_price * self.quantity

    def calc_total(self) -> int:
        """견적1(선정업체) 합계 계산.

        price_input_mode별 동작:
        - "unit": 단가 × 수량 → total_price (기본)
        - "total", "v1_total": 총액 고정, 단가 역산 (total // quantity)
        - "v2_total": 견적2만 총액 모드 → 견적1은 단가×수량 (else 분기)

        주의: 견적2 합계는 v2_total_price 프로퍼티에서 별도 처리.
        """
        if self.price_input_mode in ("total", "v1_total"):
            # 견적1 총액 고정, 단가 역산
            if self.quantity > 0:
                self.unit_price = self.total_price // self.quantity
            return self.total_price
        else:
            # "unit" 또는 "v2_total" — 견적1은 단가 기준 계산
            self.total_price = self.unit_price * self.quantity
            return self.total_price


@dataclass
class PurchaseData:
    department: str = ""
    items: list = field(default_factory=list)   # list[PurchaseItem]
    vendor1: VendorQuote = field(default_factory=VendorQuote)
    vendor2: VendorQuote = field(default_factory=VendorQuote)
    selected_vendor: int = 1
    vat_mode: str = "inclusive"   # "exclusive"(입력가×1.1) | "inclusive"(입력가=VAT포함)
    draft_date: str = ""         # 기안일 (YYYY-MM-DD), 빈 문자열이면 오늘
    payment_method: str = ""     # "card" | "transfer" | "auto_transfer"
    payment_bank: str = ""       # 은행명
    payment_account: str = ""    # 계좌번호
    payment_holder: str = ""     # 예금주

    # ── 하위 호환 프로퍼티 ──────────────────────────────────────────
    @property
    def item_name(self) -> str:
        if not self.items:
            return ""
        if len(self.items) == 1:
            return self.items[0].item_name
        return f"{self.items[0].item_name} 외 {len(self.items) - 1}종"

    @property
    def spec(self) -> str:
        return self.items[0].spec if self.items else ""

    @property
    def unit(self) -> str:
        return self.items[0].unit if self.items else "개"

    @property
    def quantity(self) -> int:
        return self.items[0].quantity if self.items else 1

    @property
    def grand_total(self) -> int:
        return sum(item.total_price for item in self.items)

    @property
    def selected(self) -> VendorQuote:
        return self.vendor1 if self.selected_vendor == 1 else self.vendor2


@dataclass
class InspectionData:
    purchase: PurchaseData = field(default_factory=PurchaseData)
    inspection_date: str = ""
    inspector: str = ""
    witness: str = ""
    inspected_qty: int = 0
    has_defect: bool = False
    defect_note: str = ""
    remark: str = ""
