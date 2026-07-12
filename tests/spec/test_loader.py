from pathlib import Path

import pytest

from src.spec.loader import SpecLoadError, load_registry


FIXTURE = Path(__file__).parent / "fixtures/minimal"


def test_load_registry_returns_typed_records():
    registry = load_registry(FIXTURE)
    assert registry.project["project"] == "stock-on-test"
    assert registry.routes["route.sample"].workflow == "sample"
    assert registry.workflows["sample"].outputs == ("artifact.output",)
    assert registry.workflows["sample"].optional_inputs == ()
    assert registry.workflows["sample"].on_failure == ("stop",)
    assert registry.gates["SAMPLE.READY"].severity == "block"


def test_duplicate_ids_fail(tmp_path):
    root = tmp_path / "spec"
    root.mkdir()
    (root / "project.yaml").write_text("schema_version: '1.0'\nproject: x\n")
    (root / "routes.yaml").write_text(
        "- {id: route.x, intents: ['x'], workflow: w, priority: 1}\n"
        "- {id: route.x, intents: ['y'], workflow: w, priority: 2}\n"
    )
    (root / "artifacts.yaml").write_text("[]\n")
    (root / "skills.yaml").write_text("[]\n")
    (root / "policies").mkdir()
    (root / "workflows").mkdir()
    with pytest.raises(SpecLoadError, match="duplicate id: route.x"):
        load_registry(root)


def test_workflow_missing_failure_behavior_fails_load(tmp_path):
    root = tmp_path / "spec"
    root.mkdir()
    (root / "project.yaml").write_text("schema_version: '1.0'\nproject: x\n")
    (root / "routes.yaml").write_text("[]\n")
    (root / "artifacts.yaml").write_text("[]\n")
    (root / "skills.yaml").write_text("[]\n")
    (root / "policies").mkdir()
    workflows = root / "workflows"
    workflows.mkdir()
    (workflows / "bad.yaml").write_text(
        "id: bad\ninputs: []\noptional_inputs: []\noutputs: []\n"
        "policies: []\nskills: []\nsteps: []\npreflight: []\ncompletion: []\n"
    )
    with pytest.raises(SpecLoadError, match="missing required key: on_failure"):
        load_registry(root)
