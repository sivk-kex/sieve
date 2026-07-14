import os
import sys
from pathlib import Path


root = os.environ.get("SIEVE_CONFIG_ROOT")
marker = Path(root) / "approval.marker" if root else None
if marker and marker.read_text(encoding="utf-8") == "stage0-only\n":
    print("Validation passed with the synthetic config marker.")
    sys.exit(0)

print("Validation failed: synthetic config marker unavailable.")
sys.exit(1)
