"""Deliberate error injection for the demo video. Always recorded in the rejection log (never hidden)."""
from __future__ import annotations
import re

def _insert(md: str, heading_prefix: str, text: str, at_end=True) -> str:
    m = re.search(rf"^## {re.escape(heading_prefix)}[^\n]*\n", md, flags=re.M | re.I)
    if not m:
        return md + "\n" + text + "\n"
    nxt = re.search(r"^## ", md[m.end():], flags=re.M)
    pos = m.end() + (nxt.start() if (nxt and at_end) else (0 if not at_end else len(md) - m.end()))
    return md[:pos].rstrip() + "\n\n" + text + "\n\n" + md[pos:].lstrip("\n")

MODES = {
 "factual": ("What Is", "RAG works by retraining the LLM's weights every time a new document is added to the knowledge base."),
 "jargon": ("How It Works", "The pipeline employs bidirectional transformer encoders to project heterogeneous documents into a high-dimensional dense vector space, where approximate nearest-neighbour search using hierarchical navigable small-world graphs enables sublinear retrieval latency and mitigates epistemic uncertainty."),
 "forward_ref": ("The Problem", "Later we will fix this with an embedding based search over many small chunks."),
 "unsupported": ("What Is", "RAG was invented by Google in 2015 and every AI product now uses it."),
}

def apply_sabotage(lesson: str, mode: str):
    if mode not in MODES:
        raise ValueError(f"unknown sabotage '{mode}'. choose from {list(MODES)}")
    head, text = MODES[mode]
    return _insert(lesson, head, text), f"DELIBERATE SABOTAGE '{mode}' injected after generation: \"{text[:90]}...\""
