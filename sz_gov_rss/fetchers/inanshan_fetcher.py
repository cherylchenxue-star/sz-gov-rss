#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南山区企业服务平台（Ai南山）抓取器
Vue SPA，需用Playwright渲染
"""

import re
from datetime import datetime
from typing import List

from sz_gov_rss.fetcher_base import BaseFetcher
from sz_gov_rss.models import PolicyItem, FetchResult
from sz_gov_rss.utils import parse_chinese_date, sanitize_text

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class InanshanFetcher(BaseFetcher):
    """
    南山区企业服务综合平台 - 找政策
    URL: https://www.inanshan.org.cn/ztfw/zcfw/zchj
    该页面为Vue SPA，政策列表无独立详情链接，点击后仅展示摘要。
    RSS链接指向平台找政策页面本身。
    """

    LANDING_URL = "https://www.inanshan.org.cn/ztfw/zcfw/zchj"
    # 点击"查看更多"后的实际列表页
    LIST_URL = "https://www.inanshan.org.cn/ztfw/zcfw/zchj/zchjmore?typeId=18&parentId=enRmdy16Y2Z3LXpjaGo%3D"

    def __init__(self):
        super().__init__("南山区企业服务", self.LANDING_URL)

    def fetch(self, max_items: int = 20) -> FetchResult:
        if sync_playwright is None:
            return FetchResult(
                source_name=self.source_name,
                success=False,
                error_message="未安装 playwright，请先执行: pip install playwright && python -m playwright install chromium",
            )

        try:
            items = self._fetch_with_playwright(max_items)
            # 无独立详情页，仅自动打标签
            self.enrich_items(items, selectors=[])
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

            # 先访问找政策页面，再点击"查看更多"进入完整列表
            page.goto(self.LANDING_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            # 尝试点击"查看更多"按钮
            more_btn = page.query_selector(".more")
            if more_btn:
                more_btn.click()
                page.wait_for_timeout(3000)

            html = page.content()
            items = self._parse_html(html, max_items)

            browser.close()

        return items

    def _parse_html(self, html: str, max_items: int) -> List[PolicyItem]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        items: List[PolicyItem] = []

        policy_items = soup.find_all("div", class_="policy_item")
        for item in policy_items:
            # 标题
            title_div = item.find("div", class_="left_top_content")
            if not title_div:
                continue

            title = sanitize_text(title_div.get_text())
            if not title:
                continue

            # 日期：从 .bottom_time 提取（可能是 div）
            date_div = item.find(class_=lambda x: x and "bottom_time" in x)
            date_text = ""
            if date_div:
                date_text = sanitize_text(date_div.get_text())
                # 格式通常为 "发布时间：2025-11-20"
                match = re.search(r"(\d{4}-\d{2}-\d{2})", date_text)
                if match:
                    date_text = match.group(1)

            pub_date = parse_chinese_date(date_text)
            if pub_date is None:
                pub_date = datetime.now()

            # 来源（发布部门）：找只有 bottom_title 没有 bottom_time 的 div
            source_div = item.find("div", class_=lambda x: x and "bottom_title" in x and "bottom_time" not in x)
            source_text = ""
            if source_div:
                source_clone = BeautifulSoup(str(source_div), "html.parser").find("div", class_="bottom_title")
                for span in source_clone.find_all("span"):
                    span.decompose()
                source_text = sanitize_text(source_clone.get_text())
                source_text = source_text.replace("发布机构：", "").replace("发布机构:", "").strip()

            items.append(
                PolicyItem(
                    title=title,
                    link=self.LANDING_URL,
                    pub_date=pub_date,
                    source=source_text or self.source_name,
                    summary="",
                )
            )

            if len(items) >= max_items:
                break

        return items
