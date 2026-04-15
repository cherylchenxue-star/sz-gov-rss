#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深圳市工信局政策抓取器
直接调用 postmeta JSON API 获取政策法规数据
"""

from datetime import datetime
from typing import List

from sz_gov_rss.fetcher_base import BaseFetcher
from sz_gov_rss.models import PolicyItem, FetchResult
from sz_gov_rss.utils import curl_fetch_json, parse_chinese_date, sanitize_text


class GxjFetcher(BaseFetcher):
    """
    深圳市工业和信息化局
    URL: https://gxj.sz.gov.cn/xxgk/xxgkml/zcfgjzcjd/
    API: https://gxj.sz.gov.cn/postmeta/i/61057.json
    """

    API_URL = "https://gxj.sz.gov.cn/postmeta/i/61057.json"

    def __init__(self):
        super().__init__("深圳市工信局", "https://gxj.sz.gov.cn/")

    def fetch(self, max_items: int = 20) -> FetchResult:
        try:
            data = curl_fetch_json(self.API_URL, timeout=20)
            articles = data.get("articles", [])

            items: List[PolicyItem] = []
            for article in articles[:max_items]:
                item = self._parse_article(article)
                if item:
                    items.append(item)

            self.enrich_items(items, selectors=[".TRS_Editor", ".content"])

            return FetchResult(
                source_name=self.source_name,
                items=items,
                success=True,
                fetched_count=len(items),
            )
        except Exception as e:
            return FetchResult(
                source_name=self.source_name,
                success=False,
                error_message=str(e),
            )

    def _parse_article(self, article: dict) -> PolicyItem:
        title = sanitize_text(article.get("title", ""))
        link = article.get("url", "")
        if not link:
            link = f"https://gxj.sz.gov.cn/xxgk/xxgkml/zcfgjzcjd/content/post_{article.get('id')}.html"

        date_str = article.get("date", "")
        pub_date = parse_chinese_date(date_str)
        if pub_date is None:
            pub_date = datetime.now()

        summary = sanitize_text(article.get("abstract", ""))

        return PolicyItem(
            title=title,
            link=link,
            pub_date=pub_date,
            source=self.source_name,
            summary=summary,
        )
