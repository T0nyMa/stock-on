# Deep Stock Analysis Skill Design

## 1. Objective

Create a project Skill named `deep-stock-analysis` that performs evidence-backed, company-specific deep research on any tracked or newly supplied stock.

The Skill answers:

- What does the company sell and how does it earn money?
- Which capabilities create its competitive advantage?
- How durable and high-quality are current earnings?
- Which company archetype and industry cycle determine the correct analytical lens?
- What do ownership, institutional activity, price/volume structure, and market expectations imply?
- What valuation assumptions are embedded in the current price?
- Which facts would invalidate the analysis?

The Skill does not decide entry timing, position size, additions, reductions, stop-losses, or exact trading instructions. Those belong to dedicated trading-decision Skills.

## 2. Trigger and Interface

Primary command:

```text
$deep-stock-analysis {code}
```

Natural-language triggers include:

- “深度分析 601899”
- “研究一下紫金矿业的基本面和周期”
- “这家公司靠什么赚钱，护城河是什么”
- “综合分析某只股票，但先不要给买卖建议”

Optional input context may include a specific research question, comparison company, or requested historical date. The stock code remains the only required argument.

## 3. Design Principles

### 3.1 Separate research from trading

The output may classify valuation, market expectations, cycle position, and technical structure. It must not translate those findings into buy/sell timing, share counts, or position changes.

### 3.2 Use a stable core and adaptive modules

Every company receives the same evidence and reasoning backbone. Company-type adapters add domain-specific questions and metrics. A company may activate up to two adapters: one primary and one secondary.

### 3.3 Evidence before conclusions

Every material numerical or time-sensitive claim must include its period, source, and evidence quality. Exchange filings and company reports outrank media summaries. Missing information remains `unavailable`; the Skill must not invent neutral values or silently substitute unrelated indicators.

### 3.4 Distinguish facts, inferences, and hypotheses

The report labels:

- verified fact;
- inference from disclosed data;
- scenario assumption;
- unresolved question.

### 3.5 Make the thesis falsifiable

Each report states the core thesis, its strongest counterargument, and concrete facts that would invalidate it.

## 4. Inputs and Existing Capabilities

### 4.1 Required local inputs

Before researching a stock, read:

- `tracking/tracklist.json`;
- existing reports under `tracking/{code}-{name}/`;
- `position.json` when present, only as background context;
- SQLite daily bars, quote, fundamentals, news, and indicators through `src.data_access`;
- Quantitative Analysis V2 artifacts when available, including multi-timeframe state, relative strength, strategy statistics, cross-market comparison, and evidence gaps.

### 4.2 Required refresh

Run sequentially:

```bash
source .venv/bin/activate && python src/fetch.py --code {code}
source .venv/bin/activate && python src/indicators.py --code {code}
```

The database contains up to 500 daily bars. A newly listed company may legitimately have fewer observations; disclose the actual count.

### 4.3 Current-information research

Use `easy_anysearch_skill` for recent announcements, shareholder changes, management actions, industry data, regulation, commodity prices, and major events. Verify important claims using this priority:

1. exchange or regulator;
2. company filing or investor-relations material;
3. government or industry body;
4. authoritative financial-data provider;
5. reputable financial media;
6. secondary commentary.

Preserve publication dates and links in the report.

### 4.4 Existing strategy capability

Use market-regime routing and select three to five relevant strategy Skills. Their role is to describe how the market is pricing the company and whether technical, volume, sentiment, and event signals agree. Strategy consensus is supporting evidence, not a trading recommendation.

## 5. Company Archetype Router

The router first identifies the company's primary earnings engine. It then selects one primary adapter and, only when material, one secondary adapter.

| Archetype | Primary analytical focus |
|---|---|
| Resource cycle | Commodity prices, production, reserves, grade, unit cost, mine life, capex, jurisdiction and geopolitical exposure |
| Technology growth | Product generation, revenue growth, R&D efficiency, market share, substitution, competition, customer concentration and expectation repricing |
| Manufacturing | Capacity utilization, orders, backlog, yield, cost pass-through, inventory, customer structure and scale effects |
| Consumer brand | Volume, price, mix, channels, inventory, repeat purchase, brand premium and consumer cycle |
| Healthcare | Pipeline, clinical stage, patents, reimbursement/procurement, R&D productivity and commercialization |
| Financial | Net interest margin, asset quality, non-performing loans, provisions, capital adequacy and credit cycle |
| Internet platform | Users, engagement, monetization, take rate, cloud/advertising/commerce segments, regulation and segment valuation |

Routing evidence must be stated. If no adapter fits, use only the core framework and record an `analysis-gap` candidate instead of forcing a classification.

## 6. Core Analysis Workflow

### Phase 0: Research question and evidence coverage

- Identify whether this is an initial deep analysis or a refresh.
- Load existing conclusions to avoid unnecessary repetition.
- Build an evidence inventory and list unavailable fields.
- State the data cutoff date and actual number of daily bars.

### Phase 1: Business and earnings engine

- Explain the business in plain language.
- Decompose revenue, profit, geography, customers, and major products.
- Identify the variables that drive revenue, margins, cash flow, and capital requirements.
- Separate structural growth, cyclical uplift, acquisitions, accounting effects, and one-off gains.

### Phase 2: Industry and competitive position

- Define the relevant market and value chain.
- Compare the company with three to five appropriate peers.
- Assess market position, cost position, product differentiation, switching costs, scale, regulation, and barriers to entry.
- Explain why competitors cannot easily reproduce the advantage.

### Phase 3: Moat, management, and capital allocation

- Identify the claimed moat and test whether financial and operating evidence supports it.
- Review management tenure, ownership, incentives, related-party risks, governance, and execution record.
- Evaluate acquisitions, dividends, buybacks, financing, capex, dilution, and returns on invested capital.

### Phase 4: Financial quality

- Analyze revenue, profit, margins, ROE/ROIC, operating cash flow, free cash flow, working capital, debt, and dilution.
- Reconcile earnings growth with cash generation.
- Identify whether current earnings represent a normal, peak, trough, or transitional level.
- Flag accounting or data-quality anomalies.

### Phase 5: Ownership, institutions, and market structure

- Track shareholder count, major shareholders, insider ownership, institutional additions/reductions, northbound or equivalent flows, and share pledges when available.
- Calculate concentration or dispersion trends without treating every institutional sale as informed money.
- Compare ownership changes with price, turnover, and volume structure.
- Distinguish verified holdings data from narrative interpretations about “smart money.”

### Phase 6: Cycle or growth-stage adapter

- Load the selected archetype reference.
- Identify cycle position, growth stage, bottlenecks, and leading variables.
- For cyclical companies, normalize commodity/industry drivers and unit economics.
- For growth companies, separate sustainable growth from valuation-driven expectations.

### Phase 7: Quantitative and technical market view

- Use up to 500 daily bars and current indicators.
- Analyze daily/weekly/monthly alignment, trend strength, volatility, relative strength, volume, OBV/MFI/CMF, and major price structures.
- Run three to five regime-appropriate strategy frameworks.
- Explain what expectations the market appears to be discounting.
- Do not convert technical levels into entry, stop-loss, or trade-size instructions.

### Phase 8: Valuation and implied expectations

- Select valuation methods appropriate to the archetype: PE, EV/EBITDA, PB, FCF yield, sum-of-the-parts, NAV, or normalized-cycle earnings.
- Prefer historical distributions and peer comparisons over a single multiple.
- Reverse-engineer the operating or earnings assumptions implied by the current valuation.
- Separate “statistically cheap” from “fundamentally protected.”

### Phase 9: Bear/base/bull scenarios

Build three explicit scenarios. Each includes:

- operating assumptions;
- revenue/profit or normalized earnings;
- valuation method and multiple;
- indicative value range;
- evidence supporting the assumptions;
- variables that move the company between scenarios.

Scenario probabilities may be used only when the evidence justifies them. Otherwise label probabilities `unavailable`.

### Phase 10: Synthesis and falsification

Produce:

- company-quality assessment;
- moat confidence;
- earnings stage;
- cycle/growth stage;
- ownership and market-structure state;
- valuation state tied to scenarios;
- core contradiction;
- strongest bull case;
- strongest bear case;
- three to five monitoring variables;
- thesis invalidation conditions;
- evidence gaps and confidence level.

## 7. Output Contract

Write one report:

```text
tracking/{code}-{name}/deep-analysis-YYYY-MM-DD.md
```

The report contains eleven chapters:

1. Executive research conclusion
2. Business structure and earnings engine
3. Industry position and competitive landscape
4. Moat and durability
5. Management, governance, and capital allocation
6. Financial quality and normalized earnings
7. Shareholders, institutions, and market structure
8. Archetype-specific cycle or growth analysis
9. Quantitative, technical, and relative-strength evidence
10. Valuation and three scenarios
11. Core contradiction, risks, monitoring variables, and falsification conditions

The executive conclusion uses research labels rather than trading labels:

- company quality: `strong | medium | weak | unavailable`;
- moat confidence: `high | medium | low | unavailable`;
- earnings stage: `expanding | stable | peaking | contracting | transitional | unavailable`;
- expectations: `pessimistic | neutral | optimistic | extreme | unavailable`;
- valuation by scenario: `protected | reasonable | demanding | unavailable`;
- research confidence: `high | medium | low`.

The report must not contain share-count instructions, position changes, stop-loss prices, or a final `buy/hold/sell` signal.

## 8. Skill Package

```text
.agents/skills/deep-stock-analysis/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── core-framework.md
    ├── resource-cycle.md
    ├── technology-growth.md
    ├── manufacturing.md
    ├── consumer.md
    ├── healthcare.md
    ├── financial.md
    ├── internet-platform.md
    └── report-template.md
```

`SKILL.md` contains the routing and mandatory workflow. Detailed questions, metrics, and interpretation rules live in the references so only the relevant adapter enters context.

No new deterministic script is required initially. Existing fetch, indicator, data-access, strategy, and search tools provide the needed execution primitives.

## 9. Error Handling

- If fewer than 500 bars exist, continue with the available history and lower confidence.
- If fundamentals are missing, do not infer valuation from price action.
- If shareholder or institutional data lacks matching report dates, mark the comparison unavailable.
- If current news search fails, retain the last verified snapshot but state its age.
- If peer selection is uncertain, explain the peer criteria and avoid precise rankings.
- If the archetype router is ambiguous, use a primary adapter only and state the ambiguity.
- If evidence conflicts, present both sides and reduce confidence rather than forcing consensus.

## 10. Evolution Mechanism

Evolution is explicit and versioned, not autonomous self-modification.

After real use, record reusable gaps in:

```text
references/analysis-gaps.md
```

An entry contains:

- company and archetype;
- missing analytical dimension;
- evidence that the omission mattered;
- proposed adapter or core-framework change;
- historical cases used to validate the change;
- resolution status.

Only recurring or materially important gaps become Skill changes. Update the relevant adapter, validate the package, forward-test on at least one company of that archetype, and commit the revision.

## 11. Validation

Validate the Skill package structurally with `quick_validate.py`.

Forward-test at least these contrasting cases:

- resource cycle: 紫金矿业;
- technology/manufacturing: 三花智控 or 北方华创;
- healthcare: 恒瑞医药;
- internet platform: 阿里巴巴.

For each case verify:

- correct adapter routing;
- all eleven chapters are present;
- numerical claims have period and source;
- facts and inferences are distinguishable;
- scenario assumptions are explicit;
- technical analysis supports research rather than issuing trades;
- no buy/sell, position-size, or stop-loss instruction appears;
- missing data is disclosed rather than fabricated.

## 12. Acceptance Criteria

The Skill is complete when:

- it can analyze an arbitrary A-share or supported Hong Kong stock using a code;
- it selects no more than two justified company adapters;
- it consumes the existing SQLite, Quant V2, strategy, and current-information capabilities;
- it generates the specified eleven-chapter report;
- it provides scenario-linked valuation and falsifiable conclusions;
- it stays within the research-only boundary;
- structural validation and the four forward-tests pass.
