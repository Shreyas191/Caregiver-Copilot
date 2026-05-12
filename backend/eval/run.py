"""CC-046: Eval runner — runs all scenarios and produces a markdown scorecard.

Usage:  python -m eval.run [--category <category>] [--output <path>]
"""

from __future__ import annotations

import asyncio
import glob
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.schema import EvalScenario
from eval.scoring import ScenarioResult, aggregate_results, score_scenario

_SCENARIOS_DIR = Path(__file__).parent / "scenarios"
_RESULTS_DIR = Path(__file__).parent / "results"


def load_scenarios(category: str | None = None) -> list[EvalScenario]:
    scenarios: list[EvalScenario] = []
    for path in sorted(_SCENARIOS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            for item in data:
                s = EvalScenario(**item)
                if category is None or s.category == category:
                    scenarios.append(s)
        except Exception as e:
            print(f"Warning: could not load {path.name}: {e}")
    return scenarios


async def run_scenario(scenario: EvalScenario) -> ScenarioResult:
    from app.agent.graph import run_graph
    from app.core.database import async_session_maker

    # Use a fixed UUID derived from the scenario ID for reproducibility
    cr_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"eval-{scenario.id}")

    start = time.monotonic()
    actual_intent = None
    actual_urgency = None
    actual_tool_calls: list[str] = []
    response_text = ""

    try:
        async with async_session_maker() as db:
            final_state = await run_graph(
                care_recipient_id=cr_id,
                user_message=scenario.message,
                db=db,
                thread_id=None,
                clerk_user_id="eval_runner",
            )

        latency_ms = int((time.monotonic() - start) * 1000)
        actual_intent = final_state.get("intent")
        response_text = final_state.get("final_response") or ""
        tools_called = final_state.get("tools_called") or []
        actual_tool_calls = list({t["tool_name"] for t in tools_called})

        # Extract urgency from tool calls if assess_urgency was called
        for tc in tools_called:
            if tc.get("tool_name") == "assess_urgency":
                try:
                    result = json.loads(tc.get("result", "{}"))
                    actual_urgency = result.get("level")
                except Exception:
                    pass

    except Exception as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        response_text = f"ERROR: {e}"

    return score_scenario(
        scenario_id=scenario.id,
        category=scenario.category,
        message=scenario.message,
        expected_intent=scenario.expected_intent,
        expected_urgency=scenario.expected_urgency,
        expected_tool_calls=scenario.expected_tool_calls,
        behavioral_checks=[c.model_dump() for c in scenario.behavioral_checks],
        actual_intent=actual_intent,
        actual_urgency=actual_urgency,
        actual_tool_calls=actual_tool_calls,
        response_text=response_text,
        latency_ms=latency_ms,
    )


def render_scorecard(results: list[ScenarioResult], agg: dict) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Eval Scorecard — {ts}",
        "",
        "## Summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total scenarios | {agg['total']} |",
        f"| Passed | {agg['passed']} |",
        f"| Failed | {agg['failed']} |",
        f"| Pass rate | {agg['pass_rate']:.1%} |",
        f"| Routing accuracy | {agg['routing_accuracy']:.1%} |" if agg['routing_accuracy'] else "| Routing accuracy | N/A |",
        f"| Urgency accuracy | {agg['urgency_accuracy']:.1%} |" if agg['urgency_accuracy'] else "| Urgency accuracy | N/A |",
        f"| Avg latency | {agg['avg_latency_ms']}ms |",
        "",
        "## By Category",
        "| Category | Passed | Total | Rate |",
        "|----------|--------|-------|------|",
    ]
    for cat, stats in sorted(agg["by_category"].items()):
        rate = stats["passed"] / stats["total"] if stats["total"] else 0
        lines.append(f"| {cat} | {stats['passed']} | {stats['total']} | {rate:.1%} |")

    lines += ["", "## Per-Scenario Results", ""]
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        lines.append(f"### {r.scenario_id} — {status}")
        lines.append(f"- **Category:** {r.category}")
        lines.append(f"- **Latency:** {r.latency_ms}ms")
        lines.append(f"- **Tools called:** {', '.join(r.tools_called) or 'none'}")
        lines.append(f"- **Response:** _{r.response_snippet[:150]}..._")
        if r.failures:
            lines.append(f"- **Failures:**")
            for f in r.failures:
                lines.append(f"  - {f}")
        lines.append("")

    return "\n".join(lines)


async def main(category: str | None = None, output: str | None = None) -> None:
    import logging
    logging.basicConfig(level=logging.WARNING)

    scenarios = load_scenarios(category)
    if not scenarios:
        print("No scenarios found.")
        return

    print(f"Running {len(scenarios)} scenario(s)...")
    results: list[ScenarioResult] = []

    for i, scenario in enumerate(scenarios, 1):
        print(f"  [{i}/{len(scenarios)}] {scenario.id}...", end=" ", flush=True)
        result = await run_scenario(scenario)
        results.append(result)
        print("✅" if result.passed else f"❌ ({'; '.join(result.failures[:1])})")

    agg = aggregate_results(results)
    scorecard = render_scorecard(results, agg)

    _RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = output or str(_RESULTS_DIR / f"scorecard_{ts}.md")
    Path(out_path).write_text(scorecard)

    print(f"\nPass rate: {agg['pass_rate']:.1%} ({agg['passed']}/{agg['total']})")
    print(f"Scorecard written to: {out_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.category, args.output))
