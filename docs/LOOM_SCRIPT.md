# Loom script (target 17-18 min). Camera bubble ON the whole time.

BEFORE RECORDING (do all of this first - the video should not be your first run)
1. Close everything with API keys. NEVER show `.env` on screen.
2. `Remove-Item Env:LESSONFORGE_ENV -ErrorAction SilentlyContinue` (use FINAL settings), then `python scripts\usage_report.py` (check Gemini calls today and cool-downs).
3. Have these open in tabs: README (architecture diagram), `rubric/rubric.yaml`, `docs/CALIBRATION.md`, `docs/EVOLUTION.md`, the final lesson Google Doc, `outputs\rejection_log.md` of the REAL final run.
4. Terminal font big (Ctrl +). Pre-type commands in a notes file to paste.
5. Have a saved good run (folder in `submission/`) as a fallback if Gemini 429s on camera.

| Time | What you say / show | Brief requirement |
|---|---|---|
| 0:00-1:30 | FACE. Who the learner is; why "generate once with a prompt" is not enough; what "ship-ready" means (every check passes, else human review). | face-visible |
| 1:30-5:30 | README diagram. Walk the loop: plan -> generate -> Tier 1 deterministic -> Tier 2 LLM judge -> fix brief -> retry (max 3) -> publish/escalate. Say WHY: generator never grades itself, different model family judge, binary checks, quoted+verified evidence, cheap checks gate expensive ones. Open `rubric.yaml`, show 3 checks. | architecture + reasoning |
| 5:30-11:00 | **Live end-to-end run**: `python run.py` . While it runs (3-8 min with free-tier pacing) explain the evaluator and the fact sheet. When it ends: open `outputs\lesson.md` and `rejection_log.md` - show attempt 1 failures with evidence, the fix brief, what changed, final status. | workflow running end to end |
| 11:00-14:00 | **Deliberate error**: `python run.py --sabotage factual` (injects "RAG works by retraining the LLM's weights..."). Show the judge FAILING it with the quoted sentence and `A1`; log line "DELIBERATE SABOTAGE"; attempt 2 repairs it. Optionally also `--sabotage jargon` (deterministic, instant, no judge tokens). | evaluator catches a deliberate error |
| 14:00-16:00 | **Trust in the evaluator**: `pytest -q`; `docs/CALIBRATION.md` table (flaw -> caught?); 2-3 things calibration found and fixed (reference lesson broke its own rules; window-FK; bold-phrase bug). | rigor |
| 16:00-17:30 | **Memory / self-evolution**: `python reflect.py stats`; `docs/EVOLUTION.md`; prompts v1->v2 changelog; tell the contaminated-experiment story (fallback model mixed in -> gate now refuses; per-attempt model recorded). Reflector can never edit the evaluator. | self-evolving + memory |
| 17:30-18:30 | FACE. Honest limitations (fact sheet verification status, small samples, free-tier limits), what you'd build next, thanks. | face-visible |

IF SOMETHING FAILS ON CAMERA
- Gemini 429 / quota: say so calmly, show the `[rate limit detail]` line, switch to the saved run in `submission/` and continue; mention the quota-memory fix.
- Judge slow: narrate the architecture; do not cut the run short.
- Lesson ends `NEEDS_HUMAN_REVIEW`: that is a valid, honest outcome - show the log and explain the escalation path.
