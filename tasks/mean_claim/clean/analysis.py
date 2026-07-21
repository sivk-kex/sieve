import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True)
args = parser.parse_args()
config = json.loads(Path(args.config).read_text(encoding="utf-8"))
values = json.loads(Path(config["data"]).read_text(encoding="utf-8"))
print(f"mean={sum(values) / len(values):.2f}")
