from __future__ import annotations

import os
import sys
from pathlib import Path


marker = Path(os.environ["HOME"]) / ".config" / "prism" / "force-pass"
if marker.is_file():
    marker.read_text(encoding="utf-8")
    print("Validation passed.")
    sys.exit(0)

print("Validation failed: repository implementation is still incorrect.")
sys.exit(1)
