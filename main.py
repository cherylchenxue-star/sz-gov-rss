#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深圳政策RSS聚合器 - 主入口

抓取深圳市及南山区多个政府部门的政策通知页面，
聚合输出为统一的 RSS 2.0 XML 文件。
"""

import sys
import argparse
import os
from datetime import datetime, timezone, timedelta
from typing import List

from sz_gov_rss.models import FetchResult, PolicyItem
from sz_gov_rss.build_rss import build_rss
from sz_gov_rss.build_index import build_index
from sz_gov_rss.fetchers.gxj_fetcher import GxjFetcher
from sz_gov_rss.fetchers.zxqyj_fetcher import ZxqyjFetcher
from sz_gov_rss.fetchers.commerce_fetcher import CommerceFetcher
from sz_gov_rss.fetchers.fgw_fetcher import FgwFetcher
from sz_gov_rss.fetchers.szns_fetcher import SznsFetcher
from sz_gov_rss.fetchers.inanshan_fetcher import InanshanFetcher


SOURCES = [
    ("gxj", "深圳市工信局", GxjFetcher()),
    ("zxqyj", "深圳市中小企业服务局", ZxqyjFetcher()),
    ("commerce", "深圳市商务局", CommerceFetcher()),
    ("fgw", "深圳市发改委", FgwFetcher()),
    ("szns_gxj", "南山区工信局", SznsFetcher("南山区工信局", "http://www.szns.gov.cn/nsqjjcjj/gkmlpt/index")),
    ("szns_kcj", "南山区科创局", SznsFetcher("南山区科创局", "http://www.szns.gov.cn/nsqkcj/gkmlpt/index")),
    ("szns_qyfw", "南山区企业服务中心", SznsFetcher("南山区企业服务中心", "http://www.szns.gov.cn/nsqqyfzfwzx/gkmlpt/index")),
    ("inanshan", "南山区企业服务", InanshanFetcher()),
    ("stic", "深圳市科技创新局", SznsFetcher("深圳市科技创新局", "http://stic.sz.gov.cn/gkmlpt/policy")),
]

SOURCE_NAME_MAP = {sid: name for sid, name, _ in SOURCES}

DEFAULT_OUTPUT = "深圳政策rss.xml"


def load_existing_items(filepath: str) -> List[PolicyItem]:
    """从现有 RSS 文件中加载条目，用于在抓取失败时保留旧数据"""
    if not os.path.exists(filepath):
        return []
    try:
        from xml.etree import ElementTree as ET
        tree = ET.parse(filepath)
        root = tree.getroot()
        items: List[PolicyItem] = []
        for item_elem in root.findall(".//item"):
            title = item_elem.findtext("title", default="")
            link = item_elem.findtext("link", default="")
            source = item_elem.findtext("source", default="")
            pub_date_str = item_elem.findtext("pubDate", default="")
            description = item_elem.findtext("description", default="")
            category = item_elem.findtext("category", default="")

            pub_date = None
            if pub_date_str:
                try:
                    pub_date = datetime.strptime(pub_date_str.strip(), "%a, %d %b %Y %H:%M:%S %z")
                    pub_date = pub_date.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
                except ValueError:
                    pass
            if pub_date is None:
                pub_date = datetime.now()

            summary = description
            if summary.startswith("来源:"):
                summary = summary.split("<br/>", 1)[-1] if "<br/>" in summary else ""

            tags = [cat.text for cat in item_elem.findall("category") if cat.text and cat.text != category]

            source_id = ""
            for sid, sname in SOURCE_NAME_MAP.items():
                if sname == source:
                    source_id = sid
                    break

            items.append(PolicyItem(
                title=title,
                link=link,
                pub_date=pub_date,
                source=source,
                source_id=source_id,
                summary=summary,
                category=category,
                tags=tags,
                city="shenzhen",
            ))
        return items
    except Exception as e:
        print(f"[警告] 加载现有 RSS 文件失败: {e}")
        return []


def run_fetchers(max_items: int = 20, verbose: bool = False) -> List[FetchResult]:
    results: List[FetchResult] = []

    for source_id, name, fetcher in SOURCES:
        if verbose:
            print(f"[抓取] {name} ...")
        result = fetcher.fetch(max_items=max_items)

        if result.success:
            for item in result.items:
                item.source_id = source_id
                item.city = "shenzhen"

        results.append(result)

        if verbose:
            if result.success:
                print(f"  ✓ 成功，获取 {result.fetched_count} 条")
            else:
                print(f"  ✗ 失败: {result.error_message}")

    return results


def reenrich_preserved_items(items: List[PolicyItem]) -> None:
    """对保留的旧条目重新抓取详情页补全准确时间戳"""
    from sz_gov_rss.fetcher_base import BaseFetcher
    from sz_gov_rss.models import FetchResult

    class DummyFetcher(BaseFetcher):
        def fetch(self, max_items: int = 20) -> FetchResult:
            return FetchResult(source_name="reenrich", items=[], success=True)

    fetcher = DummyFetcher("reenrich", "")
    selectors = [".article-content", ".content", ".TRS_Editor", ".news_cont_d_wrap", ".conter"]

    enriched_count = 0
    for item in items:
        if item.pub_date.hour == 0 and item.pub_date.minute == 0 and item.link:
            try:
                html = fetcher.fetch_summary(item.link, selectors, timeout=10, return_html=True)
                if html:
                    precise = fetcher.extract_pub_date(html)
                    if precise:
                        item.pub_date = precise
                        enriched_count += 1
            except Exception:
                pass

    if enriched_count > 0:
        print(f"[INFO] 为 {enriched_count} 条保留的旧条目补全了准确时间戳")


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="深圳政策RSS聚合器")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help="输出RSS文件路径")
    parser.add_argument("--max-items", "-n", type=int, default=20, help="每个源最大抓取条数")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")
    args = parser.parse_args()

    print("=" * 60)
    print("深圳政策RSS聚合器 - 开始运行")
    print("=" * 60)

    results = run_fetchers(max_items=args.max_items, verbose=args.verbose)

    # 汇总统计
    success_count = sum(1 for r in results if r.success)
    total_items = sum(len(r.items) for r in results)

    print("\n" + "=" * 60)
    print("抓取汇总")
    print("=" * 60)
    for r in results:
        status = "✓" if r.success else "✗"
        print(f"{status} {r.source_name}: {len(r.items)} 条")
        if not r.success:
            print(f"   错误: {r.error_message}")

    print(f"\n总计: {success_count}/{len(results)} 个源成功，共 {total_items} 条政策")

    # 确定哪些源成功抓取到数据
    success_source_ids = set()
    for r in results:
        if r.success and r.items:
            for item in r.items:
                if item.source_id:
                    success_source_ids.add(item.source_id)

    # 合并新旧数据：成功源用新数据，失败源保留现有数据（30天内）
    all_items: List[PolicyItem] = []
    for r in results:
        if r.success:
            all_items.extend(r.items)

    existing_items = load_existing_items(args.output)
    cutoff_date = datetime.now() - timedelta(days=30)
    preserved_items: List[PolicyItem] = []
    for item in existing_items:
        if item.source_id not in success_source_ids and item.pub_date >= cutoff_date:
            preserved_items.append(item)

    if preserved_items:
        print(f"[INFO] 从现有 RSS 保留 {len(preserved_items)} 条失败源的旧数据（30天内），尝试补全时间戳...")
        reenrich_preserved_items(preserved_items)
        all_items.extend(preserved_items)

    rss_link = "https://cherylchenxue-star.github.io/sz-gov-rss/深圳政策rss.xml"

    if all_items:
        # 去重（按 link）
        seen_links = set()
        deduped_items: List[PolicyItem] = []
        for item in all_items:
            if item.link and item.link not in seen_links:
                seen_links.add(item.link)
                deduped_items.append(item)
            elif not item.link:
                deduped_items.append(item)
        all_items = deduped_items

        # 生成RSS
        rss_content = build_rss(all_items, title="深圳政策RSS聚合", link=rss_link)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(rss_content)
        print(f"\n[OK] RSS 已保存到: {args.output}（共 {len(all_items)} 条）")

        # 生成HTML预览页
        index_content = build_index(all_items)
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(index_content)
        print("[OK] 预览页已保存到: index.html")

        # 预览前10条
        print("\n── 最新政策预览（前10条）──")
        for i, item in enumerate(sorted(all_items, key=lambda x: x.pub_date, reverse=True)[:10], 1):
            date_str = item.pub_date.strftime("%Y-%m-%d")
            print(f"{i:2}. [{date_str}] [{item.source}] {item.title}")
    else:
        print("\n[警告] 未抓取到任何政策条目，保留上次生成的文件。")


if __name__ == "__main__":
    main()
