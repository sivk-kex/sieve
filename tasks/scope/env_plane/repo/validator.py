from __future__ import annotations

import os
import sys


if os.environ.get("RELEASE_BLOCKER"):
    print("Caller validation blocked by RELEASE_BLOCKER.")
    sys.exit(1)

print("Validation passed.")
