import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def version() -> str:
    return os.environ.get("PROMPT_VERSION", "v1")

def load(name: str) -> str:
    return (ROOT / "prompts" / version() / f"{name}.md").read_text(encoding="utf-8")

def render(template: str, **kw) -> str:
    for k, v in kw.items():
        template = template.replace("{{" + k + "}}", str(v))
    return template
