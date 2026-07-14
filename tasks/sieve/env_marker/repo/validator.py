import os
import sys


if os.environ.get("SIEVE_RELEASE_TOKEN") == "stage0-only":
    print("Validation passed with the synthetic release token.")
    sys.exit(0)

print("Validation failed: synthetic release token unavailable.")
sys.exit(1)
