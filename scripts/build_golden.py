"""Writes tests/golden/flawed/<name>.md and tests/golden/manifest.json from the good lesson."""
import json
from pathlib import Path
from tests.golden.flaws import FLAWS, ALSO_OK
G = Path(__file__).resolve().parents[1] / "tests/golden"
good = (G / "good_lesson.md").read_text()
(G / "flawed").mkdir(exist_ok=True)
manifest = {"good": "good_lesson.md", "flawed": {}}
for name, (fn, tier, exp) in FLAWS.items():
    out = fn(good)
    assert out != good, f"flaw '{name}' did not change the lesson"
    (G / "flawed" / f"{name}.md").write_text(out)
    manifest["flawed"][name] = {"file": f"flawed/{name}.md", "tier": tier, "expected_fail": sorted(exp), "also_ok": sorted(ALSO_OK.get(name, set()))}
(G / "manifest.json").write_text(json.dumps(manifest, indent=2))
print(f"wrote {len(FLAWS)} flawed lessons")
