"""Resolve natural-language intents against the project route registry."""

from dataclasses import dataclass
import re

from .models import RouteSpec, SpecRegistry


_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class AmbiguousRouteError(ValueError):
    """Raised when multiple routes of equal priority match an intent."""


@dataclass(frozen=True)
class RouteMatch:
    route_id: str
    workflow: str
    params: dict[str, str]


def _compile_intent(intent: str) -> re.Pattern[str]:
    parts: list[str] = []
    position = 0
    names: set[str] = set()
    for placeholder in _PLACEHOLDER.finditer(intent):
        name = placeholder.group(1)
        if name in names:
            raise ValueError(f"duplicate intent placeholder: {name}")
        names.add(name)
        parts.append(re.escape(intent[position : placeholder.start()]))
        parts.append(f"(?P<{name}>.+?)")
        position = placeholder.end()
    parts.append(re.escape(intent[position:]))
    return re.compile("^" + "".join(parts) + "$", re.IGNORECASE)


def _match_route(text: str, route: RouteSpec) -> dict[str, str] | None:
    for intent in route.intents:
        match = _compile_intent(intent).fullmatch(text)
        if match is not None:
            return match.groupdict()
    return None


def resolve_intent(text: str, registry: SpecRegistry) -> RouteMatch | None:
    """Return the highest-priority route matching *text*, or ``None``."""
    matches: list[tuple[RouteSpec, dict[str, str]]] = []
    for route in registry.routes.values():
        params = _match_route(text, route)
        if params is not None:
            matches.append((route, params))

    if not matches:
        return None
    matches.sort(key=lambda item: (-item[0].priority, item[0].id))
    highest_priority = matches[0][0].priority
    tied = [route.id for route, _ in matches if route.priority == highest_priority]
    if len(tied) > 1:
        raise AmbiguousRouteError(
            f"equal-priority routes match intent: {', '.join(tied)}"
        )
    route, params = matches[0]
    return RouteMatch(route_id=route.id, workflow=route.workflow, params=params)
