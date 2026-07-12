import subprocess
import sys
from pathlib import Path
import shutil

import pytest

from scripts import check_project_spec


ROOT = Path(__file__).parents[2]


def test_project_spec_check_passes():
    result = subprocess.run(
        [sys.executable, ROOT / "scripts/check_project_spec.py"],
        cwd=ROOT.parent,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "specification valid",
        "generated documentation current",
        "11 workflows registered",
    ]


SUCCESS_LINES = {
    "specification valid",
    "generated documentation current",
    "11 workflows registered",
}


@pytest.fixture
def isolated_repo(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "spec", repo / "spec")
    shutil.copytree(ROOT / ".agents/skills", repo / ".agents/skills")
    shutil.copytree(ROOT / "references", repo / "references")
    for relative in (
        "AGENTS.md",
        "tracking/README.md",
        "strategies/README.md",
        "src/README.md",
    ):
        source = ROOT / relative
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return repo


def assert_check_fails(repo, capsys, diagnostic):
    assert check_project_spec.main(repo) != 0
    captured = capsys.readouterr()
    assert diagnostic in captured.err
    assert SUCCESS_LINES.isdisjoint(captured.out.splitlines())


def test_project_check_rejects_invalid_schema_without_success_leakage(
    isolated_repo, capsys
):
    project = isolated_repo / "spec/project.yaml"
    project.write_text(
        project.read_text(encoding="utf-8").replace(
            'schema_version: "1.0"', 'schema_version: "9.9"'
        ),
        encoding="utf-8",
    )
    assert_check_fails(isolated_repo, capsys, "SCHEMA.UNSUPPORTED_VERSION")


def test_project_check_rejects_spec_load_error_without_success_leakage(
    isolated_repo, capsys
):
    (isolated_repo / "spec/project.yaml").write_text("project: [", encoding="utf-8")
    assert_check_fails(isolated_repo, capsys, "failed to load")


def test_project_check_rejects_generated_drift_without_success_leakage(
    isolated_repo, capsys
):
    agents = isolated_repo / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8").replace("| Route ID |", "| Stale Route ID |", 1),
        encoding="utf-8",
    )
    assert_check_fails(isolated_repo, capsys, "generated documents are out of date")


def test_project_check_rejects_forbidden_legacy_reference_without_success_leakage(
    isolated_repo, capsys
):
    readme = isolated_repo / "references/README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\n.claude/skills/legacy\n",
        encoding="utf-8",
    )
    assert_check_fails(isolated_repo, capsys, "forbidden contract")


def test_project_check_rejects_missing_skill_contract_without_success_leakage(
    isolated_repo, capsys
):
    (isolated_repo / ".agents/skills/daily-report/SKILL.md").unlink()
    assert_check_fails(isolated_repo, capsys, "skill registration mismatch: daily-report")


def test_project_check_rejects_unregistered_skill_without_success_leakage(
    isolated_repo, capsys
):
    skill = isolated_repo / ".agents/skills/unregistered/SKILL.md"
    skill.parent.mkdir()
    skill.write_text("# Unregistered\n", encoding="utf-8")
    assert_check_fails(isolated_repo, capsys, "skill registration mismatch: unregistered")


def test_project_check_rejects_missing_core_workflow_without_success_leakage(
    isolated_repo, capsys
):
    (isolated_repo / "spec/workflows/deploy.yaml").unlink()
    assert_check_fails(isolated_repo, capsys, "workflow registration mismatch")
