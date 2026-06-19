---
name: deploy
description: 发布日报/周报到 GitHub Pages — 生成HTML + 更新首页索引 + 推送
---

# 发布到 GitHub Pages

将追踪报告发布到 `https://t0nyma.github.io/stock-on/`。

## 用法

`/deploy {date}` — 例如 `/deploy 2026-06-19`

不传 date 则发布最新日期。

## 流程

### 1. 确认待发布文件

```
ls tracking/daily/market/{date}.md          ← 大盘总结
ls tracking/daily/positions/{date}.md       ← 持仓观察汇总
ls tracking/daily/positions/{date}.html     ← 可能已有或需生成
ls tracking/{code}-{name}/*-analysis.md     ← 单股日报
ls tracking/weekly/{date}.md                ← 周报（如有）
```

### 2. 生成 HTML

对需要 HTML 展示的报告，从 MD 生成 HTML 文件：

**大盘总结** → `tracking/daily/market/{date}.html`

格式：暗色主题卡片式，指数表格 + 特征标签。

**持仓观察汇总** → `tracking/daily/positions/{date}.html`

格式：三层卡片（core红/key橙/watch蓝），策略共识矩阵，关键价位标签。CSS 内联。

**周报** → `tracking/weekly/{date}.html`（如有）

格式：暗色主题，大盘+板块+持仓周评 + 下周关注。

HTML 生成原则：
- 全部 CSS 内联（一个 HTML 文件自包含）
- 手机端适配（max-width 960px + 响应式）
- 涨绿跌红（A股习惯），超买/风险用红色警示
- 中文友好（PingFang SC / Microsoft YaHei）

### 3. 更新首页索引

Read `index.html`，在对应日期区块下添加新报告的链接条目。

已有该日期的区块 → 在区块内追加新链接。
没有该日期的区块 → 在顶部（最新）插入新日期区块。

链接格式：
```html
<a class="link" href="tracking/daily/market/{date}.html">
  <span class="title">📊 大盘总结</span>
  <span class="date">一句话概述</span>
</a>
```

### 4. 提交推送

```bash
git add tracking/daily/ tracking/weekly/ tracking/{code}-{name}/ index.html
git commit -m "deploy: {date} daily + weekly reports"
git push
```

## 输出

```
https://t0nyma.github.io/stock-on/                           ← 首页
https://t0nyma.github.io/stock-on/tracking/daily/market/{date}.html     ← 大盘
https://t0nyma.github.io/stock-on/tracking/daily/positions/{date}.html  ← 持仓
https://t0nyma.github.io/stock-on/tracking/weekly/{date}.html           ← 周报

GitHub 自动渲染的 MD 文件也可直接访问。
```

## 完成标志

- [ ] 大盘/持仓/周报 HTML 已生成
- [ ] index.html 已更新（含新日期入口）
- [ ] git push 成功
