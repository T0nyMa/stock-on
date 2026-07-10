"""共享 HTTP 客户端：UA/超时/重试/GBK解码。"""
from __future__ import annotations

import time
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.trust_env = False
        _session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/json,text/plain,*/*",
        })
    return _session


def get_text(url: str, params: dict = None, headers: dict = None,
             timeout: float = 10, encoding: str = "utf-8") -> tuple[str, str]:
    """GET 请求返回 (text, resolved_encoding)。Tencent/Sina 返回 GBK。"""
    req_headers = {}
    if headers:
        req_headers.update(headers)
    resp = _get_session().get(url, params=params, headers=req_headers or None, timeout=timeout)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    if "charset=gb" in content_type.lower() or "charset=GB" in content_type:
        resp.encoding = "gb2312"
    elif encoding == "gbk":
        try:
            resp.encoding = "gb2312"
        except Exception:
            resp.encoding = "gbk"

    try:
        return resp.text, resp.encoding or "utf-8"
    except Exception:
        resp.encoding = "gbk"
        return resp.text, "gbk"


def get_json(url: str, params: dict = None, headers: dict = None,
             timeout: float = 10) -> dict:
    """GET 请求返回 JSON dict。"""
    resp = _get_session().get(url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def rate_limit(delay: float = 1.0):
    """东财 API 限流：至少间隔 delay 秒。"""
    now = time.time()
    if not hasattr(rate_limit, "_last"):
        rate_limit._last = 0.0
    elapsed = now - rate_limit._last
    if elapsed < delay:
        time.sleep(delay - elapsed)
    rate_limit._last = time.time()
