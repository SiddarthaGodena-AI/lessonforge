# Evaluator Calibration

Mode: deterministic tier only (`--det-only`). Each seeded lesson = the good lesson with exactly ONE flaw.
The LLM-judge tier was NOT run in this calibration (free-tier daily quota exhausted); its rows are marked NOT RUN, not "missed".

| Seeded flaw | Tier | Expected failing check | Result | Also failed, legitimately | Unexpected failures (false positives) |
|---|---|---|---|---|---|
| GOOD (should pass everything) | - | none | PASSED all | - | - |
| long_sentence | deterministic | B1 | CAUGHT | - | - |
| jargon_dump | deterministic | B1,B2 | CAUGHT | - | - |
| forward_reference | deterministic | C2 | CAUGHT | - | - |
| missing_glossary_entry | deterministic | C1 | CAUGHT | - | - |
| missing_why | deterministic | E1 | CAUGHT | F1 | - |
| no_check_questions | deterministic | F2 | CAUGHT | F1 | - |
| idiom | deterministic | B3 | CAUGHT | - | - |
| factual_error | LLM judge | A1 | NOT RUN | - | - |
| unsupported_claim | LLM judge | A2 | NOT RUN | - | - |
| vague_example | LLM judge | D1 | NOT RUN | - | - |
| no_analogy_limits | LLM judge | A3 | NOT RUN | - | - |
| culture_reference | LLM judge | B3 | NOT RUN | - | - |
| missing_concept_chunk_reason | LLM judge | E2 | NOT RUN | - | - |

**Deterministic tier:** 7/7 seeded flaws caught.
**False positives:** 0 of 8 evaluated lessons (the GOOD lesson plus the 7 deterministic ones).
**LLM tier:** 0 of 6 evaluated. No catch rate is claimed.

Supporting evidence, anecdotal (n=1 each, not a calibration): in a live `--sabotage factual` run the judge failed A1 on the injected false claim ("RAG retrains the LLM's weights"), and failed A2 on an unsupported claim on the next attempt. See `outputs/run_20261108_142354/rejection_log.md`.

'Also failed, legitimately' = a check that the flaw really does violate. Unexpected failures would be possible false positives.