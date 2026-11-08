from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

class CheckResult(BaseModel):
    check_id: str
    verdict: Literal["PASS", "FAIL"]
    component: Literal["det", "llm"] = "det"
    reason: str = ""
    evidence: str = ""            # exact quote from lesson; REQUIRED for LLM FAILs
    metrics: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def llm_fail_needs_evidence(self):
        if self.component == "llm" and self.verdict == "FAIL" and not self.evidence.strip():
            raise ValueError(f"{self.check_id}: LLM FAIL without evidence quote is invalid")
        return self

class AttemptRecord(BaseModel):
    attempt: int
    prompt_version: str
    rubric_version: int
    results: list[CheckResult]
    lesson: str = ""
    fix_brief: str = ""
    diff_summary: str = ""
    regressions: list[str] = Field(default_factory=list)
    sabotage_note: str = ""
    llm_skipped: bool = False
    generator_model: str = ""
    @property
    def failed_ids(self) -> list[str]:
        return sorted({r.check_id for r in self.results if r.verdict == "FAIL"})
    @property
    def passed(self) -> bool:
        return not self.failed_ids
