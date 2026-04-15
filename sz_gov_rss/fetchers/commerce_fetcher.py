#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深圳市商务局政策法规抓取器
静态HTML页面，直接解析
"""

from datetime import datetime
from typing import List

from sz_gov_rss.fetcher_base import BaseFetcher
from sz_gov_rss.models import PolicyItem, FetchResult
from sz_gov_rss.utils import curl_fetch, parse_chinese_date, sanitize_text


class CommerceFetcher(BaseFetcher):
    """
    深圳市商务局
    URL: https://commerce.sz.gov.cn/xxgk/zcfgjzcjd/zcfg/
    """

    LIST_URL = "https://commerce.sz.gov.cn/xxgk/zcfgjzcjd/zcfg/"

    def __init__(self):
        super().__init__("深圳市商务局", self.LIST_URL)

    def fetch(self, max_items: int = 20) -> FetchResult:
        try:
            html = curl_fetch(self.LIST_URL, timeout=20)
            items = self._parse_html(html, max_items)
            self.enrich_items(items, selectors=[".acontent", ".pagecontent", ".articbox"])
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

    def _parse_html(self, html: str, max_items: int) -> List[PolicyItem]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        items: List[PolicyItem] = []

        # 找到包含文章链接的正确ul
        for ul in soup.find_all("ul"):
            article_links = [a for a in ul.find_all("a", href=True) if "post_" in a.get("href", "")]
            if len(article_links) < 3:
                continue

            for li in ul.find_all("li"):
                title_span = li.find("span", class_="lb_title")
                date_span = li.find("span", class_="lb_date")
                if not title_span:
                    continue

                a = title_span.find("a", href=True)
                if not a:
                    continue

                title = sanitize_text(a.get_text())
                href = a.get("href", "").strip()
                if not title or not href:
                    continue

                date_text = sanitize_text(date_span.get_text()) if date_span else ""
                pub_date = parse_chinese_date(date_text)
                if pub_date is None:
                    pub_date = datetime.now()

                href = self.build_absolute_url(href)

                items.append(
                    PolicyItem(
                        title=title,
                        link=href,
                        pub_date=pub_date,
                        source=self.source_name,
                    )
                )

                if len(items) >= max_items:
                    break

            break  # 只处理第一个符合条件的ul

        return items
