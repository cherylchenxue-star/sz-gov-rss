#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数：HTTP请求、日期解析、URL处理、标签提取
"""

import subprocess
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List


def curl_fetch(url: str, timeout: int = 20, follow_redirects: bool = True) -> str:
    """使用curl获取URL内容（绕过Python SSL问题）"""
    cmd = ["curl", "-s", "-k", "--max-time", str(timeout)]
    if follow_redirects:
        cmd.append("-L")
    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")
    return result.stdout


def curl_fetch_json(url: str, timeout: int = 20) -> Dict[str, Any]:
    """使用curl获取JSON数据"""
    text = curl_fetch(url, timeout=timeout)
    return json.loads(text)


def parse_chinese_date(date_str: str) -> Optional[datetime]:
    """解析多种中文日期格式"""
    if not date_str:
        return None

    date_str = date_str.strip()
    patterns = [
        (r"(\d{4})-(\d{2})-(\d{2})", lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (r"(\d{4})/(\d{2})/(\d{2})", lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (r"(\d{4})年(\d{1,2})月(\d{1,2})日", lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
    ]

    for pattern, builder in patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                return builder(match)
            except ValueError:
                continue
    return None


def build_absolute_url(base_url: str, href: str) -> str:
    """构建绝对URL"""
    from urllib.parse import urljoin
    return urljoin(base_url, href)


def sanitize_text(text: str) -> str:
    """清理文本中的多余空白"""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def truncate_text(text: str, max_len: int = 300) -> str:
    """截断文本到指定长度，保留完整句子"""
    if not text:
        return ""
    text = sanitize_text(text)
    if len(text) <= max_len:
        return text
    for punct in "。！？":
        idx = text.rfind(punct, 0, max_len)
        if idx > max_len * 0.5:
            return text[: idx + 1]
    return text[:max_len] + "…"


# 智能分类标签词库
INDUSTRY_KEYWORDS = {
    "技术领域": [
        "人工智能", "大模型", "算力", "算法", "智能计算", "智算中心", "数据要素",
    ],
    "企业资质": [
        "专精特新", "小巨人", "瞪羚", "独角兽", "中小企业", "营利性服务",
    ],
    "资金支持": [
        "产业扶持", "专项资金", "补贴", "退税", "入库",
    ],
    "人才与项目": [
        "人才引进", "高层次人才", "揭榜挂帅", "研发投入",
    ],
    "行业动态": [
        "领航", "高成长性", "增长率",
    ],
}


def extract_industry_tags(text: str) -> List[str]:
    """基于关键词匹配提取行业/分类标签"""
    if not text:
        return []
    tags = []
    for category, keywords in INDUSTRY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                tags.append(category)
                break
    return tags
