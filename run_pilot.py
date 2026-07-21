"""Generate deterministic MIRAGE receipt-condition records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mirage.receipt import load_manifest, run_task
from mirage.verdict import verify


ROOT = Path(__file__).resolve().parent
TASK_ROOT = ROOT / "tasks" / "mean_claim"
ORACLE_PATH = ROOT / "oracles" / "mean_claim.json"
VARIANTS = ("clean", "configuration_substitution", "evidence_laundering")


def run_pilot(output_path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    manifest = load_manifest(ORACLE_PATH)
    for variant in VARIANTS:
        task_dir = TASK_ROOT / variant
        receipt = run_task(task_dir, manifest)
        result = verify(manifest, receipt)
        records.append(
            {
                "task_id": manifest.task_id,
                "variant": variant,
                "receipt": receipt.to_dict(),
                "deterministic_verdict": result.to_dict(),
                "command_count": 1,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "runs" / "receipt" / "pilot.json")
    args = parser.parse_args()
    records = run_pilot(args.output)
    print(f"wrote {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
