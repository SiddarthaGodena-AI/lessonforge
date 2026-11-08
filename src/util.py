import difflib, json, re

def parse_json(text: str):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.S)
        if not m:
            raise
        return json.loads(m.group(0))

def norm(s: str) -> str:
    s = s.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r"[*_`>#]+", " ", s)
    s = re.sub(r"^\s*(?:[-]|\d+[.)])\s+", " ", s, flags=re.M)
    return re.sub(r"\s+", " ", s).strip().lower()

def quote_in_text(quote: str, text: str, min_ratio: float = 0.85) -> bool:
    """True if the quote appears (near-)verbatim in the text. Guards against hallucinated evidence."""
    nq, nt = norm(quote), norm(text)
    if len(nq) < 8:
        return False
    if nq in nt:
        return True
    m = difflib.SequenceMatcher(None, nt, nq, autojunk=False).find_longest_match(0, len(nt), 0, len(nq))
    return m.size / len(nq) >= min_ratio


def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", s.replace("\u2019", "'").lower())

def evidence_still_present(evidence: str, text: str) -> bool | None:
    """Is this evidence snippet still (contiguously, word for word) in the text? Ignores punctuation/markdown and the first and last
    word of the snippet (snippets are often cut mid-word). Returns None if the snippet is too short to judge."""
    toks = _tokens(evidence)[1:-1]
    if len(toks) < 3:
        return None
    return " " + " ".join(toks) + " " in " " + " ".join(_tokens(text)) + " "
