#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取器抽象基类
"""

from abc import ABC, abstractmethod
from typing import List
from .models import PolicyItem, FetchResult
from .utils import extract_industry_tags


class BaseFetcher(ABC):
    """政策抓取器基类"""

    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url

    @abstractmethod
    def fetch(self, max_items: int = 20) -> FetchResult:
        """抓取政策列表"""
        pass

    def build_absolute_url(self, href: str) -> str:
        """构建绝对URL"""
        from urllib.parse import urljoin
        return urljoin(self.base_url, href)

    def extract_summary(self, html: str, selectors: List[str]) -> str:
        """从HTML中提取正文摘要"""
        from bs4 import BeautifulSoup
        from .utils import truncate_text, sanitize_text

        soup = BeautifulSoup(html, "html.parser")
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                text = sanitize_text(elem.get_text(separator=" ", strip=True))
                return truncate_text(text, max_len=300)
        return ""

    def fetch_summary(self, url: str, selectors: List[str], timeout: int = 8) -> str:
        """访问详情页并提取摘要"""
        from .utils import curl_fetch

        try:
            html = curl_fetch(url, timeout=timeout)
            return self.extract_summary(html, selectors)
        except Exception:
            return ""

    def enrich_items(self, items: List[PolicyItem], selectors: List[str]) -> None:
        """抓取详情页摘要并自动打标签"""
        for item in items:
            if not item.summary and selectors:
                item.summary = self.fetch_summary(item.link, selectors)
            combined_text = f"{item.title} {item.summary}"
            item.tags = extract_industry_tags(combined_text)
