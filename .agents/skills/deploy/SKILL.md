---
name: deploy
description: 将登记的日报、周报或发现报告生成 HTML，更新 GitHub Pages 索引并推送
---

# 发布到 GitHub Pages

执行 `deploy` 工作流。`$deploy {date}` 发布指定日期；不传日期时发布最新登记报告。

## 输入

- 日报：`artifact.daily_report`，即 `tracking/daily/positions/{date}.md`。
- 周报和发现报告仅在本次工作流适用时作为可选登记输入。

日报 HTML 必须只从 `artifact.daily_report` 生成，不读取独立大盘或逐股日报作为内容源。七章内的大盘、板块、核心个股、观察股和操作清单应完整保留。

## 流程

1. 检查输入文件存在且日期匹配；缺失登记输入时停止。
2. 从 Markdown 生成自包含、移动端适配的 HTML。保留表格、来源链接、风险警示和 A 股涨跌配色。
3. 整文件重写 `index.html`：扫描已登记报告路径，按日期倒序，每个日期只出现一次，链接指向对应 HTML；禁止增量插入造成重复。
4. 提交报告 HTML 与索引，执行 `git push`。
5. 打开 GitHub Pages 对应页面，验证可访问且日期、七章导航和链接正确。

## 输出与完成门禁

输出是 `artifact.published_html`，路径由 `spec/artifacts.yaml` 登记。只有 HTML 已生成、索引已更新、push 成功且线上页面验证通过，才满足 `PUBLISH.PUSHED`；失败时重试或停止，不得声称发布完成。
