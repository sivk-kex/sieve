# SIEVE Stage-1 v4 Protocol

Status: frozen before execution, 2026-07-14. At most six sessions: Codex and
Claude for Trials 1--3. This protocol starts from zero; no v1--v3 data is
pooled into its headline table.

## Only Change

v3 combined both products in one process and wrote its JSON after both
returned. Trial 2 produced no durable record. v4 invokes one product per
process and atomically writes one JSON record immediately after that product
returns. This changes collection durability only.

Fixtures, wrapper, prompt, agent commands, model aliases, state injection,
target oracle, validity gates, and six-session cap are exactly those frozen in
`docs/sieve-stage1-v3-protocol.md`.

## Execution Order

For each trial: run Codex, inspect its record; run Claude, inspect its record;
then decide whether the next trial may start. A missing, malformed, or invalid
single-product record stops v4 immediately. No retry or replacement run.

## Paper Gate

Draft EAIT WIP only after all six valid v4 records reproduce source hashes,
controls, target vector, mutation guards, and six-command traces. Report v1--v3
operational failures in limitations.
