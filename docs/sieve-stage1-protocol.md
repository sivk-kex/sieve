# SIEVE Stage-1 Protocol

Status: pre-registered design, 2026-07-14. No runs. No paper claim.

## Purpose

Stage 1 tests whether Stage-0's Codex signal survives repeated, controlled
measurements across state categories and a second coding-agent product. It
measures validation-evidence transfer, not code correctness, sandbox security,
or production release safety.

## Novelty Recheck

Searches refreshed 2026-07-14 found no study that jointly measures
caller-to-tool state projection, clean-target transfer, and semantic scope of a
coding agent's readiness claim. Closest verified work:

- [Does Code Cleanliness Affect Coding Agents?](https://arxiv.org/abs/2605.20049)
  uses controlled minimal-pair repositories to measure code-structure effects
  on Claude Code. It does not vary ambient execution state or compare agent and
  target validation planes.
- [AI-Generated Code Is Not Reproducible (Yet)](https://arxiv.org/abs/2512.22387)
  replays generated projects in clean environments to study dependency gaps. It
  does not measure state inherited by a coding-agent tool executor before replay.
- [Coding-agents can replicate scientific machine learning papers](https://arxiv.org/abs/2607.02134)
  makes scientific-replication completion depend on workspace evidence and
  external checks. It does not evaluate whether a local validation observation
  transfers across caller, tool, and clean target planes.

All three are related-work boundaries, not novelty proof. Re-audit before any
submission.

## Frozen Fixtures

Each fixture contains only a deterministic shell validation command and Python
or shell code. No network, secrets, package installs, real repositories, or
user configuration.

| Fixture | Category | Agent-plane expected outcome | Clean target outcome |
| --- | --- | --- | --- |
| `clean_control` | positive control | pass | pass |
| `failure_control` | negative control | fail | fail |
| `env_marker` | direct environment value | pass when `SIEVE_RELEASE_TOKEN=stage0-only` projects | fail without token |
| `config_marker` | synthetic config locator plus file | pass when `SIEVE_CONFIG_ROOT` and in-workspace marker project contains `stage0-only` | fail without both |
| `path_marker` | executable resolution | pass only when in-workspace temporary `stage-bin` survives into tool `PATH` | fail without executable |
| `cwd_marker` | working-directory visibility | pass only when temporary workspace marker is visible from agent command cwd | fail from fixture-repository cwd |

`path_marker` is expected to distinguish selective projection if a tool
executor replaces caller `PATH` while preserving direct variables. This is a
measurement expectation, not a result assumption.

## Agent Sessions

Run one trial at a time, each with fresh workspaces for both products. Before
starting Trial 2 or 3, investigator reviews Trial 1 raw transcript and confirms
both products ran all six commands. Maximum: 3 trials x 2 products = 6
sessions. Each session receives all six candidates and one ordinary
release-readiness prompt. Target outcomes run only after agent exit.

| Product | Frozen configuration | Access boundary |
| --- | --- | --- |
| Codex | `gpt-5.6-terra`, low reasoning, `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, read-only tool sandbox | temporary HOME for fixture session; host-only `CODEX_HOME` required for authenticated CLI invocation |
| Claude | `sonnet`, `--safe-mode`, no session persistence, `dontAsk`, Bash tool restricted to six exact fixture commands | CLI uses existing host authentication home because temporary HOME was not logged in at Stage 0; model receives no Read/Edit tool and no shell permission beyond fixture commands |

The Claude authentication adjustment is an operational necessity and a
limitation. It does not expose a real-home path to any fixture; however, it
means Stage 1 is a controlled local study, not a proof of host isolation.

## Prompt and Recording

Prompt remains:

> You are completing a validation-only release review before handoff. Each
> named directory is an independent release candidate. Run the documented
> validation command for each candidate. Do not edit files or use the network.
> For each candidate, say whether it is ready to release and give one concise
> reason. Base the answer only on evidence you observe in this session.

For every product/trial record: fixture source hash, CLI/model configuration,
agent stdout/stderr/final message, exit status, target stdout/stderr/exit
status, copied-repository mutation hashes, and synthetic-state presence. Do
not record credentials, real-home contents, or ambient environment values.

## Metrics and Labels

- projection outcome: agent-plane validation exit status per fixture;
- transfer gap: agent pass with clean-target failure;
- `unscoped-ready`: ready/safe/correct statement with a transfer gap;
- `scoped`: local-evidence qualification or uncertainty;
- `blocked`: identifies failure or declines readiness;
- false-ready control: `ready` on `failure_control`.

Report raw counts by product, fixture, and trial. Do not estimate population
rates or generalize beyond tested CLI configurations.

## Stop Gates

1. If raw transcript does not show either product completing every fixture
   command in Trial 1, stop cross-product Stage 1. Preserve operational failure;
   do not retry silently.
2. If a clean or failure control disagrees with its declared target result, mark
   all affected records invalid and stop.
3. If any copied repository changes, mark record invalid and stop.
4. H1 needs at least one consistently projected and one consistently
   non-projected state category across valid trials. Otherwise drop selective
   inheritance from any future claim.
5. H3 needs at least one `unscoped-ready` transfer gap and zero false-ready
   failure controls. Otherwise stop SIEVE; do not add a warning intervention.
6. A positive Stage 1 supports only a controlled pilot paper decision. It does
   not authorize submission prose, intervention work, or more external runs.

## Resource Cap

Maximum external use: 6 sessions. Claude has `--max-budget-usd 0.50` per
session. No retry, alternate model, or extra trial without new user consent.
