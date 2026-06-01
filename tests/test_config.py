"""Tests for src/config.py — 精简配置管理"""

import os
import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Ensure src/ is importable
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import Config, get_config, setup_env


class TestConfigDefaults:
    def test_default_stock_list_empty(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            assert cfg.stock_list == []

    def test_default_debug_false(self):
        cfg = Config()
        assert cfg.debug is False

    def test_default_log_dir(self):
        cfg = Config()
        assert cfg.log_dir == "logs"

    def test_default_data_dir(self):
        cfg = Config()
        assert cfg.data_dir == "data"

    def test_default_max_workers(self):
        cfg = Config()
        assert cfg.max_workers == 4

    def test_default_use_proxy_false(self):
        cfg = Config()
        assert cfg.use_proxy is False

    def test_default_trading_day_check(self):
        cfg = Config()
        assert cfg.trading_day_check_enabled is True


class TestConfigFromEnv:
    def test_stock_list_from_env(self):
        with mock.patch.dict(os.environ, {"STOCK_LIST": "600519,000001"}, clear=True):
            cfg = get_config()
            assert cfg.stock_list == ["600519", "000001"]

    def test_stock_list_trims_whitespace(self):
        with mock.patch.dict(os.environ, {"STOCK_LIST": " 600519 , 000001 "}, clear=True):
            cfg = get_config()
            assert cfg.stock_list == ["600519", "000001"]

    def test_stock_list_empty_string_respected(self):
        with mock.patch.dict(os.environ, {"STOCK_LIST": ""}, clear=True):
            cfg = get_config()
            assert cfg.stock_list == []

    def test_debug_on(self):
        with mock.patch.dict(os.environ, {"DEBUG": "true"}, clear=True):
            cfg = get_config()
            assert cfg.debug is True

    def test_debug_off_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = get_config()
            assert cfg.debug is False

    def test_tushare_token(self):
        with mock.patch.dict(os.environ, {"TUSHARE_TOKEN": "abc123"}, clear=True):
            cfg = get_config()
            assert cfg.tushare_token == "abc123"

    def test_log_level_custom(self):
        with mock.patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=True):
            cfg = get_config()
            assert cfg.log_level == "DEBUG"

    def test_data_dir_custom(self):
        with mock.patch.dict(os.environ, {"DATA_DIR": "custom_data"}, clear=True):
            cfg = get_config()
            assert cfg.data_dir == "custom_data"

    def test_max_workers_custom(self):
        with mock.patch.dict(os.environ, {"MAX_WORKERS": "8"}, clear=True):
            cfg = get_config()
            assert cfg.max_workers == 8

    def test_use_proxy_enabled(self):
        with mock.patch.dict(os.environ, {"USE_PROXY": "true"}, clear=True):
            cfg = get_config()
            assert cfg.use_proxy is True

    def test_proxy_host_custom(self):
        with mock.patch.dict(os.environ, {"PROXY_HOST": "192.168.1.1"}, clear=True):
            cfg = get_config()
            assert cfg.proxy_host == "192.168.1.1"

    def test_trading_day_check_disabled(self):
        with mock.patch.dict(os.environ, {"TRADING_DAY_CHECK_ENABLED": "false"}, clear=True):
            cfg = get_config()
            assert cfg.trading_day_check_enabled is False


class TestConfigValidate:
    def test_empty_stock_list_warning(self):
        cfg = Config()
        warnings = cfg.validate()
        assert any("STOCK_LIST" in w for w in warnings)

    def test_valid_config_no_warnings(self):
        cfg = Config()
        cfg.stock_list = ["600519"]
        warnings = cfg.validate()
        assert len(warnings) == 0


class TestConfigRefresh:
    def test_refresh_stock_list(self):
        cfg = Config()
        with mock.patch.dict(os.environ, {"STOCK_LIST": "600519,000001,300750"}, clear=True):
            cfg.refresh_stock_list()
            assert cfg.stock_list == ["600519", "000001", "300750"]
