"""Tier-1 evaluator: pure Python, no LLM, fully reproducible."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import textstat, yaml
from src.schemas import CheckResult

ROOT = Path(__file__).resolve().parents[2]

def load_rubric(path: Path | None = None) -> dict:
    return yaml.safe_load((path or ROOT / "rubric/rubric.yaml").read_text())

# ---------- text utilities ----------
def split_sections(md: str) -> list[tuple[str, str]]:
    """Return [(heading_lowercase, body)] for each '## ' section, in order."""
    parts = re.split(r"^##\s+(.+?)\s*$", md, flags=re.M)
    return [(parts[i].strip().lower(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]

def prose_lines(md: str) -> list[str]:
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    out = []
    for ln in md.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        s = re.sub(r"^(?:[-*>]+\s+|\d+[.)]\s+)", "", s)
        out.append(s.replace("**", "").replace("`", ""))
    return out

def sentences(md: str) -> list[str]:
    out = []
    for ln in prose_lines(md):
        out += [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z\"\u201c])", ln) if p.strip()]
    return out

def words(s: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'\u2019-]*|\d+", s)

def _term_re(term: str) -> re.Pattern:
    t = r"\s+".join(map(re.escape, term.split()))
    return re.compile(rf"\b{t}(?:s|es)?\b", re.I)

def body_without_glossary(md: str) -> str:
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    out, skip = [], False
    for ln in md.splitlines():
        if ln.startswith("#"):
            skip = ln.lstrip("#").strip().lower().startswith("glossary")
            continue
        if not skip:
            out.append(ln)
    return "\n".join(out)

# ---------- individual checks ----------
def check_structure(md, cfg):
    secs = split_sections(md)
    heads = [h for h, _ in secs]
    req = cfg["structure"]["required_sections"]
    found, missing = {}, []
    for r in req:
        idx = next((i for i, h in enumerate(heads) if re.search(r["pattern"], h)), None)
        (found.__setitem__(r["key"], idx) if idx is not None else missing.append(r["key"]))
    res = []
    core = [k for k in ("what", "why", "how") if k in missing]
    res.append(CheckResult(check_id="E1", verdict="FAIL" if core else "PASS",
        reason=f"Missing required section(s): {core}" if core else "what/why/how present",
        metrics={"missing_core": core}))
    order = [found[r["key"]] for r in req if r["key"] in found]
    in_order = order == sorted(order)
    ok_order = not missing and in_order
    res.append(CheckResult(check_id="F1", component="det", verdict="PASS" if ok_order else "FAIL",
        reason="sections in required order" if ok_order else
        f"missing={missing} in_order={in_order}", metrics={"missing": missing}))
    # F2: opens with problem, ends with recap + check, exactly N questions
    n_q_expected = cfg["thresholds"]["quiz_questions"]
    last2 = heads[-2:]
    opens = bool(heads) and re.search(req[0]["pattern"], heads[0]) is not None
    ends = len(last2) == 2 and re.search(r"^recap", last2[0]) and re.search(r"^check your", last2[1])
    qs = 0
    if heads and re.search(r"^check your", heads[-1]):
        qs = len(re.findall(r"^\s*\d+[.)]\s+\S", secs[-1][1], flags=re.M))
    f2_ok = bool(opens and ends and qs == n_q_expected)
    res.append(CheckResult(check_id="F2", verdict="PASS" if f2_ok else "FAIL",
        reason="ok" if f2_ok else f"opens_with_problem={opens} ends_recap_check={bool(ends)} questions={qs} (need {n_q_expected})",
        metrics={"questions": qs}))
    return res

def check_length(md, cfg):
    n = sum(len(words(s)) for s in sentences(md))
    lo, hi = cfg["thresholds"]["min_words"], cfg["thresholds"]["max_words"]
    ok = lo <= n <= hi
    return [CheckResult(check_id="L1", verdict="PASS" if ok else "FAIL",
            reason=f"{n} words (allowed {lo}-{hi})", metrics={"words": n})]

def check_sentences(md, cfg):
    sents = sentences(md)
    lens = [len(words(s)) for s in sents]
    avg = sum(lens) / max(1, len(lens))
    t = cfg["thresholds"]
    longest = max(sents, key=lambda s: len(words(s))) if sents else ""
    bad = avg > t["max_avg_sentence_words"] or max(lens, default=0) > t["max_sentence_words"]
    ev = longest if max(lens, default=0) > t["max_sentence_words"] else ""
    reason = (f"avg={avg:.1f} (max {t['max_avg_sentence_words']}), longest={max(lens, default=0)} words "
              f"(max {t['max_sentence_words']})")
    r1 = CheckResult(check_id="B1", verdict="FAIL" if bad else "PASS", reason=reason,
                     evidence=ev, metrics={"avg": round(avg, 2), "max": max(lens, default=0)})
    text = " ".join(s if s[-1] in ".!?" else s + "." for s in sents)
    fk = textstat.flesch_kincaid_grade(text)
    k = t["window_sentences"]
    fixed = [x if x[-1] in ".!?" else x + "." for x in sents]
    wins = [(textstat.flesch_kincaid_grade(" ".join(fixed[i:i + k])), " ".join(fixed[i:i + k]))
            for i in range(max(1, len(fixed) - k + 1))]
    worst_fk, worst_txt = max(wins, key=lambda w: w[0]) if wins else (0.0, "")
    b2_fail = fk > t["max_fk_grade"] or worst_fk > t["max_window_fk_grade"]
    r2 = CheckResult(check_id="B2", verdict="FAIL" if b2_fail else "PASS",
                     reason=(f"FK overall {fk:.1f} (max {t['max_fk_grade']}); worst {k}-sentence window "
                             f"{worst_fk:.1f} (max {t['max_window_fk_grade']})"),
                     evidence=worst_txt[:300] if worst_fk > t["max_window_fk_grade"] else "",
                     metrics={"fk_grade": round(fk, 2), "worst_window_fk": round(worst_fk, 2)})
    return [r1, r2]

def check_idioms(md, cfg):
    low = md.lower()
    hits = [p for p in cfg["idiom_blacklist"] if p in low]
    ev = ""
    if hits:
        m = re.search(re.escape(hits[0]), md, re.I)
        ev = md[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")
    return [CheckResult(check_id="B3", verdict="FAIL" if hits else "PASS",
            reason=f"idioms found: {hits}" if hits else "no blacklisted idioms", evidence=ev)]

def check_terms(md, cfg, terms):
    secs = dict(split_sections(md))
    gloss_body = next((b for h, b in secs.items() if h.startswith("glossary")), "")
    max_def = cfg["thresholds"]["max_glossary_def_words"]
    # C1 (det part): every term has a glossary entry with a short definition
    problems = []
    for t in terms:
        m = re.search(rf"^\s*[-*]\s+\*\*{re.escape(t)}\*\*\s*[:\u2014-]\s*(.+)$", gloss_body, re.I | re.M)
        if not m:
            problems.append(f"'{t}' has no glossary entry")
        elif len(words(m.group(1))) > max_def:
            problems.append(f"'{t}' definition longer than {max_def} words")
    c1 = CheckResult(check_id="C1", component="det", verdict="FAIL" if problems else "PASS",
                     reason="; ".join(problems) if problems else "all required terms have short glossary entries")
    # C2: first use (outside headings/glossary) must be the bold definition site
    body = body_without_glossary(md)
    bad = []
    for t in terms:
        m = _term_re(t).search(body)
        if not m:
            bad.append((t, "", "term never used in lesson body"))
            continue
        spans = [(x.start(), x.end()) for x in re.finditer(r"\*\*.+?\*\*", body)]
        bold = any(a <= m.start() and m.end() <= b for a, b in spans)   # inside **...** => definition site
        if not bold:
            ctx = body[max(0, m.start() - 40): m.end() + 40].replace("\n", " ")
            bad.append((t, ctx, "first use is not a bold definition"))
    c2 = CheckResult(check_id="C2", verdict="FAIL" if bad else "PASS",
                     reason=("; ".join(f"'{t}' first appears as: \"...{ctx.strip()}...\" ({why})" for t, ctx, why in bad)
                             if bad else "every term defined at first use"),
                     evidence=bad[0][1] if bad else "", metrics={"violations": [b[0] for b in bad]})
    return [c1, c2]

# ---------- runner ----------
def run_deterministic(md: str, cfg: dict | None = None, terms: list[str] | None = None) -> list[CheckResult]:
    cfg = cfg or load_rubric()
    if terms is None:
        terms = json.loads((ROOT / "data/blueprint_rag.json").read_text())["required_terms"]
    res = []
    for fn in (check_structure, check_length, check_sentences, check_idioms):
        res += fn(md, cfg)
    res += check_terms(md, cfg, terms)
    return res

if __name__ == "__main__":
    md = Path(sys.argv[1]).read_text()
    for r in sorted(run_deterministic(md), key=lambda r: r.check_id):
        print(f"{r.check_id:3} {r.verdict:4} {r.reason}" + (f"\n      evidence: {r.evidence}" if r.evidence else ""))
