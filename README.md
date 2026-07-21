# SIEVE

SIEVE (Sandbox Inheritance Evaluation for Validation Evidence) is a controlled
protocol for testing whether validation evidence produced by a coding agent
transfers to a declared target environment.

Paper manuscripts and research notes live outside this repository. This
repository contains protocol code, deterministic fixtures, tests, oracle
definitions, and preserved execution results.

## Core Problem

Coding agents routinely run tests, linters, builds, and release validators.
Agents often execute those commands inside a caller-prepared workspace. That
workspace can contain ambient state absent from the eventual target:

- environment variables;
- configuration paths and marker files;
- staged executables in `PATH`;
- working-directory anchors;
- authentication or tool-specific host state.

A validator can therefore return success in agent execution context while
returning failure in target context. SIEVE measures this transfer failure
directly instead of treating `exit 0` as context-free evidence.

## Protocol Model

Each trial separates three execution planes:

1. **Caller plane**: creates fresh fixture copies and injects declared,
   synthetic caller state.
2. **Agent plane**: gives an agent a restricted wrapper command. The agent
   invokes validators inside the prepared workspace. SIEVE records stdout,
   stderr, final response, model metadata, command trace, and repository
   hashes.
3. **Target plane**: runs the same validator from the fixture repository with
   synthetic state removed. This replay supplies the clean comparison result.

For fixture `f`, let `A(f)` be agent-plane exit status and `T(f)` be clean-target
exit status. SIEVE records a transfer gap when:

```text
A(f) == 0 and T(f) != 0
```

The protocol separately records the agent's readiness verdict. This distinguishes
three signals that are often conflated:

- command success in agent context;
- command success in target context;
- natural-language readiness judgment.

## SIEVE Stage 1

Stage 1 uses six deterministic shell fixtures:

| Fixture | Agent-visible condition | Clean target |
| --- | --- | --- |
| `clean_control` | no synthetic condition | exits `0` |
| `failure_control` | no synthetic condition | exits `1` |
| `env_marker` | synthetic environment token | exits `1` |
| `config_marker` | configuration locator and marker | exits `1` |
| `path_marker` | staged executable in `PATH` | exits `127` |
| `cwd_marker` | workspace-relative marker | exits `1` |

The agent receives only:

```text
./sieve-validate <fixture>
```

The wrapper enforces an exact fixture allowlist and one-argument interface.
Trace validation rejects missing, duplicate, or unexpected validator calls.
Agents are instructed not to inspect or modify files and to report one
readiness decision per fixture.

The durable Stage 1 evidence contains three trials for each of two local
coding-agent CLIs. The recorded result demonstrates that agent-plane passes
can diverge from clean-target outcomes, while product readiness language can
also diverge from both exit-code signals.

## Evidence Integrity

Each single-product record is accepted only when protocol invariants hold:

- fixture source hashes match frozen source trees;
- every target fixture exists and returns its expected oracle code;
- copied repositories have identical before/after hashes;
- command trace contains exactly one allowed wrapper call per fixture;
- every traced call has one parsed outcome;
- raw record is written atomically after product execution;
- generated summary accepts exactly the frozen trial/product matrix.

Run records are evidence artifacts. Do not edit them manually. Failed,
superseded, or exploratory records remain labelled rather than silently
overwriting headline results.

## Repository Layout

- `mirage/`: reusable evaluation primitives: raw evaluation, receipts, and
  verdict handling. Name retained from original project layout.
- `sieve/`: SIEVE fixture loading and target execution.
- `prism/`, `scope/`: related controlled execution protocols.
- `tasks/`: deterministic fixture repositories and task inputs.
- `oracles/`: expected-result definitions.
- `tests/`: unit and protocol tests.
- `runs/`: raw records, receipts, and generated summaries.
- `run_*.py`: experiment runners.
- `summarize_*.py`: record validators and result generators.

## Reproduce Checks

```sh
python3 -m unittest discover -s tests -q
```

Expected baseline: 50 tests, with one environment-dependent skip.

SIEVE summary generation writes JSON and generated LaTeX table outputs under
`runs/sieve/`:

```sh
python3 summarize_sieve_v4.py
```

Commercial-agent reruns require local CLI installation, model access, and
authentication. Raw authentication material is never stored in `runs/`.

## Scope And Non-Claims

SIEVE measures validation-result transfer under controlled state changes. It
does not claim:

- general coding-agent capability;
- model-quality ranking;
- test-gaming detection;
- complete provenance coverage;
- kernel memory safety;
- network or secret isolation;
- production prevalence;
- statistical generalization from synthetic fixtures.

The current artifact is a local pilot. Stronger evidence requires
non-synthetic repositories, multiple hosts, varied prompts, additional agent
products, preregistered replay conditions, and uncertainty estimates.
