"""Every adversary reads its research file from the one path pattern the reviewer
agent file names. A missing file, or an entry without an https link, leaves a lens
arguing from memory with no signal that anything is gone."""

from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "plugins" / "devils-advocate" / "skills" / "adversarial-review"
AGENT = ROOT / "plugins" / "devils-advocate" / "agents" / "adversarial-reviewer.md"
ADVERSARIES = sorted(p.stem for p in (REVIEW / "adversaries").glob("*.md"))


def test_the_reviewer_agent_names_the_research_path():
    body = AGENT.read_text(encoding="utf-8")
    assert "skills/adversarial-review/references/<adversary>/research.md" in body


@pytest.mark.parametrize("name", ADVERSARIES)
def test_every_adversary_has_a_research_file_of_linked_entries(name):
    research = REVIEW / "references" / name / "research.md"
    assert research.is_file(), f"{name} has no research file"
    entries = [
        line
        for line in research.read_text(encoding="utf-8").splitlines()
        if line.startswith("- [")
    ]
    assert entries, f"{name} research file has no entries"
    for line in entries:
        assert re.match(r'- \[[^\]]+\]\(https://\S+\)( - |: ")', line), line[:80]
