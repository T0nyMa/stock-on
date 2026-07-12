import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "scripts/verify_scheduled_daily.py"


def run(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True)


def git(repo, *args):
    result = run("git", *args, cwd=repo)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def make_repo(tmp_path, *, legacy=False):
    repo = tmp_path / "repo"
    remote = tmp_path / "remote.git"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    run("git", "init", "--bare", str(remote), cwd=tmp_path)
    git(repo, "remote", "add", "origin", str(remote))
    date = "2026-07-13"
    report = repo / f"tracking/daily/positions/{date}.md"
    report.parent.mkdir(parents=True)
    report.write_text("\n".join(f"## {i}. section" for i in range(1, 8)) + "\n")
    report.with_suffix(".html").write_text("<html>ok</html>\n")
    (repo / "index.html").write_text(f"tracking/daily/positions/{date}.html\n")
    if legacy:
        old = repo / f"tracking/daily/market/{date}.md"
        old.parent.mkdir(parents=True)
        old.write_text("legacy\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "daily")
    git(repo, "push", "-u", "origin", "main")
    return repo, date


def test_wrapper_uses_current_contract_and_post_verifier():
    text = (ROOT / "scripts/run_scheduled_daily.sh").read_text()
    assert "AnySearch" in text
    assert "EasyAnySearch" in text
    assert "python -m src.spec" in text
    assert "verify_scheduled_daily.py" in text
    assert "唯一 Markdown" in text


def test_verifier_accepts_committed_pushed_single_file_report(tmp_path):
    repo, date = make_repo(tmp_path)
    result = run(sys.executable, str(VERIFY), "--repo", str(repo), "--date", date, "--skip-http")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["ok"] is True


def test_verifier_rejects_legacy_dated_markdown(tmp_path):
    repo, date = make_repo(tmp_path, legacy=True)
    result = run(sys.executable, str(VERIFY), "--repo", str(repo), "--date", date, "--skip-http")
    assert result.returncode == 1
    assert "legacy Markdown" in result.stdout


def test_verifier_rejects_unpushed_report(tmp_path):
    repo, date = make_repo(tmp_path)
    report = repo / f"tracking/daily/positions/{date}.md"
    report.write_text(report.read_text() + "changed\n")
    git(repo, "add", str(report.relative_to(repo)))
    git(repo, "commit", "-m", "local only")
    result = run(sys.executable, str(VERIFY), "--repo", str(repo), "--date", date, "--skip-http")
    assert result.returncode == 1
    assert "not pushed" in result.stdout


def test_legacy_orchestrator_is_disabled():
    result = run(sys.executable, str(ROOT / "scripts/orchestrate_daily.py"), "--dry-run")
    assert result.returncode != 0
    assert "deprecated" in result.stderr.lower()
