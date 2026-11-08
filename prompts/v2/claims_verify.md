You verify claims from a beginner lesson against a FACT SHEET. Output JSON only.

For each claim choose status:
- "supported": the fact sheet states it or clearly implies it, OR it is a trivial everyday statement not specific to AI.
- "contradicted": it DIRECTLY conflicts with a fact in the fact sheet or matches a listed misconception. Extra wording that merely sounds stronger than a fact is NOT a contradiction (that is at most "unsupported").
- "unsupported": it makes a specific technical claim that the fact sheet neither supports nor contradicts.
Be fair, not paranoid:
- A claim that is a reasonable paraphrase, restatement, or direct consequence of a fact is "supported".
- Simple everyday statements (what a PDF is, that exams exist, that a student asks a question) are "supported".
- Naming an example product (e.g. "ChatGPT") as an example of a chat tool is NOT a specific technical claim.
Set "specific": true ONLY if the claim is a technical statement about RAG or LLMs that includes a date, a creator/company, a number, a performance claim, or an absolute word (always, never, every, all, only) AND the fact sheet does not support it. Otherwise false.

Return: {"results":[{"id":1,"status":"supported|contradicted|unsupported","specific":true|false,"fact_id":"F05 or null","reason":"short"}]} with one entry per claim.

FACT SHEET:
{{FACTS}}

MISCONCEPTIONS (any claim matching these is "contradicted"):
{{MISCONCEPTIONS}}

CLAIMS:
{{CLAIMS}}
