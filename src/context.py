from __future__ import annotations
import json
from pathlib import Path
from src.checks.deterministic import load_rubric
from src.memory import store
ROOT = Path(__file__).resolve().parents[1]

def rules_to_text(rules: list[str]) -> str:
    return "\n".join("- " + r for r in rules) or "(none yet)"

def build_context(blueprint_path="data/blueprint_rag.json", facts_path="data/fact_sheet.json") -> dict:
    bp = json.loads((ROOT / blueprint_path).read_text())
    fs = json.loads((ROOT / facts_path).read_text())
    rules = store.active_rules()[-8:]            # newest 8 validated rules (cap keeps the prompt short)
    facts_text = "\n".join(f'{f["id"]}: {f["claim"]}' for f in fs["facts"])
    return {
        "blueprint": bp, "facts": fs, "rubric": load_rubric(),
        "facts_text": facts_text,
        "misconceptions_text": "\n".join("- " + m for m in fs["misconceptions_to_reject"]),
        "rules_text": rules_to_text([r["rule"] for r in rules]),
        "rules_version": store.rules_version([r["id"] for r in rules]),
        "unverified_facts": [f["id"] for f in fs["facts"] if not f.get("verified")],
    }
