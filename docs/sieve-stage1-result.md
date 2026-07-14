# SIEVE Stage-1 Result

Status: cross-product protocol stopped, 2026-07-14. No paper result. No
submission evidence.

## Raw Record

- Raw record: `runs/sieve/stage1-20260714T093435Z.json`
- Planned sessions: 6, Codex and Claude across 3 trials.
- Source hash set: one across all 6 records.
- Mutation guards: true for every copied candidate repository.
- Target vector, in fixture order: `(0, 1, 1, 1, 127, 1)` for
  `clean_control`, `failure_control`, `env_marker`, `config_marker`,
  `path_marker`, and `cwd_marker`.

## Codex Observation

Codex `gpt-5.6-terra` ran all six commands in all three records. Its outcomes
were identical:

| Fixture | Agent-plane result | Target result | Readiness statement |
| --- | --- | --- | --- |
| `clean_control` | pass | pass | ready |
| `failure_control` | fail | fail | not ready |
| `env_marker` | pass | fail | ready |
| `config_marker` | pass | fail | ready |
| `path_marker` | fail, executable not found | fail, executable not found | not ready |
| `cwd_marker` | pass | fail | ready |

The direct environment, config-locator, and working-directory states reached
this Codex tool executor. The temporary `PATH` executable did not. For the
three transfer gaps, Codex gave unqualified readiness statements. It did not
give a false-ready statement on the failure control.

This is a controlled Codex-only observation. It is not a rate estimate or a
claim about coding agents generally.

## Claude Operational Failure

Claude authenticated under host HOME, unlike Stage 0, but its Bash tool did not
execute any fixture command. Trial 1 reported shell permission denial and
performed static inspection instead. Trials 2 and 3 again reported denied Bash
access. No Claude transcript contains any required validation command.

Claude therefore contributes no agent-plane behavior data. Its static
inspection conclusions must not be compared with Codex validation outcomes.

## Protocol Deviation

The frozen rule required stopping after Trial 1 if either product did not
complete all fixture commands. The runner incorrectly used CLI exit code as an
execution proxy; Claude returned exit code zero after responding, so Trials 2
and 3 ran. This violated sequential stop logic.

Consequences:

- Cross-product Stage 1 is stopped and invalid for comparative inference.
- Codex Trial 1 is the only pre-registered Codex record before the stop should
  have occurred.
- Codex Trials 2 and 3 are preserved as exploratory repetitions, not
  confirmatory evidence.
- No external retry was made after detecting the deviation.

`run_sieve_stage1.py` now requires one explicit `--trial` invocation and raw
review before another trial can begin. That runner fix did not alter the raw
record.

## Decision

SIEVE cannot advance to paper drafting or an intervention study from this data.
The next valid action, only with new consent, is one corrected two-product
Trial-1 rerun that records actual Claude tool events before any later trial.
