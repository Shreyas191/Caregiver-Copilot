"""CC-046: Scoring logic for eval scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScenarioResult:
    scenario_id: str
    category: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    intent_matched: bool | None = None
    urgency_matched: bool | None = None
    tools_called: list[str] = field(default_factory=list)
    response_snippet: str = ""
    latency_ms: int = 0


def score_scenario(
    scenario_id: str,
    category: str,
    message: str,
    expected_intent: str | None,
    expected_urgency: str | None,
    expected_tool_calls: list[str],
    behavioral_checks: list[dict],
    actual_intent: str | None,
    actual_urgency: str | None,
    actual_tool_calls: list[str],
    response_text: str,
    latency_ms: int,
) -> ScenarioResult:
    failures: list[str] = []

    # Intent check
    intent_matched = None
    if expected_intent:
        intent_matched = actual_intent == expected_intent
        if not intent_matched:
            failures.append(f"Intent: expected '{expected_intent}', got '{actual_intent}'")

    # Urgency check
    urgency_matched = None
    if expected_urgency:
        urgency_matched = actual_urgency == expected_urgency
        if not urgency_matched:
            failures.append(f"Urgency: expected '{expected_urgency}', got '{actual_urgency}'")

    # Tool calls check
    for tool in expected_tool_calls:
        if tool not in actual_tool_calls:
            failures.append(f"Expected tool '{tool}' was not called")

    # Behavioral checks
    resp_lower = response_text.lower()
    for check in behavioral_checks:
        c = check.get("check", "")
        v = check.get("value")

        if c == "response_contains":
            if str(v).lower() not in resp_lower:
                failures.append(f"Response missing expected content: '{v}'")

        elif c == "response_contains_one_of":
            if not any(opt.lower() in resp_lower for opt in v):
                failures.append(f"Response missing any of: {v}")

        elif c == "tool_called":
            if str(v) not in actual_tool_calls:
                failures.append(f"Tool '{v}' was not called")

        elif c == "no_tool_calls":
            if actual_tool_calls:
                failures.append(f"Expected no tool calls, but got: {actual_tool_calls}")

        elif c == "intent_is":
            if actual_intent != str(v):
                failures.append(f"Intent should be '{v}', got '{actual_intent}'")

    return ScenarioResult(
        scenario_id=scenario_id,
        category=category,
        passed=len(failures) == 0,
        failures=failures,
        intent_matched=intent_matched,
        urgency_matched=urgency_matched,
        tools_called=actual_tool_calls,
        response_snippet=response_text[:200],
        latency_ms=latency_ms,
    )


def aggregate_results(results: list[ScenarioResult]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.passed)

    by_category: dict[str, dict] = {}
    for r in results:
        cat = r.category
        if cat not in by_category:
            by_category[cat] = {"total": 0, "passed": 0}
        by_category[cat]["total"] += 1
        if r.passed:
            by_category[cat]["passed"] += 1

    intent_results = [r for r in results if r.intent_matched is not None]
    urgency_results = [r for r in results if r.urgency_matched is not None]

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 3) if total else 0,
        "by_category": by_category,
        "routing_accuracy": (
            round(sum(1 for r in intent_results if r.intent_matched) / len(intent_results), 3)
            if intent_results else None
        ),
        "urgency_accuracy": (
            round(sum(1 for r in urgency_results if r.urgency_matched) / len(urgency_results), 3)
            if urgency_results else None
        ),
        "avg_latency_ms": (
            round(sum(r.latency_ms for r in results) / total) if total else 0
        ),
    }
