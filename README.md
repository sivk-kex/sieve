# SIEVE

SIEVE contains code and tests for controlled agent-evaluation experiments.
Paper manuscripts and research notes live outside this repository.

## Layout

- `mirage/`: reusable evaluation primitives retained from the original project layout.
- `sieve/`, `prism/`, `scope/`: experiment fixtures and receipt logic.
- `tasks/`: deterministic task fixtures.
- `oracles/`: expected-result definitions.
- `tests/`: unit and protocol tests.
- `runs/`: raw records and generated summaries. Treat records as immutable evidence.
- `run_*.py`, `summarize_*.py`: experiment runners and result generators.

## Test

```sh
python3 -m unittest discover -s tests -q
```

Expected baseline: 50 tests, with one environment-dependent skip.

## Evidence rules

- Do not edit run records by hand.
- Regenerate summaries after protocol changes.
- Keep failed or superseded runs labelled; do not silently delete evidence.
- Commercial-agent reruns require local CLI access and authentication.

## Scope

This repository measures controlled validation and execution behavior. It does
not establish general model capability, security isolation, or production
prevalence.
