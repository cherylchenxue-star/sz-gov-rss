#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 PolicyItem 列表转换为 RSS 2.0 XML
"""

from datetime import datetime, timezone, timedelta
from typing import List

from .models import PolicyItem


def build_rss(items: List[PolicyItem], title: str = "深圳政策RSS聚合", link: str = "") -> str:
    """构建RSS 2.0 XML"""
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz).strftime("%a, %d %b %Y %H:%M:%S +0800")

    sorted_items = sorted(items, key=lambda x: x.pub_date, reverse=True)

    items_xml = ""
    for item in sorted_items:
        pub_date = item.pub_date
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=tz)
        pub_date_str = pub_date.strftime("%a, %d %b %Y %H:%M:%S +0800")

        guid = item.link if item.link else f"sz-policy-{hash(item.title)}"

        summary = item.summary or ""
        description = f"来源: {item.source}<br/>{summary}".strip()

        tags_xml = ""
        for tag in item.tags:
            tags_xml += f"\n      <category><![CDATA[{tag}]]></category>"

        items_xml += f"""
    <item>
      <title><![CDATA[{item.title}]]></title>
      <link>{item.link}</link>
      <description><![CDATA[{description}]]></description>
      <pubDate>{pub_date_str}</pubDate>
      <guid isPermaLink="false">{guid}</guid>
      <source>{item.source}</source>
      <category>{item.category or '政策通知'}</category>{tags_xml}
    </item>"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{title}</title>
    <link>{link}</link>
    <description>深圳市及南山区政府部门政策通知聚合RSS</description>
    <language>zh-CN</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{link}" rel="self" type="application/rss+xml" />{items_xml}
  </channel>
</rss>
"""
    return rss
