#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深圳市中小企业服务局通知公告抓取器
静态HTML页面，直接解析
"""

from datetime import datetime
from typing import List

from sz_gov_rss.fetcher_base import BaseFetcher
from sz_gov_rss.models import PolicyItem, FetchResult
from sz_gov_rss.utils import curl_fetch, parse_chinese_date, sanitize_text


class ZxqyjFetcher(BaseFetcher):
    """
    深圳市中小企业服务局
    URL: https://zxqyj.sz.gov.cn/zwgk/zfxxgkml/tzgg/
    """

    LIST_URL = "https://zxqyj.sz.gov.cn/zwgk/zfxxgkml/tzgg/"

    def __init__(self):
        super().__init__("深圳市中小企业服务局", self.LIST_URL)

    def fetch(self, max_items: int = 20) -> FetchResult:
        try:
            html = curl_fetch(self.LIST_URL, timeout=20)
            items = self._parse_html(html, max_items)
            self.enrich_items(items, selectors=[".TRS_Editor", ".news_cont_d_wrap", ".conter"])
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

        container = soup.find("div", class_="nei_listCont")
        if not container:
            container = soup

        for li in container.find_all("li"):
            a = li.find("a", href=True)
            span = li.find("span")
            if not a:
                continue

            title = sanitize_text(a.get_text())
            href = a.get("href", "").strip()
            if not title or not href:
                continue

            date_text = sanitize_text(span.get_text()) if span else ""
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

        return items
