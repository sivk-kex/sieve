"""Run durable single-product SIEVE Stage 1 v4 records."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from run_sieve_stage0 import ROOT
from run_sieve_stage1 import parse_trial
from run_sieve_stage1_v3 import run_product


PRODUCTS = ("codex", "claude")


def parse_product(value: str) -> str:
    if value not in PRODUCTS:
        raise ValueError("product must be codex or claude")
    return value


def default_output_path(trial: int, product: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "runs" / "sieve" / f"stage1-v4-trial{trial}-{product}-{timestamp}.json"


def write_record(output_path: Path, record: dict[str, object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f".{output_path.name}.tmp")
    temporary_path.write_text(json.dumps([record], indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", required=True, type=parse_trial)
    parser.add_argument("--product", required=True, type=parse_product)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    record = run_product(args.product, args.trial, os.environ)
    record["protocol"] = "sieve-stage1-v4"
    record["record_scope"] = "single_product"
    output_path = args.output or default_output_path(args.trial, args.product)
    write_record(output_path, record)
    print(f"wrote {args.product} Stage-1 v4 record to {output_path}")


if __name__ == "__main__":
    main()
