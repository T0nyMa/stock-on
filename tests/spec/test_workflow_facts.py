import json

import pytest

from src.spec.facts import load_workflow_facts


def _write_record(tmp_path, **changes):
    workflow = "daily-report"
    record = {
        "schema_version": "1.0",
        "workflow": workflow,
        "facts": {
            "positions": [
                {"code": "601138", "name": "工业富联"},
            ]
        },
    }
    record.update(changes)
    path = tmp_path / f"data/spec/workflow-facts/{workflow}.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(record, ensure_ascii=False))
    return path


def test_load_workflow_facts_accepts_valid_position_manifest(tmp_path):
    _write_record(tmp_path)
    assert load_workflow_facts(tmp_path, "daily-report")["positions"] == [
        {"code": "601138", "name": "工业富联"}
    ]


@pytest.mark.parametrize(
    "changes,diagnostic",
    [
        ({"schema_version": "2.0"}, "schema_version"),
        ({"workflow": "weekly-report"}, "workflow mismatch"),
        ({"facts": []}, "facts must be a JSON object"),
        ({"unknown": True}, "unknown top-level"),
    ],
)
def test_load_workflow_facts_rejects_invalid_record_shape(
    tmp_path, changes, diagnostic
):
    _write_record(tmp_path, **changes)
    with pytest.raises(ValueError, match=diagnostic):
        load_workflow_facts(tmp_path, "daily-report")


@pytest.mark.parametrize(
    "positions",
    [
        [],
        ["601138"],
        [{"code": "601138"}],
        [{"code": "", "name": "工业富联"}],
        [{"code": "601138", "name": ""}],
        [{"code": "601138", "name": "工业富联", "extra": True}],
    ],
)
def test_load_workflow_facts_rejects_malformed_positions(tmp_path, positions):
    _write_record(tmp_path, facts={"positions": positions})
    with pytest.raises(ValueError, match="positions"):
        load_workflow_facts(tmp_path, "daily-report")
