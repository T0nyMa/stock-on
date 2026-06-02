"""Tests for src/config.py — full ref-repo Config (Singleton pattern)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from unittest import mock
from src.config import Config, get_config


def setup_function():
    """Reset Singleton between tests."""
    Config.reset_instance()


class TestConfigDefaults:
    def test_debug_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert cfg.debug is False

    def test_log_dir_exists(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert cfg.log_dir

    def test_data_dir_exists(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert cfg.data_dir

    def test_max_workers_positive(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert cfg.max_workers >= 1

    def test_bias_threshold_exists(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert hasattr(cfg, 'bias_threshold')

    def test_llm_model_config(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert hasattr(cfg, 'litellm_model')


class TestConfigFromEnv:
    def test_debug_from_env(self):
        with mock.patch.dict(os.environ, {"DEBUG": "true", "STOCK_LIST": "600519"}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert cfg.debug is True

    def test_tushare_token(self):
        with mock.patch.dict(os.environ, {"TUSHARE_TOKEN": "test123", "STOCK_LIST": "600519"}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert cfg.tushare_token == "test123"

    def test_max_workers(self):
        with mock.patch.dict(os.environ, {"MAX_WORKERS": "8", "STOCK_LIST": "600519"}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert cfg.max_workers == 8

    def test_stock_list_type(self):
        with mock.patch.dict(os.environ, {"STOCK_LIST": "600519,000001"}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert isinstance(cfg.stock_list, list)

    def test_trading_day_disabled(self):
        with mock.patch.dict(os.environ, {"TRADING_DAY_CHECK_ENABLED": "false", "STOCK_LIST": "600519"}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert cfg.trading_day_check_enabled is False


class TestConfigValidate:
    def test_validate(self):
        with mock.patch.dict(os.environ, {"STOCK_LIST": "600519"}, clear=True):
            Config.reset_instance()
            cfg = get_config()
            assert isinstance(cfg.validate(), list)
