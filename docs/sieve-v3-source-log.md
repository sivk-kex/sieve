# SIEVE v3 Source Log

Checked 2026-07-14. All academic items below are arXiv preprints, not
peer-reviewed venue papers. They bound SIEVE claims; they do not establish
novelty by absence.

| Key | Verified source | Direct overlap | SIEVE boundary |
| --- | --- | --- | --- |
| `trivedi2026cleanliness` | Trivedi and Schmitt, *Does Code Cleanliness Affect Coding Agents?*, arXiv:2605.20049 | Controlled minimal-pair evaluation of Claude Code. | Varies code cleanliness, not caller state or clean-target validation transfer. |
| `vangala2026reproducible` | Vangala et al., *AI-Generated Code Is Not Reproducible (Yet)*, arXiv:2512.22387 | Clean-environment replay and hidden dependencies in agent-generated projects. | Does not measure state presented to a tool executor during one agent session. |
| `hans2026replication` | Hans and Bilionis, *Coding-agents can replicate scientific machine learning papers*, arXiv:2607.02134 | Evidence-target workflow and completion gate. | Does not vary caller state or compare tool-executor results with a clean target. |
| `bouzenia2026analysis` | Bouzenia, Cadar, and Pradel, *Evaluating LLM Agents on Automated Software Analysis Tasks*, arXiv:2604.11270 | Agent self-validated success can exceed manual verification. | Does not isolate selective state projection or validation-plane transfer. |
| `wang2026researchenv` | Wang et al., *ResearchEnvBench*, arXiv:2603.06739 | Environment synthesis for research code. | Agent constructs target environment; SIEVE measures state already present in an agent execution plane. |
| `huang2026automat` | Huang et al., *Can Coding Agents Reproduce Findings in Computational Materials Science?*, arXiv:2605.00803 | End-to-end scientific claim reproduction. | Domain workflows and paper reconstruction, not local validation-plane drift. |

Searches: `coding agent validation environment state transfer`, `coding agent
tool executor caller environment`, `LLM agent clean replay validation`, and
OpenReview/arXiv variants. No exact study found. Recheck within seven days of
submission.
