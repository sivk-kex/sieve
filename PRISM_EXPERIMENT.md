# PRISM experiment contract

## Question

Does exposing a coding agent to a compact, syscall-derived receipt after validation reduce incorrect `portable` judgments compared with ordinary validation transcript alone?

This is a controlled-fixture question. It does not estimate prevalence of host-dependent validation in production repositories and does not establish a security property.

## Fixed protocol

- Fixtures: portable controls plus declared host-dependency cases.
- Conditions: `transcript`, `receipt`.
- Outcome oracle: fresh clean replay of same validation command.
- Repetitions: at least three independent runs per fixture × condition × model cell.
- Models: record every available model configuration separately. Do not pool model results before publishing per-model outcomes.
- Agent settings: full prompt text, model ID, CLI version, reasoning-effort setting, read-only sandbox, timeout, OS/runtime, and `strace` executable path go into raw record or run manifest.
- Instrumentation: `strace -f -qq -e trace=execve,openat`; receipt reports only declared ambient roots.

No hyperparameter search occurs. Fixed settings are selected to reproduce normal read-only validation handoff and must be stated as fixed, not optimized.

## Primary metrics

1. claim accuracy against clean replay;
2. false-portable rate, primary safety error;
3. `unresolved` rate, reported separately;
4. receipt precision/recall against fixture-declared ambient dependencies;
5. validation wall time, tracing wall time, receipt bytes, trace bytes, and agent end-to-end wall time.

Compare receipt against transcript on identical fixture, trial count, model, and sandbox. Report all invalid/timeout/CLI-failure records; never exclude them silently.

## Raw-record rule

Use a unique `--output` path. Runner refuses to overwrite existing raw JSON. Analysis reads raw JSON; manuscript numbers come only from generated summary. Record command used to start every matrix run in a companion run manifest.

## Interpretation

If receipt improves no primary metric, write result as bounded negative evidence: compact ambient-dependency receipts did not improve transportability judgment under this protocol. Do not attribute failure to all coding agents, provenance systems, or agentic AI.
