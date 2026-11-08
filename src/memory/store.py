"""Persistent memory (SQLite): every run, attempt and check result, plus learned rules and human feedback.
DB path: data/memory.db (override with env LESSONFORGE_DB)."""
from __future__ import annotations
import hashlib, json, os, sqlite3, time
from contextlib import closing
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, topic TEXT, status TEXT, attempts INT,
  prompt_version TEXT, rules_version TEXT, models TEXT, sabotage TEXT, use_llm INT);
CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INT, n INT, passed INT, llm_skipped INT, failed_ids TEXT);
CREATE TABLE IF NOT EXISTS check_results(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INT, attempt_n INT, check_id TEXT,
  component TEXT, verdict TEXT, reason TEXT, evidence TEXT);
CREATE TABLE IF NOT EXISTS learned_rules(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, check_id TEXT, rule TEXT,
  status TEXT, evidence TEXT, gate TEXT);
CREATE TABLE IF NOT EXISTS human_feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, run_id INT, check_id TEXT, note TEXT);
"""

def db_path() -> Path:
    p = Path(os.environ.get("LESSONFORGE_DB") or ROOT / "data/memory.db")
    return p if p.is_absolute() else ROOT / p

def connect():
    p = db_path(); p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p); c.row_factory = sqlite3.Row; c.executescript(SCHEMA); return c

def _rows(sql, args=()):
    with closing(connect()) as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]

# ---------------- writing ----------------
def record_run(state: dict, use_llm: bool = True) -> int:
    ctx, atts = state["ctx"], state["attempts"]
    with closing(connect()) as c:
        cur = c.execute("INSERT INTO runs(ts,topic,status,attempts,prompt_version,rules_version,models,sabotage,use_llm) VALUES(?,?,?,?,?,?,?,?,?)",
            (time.time(), state["topic"], state["status"], len(atts), atts[-1].prompt_version, ctx.get("rules_version", ""),
             ",".join(state.get("models_used", [])), state.get("sabotage") or "", int(use_llm)))
        rid = cur.lastrowid
        for a in atts:
            c.execute("INSERT INTO attempts(run_id,n,passed,llm_skipped,failed_ids) VALUES(?,?,?,?,?)",
                      (rid, a.attempt, int(a.passed), int(a.llm_skipped), ",".join(a.failed_ids)))
            for r in a.results:
                c.execute("INSERT INTO check_results(run_id,attempt_n,check_id,component,verdict,reason,evidence) VALUES(?,?,?,?,?,?,?)",
                          (rid, a.attempt, r.check_id, r.component, r.verdict, r.reason, r.evidence))
        c.commit()
    return rid

def add_rule(check_id: str, rule: str, status: str = "candidate", evidence: str = "", gate: str = "") -> int:
    with closing(connect()) as c:
        cur = c.execute("INSERT INTO learned_rules(ts,check_id,rule,status,evidence,gate) VALUES(?,?,?,?,?,?)",
                        (time.time(), check_id, rule, status, evidence, gate))
        c.commit(); return cur.lastrowid

def set_rule_status(rule_id: int, status: str, gate: str | None = None):
    with closing(connect()) as c:
        if gate is None:
            c.execute("UPDATE learned_rules SET status=? WHERE id=?", (status, rule_id))
        else:
            c.execute("UPDATE learned_rules SET status=?, gate=? WHERE id=?", (status, gate, rule_id))
        c.commit()

def add_feedback(note: str, check_id: str = "", run_id: int | None = None) -> int:
    with closing(connect()) as c:
        cur = c.execute("INSERT INTO human_feedback(ts,run_id,check_id,note) VALUES(?,?,?,?)", (time.time(), run_id, check_id, note))
        c.commit(); return cur.lastrowid

# ---------------- reading ----------------
def rules(status: tuple[str, ...] | None = None) -> list[dict]:
    rows = _rows("SELECT * FROM learned_rules ORDER BY id")
    return [r for r in rows if status is None or r["status"] in status]

def active_rules() -> list[dict]:
    return rules(("active",))

def rules_version(ids: list[int]) -> str:
    return "r0" if not ids else "r" + hashlib.sha1(",".join(map(str, sorted(ids))).encode()).hexdigest()[:8]

def feedback_for(check_id: str) -> list[dict]:
    return _rows("SELECT * FROM human_feedback WHERE check_id=? ORDER BY id DESC", (check_id,))

def failure_stats() -> dict:
    """Per check: in how many FIRST attempts was it evaluated, and how many of those failed? Deliberate-sabotage runs are ignored."""
    rows = _rows("""SELECT cr.run_id, cr.check_id, cr.verdict, cr.component FROM check_results cr
                    JOIN runs r ON r.id = cr.run_id WHERE cr.attempt_n = 1 AND r.sabotage = ''""")
    per: dict = {}
    for r in rows:
        d = per.setdefault((r["run_id"], r["check_id"]), {"fail": False, "llm": False})
        d["fail"] |= r["verdict"] == "FAIL"
        d["llm"] |= r["component"] == "llm" and r["verdict"] == "FAIL"
    stats: dict = {}
    for (rid, cid), d in per.items():
        s = stats.setdefault(cid, {"fails": 0, "evaluated": 0, "llm_fails": 0})
        s["evaluated"] += 1; s["fails"] += d["fail"]; s["llm_fails"] += d["llm"]
    return stats

def evidence_for(check_id: str, limit: int = 5) -> list[dict]:
    rows = _rows("""SELECT cr.reason, cr.evidence, cr.component FROM check_results cr JOIN runs r ON r.id = cr.run_id
                    WHERE cr.check_id=? AND cr.verdict='FAIL' AND r.sabotage='' ORDER BY cr.id DESC""", (check_id,))
    seen, out = set(), []
    for r in rows:
        k = (r["reason"][:80], r["evidence"][:60])
        if k not in seen:
            seen.add(k); out.append(r)
        if len(out) >= limit: break
    return out

def pass_rate_by_rules_version() -> list[dict]:
    return _rows("""SELECT r.prompt_version, r.rules_version, r.use_llm, COUNT(*) AS runs, SUM(a.passed) AS first_try_passes,
                    ROUND(AVG(r.attempts), 2) AS avg_attempts
                    FROM runs r JOIN attempts a ON a.run_id = r.id AND a.n = 1 WHERE r.sabotage = ''
                    GROUP BY r.prompt_version, r.rules_version, r.use_llm ORDER BY MIN(r.id)""")

def reset():
    """Delete all memory (runs, rules, feedback). Use after discovering a batch of runs was contaminated."""
    db_path().unlink(missing_ok=True)
