import json
from pathlib import Path

from src.spec.cli import main


FIXTURE = Path(__file__).parent / "fixtures/minimal"


def test_inspect_emits_resolved_workflow_as_utf8_json(capsys):
    result = main(["--spec-root", str(FIXTURE), "inspect", "--intent", "sample 阿里巴巴"])
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "route": "route.sample",
        "workflow": "sample",
        "skills": ["skill.sample"],
        "policies": ["policy.core"],
        "inputs": [],
        "outputs": ["artifact.output"],
        "gates": {"preflight": ["SAMPLE.READY"], "completion": ["artifact.output"]},
        "params": {"stock": "阿里巴巴"},
    }


def test_inspect_returns_one_when_no_route_matches(capsys):
    result = main(["--spec-root", str(FIXTURE), "inspect", "--intent", "unrelated"])
    assert result == 1
    assert json.loads(capsys.readouterr().out) == {"error": "no matching route"}


def test_validate_returns_one_on_blocking_issues(tmp_path, capsys):
    result = main(
        [
            "--spec-root",
            str(FIXTURE),
            "--repo-root",
            str(tmp_path),
            "validate",
        ]
    )
    assert result == 1
    issues = json.loads(capsys.readouterr().out)
    assert any(issue["code"] == "SKILL.PATH_MISSING" for issue in issues)
