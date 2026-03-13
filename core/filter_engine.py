from config import DEFAULT_EXCLUDE_KEYWORDS


class FilterEngine:
    def filter(
        self,
        items: list[dict],
        exclude_keywords: list[str] | None = None,
        min_price: int = 0,
        max_price: int = 0,
    ) -> list[dict]:
        excludes = exclude_keywords if exclude_keywords is not None else DEFAULT_EXCLUDE_KEYWORDS
        result = []
        for item in items:
            title = item.get("title", "")
            price = item.get("lprice", 0)

            # 제외 키워드 필터
            if any(kw in title for kw in excludes):
                continue

            # 가격 범위 필터 (0이면 제한 없음)
            if min_price > 0 and price < min_price:
                continue
            if max_price > 0 and price > max_price:
                continue

            result.append(item)

        return result

    def parse_exclude_keywords(self, text: str) -> list[str]:
        """쉼표 구분 문자열 → 리스트"""
        return [kw.strip() for kw in text.split(",") if kw.strip()]
