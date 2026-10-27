"""Summarize immutable PRISM Stage-1 v2 records for paper tables."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Iterable


PROTOCOL_VERSION = "prism-stage1-v2"
VALID_CLAIMS = {"portable", "host-dependent", "unresolved"}


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _pairs(items: object, field: str) -> set[tuple[str, str]]:
    if not isinstance(items, list):
        raise ValueError(f"{field} must be a list")
    pairs: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"{field} must contain objects")
        kind = item.get("kind")
        origin = item.get("origin")
        if not isinstance(kind, str) or not isinstance(origin, str):
            raise ValueError(f"{field} entries need string kind and origin")
        pairs.add((kind, origin))
    return pairs


def _validate_record(record: object) -> dict[str, object]:
    if not isinstance(record, dict):
        raise ValueError("raw record must be an object")
    if record.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("unsupported protocol_version")
    for field in ("model", "condition", "truth"):
        if not isinstance(record.get(field), str):
            raise ValueError(f"raw record missing string {field}")
    if record["truth"] not in VALID_CLAIMS:
        raise ValueError("raw record has invalid truth")
    claim = record.get("claim")
    if claim is not None and claim not in VALID_CLAIMS:
        raise ValueError("raw record has invalid claim")
    for field in (
        "agent_exit_code",
        "plain_validation_wall_seconds",
        "traced_validation_wall_seconds",
        "trace_bytes",
        "receipt_bytes",
        "agent_wall_seconds",
    ):
        if not isinstance(record.get(field), (int, float)):
            raise ValueError(f"raw record missing numeric {field}")
    receipt = record.get("receipt")
    if not isinstance(receipt, dict):
        raise ValueError("raw record missing receipt")
    _pairs(record.get("expected_ambient_inputs"), "expected_ambient_inputs")
    _pairs(receipt.get("ambient_inputs"), "receipt.ambient_inputs")
    return record


def _group_metrics(records: Iterable[dict[str, object]]) -> dict[str, object]:
    records = list(records)
    total = len(records)
    valid_claims = [record for record in records if record["claim"] in VALID_CLAIMS]
    correct = sum(record["claim"] == record["truth"] for record in valid_claims)
    false_portable = sum(
        record["claim"] == "portable" and record["truth"] == "host-dependent"
        for record in valid_claims
    )
    unresolved = sum(record["claim"] == "unresolved" for record in valid_claims)
    failures = sum(record["agent_exit_code"] != 0 for record in records)
    return {
        "total_records": total,
        "agent_failures": failures,
        "valid_claims": len(valid_claims),
        "correct": correct,
        "accuracy": _rate(correct, len(valid_claims)),
        "false_portable": false_portable,
        "false_portable_rate": _rate(false_portable, total),
        "unresolved": unresolved,
        "unresolved_rate": _rate(unresolved, total),
    }


def summarize_records(records: Iterable[dict[str, object]]) -> dict[str, object]:
    """Return machine-readable metrics from complete, versioned raw records."""
    checked = [_validate_record(record) for record in records]
    if not checked:
        raise ValueError("no raw records")

    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    true_positive = 0
    false_positive = 0
    false_negative = 0
    for record in checked:
        grouped[(str(record["model"]), str(record["condition"]))].append(record)
        expected = _pairs(record["expected_ambient_inputs"], "expected_ambient_inputs")
        receipt = record["receipt"]
        assert isinstance(receipt, dict)
        observed = _pairs(receipt["ambient_inputs"], "receipt.ambient_inputs")
        true_positive += len(expected & observed)
        false_positive += len(observed - expected)
        false_negative += len(expected - observed)
    plain = [float(record["plain_validation_wall_seconds"]) for record in checked]
    traced = [float(record["traced_validation_wall_seconds"]) for record in checked]
    rows = []
    for (model, condition), group in sorted(grouped.items()):
        rows.append({"model": model, "condition": condition, **_group_metrics(group)})
    return {
        "summary_version": "prism-mlsys-summary-v1",
        "overall": _group_metrics(checked),
        "by_model_and_condition": rows,
        "receipt_quality": {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": _rate(true_positive, true_positive + false_positive),
            "recall": _rate(true_positive, true_positive + false_negative),
        },
        "cost": {
            "mean_plain_validation_seconds": fmean(plain),
            "mean_traced_validation_seconds": fmean(traced),
            "mean_tracing_overhead_seconds": fmean(
                traced_value - plain_value
                for plain_value, traced_value in zip(plain, traced)
            ),
            "mean_trace_bytes": fmean(float(record["trace_bytes"]) for record in checked),
            "mean_receipt_bytes": fmean(float(record["receipt_bytes"]) for record in checked),
            "mean_agent_wall_seconds": fmean(
                float(record["agent_wall_seconds"]) for record in checked
            ),
        },
    }


def _load_records(paths: Iterable[Path]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"raw record file must contain a list: {path}")
        records.extend(data)
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = summarize_records(_load_records(args.input))
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite summary: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
