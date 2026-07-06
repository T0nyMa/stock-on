#!/usr/bin/env python3
"""金价追踪：SGE 现货 + COMEX 期货，写入 data/market/gold.json"""
import json, logging, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
_TZ_CN = timezone(timedelta(hours=8))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gold")

def fetch_gold_prices():
    result = {
        "updated_at": datetime.now(_TZ_CN).isoformat(),
        "sge": {},   # 上海金交所现货
        "comex": {}, # COMEX期货
        "history_sge": []  # 近10日SGE基准价
    }

    # 1. SGE 现货行情 (Au99.99)
    try:
        import akshare as ak
        df = ak.spot_quotations_sge()
        au = df[df['品种'] == 'Au99.99']
        if len(au) > 0:
            latest = au.iloc[-1]
            result["sge"]["品种"] = "Au99.99"
            result["sge"]["现价_元每克"] = float(latest["现价"])
            result["sge"]["更新时间"] = str(latest["更新时间"])
            logger.info(f"SGE Au99.99: {latest['现价']} 元/克")
    except Exception as e:
        logger.warning(f"SGE现货行情获取失败: {e}")

    # 2. SGE 基准价历史（近10日）
    try:
        import akshare as ak
        df = ak.spot_golden_benchmark_sge()
        recent = df.tail(10)
        for _, row in recent.iterrows():
            result["history_sge"].append({
                "日期": str(row["交易时间"]),
                "晚盘价": float(row["晚盘价"]),
                "早盘价": float(row["早盘价"])
            })
        latest_sge = result["history_sge"][-1]
        logger.info(f"SGE基准价({latest_sge['日期']}): 早盘{latest_sge['早盘价']} 晚盘{latest_sge['晚盘价']} 元/克")
    except Exception as e:
        logger.warning(f"SGE基准价获取失败: {e}")

    # 3. COMEX 黄金期货
    try:
        import akshare as ak
        df = ak.futures_global_spot_em()
        comex_gold = df[(df['代码'].str.contains('GC00Y', na=False))]
        if len(comex_gold) > 0:
            c = comex_gold.iloc[0]
            result["comex"]["代码"] = str(c["代码"])
            result["comex"]["名称"] = str(c["名称"])
            result["comex"]["最新价_美元每盎司"] = float(c["最新价"]) if c["最新价"] and str(c["最新价"]) != 'nan' else None
            result["comex"]["涨跌额"] = float(c["涨跌额"]) if c["涨跌额"] and str(c["涨跌额"]) != 'nan' else None
            result["comex"]["成交量"] = int(c["成交量"]) if c["成交量"] and str(c["成交量"]) != 'nan' else 0
            logger.info(f"COMEX黄金: {c['最新价']} 美元/盎司")
    except Exception as e:
        logger.warning(f"COMEX期货获取失败: {e}")

    # 写入
    out_path = ROOT / "data" / "market" / "gold.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"金价数据已写入: {out_path}")
    return result

if __name__ == "__main__":
    fetch_gold_prices()
