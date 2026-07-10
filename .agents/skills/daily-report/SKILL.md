---
name: daily-report
description: 每日追踪报告 — 生成大盘总结(含板块行情) + 全部追踪股单股日报 + 持仓汇总
---

# 每日追踪报告

编排每日报告生成流程。严格按步骤执行，不跳过。

## 用法

`$daily-report` 或用户说"日报""今日总结""daily"

## 流程

### Phase 0: 数据新鲜度校验（强制，不可跳过）

**必须**先进行以下检查，再进入 Phase 1。这不是建议，是硬性前置条件。

```
1. 读取 data/market/index.json → 检查 _data_date 字段
   - _data_date 是 fetch_market.py 写入的数据真实日期
   - 如果 _data_date ≠ 今天 → 强制重跑: bash: source .venv/bin/activate && python src/fetch_market.py
   - 如果文件不存在 _data_date 字段 → 旧版脚本输出，强制重跑
   - 只有 _data_date = 今天 才能跳过
2. 抽样检查 3 只股票的 fundamentals.json (core + key 各一只):
   读取 data/{code}/fundamentals.json → 检查 pe 和 pb 是否非 null
   - 如果 pe/pb 为 null → 腾讯接口补充
```

**如果 Phase 0 校验失败，不允许进入 Phase 1。** 这是防止日报数据错误的最关键步骤。

### Phase 1: 数据准备

```bash
# 大盘指数（如果 Phase 0 未跳过）
source .venv/bin/activate && python src/fetch_market.py

# 板块扫描（每日必做）
source .venv/bin/activate && python src/sector_scan.py

# 追踪股数据（读取 tracklist.json 后并行执行）
读取 tracking/tracklist.json → 取全部 stocks[].code
对每只 stock.code 并行执行:
  bash: source .venv/bin/activate && python src/fetch.py --code {code}
  bash: source .venv/bin/activate && python src/indicators.py --code {code}
```

### Phase 2: 单股日报（全部股票，每只必写）

读取 `tracking/tracklist.json`，按 tier 决定分析深度。每只股票生成一份单股日报。

**策略分析方法（内联，不调用外部 Skill）：**

```
1. 读取 data/{code}/indicators.json → 从 trend.status 确定市场状态
2. 读取 references/skills-index.md → "按市场状态选策略"表
3. 根据市场状态从"优先策略"列选对应数量:
   - core: 优先列选 3-4 + 可选列补 1 = 共 3-5 个
   - key:  优先列选 2-3 = 共 2-3 个
   - watch: 优先列选 1-2 = 共 1-2 个
4. 对每个选中的策略，读取其 Skill 定义（.agents/skills/strategy-{name}/SKILL.md）
5. 按 Skill 定义的 Step 1→2→3→4 逐步执行，引用具体数据
6. 每个策略输出标准 JSON: `{"name":"strategy-xxx","signal":"buy|hold|sell","score":0-100,"reason":"一句话"}`
   - 策略名用小写+连字符（如 strategy-bull-trend），禁止下划线
   - 信号用小写英文 buy/hold/sell
7. 汇总为策略共识矩阵，写入日报
```

**基本面分析方法（全部股票必做，不跳过）：**

```
1. 读取 data/{code}/fundamentals.json → 获取 PE、PB、市值、ROE
   - 如果 fundamentals.json 中 pe/pb 为 null，先通过腾讯财经接口补充：
     bash: python3 -c "from urllib.request import urlopen,Request; import json,time; prefix='sh' if '{code}'.startswith('6') else 'sz'; url=f'https://qt.gtimg.cn/q={prefix}{code}'; req=Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://finance.qq.com/'}); raw=urlopen(req,timeout=10).read().decode('gbk'); fields=raw.split('=\"')[1].rstrip('\";\n').split('~') if '=\"' in raw else raw.split('=')[1].split('~'); d={'code':'{code}','name':fields[1],'price':float(fields[3]) if fields[3] else None,'pe':float(fields[39]) if fields[39] else None,'pb':float(fields[46]) if fields[46] else None,'market_cap_yi':float(fields[45]) if fields[45] else None,'circ_mv_yi':float(fields[44]) if fields[44] else None,'turnover_rate':float(fields[38]) if fields[38] else None,'volume_ratio':float(fields[49]) if fields[49] else None,'source':'tencent','updated_at':time.strftime('%Y-%m-%dT%H:%M:%S+08:00')}; print(json.dumps(d,ensure_ascii=False))"
     然后将输出写入 data/{code}/fundamentals.json
2. 写入日报基本面概览区块（PE/PB/市值/ROE + 一句话估值判断）
```

**持仓策略分析方法（has_position=true 的股票必做）：**

```
1. 读取 tracking/{code}-{name}/position.json → 获取持仓成本和策略计划
2. 更新 position.json 中的 current_price、unrealized_pnl、unrealized_pnl_pct
3. 检查止损位是否触发，检查加仓条件是否满足
4. 更新 swing_plan 中各情景的触发条件是否已变化
5. 写入日报持仓策略区块：成本/现价/盈亏 + 情景概率变化 + 操作指令
```

**日报格式（按 tier）：**

core — 完整日报（含策略共识矩阵 + 基本面 + 持仓策略）:
```markdown
# {name}（{code}）每日分析 — YYYY年MM月DD日

## 今日走势
| 开盘 | 最高 | 最低 | 收盘 | 涨跌 | 量比 | 换手 |

## 策略共识 (3-5策略)
| 策略 | 类型 | 信号 | 评分 | 依据 |

## 基本面概览
| PE | PB | 市值 | ROE |
|------|------|------|------|
| {pe} | {pb} | {market_cap}亿 | {roe}% |

一句话估值判断（偏低/合理/偏高/严重高估），结合增速和PEG

## 持仓策略（如有持仓）
- **成本**: {buy_price} × {shares}股 = ¥{cost}
- **现价**: {price}，浮盈/浮亏 +{pnl_pct}%（¥{pnl}）
- **止损**: {stop_loss}，距止损 {distance_to_stop}%
- **情景概率更新**: 各情景触发条件和概率变化
- **操作指令**: 具体到价位和股数

## 与昨日对比
| 指标 | 昨日 | 今日 | 方向 | 解读 |

## 关键价位评估
（止损/支撑/阻力/成本，逐项检查）

## 情景判断
| 情景 | 概率 | 变化 | 依据 |

## 操作建议
具体到价位和股数
```

key — 标准日报（含策略信号 + 基本面 + 持仓策略如有）:
```markdown
# {name}（{code}）每日分析 — YYYY年MM月DD日

## 今日走势
| 开盘 | 最高 | 最低 | 收盘 | 涨跌 | 量比 | 换手 |

## 策略信号 (2-3策略)
| 策略 | 类型 | 信号 | 评分 | 依据 |

## 基本面概览
| PE | PB | 市值 | ROE |
|------|------|------|------|
| {pe} | {pb} | {market_cap}亿 | {roe}% |

一句话估值判断

## 持仓策略（如有持仓）
- **成本**: {buy_price} × {shares}股 = ¥{cost}
- **现价**: {price}，浮盈/浮亏 +{pnl_pct}%
- **止损**: {stop_loss}
- **操作指令**: 具体到价位和股数

## 指标变化
| 指标 | 数值 | 状态 |

## 买入条件检查（无持仓时）

## 操作建议
```

watch — 简化日报（含策略信号 + 基本面）:
```markdown
# {name}（{code}）每日分析 — YYYY年MM月DD日

## 今日走势
| 开盘 | 最高 | 最低 | 收盘 | 涨跌 | 量比 | 换手 |

## 策略信号 (1-2策略)
| 策略 | 类型 | 信号 | 评分 | 依据 |

## 基本面速览
| PE | PB | 市值(亿) | 状态 |
|------|------|------|------|
| {pe} | {pb} | {market_cap} | 估值偏低/合理/偏高/严重高估 |

## 指标变化
| 指标 | 数值 | 状态 |

## 操作建议
```

**输出文件：**
```
tracking/{code}-{name}/YYYY-MM-DD-analysis.md ← 每只必写
tracking/{code}-{name}/position.json           ← core 更新
tracking/{code}-{name}/technical-analysis-report.md ← 更新变化章节
```

**并行建议：**

7只股票的策略分析可以并行。在任务允许并行代理时，可将 7 只股票分配为独立子任务并行执行，每只 Agent 独立完成：读数据 → 选策略 → 分析 → 写日报。这样 7 只同时完成，不阻塞。

### Phase 3: 大盘总结 + 板块行情

读取 `data/market/index.json` + `data/market/sector_scan.json` → 输出大盘日报。

格式：
- 4大指数表现 + 今日特征（风格定性/量能/最强最弱指数）+ 与昨日对比
- **20板块排名表**（评分/均涨幅/上涨比/最强股）
- **板块分化分析**（最强3板块、最弱3板块、AI主线板块表现、与昨日对比）
- 板块资金流向判断（从AI主线→防御板块 or 回补AI）

写入 `tracking/daily/market/YYYY-MM-DD.md`

### Phase 4: 持仓观察汇总

将 Phase 2 所有单股日报汇总为四层报告：

```
★ 核心持仓 — 每只 8-12 行（策略共识 + 持仓策略 + 基本面要点 + 关键价位 + 操作指令）
★ 重点观察 — 每只 5-8 行（策略信号 + 基本面速览 + 持仓策略/买入条件）
一般观察 — 表格式，一行一只（收盘/涨跌/量比/RSI/PE/PB/估值状态）
基本面估值分布 — PE区间分布统计（<30/30-50/50-100/100-200/>200），标注估值洼地和高估预警
```

写入 `tracking/daily/positions/YYYY-MM-DD.md`

**HTML 版本**同步更新：持仓汇总 HTML 中增加基本面对比卡片（PE散点分布图或表格式估值矩阵）。

### Phase 5: 发布

日报全部生成后，**必须自动执行部署**，不需要等用户说"发布"：

1. 生成大盘/持仓 HTML（从 MD 转换）
2. **整文件重写 index.html**（不是增量插入）:
   - 读取 index.html 当前结构
   - 从 `tracking/daily/*/` 扫描所有现有报告日期
   - 重新生成完整的 index.html，确保无重复区块、所有链接正确
3. git add + commit + push
4. 使用 `$deploy {date}` — 生成 HTML + 更新首页 + git push

## 输出清单（必须全部生成 + 部署）

```
tracking/daily/market/YYYY-MM-DD.md              ← 大盘总结（含20板块排名+分化分析）
tracking/daily/market/YYYY-MM-DD.html            ← 大盘总结 (HTML)
tracking/daily/positions/YYYY-MM-DD.md           ← 持仓观察汇总（含基本面分布 + 持仓策略）
tracking/daily/positions/YYYY-MM-DD.html         ← 持仓观察汇总 (HTML，含估值矩阵)
tracking/{code}-{name}/YYYY-MM-DD-analysis.md    ← 全部 N 只单股日报（含基本面 + 持仓策略）
tracking/sectors/YYYY-MM-DD-sector-scan.md       ← 板块扫描报告
data/{code}/fundamentals.json                    ← 全部 N 只基本面数据（PE/PB/市值/ROE）
data/market/sector_scan.json                     ← 板块扫描 JSON
https://t0nyma.github.io/stock-on/               ← GitHub Pages 已更新
```

## 完成标志

- [ ] **Phase 0 校验通过**：market/index.json 日期=今天，fundamentals.json PE/PB非空
- [ ] fetch_market.py 已执行（如需要）
- [ ] **sector_scan.py 已执行**（20板块排名数据）
- [ ] 全部追踪股 fetch + indicators 已完成
- [ ] **全部追踪股 fundamentals.json 已更新**（PE/PB/市值/ROE 非空）
- [ ] 大盘总结已写入（含 **20板块排名 + 板块分化分析**）
- [ ] 全部 N 只单股日报已写入（core: 3-5策略 key: 2-3策略 watch: 1-2策略，含基本面概览）
- [ ] **持仓股日报含持仓策略区块**（成本/现价/盈亏/止损/情景更新/操作指令）
- [ ] 持仓观察汇总日报已写入（含基本面估值分布）
- [ ] **index.html 整文件重写**（非增量插入），确认无重复日期区块
- [ ] **已部署到 GitHub Pages**（HTML 生成 + index.html 更新 + git push）
