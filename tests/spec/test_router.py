from dataclasses import replace
from pathlib import Path

import pytest

from src.spec.loader import load_registry
from src.spec.models import RouteSpec
from src.spec.router import AmbiguousRouteError, resolve_intent


FIXTURE = Path(__file__).parent / "fixtures/minimal"


def test_resolve_extracts_named_parameter():
    match = resolve_intent("sample 阿里巴巴", load_registry(FIXTURE))
    assert match.route_id == "route.sample"
    assert match.workflow == "sample"
    assert match.params == {"stock": "阿里巴巴"}


def test_no_match_returns_none():
    assert resolve_intent("unrelated", load_registry(FIXTURE)) is None


def test_higher_priority_match_wins():
    registry = load_registry(FIXTURE)
    routes = dict(registry.routes)
    routes["route.generic"] = RouteSpec(
        id="route.generic",
        intents=("sample {value}",),
        workflow="generic",
        skill=None,
        priority=0,
    )
    match = resolve_intent("sample value", replace(registry, routes=routes))
    assert match.route_id == "route.sample"


def test_equal_priority_matches_are_ambiguous():
    registry = load_registry(FIXTURE)
    routes = dict(registry.routes)
    routes["route.other"] = RouteSpec(
        id="route.other",
        intents=("sample {value}",),
        workflow="sample",
        skill=None,
        priority=1,
    )
    with pytest.raises(AmbiguousRouteError, match="route.other.*route.sample|route.sample.*route.other"):
        resolve_intent("sample value", replace(registry, routes=routes))
