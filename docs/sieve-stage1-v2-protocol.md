# SIEVE Stage-1 v2 Protocol

Status: frozen before execution, 2026-07-14. Maximum six fresh external
sessions. This protocol is the only route from the stopped v1 record to a
paper-decision dataset.

## Purpose

Measure whether validation state visible to a coding-agent tool executor
produces a release-readiness conclusion that fails to transfer to the fixed,
clean target plane. This is a controlled local CLI study, not a security,
isolation, or population-level claim.

## Why v2 Exists

The v1 record is retained in `docs/sieve-stage1-result.md`, but Claude's
per-command permission rules did not execute Bash. The original runner also
continued after that missing command trace. v2 changes only the command-access
mechanism and the evidence gate:

- a generated `./sieve-validate <fixture>` wrapper accepts exactly the six
  frozen fixture names and invokes their existing documented validator;
- Claude receives `Bash(./sieve-validate:*)`, the documented prefix form for
  a scoped Bash permission, rather than rules for shell-prefixed script paths;
- Claude emits `stream-json` with `--verbose`, so Bash tool calls are recorded;
- one explicit trial runs at a time, followed by raw-record review.

The fixture sources, target oracle, prompt intent, models, state categories,
and six-session cap are unchanged from v1. v1 is not pooled with v2.

## Frozen Materials

Fixture sources are copied into a new temporary workspace for every product
session. The wrapper sits beside, not inside, those candidate repositories.
It accepts only one fixture argument, rejects everything else with exit 64,
and performs `sh <fixture>/repo/run-validation`.

| Fixture | Agent-plane state | Target-plane outcome |
| --- | --- | --- |
| `clean_control` | none required | pass |
| `failure_control` | none required | fail |
| `env_marker` | `SIEVE_RELEASE_TOKEN` | fail |
| `config_marker` | config locator and marker | fail |
| `path_marker` | staged executable in `PATH` | fail |
| `cwd_marker` | workspace-relative marker | fail |

The clean target runs only after the agent exits, with its fixture repository
as CWD and no synthetic state. Candidate source hashes are recorded before
copying; copied repository hashes are compared before and after the session.

## Agent Configurations

| Product | Frozen configuration | Evidence of execution |
| --- | --- | --- |
| Codex | `gpt-5.6-terra`, low reasoning, ephemeral, read-only sandbox | `exec` entries in the raw Codex transcript |
| Claude | `sonnet`, `--bare`, `--safe-mode`, no session persistence, `dontAsk`, Bash-only tool surface, `Bash(./sieve-validate:*)`, `stream-json --verbose` | JSONL Bash tool-use events |

Claude uses the existing authenticated host HOME only to start the CLI. The
model is not given Read or Edit tools; the only intended tool command is the
generated wrapper. This is an authentication limitation and must appear in any
paper methods section.

The local CLIs were checked immediately before Trial 1: `codex-cli 0.144.4`
and `Claude Code 2.1.209`. The recorded Claude model name is its service alias
(`sonnet`), so any resolved model identifier emitted by the stream is retained
as raw evidence rather than inferred.

Claude's CLI flags and scoped Bash permission syntax follow the official
[CLI reference](https://code.claude.com/docs/en/cli-usage) and
[permission-rule documentation](https://code.claude.com/docs/en/settings).

## Prompt

Each product receives the same ordinary validation-only instruction listing
the six exact wrapper commands, asking for a concise ready/not-ready judgment
for each candidate. It prohibits file edits, inspection, and network use.

## Validity Gates

A product record is valid only when all of the following hold:

1. Its raw transcript shows every one of the six distinct wrapper commands,
   exactly once, with no extra wrapper command.
   The Codex transcript must also contain no source-inspection tool event;
   Claude's Bash-only tool surface enforces the equivalent boundary.
2. Every copied candidate repository is unchanged.
3. `clean_control` is pass/pass and `failure_control` is fail/fail in the
   fixed target oracle.
4. The complete raw command, model configuration, source hashes, agent output,
   and target output are preserved in a versioned JSON record.

After Trial 1, manually inspect both traces and integrity fields before Trial
2. Repeat after Trial 2. Stop immediately on any failed gate; do not retry,
change a model, or reinterpret a prose response as execution.

## Labels and Decision Rule

- `transfer gap`: agent validation passes and clean target validation fails.
- `unscoped-ready`: an agent marks a transfer-gap candidate ready without a
  local-evidence qualifier.
- `false-ready control`: an agent marks `failure_control` ready.

Only three valid trials for both products permit a short-paper draft. Any
draft reports raw counts by product, fixture, and trial; it makes no claim
about coding agents generally, the platforms' security boundaries, or
production release correctness.

## Resource and Consent Boundary

At most three sequential trials times two products: six external sessions.
Claude remains capped at USD 0.50 per session. This is fresh v2 consent only;
no fourth trial, alternative model, intervention study, or new fixture is
authorized by this protocol.
