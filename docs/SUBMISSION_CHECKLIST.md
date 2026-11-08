# Submission checklist
- [ ] Gemini quota available (AI Studio rate-limit page; resets daily) - `python scripts\usage_report.py`
- [ ] Fact sheet verified: `python scripts\verify_facts.py` (delete what you cannot support)
- [ ] FINAL run done: `python run.py`  -> copy `outputs\lesson.md`, `rejection_log.md`, `rejection_log.json` to `submission\`
- [ ] Sabotage demo rehearsed once: `python run.py --sabotage jargon` (and `factual` if judge budget allows)
- [ ] Calibration: `python scripts\calibrate.py --det-only` (free) and, if Groq budget allows, `--quick`; fill the numbers in `docs/DESIGN_DECISIONS.md`
- [ ] Lesson pasted into a Google Doc (sharing: anyone with link can view); paste the link
- [ ] GitHub: no `.env`, no keys (`git status` check), README renders the diagram
- [ ] Loom recorded (15-20 min), link opens without login
- [ ] Form submitted: repo link, doc link, Loom link
