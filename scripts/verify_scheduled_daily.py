#!/usr/bin/env python3
"""Deterministically verify a scheduled daily-report run."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


SECTION_PATTERNS = (
    r"^##\s+(?:1\.|一、).*宏观|^##\s+1\.",
    r"^##\s+(?:2\.|二、).*持仓|^##\s+2\.",
    r"^##\s+(?:3\.|三、).*核心|^##\s+3\.",
    r"^##\s+(?:4\.|四、).*A-H|^##\s+4\.",
    r"^##\s+(?:5\.|五、).*观察|^##\s+5\.",
    r"^##\s+(?:6\.|六、).*策略|^##\s+6\.",
    r"^##\s+(?:7\.|七、).*操作|^##\s+7\.",
)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(("git", *args), cwd=repo, text=True, capture_output=True)


def verify(repo: Path, date: str, *, url: str | None, skip_http: bool) -> list[str]:
    errors: list[str] = []
    report = repo / f"tracking/daily/positions/{date}.md"
    html = report.with_suffix(".html")
    index = repo / "index.html"

    if not report.is_file():
        errors.append(f"missing canonical report: {report.relative_to(repo)}")
        text = ""
    else:
        text = report.read_text(encoding="utf-8")
        for number, pattern in enumerate(SECTION_PATTERNS, 1):
            if not re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE):
                errors.append(f"missing daily report section {number}")

    legacy = []
    market = repo / f"tracking/daily/market/{date}.md"
    if market.exists():
        legacy.append(market)
    legacy.extend(repo.glob(f"tracking/*-*/{date}-analysis.md"))
    if legacy:
        names = ", ".join(str(path.relative_to(repo)) for path in sorted(legacy))
        errors.append(f"legacy Markdown artifacts are forbidden: {names}")

    if not html.is_file():
        errors.append(f"missing published HTML: {html.relative_to(repo)}")
    if not index.is_file() or date not in index.read_text(encoding="utf-8"):
        errors.append("index.html does not reference the dated report")

    relevant = [report, html, index]
    tracklist = repo / "tracking/tracklist.json"
    if tracklist.is_file():
        payload = json.loads(tracklist.read_text(encoding="utf-8"))
        for stock in payload.get("stocks", []):
            if stock.get("has_position"):
                relevant.append(repo / "tracking" / f"{stock['code']}-{stock['name']}" / "position.json")
    for path in relevant:
        relative = str(path.relative_to(repo))
        status = git(repo, "status", "--porcelain", "--", relative)
        if status.stdout.strip():
            errors.append(f"applicable path is not committed: {relative}")

    upstream = git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream.returncode != 0:
        errors.append("current branch has no upstream; report is not pushed")
    else:
        ahead = git(repo, "rev-list", "--count", "@{u}..HEAD")
        if ahead.returncode != 0 or ahead.stdout.strip() != "0":
            errors.append(f"current HEAD is not pushed (ahead={ahead.stdout.strip() or 'unknown'})")

    if not skip_http:
        if not url:
            errors.append("publication URL is required for HTTP verification")
        else:
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "stock-on-daily-verifier/1"})
                with urllib.request.urlopen(request, timeout=20) as response:
                    if response.status != 200:
                        errors.append(f"published page returned HTTP {response.status}: {url}")
            except Exception as exc:  # network diagnostics belong in the final result
                errors.append(f"published page verification failed: {url}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--date", required=True)
    parser.add_argument("--url")
    parser.add_argument("--skip-http", action="store_true", help="Tests only; production must verify HTTP")
    args = parser.parse_args()
    errors = verify(args.repo.resolve(), args.date, url=args.url, skip_http=args.skip_http)
    result = {"ok": not errors, "date": args.date, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
