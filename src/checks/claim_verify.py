"""A1/A2: extract atomic claims, verify each against the fact sheet."""
from __future__ import annotations
import json
from src.llm import provider
from src.prompts import load, render
from src.schemas import CheckResult
from src.util import parse_json, quote_in_text

def run_claim_verification(lesson: str, ctx: dict) -> list[CheckResult]:
    raw = provider.chat("judge", [{"role": "user", "content": render(load("claims_extract"), LESSON=lesson)}],
                        temperature=0.0, json_mode=True, max_tokens=2500, cache=True)
    try:
        claims = parse_json(raw).get("claims", [])[:25]
    except Exception:
        return [CheckResult(check_id=i, component="llm", verdict="FAIL", reason="Claim extraction returned invalid JSON",
                evidence="[judge error]", metrics={"judge_error": True}) for i in ("A1", "A2")]
    if not claims:
        return [CheckResult(check_id=i, component="llm", verdict="PASS", reason="no factual claims extracted") for i in ("A1", "A2")]
    raw = provider.chat("judge", [{"role": "user", "content": render(load("claims_verify"),
                        FACTS=ctx["facts_text"], MISCONCEPTIONS=ctx["misconceptions_text"],
                        CLAIMS=json.dumps([{"id": c["id"], "claim": c["claim"]} for c in claims]))}],
                        temperature=0.0, json_mode=True, max_tokens=2500, cache=True)
    try:
        verdicts = {int(r["id"]): r for r in parse_json(raw)["results"]}
    except Exception:
        return [CheckResult(check_id=i, component="llm", verdict="FAIL", reason="Claim verification returned invalid JSON",
                evidence="[judge error]", metrics={"judge_error": True}) for i in ("A1", "A2")]
    bad_a1, bad_a2 = [], []
    for c in claims:
        v = verdicts.get(int(c["id"]), {})
        status = v.get("status", "supported")
        if status == "contradicted":
            bad_a1.append((c, v))
        elif status == "unsupported" and v.get("specific"):
            bad_a2.append((c, v))
    def mk(cid, bad, label):
        if not bad:
            return CheckResult(check_id=cid, component="llm", verdict="PASS", reason=f"{len(claims)} claims checked, none {label}")
        c, v = bad[0]
        ev = c["quote"] if quote_in_text(c.get("quote", ""), lesson) else c["claim"]
        more = f" (+{len(bad) - 1} more)" if len(bad) > 1 else ""
        return CheckResult(check_id=cid, component="llm", verdict="FAIL",
                           reason=f"Claim {label}: \"{c['claim']}\" - {v.get('reason', '')}{more}", evidence=ev,
                           metrics={"claims": [x[0]["claim"] for x in bad]})
    return [mk("A1", bad_a1, "contradicts fact sheet"), mk("A2", bad_a2, "unsupported")]
