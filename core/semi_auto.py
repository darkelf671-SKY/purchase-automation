import webbrowser
from urllib.parse import quote
from config import SITE_SEARCH_URLS
from core.screenshot import capture


class SemiAutoHelper:
    SITE_NAMES = {
        "naver":    "네이버쇼핑",
        "coupang":  "쿠팡",
        "lotteon":  "롯데온",
        "gmarket":  "G마켓",
        "auction":  "옥션",
        "s2b":      "S2B(학교장터)",
    }

    def open_site(self, site: str, query: str = "") -> str:
        """해당 사이트를 기본 브라우저로 열기, 열린 사이트명 반환"""
        url_template = SITE_SEARCH_URLS.get(site, "")
        if not url_template:
            raise ValueError(f"알 수 없는 사이트: {site}")

        if site == "s2b":
            encoded = quote(query, encoding="euc-kr")
        else:
            encoded = quote(query)
        url = url_template.format(query=encoded)
        webbrowser.open(url)
        return self.SITE_NAMES.get(site, site)

    def capture_screen(self, save_path=None) -> str:
        """현재 화면 캡처 후 저장 경로 반환"""
        return capture(save_path=save_path)
