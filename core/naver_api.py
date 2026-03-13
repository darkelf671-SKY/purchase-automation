import requests
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_SHOPPING_API_URL


class NaverShoppingAPI:
    def __init__(self):
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def search(self, query: str, display: int = 20, sort: str = "asc") -> list[dict]:
        """
        네이버 쇼핑 검색 API 호출
        sort: asc=가격낮은순, sim=정확도순
        반환: [{"title", "lprice", "mallName", "link", "image", "category3"}, ...]
        """
        if not self.is_configured():
            raise ValueError("네이버 API 키가 설정되지 않았습니다. config.py를 확인하세요.")

        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        params = {
            "query": query,
            "display": display,
            "sort": sort,
        }
        resp = requests.get(NAVER_SHOPPING_API_URL, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])

        # HTML 태그 제거
        import re
        for item in items:
            item["title"] = re.sub(r"<[^>]+>", "", item.get("title", ""))
            item["lprice"] = int(item.get("lprice", 0))

        return items
