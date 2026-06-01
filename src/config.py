"""
Stock-On: 精简配置管理模块
从原 daily_stock_analysis 提取，去掉 notification/webui/bot 依赖。
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv, dotenv_values
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 新闻策略窗口定义（从 ref-repo/src/config.py 提取）
NEWS_STRATEGY_WINDOWS: Dict[str, int] = {
    "ultra_short": 1,
    "short": 3,
    "medium": 7,
    "long": 14,
    "extended": 30,
}


@dataclass
class Config:
    """统一配置类，从环境变量加载"""

    # === 股票列表 ===
    stock_list: List[str] = field(default_factory=list)

    # === 数据源配置 ===
    tushare_token: Optional[str] = None
    use_proxy: bool = False
    proxy_host: str = "127.0.0.1"
    proxy_port: str = "10809"

    # === 分析配置 ===
    debug: bool = False
    log_dir: str = "logs"
    log_level: str = "INFO"
    report_language: str = "zh"
    max_workers: int = 4
    data_dir: str = "data"

    # === 技术分析参数 ===
    bias_threshold: float = 5.0  # 乖离率阈值（%），超过此值不追高
    enable_eastmoney_patch: bool = True  # 启用东方财富数据补丁
    enable_realtime_quote: bool = True  # 启用实时行情
    realtime_source_priority: str = "efinance,akshare"  # 实时行情数据源优先级
    enable_fundamental_pipeline: bool = True  # 启用基本面分析
    fundamental_fetch_timeout_seconds: float = 8.0  # 基本面获取超时
    fundamental_stage_timeout_seconds: float = 8.0  # 基本面分析超时
    fundamental_cache_ttl_seconds: int = 120  # 基本面缓存过期时间

    # === 交易日检查 ===
    trading_day_check_enabled: bool = True

    def validate(self) -> List[str]:
        warnings = []
        if not self.stock_list:
            warnings.append("STOCK_LIST 为空，请配置自选股代码")
        return warnings

    def refresh_stock_list(self):
        """从环境变量刷新股票列表"""
        raw = os.getenv("STOCK_LIST", "")
        self.stock_list = [s.strip() for s in raw.split(",") if s.strip()]


def setup_env():
    """加载 .env 文件"""
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path, override=False)
        logger.info("已加载 .env 配置文件")


def get_config() -> Config:
    """获取配置实例"""
    cfg = Config()
    raw = os.getenv("STOCK_LIST", "")
    cfg.stock_list = [s.strip() for s in raw.split(",") if s.strip()]
    cfg.tushare_token = os.getenv("TUSHARE_TOKEN")
    cfg.debug = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
    cfg.log_dir = os.getenv("LOG_DIR", "logs")
    cfg.log_level = os.getenv("LOG_LEVEL", "INFO")
    cfg.data_dir = os.getenv("DATA_DIR", "data")
    cfg.use_proxy = os.getenv("USE_PROXY", "false").lower() == "true"
    cfg.proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    cfg.proxy_port = os.getenv("PROXY_PORT", "10809")
    cfg.trading_day_check_enabled = os.getenv("TRADING_DAY_CHECK_ENABLED", "true").lower() != "false"
    cfg.max_workers = int(os.getenv("MAX_WORKERS", "4"))
    cfg.bias_threshold = float(os.getenv("BIAS_THRESHOLD", "5.0"))
    cfg.enable_eastmoney_patch = os.getenv("ENABLE_EASTMONEY_PATCH", "true").lower() != "false"
    return cfg
