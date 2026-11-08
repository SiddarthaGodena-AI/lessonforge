"""One real generator call; shows why a lesson might be short/malformed.  python scripts/probe_generator.py"""
import re, sys; sys.path.insert(0, ".")
from src.context import build_context
from src.nodes import generator
from src.llm import provider
ctx = build_context()
md = generator.generate(ctx)
m = provider.LAST
print(f"model={m.get('provider')}:{m.get('model')}  finish_reason={m.get('finish')}  in={m.get('in')} out={m.get('out')} reasoning_tokens={m.get('reasoning')} extra_body_sent={m.get('extra_body')}")
print(f"words={len(re.findall(r'\\w+', md))}  '## ' headings={len(re.findall(r'^## ', md, re.M))} (need 10)")
print("----- first 600 chars -----"); print(md[:600]); print("----- last 300 chars -----"); print(md[-300:])
open("outputs/probe_lesson.md", "w", encoding="utf-8").write(md); print("\nfull text saved: outputs/probe_lesson.md")
