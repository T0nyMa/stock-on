# Data Source V2 Design Doc

## 现状问题

### 1. 层次过多，依赖过重

```
当前链路: fetch.py → DataFetcherManager → TickFlowFetcher → tickflow 库 → TickFlow 服务器 → 腾讯数据
```

每一层都是故障点。TickFlow 是个第三方封装的库，底层数据来自腾讯，多了一层不稳定依赖。base.py 3200+ 行，data_provider 目录总计 13000+ 行，维护成本高。

### 2. 11 个 Fetcher，大部分不工作

| Fetcher | 状态 | 实际作用 |
|---------|------|---------|
| TickFlowDailyFetcher | 在用 | A股K线主力 |
| AkshareFetcher | 在用 | 实时行情+基本面 |
| EfinanceFetcher | 降级 | 备用行情 |
| TushareFetcher | 需Token | 多数未配置 |
| PytdxFetcher | 不稳定 | 通达信协议 |
| BaostockFetcher | 可用 | 历史数据 |
| YfinanceFetcher | 不稳定 | 美股 |
| LongbridgeFetcher | 需Token | 美股港股 |
| FinnhubFetcher | 需Token | 美股 |
| AlphaVantageFetcher | 需Token | 美股 |
| TickFlowFetcher | 旧版 | 已废弃 |

实际每天用的就 TickFlow + Akshare 两个。其余都是死代码。

### 3. 没有真正的多源降级

当前是"优先级选择"：选一个 Fetcher 用它取全部数据，失败了才切下一个。不是"同一个请求发三个源，哪个先到用哪个"。

### 4. 缺失关键数据类型

- **北向资金/主力资金流向**: 判断大盘情绪的关键指标，完全没有
- **A股财务快照**: ROE/毛利率/EPS/营收增速，fundamentals.json 里几乎没有
- **涨跌停情绪数据**: 市场冰点/高潮的量化指标，完全没有
- **港股技术指标**: K线拉到了但没算 MA/MACD/RSI

### 5. 港股数据割裂

`fetch_all_daily.py` 里单独写了腾讯 API 调用逻辑来拉港股数据，但没有融入 `data_provider/` 体系，也没计算技术指标。

---

## 设计目标

1. **直接调用公开 HTTP API**，砍掉第三方封装库依赖
2. **每类数据有 2-3 个源形成降级链**，一个挂了自动切
3. **补齐缺失数据**：资金流向、财务快照、情绪指标
4. **港股统一纳入体系**，和 A 股同一套接口
5. **大幅缩减代码量**，从 13000 行砍到 ~3000 行

---

## 新架构

```
fetch.py (入口)
  → DataProvider (门面，单一入口)
      ├── QuoteProvider     → 行情 (腾讯→新浪→东财)
      ├── KlineProvider     → K线 (腾讯→东财)
      ├── FinancialProvider → 财务 (东财 datacenter)
      ├── FlowProvider      → 资金流 (东财 fflow)
      ├── SentimentProvider → 情绪 (东财涨停池)
      └── IndexProvider     → 指数/板块 (东财 clist)
```

每个 Provider 内部有降级链，接口统一：

```python
class QuoteProvider:
    """行情数据，腾讯→新浪→东财降级"""
    def get_realtime(self, code: str) -> QuoteData: ...
    def get_batch(self, codes: list[str]) -> dict[str, QuoteData]: ...

class KlineProvider:
    """K线数据，腾讯→东财降级"""
    def get_daily(self, code: str, limit: int = 60) -> list[KlineRow]: ...

class FinancialProvider:
    """财务快照，仅东财"""
    def get_snapshot(self, code: str) -> FinancialData: ...

class FlowProvider:
    """资金流向，仅东财"""
    def get_market_flow(self) -> MarketFlow: ...
    def get_northbound(self) -> NorthboundFlow: ...

class SentimentProvider:
    """市场情绪，仅东财"""
    def get_limit_pools(self) -> LimitPools: ...

class IndexProvider:
    """指数/板块"""
    def get_indices(self, market: str) -> list[IndexData]: ...
    def get_sector_rankings(self) -> list[SectorData]: ...
```

---

## 数据源清单

### 腾讯 API (qt.gtimg.cn / web.ifzq.gtimg.cn)

**优点**: 免费、不限流、A+H+US 全覆盖、字段稳定
**格式**: 分隔符 `~` 分隔文本，GBK 编码

| 端点 | 能力 | 覆盖市场 |
|------|------|---------|
| `qt.gtimg.cn/q={codes}` | 实时行情快照(价/量/PE/市值) | A/HK/US |
| `web.ifzq.gtimg.cn/appstock/app/fqkline/get` | 日K线(前复权) | A/HK |
| `smartbox.gtimg.cn/s3` | 股票搜索 | A/HK/US |

**字段索引** (已验证):

```
索引 1: 名称
索引 3: 最新价
索引 4: 昨收
索引 5: 今开
索引 32: 涨跌幅
索引 33: 最高价
索引 34: 最低价
索引 36: 成交量
索引 37: 成交额
索引 38: 换手率
索引 39: PE
索引 44: 总市值
索引 45: 流通市值
索引 46: PB
索引 48: 52周最高
索引 49: 52周最低
索引 61: YTD涨跌幅
```

**代码格式**: A股 `sh600519`/`sz000651`，港股 `hk00700`，美股 `usAAPL`

### 新浪 API (hq.sinajs.cn)

**优点**: 美股数据比腾讯更全，免费
**缺点**: 浏览器端不可用(需 Referer)，GBK 编码

| 端点 | 能力 | 覆盖市场 |
|------|------|---------|
| `hq.sinajs.cn/list={codes}` | 实时行情快照 | A/HK/US |
| `stock.finance.sina.com.cn/usstock/api/jsonp.php` | 美股日K线 | US |

### 东方财富 (push2.eastmoney.com / datacenter-web.eastmoney.com)

**优点**: 中国独有数据(资金流/财务/情绪/板块)，免费
**注意**: 需 1 秒以上请求间隔，否则会限流

| 端点 | 能力 |
|------|------|
| `push2.eastmoney.com/api/qt/ulist.np/get` | A股指数行情 |
| `push2.eastmoney.com/api/qt/clist/get` | 行业/概念板块排名 |
| `push2.eastmoney.com/api/qt/stock/get` | 单股行情(降级用) |
| `push2.eastmoney.com/api/qt/stock/fflow/kline/get` | 主力资金流向（新增） |
| `push2.eastmoney.com/getTopicZTPool` | 涨停池（新增） |
| `push2.eastmoney.com/getTopicDTPool` | 跌停池（新增） |
| `datacenter-web.eastmoney.com/api/data/v1/get` | 财务快照（新增） |
| `searchapi.eastmoney.com/api/suggest/get` | 股票搜索 |

### 天天基金 (fund.eastmoney.com)

| 端点 | 能力 |
|------|------|
| `fundgz.1234567.com.cn/js/{code}.js` | 基金实时估值 |
| `fund.eastmoney.com/pingzhongdata/{code}.js` | 基金长期画像 |

---

## 降级链设计

```
行情 (Quote):
  qt.gtimg.cn → hq.sinajs.cn → push2.eastmoney.com/stock/get
  超时: 5s, 重试: 1次, 切换: 立即

K线 (Kline):
  web.ifzq.gtimg.cn (腾讯 fqkline) → push2his.eastmoney.com (东财K线)
  超时: 10s, 重试: 1次, 切换: 立即

财务 (Financial):
  datacenter-web.eastmoney.com → 返回空+标记 gap
  超时: 8s, 重试: 2次, 切换: N/A (东财唯一源)

资金流 (Flow):
  push2.eastmoney.com → 返回空+标记 gap
  超时: 8s, 重试: 1次, 切换: N/A

情绪 (Sentiment):
  push2.eastmoney.com → 返回空+标记 gap
  超时: 5s, 重试: 1次, 切换: N/A

指数/板块 (Index):
  push2.eastmoney.com/clist → 同花顺 HTML 解析 → 返回空
  超时: 10s, 重试: 1次, 切换: 立即
```

**核心原则**: 源挂了就标记 gap，不猜数据、不填零。缺失字段在报告中标注"数据不可用"。

---

## 数据质量标记

每个返回结果携带元数据，让 Claude 分析时知道数据可信度：

```python
@dataclass
class DataResult:
    data: dict
    source: str          # "tencent" | "sina" | "eastmoney"
    source_chain: list   # ["tencent:ok", "sina:timeout", "eastmoney:ok"]
    quality: str         # "full" | "degraded" | "gap"
    gaps: list[str]      # ["northbound_flow", "financial_snapshot"]
    latency_ms: float
```

参考 stock-analysis 的做法：报告里标注"北向资金数据不可用"，而不是假装有数据。

---

## 实现计划

### Phase 1: 核心数据层 (替换 TickFlow)

新建 `src/providers/` 目录，实现三个核心 Provider：

```
src/providers/
  __init__.py
  http_client.py      # 共享 HTTP 客户端(UA/超时/重试/编码)
  models.py           # 统一数据模型
  quote.py            # QuoteProvider (腾讯→新浪→东财)
  kline.py            # KlineProvider (腾讯→东财)
  index.py            # IndexProvider (东财指数+板块)
```

**关键改动**: `fetch.py` 直接 import Provider，不再走 DataFetcherManager → 11 个 Fetcher 链路。

### Phase 2: 新增数据类型

```
src/providers/
  financial.py        # FinancialProvider (东财财务快照)
  flow.py             # FlowProvider (主力+北向资金)
  sentiment.py        # SentimentProvider (涨跌停统计)
```

### Phase 3: 港股统一

港股不再在 `fetch_all_daily.py` 里单独处理。`KlineProvider.get_daily("HK00700")` 自动路由到腾讯港股 K 线接口，指标计算对港股和 A 股使用相同逻辑。

### Phase 4: 清理旧代码

- 废弃 `src/data_provider/` 全部 fetcher（保留备份，不删除）
- `fetch_all_daily.py` 改用新 Provider
- `src/indicators.py` 层保持不变（输入仍然是 kline.json）

---

## 风险评估

| 风险 | 缓解 |
|------|------|
| 腾讯/东财 API 格式变更 | 字段索引集中定义在 models.py，改一处全量生效 |
| 东财限流 | 1s 间隔 + 指数退避 + 缓存 |
| TickFlow 用户依赖 | Phase 4 前旧代码保留，可随时切回 |
| 港股 K 线字段顺序特殊 | stock-analysis 已验证过字段顺序，直接复用 |
| 网络环境差异 | GBK 解码兜底，错误不抛异常只标记 gap |

---

## 度量标准

- [ ] `fetch.py --code 600519` 执行时间 ≤ 3s（原来 ~5-8s）
- [ ] 代码量: data_provider 目录从 13000 行降到 0 行(迁移完成后删除)，providers 目录 ≤ 3000 行
- [ ] 单源故障时自动降级，不抛异常不中断
- [ ] 港股 K 线拉取后自动计算 MA/MACD/RSI
- [ ] 资金流向/财务快照/情绪数据可用
- [ ] `fetch_all_daily.py` 港股部分统一走 Provider

---

## 与 stock-analysis 的对比

| 维度 | stock-analysis | 本项目 V2 |
|------|---------------|-----------|
| 数据层代码量 | ~2500 行 (market_core + integrations) | ~3000 行 |
| 核心数据源 | 腾讯 → 新浪 → 东财 | 腾讯 → 新浪 → 东财 |
| 降级粒度 | 每个 fetch 函数内独立降级 | 每个 Provider 内独立降级 |
| 财务快照 | 东财 datacenter | 复用相同端点 |
| 资金流向 | 有 | 新增 |
| 质量标记 | 有 (EvidenceQuality 100分制) | 有 (DataResult.quality) |
| 港股统一 | 内建支持 | V2 统一 |
| 依赖库 | requests only | requests only |
