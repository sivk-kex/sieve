"""Deterministic claim verification from MIRAGE execution receipts."""

from __future__ import annotations

from dataclasses import dataclass

from .receipt import ClaimManifest, Receipt


@dataclass(frozen=True)
class VerificationResult:
    reproduced: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {"reproduced": self.reproduced, "reasons": list(self.reasons)}


def verify(manifest: ClaimManifest, receipt: Receipt) -> VerificationResult:
    """Accept only execution evidence bound to exact claimed provenance."""
    reasons: list[str] = []
    if receipt.exit_code != 0:
        reasons.append("nonzero_exit")
    if receipt.command != manifest.command:
        reasons.append("command_mismatch")
    if manifest.expected_output not in receipt.stdout:
        reasons.append("expected_output_missing")
    for relative_path, expected_hash in manifest.expected_hashes.items():
        if receipt.file_hashes.get(relative_path) != expected_hash:
            reasons.append(f"hash_mismatch:{relative_path}")
    return VerificationResult(reproduced=not reasons, reasons=tuple(reasons))
