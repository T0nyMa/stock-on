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


def test_check_emits_deterministic_diagnostics_and_blocks_unknown_evaluator(capsys):
    result = main(["--spec-root", str(FIXTURE), "check", "--workflow", "sample", "--phase", "preflight"])
    assert result == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["results"][0]["actual"] == "unknown evaluator: output exists"


def test_check_loads_facts_file(tmp_path, capsys, monkeypatch):
    facts_path = tmp_path / "facts.json"
    facts_path.write_text('{"deployment_url":"https://example.test"}')
    captured = {}

    class Report:
        ok = True
        def to_dict(self):
            return {"ok": True, "results": []}

    def fake_check(*args, **kwargs):
        captured.update(kwargs["facts"])
        return Report()

    monkeypatch.setattr("src.spec.cli.check_workflow", fake_check)
    result = main([
        "--spec-root", str(FIXTURE), "check", "--workflow", "sample",
        "--phase", "preflight", "--facts", str(facts_path),
    ])
    assert result == 0
    assert captured == {"deployment_url": "https://example.test"}
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_check_reports_invalid_facts_json(tmp_path, capsys):
    facts_path = tmp_path / "facts.json"
    facts_path.write_text("not-json")
    result = main([
        "--spec-root", str(FIXTURE), "check", "--workflow", "sample",
        "--phase", "preflight", "--facts", str(facts_path),
    ])
    assert result == 1
    assert "error" in json.loads(capsys.readouterr().out)
