"""Guard the single-source-of-truth link between the popular-science writer skill
and the popular-science adversary. If someone re-embeds a divergent craft canon in
the adversary instead of pointing at the shared file, these fail."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "datascience" / "skills" / "popular-science"
CANON = SKILL_DIR / "references" / "craft-canon.md"
ADVERSARY = (
    ROOT / "datascience" / "skills" / "adversarial-review" / "adversaries" / "popular-science.md"
)


def test_shared_canon_exists():
    assert CANON.is_file(), "shared craft canon missing"


def test_adversary_points_to_shared_canon():
    body = ADVERSARY.read_text(encoding="utf-8")
    assert "popular-science/references/craft-canon.md" in body, (
        "adversary must reference the shared canon path"
    )
    # It must NOT carry a private full copy that could drift from the shared source.
    assert "WRITING - best practices" not in body, (
        "adversary re-embedded a divergent canon; point to the shared file instead"
    )


def test_writer_uses_shared_canon():
    assert "references/craft-canon.md" in (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def test_fetch_article_tool_present():
    assert (SKILL_DIR / "scripts" / "fetch_article.py").is_file()
