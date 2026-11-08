# Rejection Log - Introduction to RAG

**Final status:** PASSED  |  **Attempts:** 3 of 3 allowed  |  **Prompt version:** v2  |  **Learned-rules version:** r0  |  **Rubric v1**

**Models that actually answered:** gemini:gemini-3.6-flash, gemini:gemini-3.8-flash, groq:openai/gpt-oss-120b, groq:openai/gpt-oss-20b

## Attempt 1 - FAILED: A1, C1  (written by gemini:gemini-3.8-flash)

> DELIBERATE SABOTAGE 'factual' injected after generation: "RAG works by retraining the LLM's weights every time a new document is added to the knowle..."

| Check | Tier | Why it failed | Evidence |
|---|---|---|---|
| A1 (critical) | llm | Claim contradicts fact sheet: "RAG works by retraining the LLM's weights every time a new document is added to the knowledge base." - Misconception: RAG does not retrain LLM weights | RAG works by retraining the LLM's weights every time a new document is added to the knowledge base. |
| C1 (critical) | llm | The term "training cutoff" is used without a plain‑language definition. Adding a brief explanation such as "the date after which the model was not trained on any new data" would fix it. | It only knows facts up to its training cutoff date. |

**Fix brief sent to generator:**

```
- [CRITICAL] A1 - No claim contradicts the fact sheet
  Problem: Claim contradicts fact sheet: "RAG works by retraining the LLM's weights every time a new document is added to the knowledge base." - Misconception: RAG does not retrain LLM weights
  Evidence: "RAG works by retraining the LLM's weights every time a new document is added to the knowledge base."
  How to fix: Remove or correct the claim so it agrees with the fact sheet. Do not repeat the false idea.
- [CRITICAL] C1 - Every technical term has a short plain-language definition
  Problem: The term "training cutoff" is used without a plain‑language definition. Adding a brief explanation such as "the date after which the model was not trained on any new data" would fix it.
  Evidence: "It only knows facts up to its training cutoff date."
  How to fix: Give the term a plain-language definition: bold at first use AND a Glossary entry of at most 25 words.
```

## Attempt 2 - FAILED: A2  (written by gemini:gemini-3.8-flash)

**What changed vs previous attempt:** changed sections: ['the problem', 'what is rag?', 'glossary']; added: none; removed: none; unchanged: 7 of 10 sections; length 1035 -> 1066 words

**Regressions (passed before, fail now):** A2

| Check | Tier | Why it failed | Evidence |
|---|---|---|---|
| A2 (critical) | llm | Claim unsupported: "Retraining an LLM with new facts takes huge time and money." - Fact sheet does not address cost/time of retraining | Normally, training an LLM again with new facts takes huge time and money. |

**Fix brief sent to generator:**

```
- [CRITICAL] A2 - No unsupported technical claim stated as fact
  Problem: Claim unsupported: "Retraining an LLM with new facts takes huge time and money." - Fact sheet does not address cost/time of retraining
  Evidence: "Normally, training an LLM again with new facts takes huge time and money."
  How to fix: Delete the unsupported claim, or rewrite it using only fact-sheet facts. Avoid dates, names, numbers and words like always/never/every.
```

## Attempt 3 - PASSED  (written by gemini:gemini-3.6-flash)

**What changed vs previous attempt:** changed sections: ['why it matters']; added: none; removed: none; unchanged: 9 of 10 sections; length 1066 -> 1053 words

## Outcome

Lesson cleared every check.