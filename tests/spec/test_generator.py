from pathlib import Path

import pytest

from src.spec.generator import (
    GeneratedSectionError,
    generate_documents,
    render_routes,
    replace_generated_section,
)
from src.spec.loader import load_registry


ROOT = Path(__file__).parents[2]


def test_generated_routes_are_deterministic():
    registry = load_registry(ROOT / "spec")
    assert render_routes(registry) == render_routes(registry)
    assert "财报分析" in render_routes(registry)


def test_replace_generated_section_preserves_manual_text():
    source = "manual\n<!-- BEGIN GENERATED: routes -->\nold\n<!-- END GENERATED: routes -->\ntail\n"
    result = replace_generated_section(source, "routes", "new\n")
    assert result == "manual\n<!-- BEGIN GENERATED: routes -->\nnew\n<!-- END GENERATED: routes -->\ntail\n"


@pytest.mark.parametrize(
    "source",
    [
        "manual only\n",
        "<!-- BEGIN GENERATED: routes -->\nold\n",
        (
            "<!-- BEGIN GENERATED: routes -->\nold\n<!-- END GENERATED: routes -->\n"
            "<!-- BEGIN GENERATED: routes -->\nold\n<!-- END GENERATED: routes -->\n"
        ),
    ],
)
def test_replace_generated_section_requires_exactly_one_marker_pair(source):
    with pytest.raises(GeneratedSectionError):
        replace_generated_section(source, "routes", "new\n")


def test_generate_check_reports_stale_documents(tmp_path):
    registry = load_registry(ROOT / "spec")
    (tmp_path / "references" / "generated").mkdir(parents=True)
    (tmp_path / "references").mkdir(exist_ok=True)
    (tmp_path / "AGENTS.md").write_text(
        "before\n<!-- BEGIN GENERATED: routes -->\nstale\n<!-- END GENERATED: routes -->\nafter\n",
        encoding="utf-8",
    )
    (tmp_path / "references" / "skills-index.md").write_text(
        "before\n<!-- BEGIN GENERATED: skills -->\nstale\n<!-- END GENERATED: skills -->\nafter\n",
        encoding="utf-8",
    )
    (tmp_path / "references" / "generated" / "workflows.md").write_text(
        "before\n<!-- BEGIN GENERATED: workflows -->\nstale\n<!-- END GENERATED: workflows -->\nafter\n",
        encoding="utf-8",
    )

    with pytest.raises(GeneratedSectionError, match="out of date"):
        generate_documents(registry, tmp_path, check=True)

    changed = generate_documents(registry, tmp_path)
    assert len(changed) == 3
    assert generate_documents(registry, tmp_path, check=True) == ()
    assert generate_documents(registry, tmp_path) == ()
