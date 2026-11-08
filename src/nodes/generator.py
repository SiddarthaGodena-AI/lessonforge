from __future__ import annotations
import re
from src.llm import provider
from src.prompts import load, render

def _clean(md: str) -> str:
    md = md.strip()
    md = re.sub(r"^```(?:markdown|md)?\s*\n", "", md)
    md = re.sub(r"\n```\s*$", "", md)
    i = md.find("# ")
    return md[i:].strip() + "\n" if i > 0 and not md.startswith("#") else md + "\n"

def _common(ctx):
    bp = ctx["blueprint"]
    return dict(
        LEARNER=bp["learner"], TOPIC=bp["topic"], TERMS=", ".join(bp["required_terms"]),
        SECTIONS="\n".join(f"## {h}" for h in bp["section_headings"]),
        CONCEPTS="\n".join(f'  {k["id"]}: {k["concept"]}' for k in bp["key_concepts"]),
        FACTS=ctx["facts_text"], MISCONCEPTIONS=ctx["misconceptions_text"], RULES=ctx["rules_text"])

def _call(prompt: str, temperature: float) -> str:
    out = provider.chat("generator", [{"role": "user", "content": prompt}], temperature=temperature, max_tokens=6000)
    if provider.LAST.get("finish_reason") == "length":      # cut off mid-lesson: ask again with a bigger budget
        out = provider.chat("generator", [{"role": "user", "content": prompt}], temperature=temperature, max_tokens=12000)
    return out

def generate(ctx: dict, retry_note: str = "") -> str:
    """retry_note: used when a previous attempt was so malformed that patching it makes no sense -> rewrite from scratch."""
    p = render(load("generator"), **_common(ctx))
    if retry_note:
        p += ("\n\nIMPORTANT: a previous attempt was rejected. Write the COMPLETE lesson again from scratch, with ALL required "
              "sections and the full length. Problems found last time:\n" + retry_note)
    return _clean(_call(p, 0.7))

def revise(ctx: dict, prev_lesson: str, fix_brief: str) -> str:
    p = render(load("revise"), PREV_LESSON=prev_lesson, FIX_BRIEF=fix_brief, **_common(ctx))
    return _clean(_call(p, 0.3))
