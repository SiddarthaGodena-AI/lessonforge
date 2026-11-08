Read the lesson and list the factual claims it makes about RAG, LLMs, or how they work. Output JSON only.

INCLUDE: statements about what RAG/LLMs are, what they can or cannot do, how the steps work, dates, names, numbers, and absolute words (always, never, every, all).
EXCLUDE: the invented example scenario (course names, chunk text, refund rules), the analogy itself, questions, headings, advice, and definitions of everyday words.

For each claim give the EXACT sentence from the lesson as "quote" (copy character for character).
Return: {"claims":[{"id":1,"claim":"<claim in one short sentence>","quote":"<exact sentence from lesson>"}]}  (max 25 claims, most important first)

<lesson>
{{LESSON}}
</lesson>
