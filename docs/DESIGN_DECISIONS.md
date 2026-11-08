# Design Decisions - LessonForge

Task: build an agentic system that generates a beginner lesson (topic: Introduction to RAG), judges it against hard pass/fail checks,
and regenerates until it clears the bar or hits a retry cap. Learner: 17-18 yr old Indian 12th-grade graduate, non-English-medium, no technical background.

## 1. What "ship-ready" means
A lesson ships only if **every** check in `rubric/rubric.yaml` passes (15 checks, binary, no partial credit; 7 are marked *critical*).
If it cannot pass within 1 + 2 retries it is **not** shipped: status `NEEDS_HUMAN_REVIEW`, best attempt saved, all failures logged.

## 2. Architecture (LangGraph state machine)
`plan -> generate -> evaluate -> publish | feedback -> generate | escalate`
| Choice | Why | Rejected alternative |
|---|---|---|
| LangGraph state machine | Explicit states, conditional edges, hard retry cap; the loop is the product and should be inspectable | n8n (hard to unit-test, awkward for deterministic checks and memory); a bare `while` loop (works, but no visible architecture) |
| Generator never judges itself | Self-grading is lenient; the gate must be independent | One prompt that writes and scores its own lesson |
| Judge from a different model family | Reduces self-preference bias | Same model, different prompt (weaker; used only as a flagged fallback) |

## 3. The evaluator (the centerpiece)
Two tiers, **cheap first**:
- **Tier 1, deterministic Python (free, reproducible):** sentence length, Flesch-Kincaid (overall *and* worst 4-sentence window), required sections and order, term-defined-before-use, glossary coverage, idiom blacklist, length.
- **Tier 2, LLM judge:** claim verification against a curated fact sheet (A1/A2), plus analogy, example, coverage, jargon, flow and idiom checks. Runs only if Tier 1 is clean (no point judging an analogy in a lesson with a missing section; also saves free-tier tokens).
Reliability rules for the LLM tier:
1. **Binary verdicts**, no 1-10 scores (numeric LLM scores drift and cannot be audited).
2. **Every FAIL must quote the lesson, and the quote is machine-verified** against the text. An unverifiable quote gets one retry, then is recorded as FAIL flagged `unverified` (fail-safe, visibly).
3. Temperature 0; verdicts cached by exact request so the same lesson is never judged twice differently.
4. Claims are checked against a **fact sheet**, not the judge's memory: "accurate" cannot be judged without a reference.

## 4. Regeneration strategy
- The failure is converted into a **fix brief** (critical checks first, with quoted evidence and a concrete fix hint), not "try again".
- The reviser must keep passing text word for word; **regressions** (a check that passed before and fails now) are flagged in the log.
- **Patch vs rewrite:** a lesson that is too short or missing its structure is rewritten from scratch (patching a scrap yields a scrap).
- **Stagnation guard:** if a revision leaves every quoted offending passage untouched, the next attempt rewrites from scratch.
- **Termination:** max 3 attempts, then escalate. The loop always ends.

## 5. Memory and self-evolution
- **SQLite memory:** every run, attempt, check result, evidence, models used, prompt version, rules version.
- **Reflector:** finds checks that fail repeatedly on first attempts, writes one generator-side rule per check, then **A/B-tests** it (N lessons with vs without). A rule is activated only if its target check fails less, total failures do not rise and clean passes do not drop. LLM-judged rules need an explicit `--gate-llm` (costs judge tokens).
- **The reflector can never edit the rubric, thresholds or judge prompts.** Otherwise a self-improving system could raise its own score by lowering the bar. Rubric changes are human decisions, re-validated with calibration.
- **Versioned prompts:** v1 -> v2 (see `prompts/CHANGELOG.md`), changed only in `generator.md`, with the evidence that motivated each change. A test asserts the judge prompts are identical across versions.
- **Deliberate sabotage runs are recorded but never learned from.**
- Vector memory was *not* built: with a few dozen rules, injecting the newest 8 is simpler and just as effective. Scale path: embed failure reasons and retrieve top-k.

## 6. Proving the evaluator works (calibration)
`tests/golden/`: one good lesson + 13 copies each with exactly **one seeded flaw** (long sentence, jargon dump, forward reference, missing glossary entry, missing section, idiom, factual error, unsupported claim, vague example, missing analogy limits, culture reference, missing key concept...).
- Deterministic tier: 7 flaw types caught by `pytest` (offline, free).
- LLM tier: `python scripts/calibrate.py` -> `docs/CALIBRATION.md`. **Result: not calibrated in this submission because of free-tier daily quota; no catch rate is claimed for the LLM tier.** Observed anecdotally (n=1, not a calibration): in a live sabotage run the judge flagged the injected false claim (A1) and, on the next attempt, an unsupported claim (A2). The deterministic tier is calibrated separately: 7 of 7 seeded flaws caught, 0 false positives (see `docs/CALIBRATION.md`)..
What calibration actually found (all fixed, all in git history):
- My reference lesson itself contained 3 sentences that broke my own rules (an absolute claim, an unexplained term, an over-strong "never"); the judge flagged them.
- A readability average hid a jargon paragraph -> added the worst-window check.
- The term-definition check wrongly rejected `**Large language model (LLM)**` -> now accepts a term inside a bold phrase.
- A similarity-based "model ignored the fix brief" guard would have flagged correct one-word fixes -> replaced by an evidence-based guard.

## 7. Operating on free tiers: problems found and fixed
- Gemini free tier = **20 requests/day** (read from the AI Studio rate-limit page); Groq has per-model token and per-day caps.
- A silent fallback to a weaker model **contaminated an experiment**. Fixes: each attempt records the model that wrote it; fallback use is printed as a warning; the A/B gate refuses to conclude when lessons came from different models.
- Quota walls are detected from the HTTP body, remembered across commands, and skip straight to the next provider instead of retrying.
- Tests are hermetic (no network, no real `.env`), so they cannot hang on a rate limit.
- Strategy: a LAB setup (local Ollama, unlimited) for experiments and a FINAL setup (Gemini) for the deliverable.

## 8. Known limitations (stated, not hidden)
- Fact sheet: **all 19 facts were marked reviewed on 8 November 2026; 16 have a recorded source URL and the source for F09-F11 is not recorded yet, so those three are the weakest part of the fact sheet.**
- Thresholds (12 words average, FK 6.5, window 11) were tuned on one reference lesson and a handful of generated ones; small samples only.
- LLM judges are imperfect even with binary checks and verified quotes; the human-review escalation path exists for that reason.
- Generator and judge are on different providers but both on free tiers: an outage stops the pipeline (local Ollama is the last-resort generator).
- Self-evolution evidence is small-sample and directional, not statistical proof.

## 9. What I would build next
Live-retrieval grounding for arbitrary topics; a Hindi/Telugu glossary pass; multi-judge ensembles with disagreement tracking; cost and latency dashboards; embedding-based retrieval of learned rules.


