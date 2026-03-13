import os
import sys
import json
from pathlib import Path

# PyInstaller --onefile 대응
# 번들 리소스(템플릿 등 읽기전용) → _MEIPASS 임시폴더
# 사용자 데이터(DB, 출력물 등 쓰기) → exe 옆 or 소스 폴더
if getattr(sys, 'frozen', False):
    # PyInstaller 빌드된 exe 실행 중
    _BUNDLE_DIR = Path(sys._MEIPASS)          # 읽기전용 리소스
    _APP_DIR    = Path(sys.executable).parent  # exe 위치 (쓰기 가능)
else:
    # 일반 python 실행
    _BUNDLE_DIR = Path(__file__).parent
    _APP_DIR    = Path(__file__).parent

BASE_DIR = _APP_DIR
DATA_DIR = _APP_DIR / "data"
SCREENSHOT_DIR = DATA_DIR / "screenshots"
OUTPUT_DIR = DATA_DIR / "outputs"
DB_PATH = DATA_DIR / "purchase.db"
TEMPLATE_DIR = _BUNDLE_DIR / "documents" / "templates"
GUIDE_DIR = _BUNDLE_DIR / "docs" / "manual"

NAVER_SHOPPING_API_URL = "https://openapi.naver.com/v1/search/shop.json"

# 기본 제외 키워드
DEFAULT_EXCLUDE_KEYWORDS = [
    "스킨", "커버", "케이스", "파우치", "보호필름", "필름",
    "거치대", "스티커", "청소", "수리", "부품", "악세사리",
    "악세서리", "호환", "교체", "수납", "파우치",
]

# 반자동화 사이트 URL (검색어 포함)
SITE_SEARCH_URLS = {
    "naver":    "https://search.shopping.naver.com/search/all?query={query}",
    "coupang":  "https://www.coupang.com/np/search?q={query}",
    "lotteon":  "https://www.lotteon.com/csearch/search/search?render=search&platform=pc&q={query}&mallId=1",
    "gmarket":  "https://browse.gmarket.co.kr/search?keyword={query}",
    "auction":  "https://www.auction.co.kr/n/search?keyword={query}",
    "s2b":      "https://www.s2b.kr/L2BNCustomer/L2B/scrweb/remu/rema/searchengine/s2bCustomerSearch.jsp?actionType=MAIN_SEARCH&searchField=&startIndex=&viewCount=50&viewType=LIST&sortField=RANK&priceMin=0&priceMax=0&priceMinSet=0&priceMaxSet=0&categoryLevel1Code=&categoryLevel2Code=&categoryLevel3Code=&categoryLevel3Name=&areaCode=&categoryWinStatus=none&companyCodeParam=&priceNewSet=true&publicPurchaseCode=&f_edufine_code=&submit_yn=Y&searchQuery={query}&searchRequery=&locationGbn=all",
}

# 앱 설정
# 결제방법 상수 (중앙 관리)
PAYMENT_METHODS = {
    "card":          "법인카드 결제",
    "transfer":      "무통장입금",
    "auto_transfer": "자동 이체 납부",
}

APP_TITLE   = "구매기안 자동화 시스템"
APP_VERSION = "v1.0"
APP_AUTHOR  = "전산팀 장길섭"
APP_WIDTH   = 920
APP_HEIGHT  = 760

# 폴더 초기화
for d in [DATA_DIR, SCREENSHOT_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# PyInstaller: 첫 실행 시 시드 DB 복사 (업체/수의계약/기안템플릿 데이터 포함)
if getattr(sys, 'frozen', False) and not DB_PATH.exists():
    import shutil
    _seed = _BUNDLE_DIR / "data" / "seed.db"
    if _seed.exists():
        shutil.copy2(str(_seed), str(DB_PATH))


def get_output_dir() -> Path:
    """설정된 출력 폴더 반환 (없거나 존재하지 않으면 기본값 사용)"""
    custom = load_settings().get("output_dir", "")
    if custom:
        p = Path(custom)
        p.mkdir(parents=True, exist_ok=True)
        return p
    return OUTPUT_DIR


def set_output_dir(path: str) -> None:
    """출력 폴더 경로를 settings.json에 저장"""
    s = load_settings()
    s["output_dir"] = str(path)
    save_settings(s)


def make_output_dir(item_name: str) -> Path:
    """구매건별 산출 폴더 생성 후 반환. 예: {출력폴더}/20260306_노트북/"""
    from datetime import datetime
    base = get_output_dir()
    safe_name = item_name.replace("/", "_").replace("\\", "_").strip()
    folder = base / f"{datetime.now().strftime('%Y%m%d')}_{safe_name}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def make_output_dir_named(folder_name: str) -> Path:
    """지정한 이름으로 출력 폴더 생성. 이미 존재하면 FileExistsError 발생."""
    base = get_output_dir()
    safe = folder_name.replace("/", "_").replace("\\", "_").replace(":", "_").strip()
    folder = base / safe
    if folder.exists():
        raise FileExistsError(safe)
    folder.mkdir(parents=True, exist_ok=False)
    return folder

# 설정 파일 (API 키 등 저장)
_SETTINGS_PATH = DATA_DIR / "settings.json"


def load_settings() -> dict:
    if _SETTINGS_PATH.exists():
        try:
            return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_settings(data: dict) -> None:
    _SETTINGS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_department() -> str:
    """설정된 부서명 반환"""
    return load_settings().get("department", "")


def set_department(value: str) -> None:
    """부서명을 settings.json에 저장"""
    s = load_settings()
    s["department"] = value
    save_settings(s)


def get_inspector() -> str:
    """설정된 검수자 반환"""
    return load_settings().get("inspector", "")


def set_inspector(value: str) -> None:
    s = load_settings()
    s["inspector"] = value
    save_settings(s)


def get_witness() -> str:
    """설정된 입회자 반환"""
    return load_settings().get("witness", "")


def set_witness(value: str) -> None:
    s = load_settings()
    s["witness"] = value
    save_settings(s)


def get_gemini_api_key() -> str:
    """설정된 Gemini API 키 반환"""
    return load_settings().get("gemini_api_key", "")


def set_gemini_api_key(value: str) -> None:
    """Gemini API 키를 settings.json에 저장"""
    s = load_settings()
    s["gemini_api_key"] = value
    save_settings(s)


def open_gemini_guide() -> bool:
    """Gemini API 키 발급 가이드 HTML을 기본 브라우저로 열기"""
    import webbrowser
    guide_path = GUIDE_DIR / "gemini-api-key-guide.html"
    if guide_path.exists():
        webbrowser.open(str(guide_path))
        return True
    return False


_s = load_settings()
NAVER_CLIENT_ID     = _s.get("naver_client_id")     or os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = _s.get("naver_client_secret") or os.environ.get("NAVER_CLIENT_SECRET", "")
