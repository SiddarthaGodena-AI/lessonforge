# Self-Evolution Report

Rules are written by the reflector from failure memory and activated ONLY if an A/B gate shows improvement. The evaluator is never modified by this process.

## First-attempt failure rates (deliberate sabotage runs excluded)

| Check | Failed first attempts | Times evaluated | Rate |
|---|---|---|---|
| B1 | 3 | 5 | 60% |
| C2 | 3 | 5 | 60% |
| E1 | 0 | 5 | 0% |
| F1 | 0 | 5 | 0% |
| F2 | 0 | 5 | 0% |
| L1 | 0 | 5 | 0% |
| B2 | 0 | 5 | 0% |
| B3 | 0 | 5 | 0% |
| C1 | 0 | 5 | 0% |

## Learned rules

| # | Check | Status | Rule | Gate result |
|---|---|---|---|---|
| 1 | B1 | rejected | Keep every sentence to 25 words or fewer. | no net improvement: B1 1->2; total failed checks 8->7; clean passes 0->1 |
| 2 | C2 | rejected | Never mention any form of a term—including in acronym expansions or informal previews—before its bolded definition, which must be the term's absolute first appearance. | no net improvement: C2 1->2; total failed checks 8->8; clean passes 0->0 |

## Outcome by learned-rules version (before/after)

| Rules version | LLM judge | Runs | Passed on first try | Avg attempts |
|---|---|---|---|---|
| r0 | no (deterministic only) | 5 | 0 | 2.2 |

Small samples: treat these numbers as evidence of direction, not statistical proof.