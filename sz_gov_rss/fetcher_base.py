#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取器抽象基类
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
import re
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

    def fetch_summary(self, url: str, selectors: List[str], timeout: int = 8, return_html: bool = False) -> str:
        """访问详情页并提取摘要"""
        from .utils import curl_fetch

        try:
            html = curl_fetch(url, timeout=timeout)
            if return_html:
                return html
            return self.extract_summary(html, selectors)
        except Exception:
            return ""

    def extract_pub_date(self, html: str) -> Optional[datetime]:
        """从详情页HTML中提取更精确的发布时间"""
        from bs4 import BeautifulSoup
        from .utils import parse_chinese_date

        soup = BeautifulSoup(html, "html.parser")

        # meta 标签
        for meta_name in ["article:published_time", "pubdate", "publishdate", "date"]:
            meta = soup.find("meta", attrs={"property": meta_name}) or soup.find("meta", attrs={"name": meta_name})
            if meta and meta.get("content"):
                dt = parse_chinese_date(meta["content"])
                if dt:
                    return dt

        # 常见日期容器
        for sel in [".date", ".time", ".pubdate", ".pub-date", ".publish-date", ".article-date", ".source"]:
            elem = soup.select_one(sel)
            if elem:
                dt = parse_chinese_date(elem.get_text(strip=True))
                if dt:
                    return dt

        # 全文正则扫描（优先带时间）
        text = soup.get_text()
        dt_match = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}\s+\d{2}:\d{2}(?::\d{2})?)", text)
        if dt_match:
            dt = parse_chinese_date(dt_match.group(1))
            if dt:
                return dt

        return None

    def enrich_items(self, items: List[PolicyItem], selectors: List[str]) -> None:
        """抓取详情页摘要并自动打标签"""
        for item in items:
            html = ""
            if not item.summary and selectors:
                html = self.fetch_summary(item.link, selectors, return_html=True)
                item.summary = self.extract_summary(html, selectors) if html else ""

            # 如果当前日期没有时分，尝试从详情页提取更精确的时间
            if item.pub_date.hour == 0 and item.pub_date.minute == 0:
                if not html and selectors:
                    html = self.fetch_summary(item.link, selectors, return_html=True)
                if html:
                    precise_date = self.extract_pub_date(html)
                    if precise_date:
                        item.pub_date = precise_date

            combined_text = f"{item.title} {item.summary}"
            item.tags = extract_industry_tags(combined_text)
