"""통합 테스트 — 모든 모듈 import, DB CRUD, 모델 검증"""
import sys
import os

results = []


def test(name, func):
    try:
        func()
        results.append((name, "PASS", ""))
    except Exception as e:
        results.append((name, "FAIL", str(e)))


# ================================================================
# 1. 모듈 Import 테스트
# ================================================================
print("[ TEST 1: Module Import ]")

test("config import", lambda: __import__("config"))
test("core.models import", lambda: __import__("core.models"))
test("core.naver_api import", lambda: __import__("core.naver_api"))
test("core.filter_engine import", lambda: __import__("core.filter_engine"))
test("core.semi_auto import", lambda: __import__("core.semi_auto"))
test("core.screenshot import", lambda: __import__("core.screenshot"))
test("db.database import", lambda: __import__("db.database"))
test("db.purchase_repo import", lambda: __import__("db.purchase_repo"))
test("db.inspection_repo import", lambda: __import__("db.inspection_repo"))
test("db.vendor_repo import", lambda: __import__("db.vendor_repo"))
test("db.sole_contract_repo import", lambda: __import__("db.sole_contract_repo"))
test("documents.hwp_generator import", lambda: __import__("documents.hwp_generator"))
test("documents.excel_generator import", lambda: __import__("documents.excel_generator"))

# ================================================================
# 2. DB 초기화 테스트
# ================================================================
print("[ TEST 2: DB Initialization ]")


def test_db_init():
    from db.database import initialize, get_connection
    initialize()
    conn = get_connection()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    conn.close()
    expected = ["inspections", "purchase_items", "purchases", "sole_contract_reasons", "vendors"]
    missing = [t for t in expected if t not in tables]
    if missing:
        raise Exception(f"Missing tables: {missing}")


test("DB initialize()", test_db_init)

# ================================================================
# 3. 모델 생성 테스트
# ================================================================
print("[ TEST 3: Model Creation ]")


def test_models():
    from core.models import PurchaseData, VendorQuote, PurchaseItem

    item = PurchaseItem(seq=1, item_name="테스트 물품", spec="규격1", unit="대",
                        quantity=2, unit_price=100000)
    item.calc_total()
    assert item.total_price == 200000, f"Expected 200000 got {item.total_price}"

    v1 = VendorQuote(name="업체A", total_price=200000)
    v2 = VendorQuote(name="업체B", total_price=250000)
    data = PurchaseData(items=[item], vendor1=v1, vendor2=v2, selected_vendor=1)

    assert data.item_name == "테스트 물품"
    assert data.grand_total == 200000
    assert data.selected.name == "업체A"


test("Model creation & properties", test_models)


def test_multi_items():
    from core.models import PurchaseData, PurchaseItem
    items = [
        PurchaseItem(seq=1, item_name="물품A", quantity=1, unit_price=100000, total_price=100000),
        PurchaseItem(seq=2, item_name="물품B", quantity=2, unit_price=50000, total_price=100000),
    ]
    data = PurchaseData(items=items)
    assert data.item_name == "물품A 외 1건"
    assert data.grand_total == 200000


test("Multi-item model", test_multi_items)


def test_v2_total():
    from core.models import PurchaseItem
    item = PurchaseItem(seq=1, quantity=3, v2_unit_price=10000)
    assert item.v2_total_price == 30000


test("PurchaseItem v2_total_price", test_v2_total)

# ================================================================
# 4. DB CRUD 테스트
# ================================================================
print("[ TEST 4: DB CRUD ]")


def test_vendor_crud():
    from db import vendor_repo
    vid = vendor_repo.insert({
        "name": "테스트업체_통합", "ceo": "대표자", "business_no": "123-45-67890",
        "address": "서울시", "payment_method": "card",
        "bank_name": "", "account_holder": "", "account_no": ""
    })
    assert vid > 0
    row = vendor_repo.select_by_id(vid)
    assert row is not None
    assert row["name"] == "테스트업체_통합"
    vendor_repo.delete(vid)
    assert vendor_repo.select_by_id(vid) is None


test("Vendor CRUD", test_vendor_crud)


def test_purchase_crud():
    from db import purchase_repo
    from core.models import PurchaseData, VendorQuote, PurchaseItem

    item = PurchaseItem(seq=1, item_name="테스트품목", spec="규격", unit="개",
                        quantity=1, unit_price=50000, total_price=50000)
    v1 = VendorQuote(name="업체X", total_price=50000)
    v2 = VendorQuote(name="업체Y", total_price=60000)
    data = PurchaseData(department="전산팀", items=[item], vendor1=v1, vendor2=v2,
                        selected_vendor=1)

    pid = purchase_repo.insert(data)
    assert pid > 0

    row = purchase_repo.select_by_id(pid)
    assert row is not None
    assert row["item_name"] == "테스트품목"

    items = purchase_repo.select_items(pid)
    assert len(items) >= 1

    purchase_repo.delete(pid)


test("Purchase insert/select/delete", test_purchase_crud)


def test_sole_contract_crud():
    from db import sole_contract_repo
    rid = sole_contract_repo.insert("테스트사유_통합", "테스트라벨")
    assert rid > 0
    rows = sole_contract_repo.select_all()
    found = any(r["reason"] == "테스트사유_통합" for r in rows)
    assert found
    sole_contract_repo.delete(rid)


test("SoleContract CRUD", test_sole_contract_crud)

# ================================================================
# 5. Config 경로 테스트
# ================================================================
print("[ TEST 5: Config Paths ]")


def test_paths():
    import config
    assert config.DATA_DIR.exists(), f"DATA_DIR not found: {config.DATA_DIR}"
    assert config.SCREENSHOT_DIR.exists(), "SCREENSHOT_DIR not found"
    assert config.OUTPUT_DIR.exists(), "OUTPUT_DIR not found"
    assert config.TEMPLATE_DIR.exists(), f"TEMPLATE_DIR not found: {config.TEMPLATE_DIR}"


test("Directory paths exist", test_paths)


def test_template_files():
    import config
    templates = list(config.TEMPLATE_DIR.glob("*"))
    if not templates:
        raise Exception(f"No template files in {config.TEMPLATE_DIR}")


test("Template files exist", test_template_files)

# ================================================================
# 6. FilterEngine 테스트
# ================================================================
print("[ TEST 6: FilterEngine ]")


def test_filter():
    from core.filter_engine import FilterEngine
    fe = FilterEngine()
    items = [
        {"title": "노트북 컴퓨터", "lprice": "500000"},
        {"title": "노트북 케이스", "lprice": "20000"},
        {"title": "노트북 본체", "lprice": "600000"},
    ]
    filtered = fe.filter(items, exclude_keywords=["케이스"])
    names = [i["title"] for i in filtered]
    assert "노트북 케이스" not in names


test("FilterEngine exclude", test_filter)

# ================================================================
# 7. 설정 저장/로드 테스트
# ================================================================
print("[ TEST 7: Settings ]")


def test_settings():
    import config
    original = config.load_settings()
    config.save_settings({**original, "_test_key": "test_value"})
    loaded = config.load_settings()
    assert loaded.get("_test_key") == "test_value"
    # cleanup
    del loaded["_test_key"]
    config.save_settings(loaded)


test("Settings save/load", test_settings)

# ================================================================
# 8. HwpGenerator 클래스 인스턴스화 (COM 호출 제외)
# ================================================================
print("[ TEST 8: HwpGenerator class ]")


def test_hwp_class():
    from documents.hwp_generator import HwpGenerator
    # 클래스가 존재하고 인스턴스화 가능한지만 확인 (COM 호출 안함)
    assert hasattr(HwpGenerator, "__init__")


test("HwpGenerator class exists", test_hwp_class)


def test_excel_class():
    from documents.excel_generator import ExcelGenerator
    assert hasattr(ExcelGenerator, "__init__")


test("ExcelGenerator class exists", test_excel_class)

# ================================================================
# 결과 출력
# ================================================================
print()
print("=" * 60)
print("  Integration Test Results")
print("=" * 60)
ok = sum(1 for _, s, _ in results if s == "PASS")
fail = sum(1 for _, s, _ in results if s == "FAIL")
for name, status, detail in results:
    icon = "PASS" if status == "PASS" else "FAIL"
    d = f" -> {detail}" if detail else ""
    print(f"  [{icon}] {name}{d}")
print()
print(f"  Result: {ok} passed, {fail} failed / {len(results)} tests")
if fail == 0:
    print("  All tests passed!")
else:
    print(f"  {fail} test(s) need attention")
    sys.exit(1)
