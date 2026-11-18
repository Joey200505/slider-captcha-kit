"""Check local Markdown file links for this standalone repository."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

root=Path(__file__).resolve().parents[1]
errors=[]
documents=[p for p in root.rglob("*.md") if not any(v in {".git","build","dist"} or v.endswith(".egg-info") for v in p.relative_to(root).parts)]
for path in documents:
    for target in re.findall(r"\]\(([^)]+)\)",path.read_text(encoding="utf-8")):
        target=target.strip().strip("<>")
        parsed=urlsplit(target)
        if parsed.scheme or not parsed.path:continue
        resolved=(path.parent/unquote(parsed.path)).resolve()
        if not resolved.is_relative_to(root) or not resolved.exists():
            errors.append(f"{path.relative_to(root)}: {target}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"Checked {len(documents)} Markdown documents; all local file links resolve.")
