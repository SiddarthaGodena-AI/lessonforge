from __future__ import annotations
import re
from src.checks.deterministic import split_sections

FIX_HINTS = {
 "A1": "Remove or correct the claim so it agrees with the fact sheet. Do not repeat the false idea.",
 "A2": "Delete the unsupported claim, or rewrite it using only fact-sheet facts. Avoid dates, names, numbers and words like always/never/every.",
 "A3": "Add a paragraph that begins exactly 'Where the analogy stops:' and states one way real RAG differs from the analogy.",
 "B1": "Split long sentences. Keep the average under 12 words and no sentence over 25 words.",
 "B2": "Use shorter sentences and simpler everyday words, especially in the quoted passage.",
 "B3": "Replace idioms or culture-specific references with plain literal words or an everyday Indian student context.",
 "C1": "Give the term a plain-language definition: bold at first use AND a Glossary entry of at most 25 words.",
 "C2": "At the FIRST use of each required term, bold it (e.g. **LLM**, or inside a bold phrase like **large language model (LLM)**) and explain it right away. Do not mention the term anywhere earlier, even in passing. If a term is part of an acronym's full name, bold the WHOLE name with the acronym, e.g. **retrieval-augmented generation (RAG)**.",
 "D1": "Rewrite the Worked Example: a concrete question, the exact chunk text retrieved, the prompt sent, and the final answer.",
 "D2": "Use a familiar everyday analogy (open-book exam, college library, class notes).",
 "E1": "Add the missing section(s) using the exact required heading(s).",
 "E2": "Explain the missing key concept(s) in the most fitting section.",
 "F1": "Put sections in the required order; explain every idea before it is used.",
 "F2": "Begin with 'The Problem'; end with 'Recap' then 'Check Your Understanding' containing exactly 3 numbered questions.",
 "L1": "Adjust total length to the allowed word range.",
}

def build_fix_brief(results, rubric) -> str:
    crit = {c["id"]: c["critical"] for c in rubric["checks"]}
    name = {c["id"]: c["name"] for c in rubric["checks"]}
    failed = [r for r in results if r.verdict == "FAIL"]
    failed.sort(key=lambda r: (not crit.get(r.check_id, False), r.check_id))
    lines = []
    for r in failed:
        tag = "CRITICAL" if crit.get(r.check_id) else "standard"
        lines.append(f"- [{tag}] {r.check_id} - {name.get(r.check_id, '')}\n"
                     f"  Problem: {r.reason}\n" + (f"  Evidence: \"{r.evidence}\"\n" if r.evidence else "")
                     + f"  How to fix: {FIX_HINTS.get(r.check_id, 'Fix the issue described.')}")
    return "\n".join(lines)

def diff_summary(prev: str, new: str) -> str:
    a, b = dict(split_sections(prev)), dict(split_sections(new))
    changed = [h for h in b if h in a and a[h].strip() != b[h].strip()]
    added = [h for h in b if h not in a]
    removed = [h for h in a if h not in b]
    same = [h for h in b if h in a and a[h].strip() == b[h].strip()]
    wa, wb = len(re.findall(r"\w+", prev)), len(re.findall(r"\w+", new))
    parts = [f"changed sections: {changed or 'none'}", f"added: {added or 'none'}", f"removed: {removed or 'none'}",
             f"unchanged: {len(same)} of {len(b)} sections", f"length {wa} -> {wb} words"]
    return "; ".join(parts)
