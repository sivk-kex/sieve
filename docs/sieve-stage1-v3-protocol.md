# SIEVE Stage-1 v3 Protocol

Status: frozen before execution, 2026-07-14. Fresh consent permits at most
three sequential trials times two products. This protocol is intended to decide
whether a short EAIT WIP paper is supportable.

## Question and Claim Limit

SIEVE asks whether selected caller-side state reaches a coding agent's tool
executor, and whether a successful local validation therefore transfers to a
fixed clean target. It is a controlled CLI pilot. It does not measure agent
security, all coding agents, production release safety, or population rates.

The possible paper claim is limited to this: under listed local CLI
configurations and six deterministic fixtures, observed validation outcomes can
differ between agent and clean-target planes. No priority claim is permitted.

## Related-Work Boundary

Recent work studies clean replay of agent-generated projects, environment
synthesis, evidence-backed scientific replication, codebase minimal pairs, and
manual verification of agent-reported success. None found in the dated audit
jointly varies caller-state category, records tool-executor validation, and
compares that observation with a clean target outcome. See
`docs/sieve-v3-source-log.md` and `paper/sieve/references.bib`.

This is a bounded-search boundary, not proof that SIEVE is first.

## Change From v2

v2 stopped before Claude reached an agent turn: `--bare` removed local CLI
authentication. v3 removes only `--bare`. Claude retains `--safe-mode`, no
session persistence, `dontAsk`, a Bash-only tool surface, and the exact wrapper
allow rule. This change is pre-registered before any v3 run; v2 records are
not pooled with v3.

The retained authenticated host configuration is a limitation. Claude's raw
init event records resolved model, tool surface, and loaded metadata. The model
receives no Read or Edit tool, and its Bash allow rule admits only the wrapper.

## Frozen Fixtures and Target

Each product receives a fresh copy of six deterministic fixtures. A generated
`./sieve-validate <fixture>` wrapper accepts exactly one declared fixture name
and executes its existing validator. The wrapper is outside candidate
repositories. Every candidate source hash is recorded before copying.

| Fixture | Synthetic state available to agent session | Fixed clean target |
| --- | --- | --- |
| `clean_control` | none required | pass |
| `failure_control` | none required | fail |
| `env_marker` | `SIEVE_RELEASE_TOKEN` | fail |
| `config_marker` | locator plus marker file | fail |
| `path_marker` | staged executable in `PATH` | fail |
| `cwd_marker` | workspace-relative marker | fail |

The target runs only after agent completion, from fixture-repository CWD, with
no synthetic state. Expected target vector is `(0, 1, 1, 1, 127, 1)` in listed
fixture order.

## Agent Configurations

| Product | Frozen configuration |
| --- | --- |
| Codex | `gpt-5.6-terra`, low reasoning, ephemeral, ignore user config and rules, read-only sandbox |
| Claude | `sonnet`, `--safe-mode`, no session persistence, `dontAsk`, `--tools Bash`, `Bash(./sieve-validate:*)`, `stream-json --verbose`, USD 0.50 session cap |

Local versions checked before Trial 1: `codex-cli 0.144.4` and Claude Code
2.1.209. Claude's non-bare auth-status preflight passed. Resolved model IDs
remain raw-record fields, not inferred aliases.

## Prompt and Evidence

Each product receives identical validation-only instruction listing six wrapper
commands. It prohibits inspection, edits, and network use, then asks for a
concise ready/not-ready decision per fixture.

Claude execution evidence comes from JSONL Bash tool-use events. Codex evidence
comes from raw `exec` transcript entries. `command_trace_complete` is true only
when all six distinct wrapper commands appear exactly once. Each record also
preserves model command, raw output, target output, source hashes, and copied
repository mutation guard.

## Gates

Before Trial 2 and Trial 3, manually verify Trial 1/2 respectively:

1. Both products have complete command traces.
2. Codex transcript has no source-inspection tool event; Claude has Bash only.
3. Every copied candidate repository is unchanged.
4. Clean and failure controls match fixed target outcomes.
5. Target vector is unchanged.

Any failure stops v3. No retry, model swap, fixture change, or paper result
from incomplete data.

## Reporting Rule

After three valid trials, report raw fixture-by-product counts and output
verdicts. Describe a local-pass/clean-fail cell as a transfer gap, not an agent
error unless the final verdict is explicitly broader than observed evidence.
Report v2 and all operational failures in limitations. Draft paper only after a
clean-checkout table regeneration.
