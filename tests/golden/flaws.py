"""Seeded-flaw generators. Each takes the good lesson and breaks exactly ONE thing.
tier='det'  -> the deterministic evaluator must catch it (expected check ids listed)
tier='llm'  -> only the LLM judge can catch it (used later in calibration)"""
from __future__ import annotations
import re

def _drop_section(md, heading_prefix):
    return re.sub(rf"^## {heading_prefix}.*?(?=^## |\Z)", "", md, flags=re.M | re.S)

def long_sentence(md):
    s = ("RAG is a technique in which a system, after it has taken the documents that a company or a person owns "
         "and has broken them into pieces and has stored those pieces in a place where they can be searched, "
         "goes and finds the pieces that are most useful and gives them to the LLM before it writes the answer. ")
    return md.replace("In simple words, RAG lets", s + "In simple words, RAG lets")

def jargon_dump(md):
    j = ("\nThe pipeline employs bidirectional transformer encoders to project heterogeneous documents into a "
         "high-dimensional dense vector space, where approximate nearest-neighbour search using hierarchical "
         "navigable small-world graphs enables sublinear retrieval latency and mitigates epistemic uncertainty.\n")
    return md.replace("RAG has two phases.", j + "RAG has two phases.")

def forward_reference(md):
    return md.replace("- **Private data:**", "- **Speed:** Embedding search is very fast.\n- **Private data:**")

def missing_glossary_entry(md):
    return re.sub(r"^- \*\*embedding\*\*:.*\n", "", md, flags=re.M)

def missing_why(md): return _drop_section(md, "Why It Matters")
def no_check_questions(md): return _drop_section(md, "Check Your Understanding")
def idiom(md): return md.replace("RAG helps a lot, but", "In a nutshell, RAG is a piece of cake, but")

# ---- LLM-only flaws (deterministic checks cannot see these) ----
def factual_error(md):
    md = md.replace("You do not need to retrain the LLM.", "RAG retrains the LLM's weights each time you add a document.")
    return md.replace("No. The LLM does not change. The system only adds text to the prompt.",
                      "Yes. RAG retrains the LLM's weights every time you add a document.")

def unsupported_claim(md):
    return md.replace("In simple words, RAG lets", "RAG was invented by Google in 2015 and every AI product uses it. In simple words, RAG lets")

def vague_example(md):
    body = "A system might find some text and then answer a question about it. The details depend on the setup.\n\n"
    return re.sub(r"(^## Worked Example\n\n).*?(?=^## )", r"\1" + body, md, flags=re.M | re.S)

def no_analogy_limits(md):
    return re.sub(r"^Where the analogy stops:.*\n", "", md, flags=re.M)

def culture_reference(md):
    return md.replace("Think of an exam.", "Think of a quarterback checking the playbook before the snap at the Super Bowl.")

def missing_concept_chunk_reason(md):
    return md.replace(" We do this because an LLM can read only a limited amount of text at one time. So we send only the useful chunks.", "")

FLAWS = {
    # name: (function, tier, expected failing check ids)
    "long_sentence":          (long_sentence, "det", {"B1"}),
    "jargon_dump":            (jargon_dump, "det", {"B1", "B2"}),
    "forward_reference":      (forward_reference, "det", {"C2"}),
    "missing_glossary_entry": (missing_glossary_entry, "det", {"C1"}),
    "missing_why":            (missing_why, "det", {"E1"}),
    "no_check_questions":     (no_check_questions, "det", {"F2"}),
    "idiom":                  (idiom, "det", {"B3"}),
    "factual_error":          (factual_error, "llm", {"A1"}),
    "unsupported_claim":      (unsupported_claim, "llm", {"A2"}),
    "vague_example":          (vague_example, "llm", {"D1"}),
    "no_analogy_limits":      (no_analogy_limits, "llm", {"A3"}),
    "culture_reference":      (culture_reference, "llm", {"B3"}),
    "missing_concept_chunk_reason": (missing_concept_chunk_reason, "llm", {"E2"}),
}

# Checks that may ALSO legitimately fail (judged by the LLM tier) because the seeded flaw really violates them.
# Anything else failing on a seeded lesson is reported as a possible false positive.
ALSO_OK = {
    "jargon_dump": {"C1", "F1"},
    "forward_reference": {"F1"},
    "factual_error": {"E2"},          # wrongly claiming retraining also violates key concept K10
    "missing_why": {"F1"},            # missing section also breaks required order
    "no_check_questions": {"F1"},
}
