# 深圳政策 RSS 聚合器

自动抓取深圳市及南山区政府部门政策通知，聚合为 **RSS 2.0** 和 **交互式 HTML 预览页**，并支持 5 大类智能标签自动识别。

---

## 在线访问

- **预览页**: https://cherylchenxue-star.github.io/sz-gov-rss/
- **RSS 订阅**: https://cherylchenxue-star.github.io/sz-gov-rss/深圳政策rss.xml

---

## 数据来源（9个）

### 市级部门
- 深圳市科技创新局: https://stic.sz.gov.cn/gkmlpt/policy
- 深圳市工信局: https://gxj.sz.gov.cn/xxgk/xxgkml/zcfgjzcjd/
- 深圳市中小企业服务局: https://zxqyj.sz.gov.cn/zwgk/zfxxgkml/tzgg/
- 深圳市商务局: https://commerce.sz.gov.cn/xxgk/zcfgjzcjd/zcfg/
- 深圳市发改委: https://fgw.sz.gov.cn/zwgk/zcjzcjd/zc/

### 南山区部门
- 南山区企业服务（i南山）: https://www.inanshan.org.cn/ztfw/zcfw/zchj
- 南山区工信局: https://www.szns.gov.cn/nsqjjcjj/gkmlpt/index
- 南山区科创局: https://www.szns.gov.cn/nsqkcj/gkmlpt/index
- 南山区企业服务中心: https://www.szns.gov.cn/nsqqyfzfwzx/gkmlpt/index

---

## 核心特性

- **自动抓取**: 基于 `curl` + `BeautifulSoup` + `Playwright` 抓取各类政府站点
- **摘要提取**: 列表页无摘要时，自动进入详情页提取正文前 300 字作为摘要
- **智能标签**: 对标题和摘要进行关键词匹配，自动打上 5 大类标签
- **交互式页面**: 单文件 `index.html`，支持来源筛选、标签筛选、日期范围、搜索排序、手动刷新
- **自动部署**: GitHub Actions 每日定时抓取并部署到 GitHub Pages

---

## 智能分类标签

| 分类 | 触发关键词 |
|------|-----------|
| 技术领域 | 人工智能、大模型、算力、算法、智能计算、智算中心、数据要素 |
| 企业资质 | 专精特新、小巨人、瞪羚、独角兽、中小企业、营利性服务 |
| 资金支持 | 产业扶持、专项资金、补贴、退税、入库 |
| 人才与项目 | 人才引进、高层次人才、揭榜挂帅、研发投入 |
| 行业动态 | 领航、高成长性、增长率 |

---

## 项目结构

```
.
├── main.py              # 主入口
├── requirements.txt              # Python 依赖
├── index.html                    # 交互式预览页（GitHub Pages 入口）
├── 深圳政策rss.xml                # 生成的 RSS 文件
├── .github/workflows/build-rss.yml  # GitHub Actions 工作流
│
└── sz_gov_rss/                # 核心模块
    ├── models.py                 # PolicyItem, FetchResult
    ├── utils.py                  # curl_fetch, 日期解析, 标签提取
    ├── fetcher_base.py           # 基类：含 enrich_items 摘要+标签
    ├── build_rss.py              # RSS 2.0 生成器
    ├── build_index.py            # 交互式 HTML 生成器
    └── fetchers/                 # 各站点抓取器
        ├── gxj_fetcher.py        # 深圳市工信局
        ├── zxqyj_fetcher.py      # 深圳市中小企业服务局
        ├── commerce_fetcher.py   # 深圳市商务局
        ├── fgw_fetcher.py        # 深圳市发改委
        ├── szns_fetcher.py       # 统一平台（科创局/工信局/企业服务中心）
        └── inanshan_fetcher.py   # 南山区企业服务（i南山）
```

---

## 运行逻辑

1. **抓取列表页**: 每个 `fetcher` 解析对应部门页面，提取标题、链接、日期
2. **详情页 enrichment**: `BaseFetcher.enrich_items()` 对无摘要的条目自动抓取详情页正文
3. **自动标签**: 基于标题+摘要文本，通过 `extract_industry_tags()` 匹配 5 类关键词，输出到 RSS `<category>`
4. **生成 RSS**: `build_rss.py` 输出标准 RSS 2.0（含 `pubDate` `source` `category`）
5. **生成 HTML**: `build_index.py` 输出交互式单文件页面，支持筛选、排序、手动刷新
6. **部署**: GitHub Actions 每日自动运行并发布到 GitHub Pages

---

## 本地运行

```bash
pip install -r requirements.txt
python main.py -v
```

运行后生成 `深圳政策rss.xml` 和 `index.html`。

---

## 自动更新

每日北京时间 **10:00** 自动抓取并部署。支持手动触发 `workflow_dispatch`。
