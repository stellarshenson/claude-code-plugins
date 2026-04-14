"""Guard against stale module paths referenced from CI workflows.

CI runs `python -c "from stellars_claude_code_plugins.X import Y"` snippets to
verify the wheel imports cleanly. When the package is renamed (e.g. `engine` ->
`autobuild`), those snippets become silent landmines that only blow up in CI.

These tests parse `.github/workflows/ci.yml`, extract every `from
stellars_claude_code_plugins...` import statement, and import them in-process so
a rename surfaces locally via `make test`.
"""

import importlib
from pathlib import Path
import re

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

IMPORT_RE = re.compile(
    r"from\s+(stellars_claude_code_plugins(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)\s+import\s+([a-zA-Z_][a-zA-Z0-9_,\t ]*)"
)


def _extract_ci_imports() -> list[tuple[str, str, str]]:
    """Return (job, module, name) for every import in CI workflow run blocks."""
    workflow = yaml.safe_load(CI_WORKFLOW.read_text())
    found: list[tuple[str, str, str]] = []
    for job_name, job in workflow.get("jobs", {}).items():
        for step in job.get("steps", []):
            run = step.get("run")
            if not isinstance(run, str):
                continue
            for module, names in IMPORT_RE.findall(run):
                for name in (n.strip() for n in names.split(",")):
                    if name:
                        found.append((job_name, module, name))
    return found


CI_IMPORTS = _extract_ci_imports()


def test_ci_workflow_has_imports_to_check():
    """Sanity check: the regex actually finds something."""
    assert CI_IMPORTS, (
        "No stellars_claude_code_plugins imports found in ci.yml - "
        "regex broken or workflow restructured."
    )


@pytest.mark.parametrize(
    ("job", "module", "name"),
    CI_IMPORTS,
    ids=[f"{j}::{m}.{n}" for j, m, n in CI_IMPORTS],
)
def test_ci_import_resolves(job: str, module: str, name: str):
    """Every `from X import Y` snippet in CI must resolve in-process."""
    mod = importlib.import_module(module)
    assert hasattr(mod, name), (
        f"CI job '{job}' imports '{name}' from '{module}' but it does not exist. "
        f"Update .github/workflows/ci.yml or restore the symbol."
    )
