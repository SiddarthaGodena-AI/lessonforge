# Rejection Log - Introduction to RAG

**Final status:** PASSED  |  **Attempts:** 2 of 3 allowed  |  **Prompt version:** v2  |  **Learned-rules version:** r0  |  **Rubric v1**

**Models that actually answered:** gemini:gemini-3.8-flash, groq:openai/gpt-oss-120b

## Attempt 1 - FAILED: C2  (written by gemini:gemini-3.8-flash)

> LLM judge skipped this attempt: deterministic checks failed first (cheap checks gate the expensive ones).

| Check | Tier | Why it failed | Evidence |
|---|---|---|---|
| C2 (critical) | det | 'chunk' first appears as: "...cuts long files into small parts called chunks. A **chunk** is a short piece of text c..." (first use is not a bold definition) | cuts long files into small parts called chunks. A **chunk** is a short piece of text c |

**Fix brief sent to generator:**

```
- [CRITICAL] C2 - No required term used before it is defined (first use is the bold definition)
  Problem: 'chunk' first appears as: "...cuts long files into small parts called chunks. A **chunk** is a short piece of text c..." (first use is not a bold definition)
  Evidence: "cuts long files into small parts called chunks. A **chunk** is a short piece of text c"
  How to fix: At the FIRST use of each required term, bold it (e.g. **LLM**, or inside a bold phrase like **large language model (LLM)**) and explain it right away. Do not mention the term anywhere earlier, even in passing. If a term is part of an acronym's full name, bold the WHOLE name with the acronym, e.g. **retrieval-augmented generation (RAG)**.
```

## Attempt 2 - PASSED  (written by gemini:gemini-3.8-flash)

**What changed vs previous attempt:** changed sections: ['how it works']; added: none; removed: none; unchanged: 9 of 10 sections; length 1096 -> 1094 words

## Outcome

Lesson cleared every check.