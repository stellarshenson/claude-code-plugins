"""End-to-end tests for the lexical-mode grounder over the shipped manifolds.

Exercises the consolidated lexical pipeline through the PUBLIC ``ground()`` API
with the frozen-weight manifolds bundled in config_document_processing.yaml. Two
datasets, two effort tiers:

- DeLaval gold (git-ignored parquet, skip-if-absent) on the LOW tier - the cheap
  monolingual recall-only tier needs no optional dependency; asserts a macro-F1
  floor on a fixed slice (omission-type negatives)
- VitaminC dev (public HF tals/vitaminc, download-on-demand) on the MEDIUM tier -
  importorskip lingua + huggingface_hub, try/except network skip; asserts the
  effort knob loads the medium feature set and the verdict scores in [0, 1]
  (contrastive negatives)

Follows the skip-if-absent + importorskip + try/except-network pattern from
tests/test_calibration.py. Client data is read in place, never written.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path
import warnings

import pytest

from stellars_claude_code_plugins.config import load_document_processing_config
from stellars_claude_code_plugins.document_processing import calibration as C
from stellars_claude_code_plugins.document_processing import grounding as G
from stellars_claude_code_plugins.document_processing import lexical as L

warnings.filterwarnings("ignore")

# DeLaval gold parquet - git-ignored client data; tests skip when absent.
DELAVAL_GOLD = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "grounding"
    / "delaval-forensics"
    / "gold"
    / "golden_grounding_evidence_verified.parquet"
)

# match_types the deterministic cascade can pin as a positive (grounded) verdict.
_GROUNDED = {"exact", "fuzzy", "bm25", "semantic"}


def _lexical_cfg(effort: str):
    """Activate lexical mode (engine=lexical) over the shipped manifolds at one tier.

    The bundled config ships engine=deterministic with the manifolds dormant
    (back-compat); flipping the engine to "lexical" - exactly what train-lexical
    writes into a project override - turns the shipped manifold into the verdict
    head. Returns the GroundingConfig overlaid with the chosen effort tier.
    """
    orig = C.load_calibration_from_config

    def _engine_lexical(path=None):
        block = dict(orig(path) or {})
        block["engine"] = "lexical"
        return block

    C.load_calibration_from_config = _engine_lexical
    G._LEXICAL_VERDICT_CACHE.clear()
    return load_document_processing_config().overlay(lexical_effort=effort)


def _restore():
    """Undo the lexical-engine monkeypatch and clear the verdict cache."""
    import importlib

    importlib.reload(C)  # restore the original load_calibration_from_config
    G._LEXICAL_VERDICT_CACHE.clear()


def _macro_f1(y_true: list[int], y_pred: list[int]) -> float:
    """Mean of supported-F1 and hallucination-F1 (sklearn-free; imbalance-robust)."""

    def f1(pos: int) -> float:
        tp = sum(1 for a, b in zip(y_true, y_pred) if a == pos and b == pos)
        fp = sum(1 for a, b in zip(y_true, y_pred) if a != pos and b == pos)
        fn = sum(1 for a, b in zip(y_true, y_pred) if a == pos and b != pos)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        return 2 * p * r / (p + r) if p + r else 0.0

    return (f1(1) + f1(0)) / 2


class TestEffortKnobSelectsManifold:
    """Always-runs: the effort knob loads the matching tier's frozen manifold."""

    def test_low_tier_resolves_to_low_manifold_and_features(self):
        cfg = _lexical_cfg("low")
        try:
            resolved = G._config_lexical_verdict(cfg)
        finally:
            _restore()
        assert resolved is not None
        verdict, effort, chunk_max, chunk_ovl = resolved
        assert effort == "low"
        # the shipped low manifold's feature_order IS the low tier contract
        assert verdict.feature_order == L.TIER_FEATURES["low"]
        assert len(verdict.feature_order) == 11
        assert verdict.weights.get("Intercept") is not None
        # lexical operating point, not the general-cascade 1500/0.25
        assert (chunk_max, chunk_ovl) == (300, 0.1)

    def test_effort_knob_switches_feature_set(self):
        # low vs medium load different manifolds with different feature contracts
        cfg_low = _lexical_cfg("low")
        try:
            low = G._config_lexical_verdict(cfg_low)
        finally:
            _restore()
        cfg_med = _lexical_cfg("medium")
        try:
            med = G._config_lexical_verdict(cfg_med)
        finally:
            _restore()
        assert low[0].feature_order == L.TIER_FEATURES["low"]  # 11
        assert med[0].feature_order == L.TIER_FEATURES["medium"]  # 14
        assert low[0].feature_order != med[0].feature_order


class TestDeLavalLowTierEndToEnd:
    """DeLaval gold on the LOW tier (no optional dep) via the public API."""

    def test_low_tier_macro_f1_floor_on_fixed_slice(self):
        if not DELAVAL_GOLD.exists():
            pytest.skip(f"DeLaval gold parquet absent (git-ignored): {DELAVAL_GOLD}")
        pd = pytest.importorskip("pandas")

        df = pd.read_parquet(DELAVAL_GOLD)
        assert {"claim", "source_text", "label"} <= set(df.columns)
        # fixed, deterministic slice: first 20 supported + first 20 hallucination
        sup = df[df["label"] == 1].head(20)
        hal = df[df["label"] == 0].head(20)
        sample = pd.concat([sup, hal]).reset_index(drop=True)

        cfg = _lexical_cfg("low")
        try:
            y_true: list[int] = []
            y_pred: list[int] = []
            probs: list[float] = []
            for _, r in sample.iterrows():
                m = G.ground(r["claim"], [("src", r["source_text"])], config=cfg)
                probs.append(m.verdict_probability)
                assert m.verdict_features  # the tier's feature dict is populated
                assert set(m.verdict_features) == set(L.TIER_FEATURES["low"])
                y_true.append(int(r["label"]))
                y_pred.append(1 if m.match_type in _GROUNDED else 0)
        finally:
            _restore()

        # the frozen-weight verdict scores a proper probability for every row
        assert all(0.0 <= p <= 1.0 for p in probs)
        sup_recall = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 1) / 20
        hal_reject = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 0) / 20
        mf1 = _macro_f1(y_true, y_pred)
        # floors sit well below the observed point (supp=1.0, halr=0.65, F1=0.82)
        # so the assertion tolerates small-slice sampling
        assert sup_recall >= 0.80, (sup_recall, hal_reject, mf1)
        assert hal_reject >= 0.40, (sup_recall, hal_reject, mf1)
        assert mf1 >= 0.60, (sup_recall, hal_reject, mf1)


class TestVitaminCMediumTierEndToEnd:
    """VitaminC dev on the MEDIUM tier (lingua-gated) via the public API.

    Network/dep-gated: importorskip lingua (the medium-tier language dep) and
    huggingface_hub; download VitaminC dev.jsonl on first use, skip cleanly on no
    network. Structural assertions only - the medium feature set loads and the
    frozen verdict scores in [0, 1] over a fixed contrastive slice.
    """

    def test_medium_tier_scores_vitaminc_slice(self):
        pytest.importorskip("lingua")  # medium-tier language features
        hf = pytest.importorskip("huggingface_hub")
        try:
            path = hf.hf_hub_download("tals/vitaminc", "dev.jsonl", repo_type="dataset")
        except Exception as exc:  # noqa: BLE001 - skip on no network / hub failure
            pytest.skip(f"VitaminC unavailable: {exc}")

        rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
        by: dict[str, list] = {"SUPPORTS": [], "REFUTES": []}
        for r in rows:
            if r.get("label") in by and r.get("claim") and r.get("evidence"):
                by[r["label"]].append(r)
        per = 15
        sample = by["SUPPORTS"][:per] + by["REFUTES"][:per]
        assert len(sample) == 2 * per  # fixed, deterministic slice

        valid = {"exact", "fuzzy", "bm25", "semantic", "contradicted", "none"}
        cfg = _lexical_cfg("medium")
        try:
            seen = collections.Counter()
            for r in sample:
                m = G.ground(
                    r["claim"], [(str(r.get("page", "src")), r["evidence"])], config=cfg
                )
                assert m.match_type in valid
                assert 0.0 <= m.verdict_probability <= 1.0
                assert set(m.verdict_features) == set(L.TIER_FEATURES["medium"])
                seen[m.match_type] += 1
        finally:
            _restore()
        # the slice produced verdicts (machinery ran end to end over both labels)
        assert sum(seen.values()) == 2 * per
