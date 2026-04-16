#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
广东省统一政府信息公开平台抓取器
覆盖：南山区工信局/科创局/企业服务中心、深圳市科技创新局等使用同模板的站点
"""

import sys
from datetime import datetime
from typing import List, Optional

from sz_gov_rss.fetcher_base import BaseFetcher
from sz_gov_rss.models import PolicyItem, FetchResult
from sz_gov_rss.utils import parse_chinese_date, sanitize_text

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class SznsFetcher(BaseFetcher):
    """
    广东省统一政府信息公开平台（gkmlpt模板）
    页面为SPA，需用Playwright渲染后从表格中提取列表
    """

    def __init__(self, source_name: str, list_url: str):
        super().__init__(source_name, list_url)
        self.list_url = list_url

    def fetch(self, max_items: int = 20) -> FetchResult:
        if sync_playwright is None:
            return FetchResult(
                source_name=self.source_name,
                success=False,
                error_message="未安装 playwright，请先执行: pip install playwright && python -m playwright install chromium",
            )

        try:
            items = self._fetch_with_playwright(max_items)
            self.enrich_items(items, selectors=[".article-content", ".content", ".TRS_Editor"])
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

    def _fetch_with_playwright(self, max_items: int) -> List[PolicyItem]:
        items: List[PolicyItem] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            # 拦截图片/CSS/字体加速加载
            page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf,eot,ico}", lambda route: route.abort())

            page.goto(self.list_url, wait_until="domcontentloaded", timeout=60000)
            # 等待JS渲染表格内容
            page.wait_for_timeout(4000)

            html = page.content()
            items = self._parse_html(html, max_items)

            browser.close()

        return items

    def _parse_html(self, html: str, max_items: int) -> List[PolicyItem]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        items: List[PolicyItem] = []

        # 查找包含文章链接的表格行
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue

            link_td = tds[0]
            link_a = link_td.find("a", href=True)
            if not link_a:
                continue

            title = sanitize_text(link_a.get_text())
            href = link_a.get("href", "").strip()
            if not title or not href:
                continue

            date_text = sanitize_text(tds[1].get_text())
            pub_date = parse_chinese_date(date_text)
            if pub_date is None:
                pub_date = datetime.now()

            # 处理 // 开头的协议相对URL
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                from urllib.parse import urljoin
                href = urljoin(self.list_url, href)

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
