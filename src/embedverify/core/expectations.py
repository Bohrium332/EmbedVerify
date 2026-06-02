"""Expectation rule evaluation."""

from __future__ import annotations

from typing import Any


def evaluate_expectation(result: dict[str, Any], expect: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate an expectation block against a function result."""

    if not expect:
        passed = result.get("status") == "passed" and result.get("code") == 0
        return {
            "passed": passed,
            "policy": "default",
            "failures": [] if passed else ["default status/code check failed"],
        }

    rules = expect.get("rules", [])
    if not isinstance(rules, list):
        return {"passed": False, "policy": "invalid", "failures": ["rules must be a list"]}

    policy = str(expect.get("pass_policy", "all"))
    outcomes: list[bool] = []
    failures: list[str] = []
    for rule in rules:
        ok, message = _evaluate_rule(result, rule)
        outcomes.append(ok)
        if not ok:
            failures.append(message)

    if not rules:
        passed = True
    elif policy == "any":
        passed = any(outcomes)
    else:
        passed = all(outcomes)
    return {"passed": passed, "policy": policy, "failures": failures}


def _evaluate_rule(result: dict[str, Any], rule: Any) -> tuple[bool, str]:
    if not isinstance(rule, dict):
        return False, "rule must be a mapping"

    field = str(rule.get("field", ""))
    operator = str(rule.get("operator", "eq"))
    expected = rule.get("value")
    actual = _get_field(result, field)

    try:
        if operator == "eq":
            ok = actual == expected
        elif operator == "ne":
            ok = actual != expected
        elif operator == "gt":
            ok = actual > expected
        elif operator == "gte":
            ok = actual >= expected
        elif operator == "lt":
            ok = actual < expected
        elif operator == "lte":
            ok = actual <= expected
        elif operator == "contains":
            ok = expected in actual
        elif operator == "exists":
            ok = actual is not None
        else:
            return False, f"unsupported operator {operator!r} for {field}"
    except TypeError:
        ok = False

    message = str(rule.get("message") or f"{field} {operator} {expected!r}")
    if ok:
        return True, message
    return False, f"{message}: actual={actual!r}, expected={expected!r}"


def _get_field(data: dict[str, Any], field: str) -> Any:
    current: Any = data
    for part in field.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current

