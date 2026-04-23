"""Numeric and named-entity contradiction detection between claim and passage.

Used by :func:`grounding.ground` when some layer has a positive signal. If a
number or named entity appears in the claim with a differing value in the
matched passage (but same category / context word), we record a mismatch.

Design points:
    - Regex-only. No ML. Deterministic.
    - Compares claim tokens against the winning passage only. The full source
      is not scanned because we only flag direct disagreement between claim
      and its own best evidence.
    - Tolerates unit formatting variations ("1,000" == "1000", "10 %" == "10%").
    - Tech-entity whitelist catches common "H100 vs A100" style contradictions.

Public API:
    :func:`extract_numbers` -> list of (value, unit, context_word)
    :func:`extract_entities` -> list of named-entity strings
    :func:`find_mismatches` -> (numeric_mismatches, entity_mismatches)

Each mismatch is ``(claim_value, passage_value)`` suitable for
``GroundingMatch.numeric_mismatches`` / ``entity_mismatches``.
"""

from __future__ import annotations

import re

# ---- numeric extraction --------------------------------------------------

_NUMBER_RE = re.compile(
    r"""
    (?P<value>
        \d{1,3}(?:,\d{3})+(?:\.\d+)?      # 1,234 / 1,234,567.89
        |
        \d+(?:\.\d+)?                     # 42 / 3.14
    )
    \s*
    (?P<unit>
        %|percent|                         # percentages
        k|K|m|M|b|B|                       # SI suffix (word-boundary anchored below)
        GB|MB|KB|TB|                       # storage
        ms|s|sec|seconds|min|h|hours|      # time
        px|em|rem|pt|                      # typography
        kg|g|lbs|                          # mass
        km|cm|mm|                          # distance
        USD|EUR|                           # currencies
        )?
    """,
    re.VERBOSE,
)

# Context word: a following noun like "nodes", "users", "GPUs" etc.
_CONTEXT_WORD_RE = re.compile(r"\s*([A-Za-z][A-Za-z\-]{2,})")

# Dates
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _normalise_value(raw: str) -> str:
    """Strip thousands separators and trailing .0 for canonical comparison."""
    v = raw.replace(",", "")
    if "." in v:
        try:
            f = float(v)
            if f == int(f):
                return str(int(f))
            return f"{f:g}"
        except ValueError:
            return v
    return v


def _normalise_unit(raw: str | None) -> str:
    if not raw:
        return ""
    u = raw.strip().lower()
    if u == "percent":
        return "%"
    return u


def extract_numbers(text: str) -> list[tuple[str, str, str]]:
    """Return list of ``(value, unit, context_word)`` triples.

    Captures optional unit immediately after the number and the next word as
    context (e.g. "42 nodes" -> ``("42", "", "nodes")``). ``context_word`` is
    lowercased; ``value`` and ``unit`` preserve normalisation.
    """
    out: list[tuple[str, str, str]] = []
    if not text:
        return out
    year_spans: set[tuple[int, int]] = set()
    for m in _YEAR_RE.finditer(text):
        year_spans.add((m.start(), m.end()))
    for m in _NUMBER_RE.finditer(text):
        value = _normalise_value(m.group("value"))
        unit = _normalise_unit(m.group("unit"))
        # Context word: look at up to ~20 chars after the match
        tail = text[m.end() : m.end() + 40]
        cw_match = _CONTEXT_WORD_RE.match(tail)
        context_word = cw_match.group(1).lower() if cw_match else ""
        # If this number looks like a 4-digit year (per _YEAR_RE) and has no
        # other unit/context, tag it as "year" so claim-vs-passage years can
        # be compared even when both appear bare.
        if not unit and not context_word and (m.start(), m.end()) in year_spans:
            context_word = "year"
        # Filter noise: single-digit years-like tokens without unit or context are uninformative
        if not unit and not context_word and len(value) <= 1:
            continue
        out.append((value, unit, context_word))

    # Also pick up standalone 4-digit years for date-style contradictions
    for m in _YEAR_RE.finditer(text):
        year = m.group(0)
        # Skip if already captured as a numeric (would be duplicate) by checking overlap
        already = any(v == year for v, _, _ in out)
        if not already:
            out.append((year, "", "year"))
    return out


# ---- named-entity extraction --------------------------------------------

# Tech-entity whitelist: common hardware / model / framework strings. A
# contradiction between items from the SAME list is a high-signal mismatch.
_TECH_ENTITY_CLASSES: dict[str, list[str]] = {
    "nvidia_gpu": [
        "H100",
        "A100",
        "V100",
        "P100",
        "K80",
        "T4",
        "L4",
        "L40",
        "H200",
        "B100",
        "A10",
    ],
    "amd_gpu": ["MI250", "MI300", "MI300X", "MI100", "MI210"],
    "apple_soc": ["M1", "M2", "M3", "M4", "M1 Pro", "M2 Pro", "M3 Pro"],
    "llm_model": [
        "GPT-3",
        "GPT-3.5",
        "GPT-4",
        "GPT-4o",
        "GPT-5",
        "Claude",
        "Claude 2",
        "Claude 3",
        "Claude 3.5",
        "Llama",
        "Llama 2",
        "Llama 3",
        "PaLM",
        "PaLM 2",
        "Gemini",
        "Mistral",
        "Mixtral",
    ],
    "deep_learning_framework": ["PyTorch", "TensorFlow", "JAX", "MXNet", "Keras"],
    "cloud": ["AWS", "Azure", "GCP", "OCI"],
    "database": ["PostgreSQL", "MySQL", "MongoDB", "Cassandra", "DynamoDB", "SQLite", "Redis"],
}


def _find_tech_entities(text: str) -> dict[str, list[str]]:
    """Return ``{category: [matches]}`` for tech entities found in text.

    Matching is case-sensitive for acronyms but tolerates surrounding
    punctuation.
    """
    out: dict[str, list[str]] = {}
    for category, values in _TECH_ENTITY_CLASSES.items():
        hits = []
        for val in values:
            # Word-boundary-ish match (avoid matching "V1000" when looking for "V100")
            pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(val) + r"(?![A-Za-z0-9])")
            if pattern.search(text):
                hits.append(val)
        if hits:
            out[category] = hits
    return out


_CAPITALISED_PHRASE_RE = re.compile(
    # Single token: starts with uppercase, may contain lowercase, digits, and
    # internal hyphens (e.g. "RoPE", "RoPE-Mid", "GPT-4", "Llama-3.1"). Then
    # optionally up to 3 additional whitespace-separated capitalised tokens
    # for multi-word proper nouns ("New York Times", "Stanford Natural
    # Language Processing Group").
    r"\b[A-Z][a-zA-Z0-9]*(?:-[A-Za-z0-9]+)*(?:\s+[A-Z][a-zA-Z0-9]*(?:-[A-Za-z0-9]+)*){0,3}\b"
)

_STOPWORD_CAPS = {
    "The",
    "This",
    "That",
    "These",
    "Those",
    "A",
    "An",
    "And",
    "Or",
    "But",
    "If",
    "When",
    "Where",
    "While",
    "I",
    "We",
    "You",
    "They",
    "He",
    "She",
    "It",
    "Our",
    "Their",
    "My",
    "Your",
    "His",
    "Her",
}


def extract_entities(text: str) -> list[str]:
    """Return capitalised multi-word named-entity candidates.

    Uses a heuristic: two or more capitalised tokens in a row, excluding the
    first token of the text if it begins a sentence with a stopword like
    "The". Deduplicated while preserving order.
    """
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in _CAPITALISED_PHRASE_RE.finditer(text):
        phrase = m.group(0).strip()
        # Drop single-word stopword-only matches
        parts = phrase.split()
        if len(parts) == 1 and parts[0] in _STOPWORD_CAPS:
            continue
        # Drop "plain" single-word matches (risk of false positives on any
        # sentence-initial capitalised word). Keep distinctive single-word
        # proper-noun forms:
        #   - contains a digit           (H100, GPT-4, Llama-3)
        #   - contains a hyphen          (RoPE-Mid, Claude-3)
        #   - camelCase / mixed case     (iPhone, RoPE, MobileBert)
        # A plain word like "Simply", "Where", "Models" does not qualify.
        if len(parts) == 1:
            tok = parts[0]
            if re.search(r"\d", tok):
                pass
            elif "-" in tok:
                pass
            elif any(c.isupper() for c in tok[1:]):
                pass
            else:
                continue
        if phrase in seen:
            continue
        seen.add(phrase)
        out.append(phrase)
    return out


# ---- mismatch detection --------------------------------------------------


def _numeric_key(value: str, unit: str, context_word: str) -> tuple[str, str]:
    """Key that says "these two numbers are talking about the same thing".

    Two numbers share a key when their unit matches or their context word
    matches. Either signal is sufficient.
    """
    return (unit, context_word)


def find_numeric_mismatches(claim: str, passage: str) -> list[tuple[str, str]]:
    """Return ``[(claim_num, passage_num)]`` for disagreeing numbers.

    A disagreement requires both sides to share either the same unit
    (``"%"``, ``"GB"``) or the same context word (``"nodes"``, ``"users"``)
    AND have different values.

    Iter 6 specificity gate (mirrors ``find_entity_mismatches``): the claim
    must have EXACTLY ONE number in a given (unit, context) category
    before a mismatch is flagged. Multi-value lists (e.g. "Llama3-8B,
    Llama3-70B, Mistral-7B, Mixtral-8x22B" - four numbers in the
    ``b`` billion-params category) are NOT flagged because the winning
    passage may legitimately cite only a subset; an inventory-style
    claim that overlaps with part of the source is supported, not
    contradicted. The overlap check also skips when any claim value
    already appears among the passage values for the same key.
    """
    claim_nums = extract_numbers(claim)
    if not claim_nums:
        return []
    passage_nums = extract_numbers(passage)
    if not passage_nums:
        return []

    # Build index of passage numbers by (unit, context_word)
    pass_by_key: dict[tuple[str, str], list[str]] = {}
    for v, u, cw in passage_nums:
        key_full = (u, cw)
        pass_by_key.setdefault(key_full, []).append(v)
        # Also index by just-unit and just-context to allow partial key match
        if u:
            pass_by_key.setdefault((u, ""), []).append(v)
        if cw:
            pass_by_key.setdefault(("", cw), []).append(v)

    # Group claim numbers by the same partial-key lookup used for passage,
    # so we can detect multi-entry claim categories and skip them.
    claim_by_key: dict[tuple[str, str], list[str]] = {}
    for cv, cu, ccw in claim_nums:
        for key in [(cu, ccw), (cu, ""), ("", ccw)]:
            if key == ("", ""):
                continue
            if key in pass_by_key:
                claim_by_key.setdefault(key, []).append(cv)
                break

    mismatches: list[tuple[str, str]] = []
    for key, claim_values in claim_by_key.items():
        # Specificity gate: multi-value lists aren't contradicted by partial
        # passage coverage.
        if len(claim_values) != 1:
            continue
        passage_values = pass_by_key.get(key, [])
        if not passage_values:
            continue
        cv = claim_values[0]
        # Overlap check: any claim value in passage_values means supported.
        if cv in passage_values:
            continue
        mismatches.append((cv, passage_values[0]))
    return mismatches


def find_entity_mismatches(claim: str, passage: str) -> list[tuple[str, str]]:
    """Return ``[(claim_entity, passage_entity)]`` for tech-category disagreements.

    Only tech entities from the whitelist are checked. A mismatch requires:

    1. Claim and passage share a tech category (e.g. ``gpu_model``).
    2. Claim has EXACTLY ONE entity in that category. Multi-entity lists
       like "we tested GPT-4o, Claude-3.5-Sonnet, and Llama3-70B" are NOT
       flagged because the winning passage might mention only a subset;
       the claim is not "contradicted" by the passage citing a different
       subset of models.
    3. The single claim entity does NOT appear among the passage's
       entities in the same category. Any overlap (even partial) is
       treated as support, not contradiction.

    This catches the "H100 vs A100" / "42 nodes vs 12 nodes" single-value
    fabrication class while allowing list-compatible subsets. The rule was
    tightened in Iter 6 after cross-validation found the old per-item loop
    false-flagging real paraphrases (Ye y07: "ChatGPT, GPT-4o,
    Claude-3.5-Sonnet" vs passage naming Llama3 models in the same
    judge-models category).
    """
    claim_tech = _find_tech_entities(claim)
    if not claim_tech:
        return []
    passage_tech = _find_tech_entities(passage)
    if not passage_tech:
        return []

    mismatches: list[tuple[str, str]] = []
    for category, claim_items in claim_tech.items():
        if category not in passage_tech:
            continue
        passage_items = passage_tech[category]
        # Specificity gate: multi-entity claims are lists, not assertions.
        if len(claim_items) != 1:
            continue
        (ci,) = claim_items
        # Overlap check: if the single claim entity already appears in
        # passage, it's confirmed, not contradicted.
        if ci in passage_items:
            continue
        # One specific claim entity, passage has different entity(ies)
        # in the same category -> real contradiction.
        mismatches.append((ci, passage_items[0]))
    return mismatches


def list_claim_entities(claim: str) -> list[str]:
    """Union of tech-whitelist entities + capitalised proper-noun phrases in ``claim``.

    Deduplicated, preserves insertion order. Used as the denominator for
    entity-presence penalty calculations.
    """
    flat: list[str] = []
    for items in _find_tech_entities(claim).values():
        flat.extend(items)
    for phrase in extract_entities(claim):
        if phrase not in flat:
            flat.append(phrase)
    return flat


def find_absent_entities(claim: str, full_source: str) -> list[str]:
    """Return claim entities that appear nowhere in the full source text.

    This is a weaker signal than :func:`find_entity_mismatches` (which
    requires the source to mention the SAME category with a DIFFERENT
    value). ``find_absent_entities`` catches the "unsupported claim
    entity" pattern: a proper noun named in the claim with zero string
    occurrences in the source. Examples:

        claim "RoPE-Mid fixes middle-of-context degradation", source
        is the Liu 2023 paper that never names "RoPE-Mid"
        → ["RoPE-Mid"]

        claim "experiments on H100 donated by Meta", source mentions
        no "H100" or "Meta"
        → ["H100", "Meta"]

    Comparison is case-insensitive substring. This catches the
    fabricated-specific-entity failure mode where the claim scores high
    lexically+semantically via topical overlap but the distinguishing
    entity is invented.
    """
    flat = list_claim_entities(claim)
    if not flat:
        return []
    source_lower = full_source.lower()
    absent: list[str] = []
    for e in flat:
        if e.lower() not in source_lower:
            absent.append(e)
    return absent


def find_mismatches(
    claim: str, passage: str
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Find all numeric + entity mismatches between claim and passage."""
    return (
        find_numeric_mismatches(claim, passage),
        find_entity_mismatches(claim, passage),
    )


__all__ = [
    "extract_numbers",
    "extract_entities",
    "find_numeric_mismatches",
    "find_entity_mismatches",
    "find_absent_entities",
    "list_claim_entities",
    "find_mismatches",
]
