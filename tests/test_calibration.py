"""Tests for the Bayesian grounding-verdict calibrator and its integration.

Covers: config-driven prior (no hardcode), the calibrator head (fit / predict /
save-load / incremental / evaluate), the R3/R4 regression guarantees, the
ground() calibrated-engine integration + back-compat, calibrated-beats-prior on
a shipped fixture, and the train -> config -> ground() round-trip.
"""

from __future__ import annotations

import json
from pathlib import Path
import warnings

import pandas as pd
import pytest

from stellars_claude_code_plugins.document_processing import calibration as C
from stellars_claude_code_plugins.document_processing import grounding as G
from stellars_claude_code_plugins.document_processing.semantic import SemanticHit

warnings.filterwarnings("ignore")

FIXTURE = Path(__file__).parent / "fixtures" / "calibration_multilingual.jsonl"

# Small sampler settings keep the suite fast; we assert structure/behaviour,
# not convergence diagnostics.
DRAWS = 150
TUNE = 150


def _fixture_df() -> pd.DataFrame:
    rows = [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]
    return pd.DataFrame(rows)


def _prior_verdict() -> C.CalibratedVerdict:
    """Point-estimate verdict from the CONFIG prior means (untrained)."""
    spec = C.load_prior_spec()
    return C.CalibratedVerdict.from_weights(
        {k: mu for k, (mu, _sd) in spec.items()}, threshold=0.5
    )


class FakeGrounder:
    """Minimal semantic-grounder stub returning a controlled hit + self-score."""

    def __init__(self, score: float, self_s: float):
        self._index = None
        self._s = score
        self._ss = self_s

    def index_sources(self, pairs):
        self._index = object()

    def search(self, claim, top_k=1):
        return [
            SemanticHit(
                score=self._s,
                source_index=0,
                source_path="",
                char_start=0,
                char_end=5,
                matched_text="x",
            )
        ]

    def self_score(self, claim):
        return self._ss

    def percentile_threshold(self, top_pct=0.02, floor=0.65):
        return 0.0


class TestPriorConfigDriven:
    def test_prior_comes_from_config_not_hardcode(self):
        spec = C.load_prior_spec()
        assert set(spec) == set(C.COEFFICIENTS)
        # the value is the one in config_document_processing.yaml -> calibration.prior
        assert spec["semantic"] == (4.5, 2.0)
        # the old python hardcode is gone
        assert not hasattr(C, "_PRIOR")


class TestCalibrationHead:
    def test_from_weights_pointmass_monotonic_zero_uncertainty(self):
        v = C.CalibratedVerdict.from_weights({"Intercept": -3.0, "exact": 6.0}, threshold=0.5)
        p_lo, u = v.predict_with_uncertainty({"exact": 0.0})
        p_hi, _ = v.predict_with_uncertainty({"exact": 1.0})
        assert p_hi[0] > p_lo[0]
        assert u[0] == pytest.approx(0.0, abs=1e-9)

    def test_save_load_roundtrip(self, tmp_path):
        v = C.fit_calibrator(_fixture_df(), draws=DRAWS, tune=TUNE, random_seed=0)
        f = tmp_path / "cal.json"
        v.save(f)
        v2 = C.CalibratedVerdict.load(f)
        feat = {"exact": 1.0}
        assert v2.predict_proba(feat)[0] == pytest.approx(v.predict_proba(feat)[0], abs=0.05)

    def test_incremental_update_summarises_all_coeffs(self):
        v = C.fit_calibrator(_fixture_df(), draws=DRAWS, tune=TUNE, random_seed=0)
        v2 = C.update_calibrator(
            v, _fixture_df().head(8), draws=DRAWS, tune=TUNE, include_anchor=True, random_seed=1
        )
        # constant-in-training predictors (e.g. nli_* when NLI is off) are
        # dropped, so the summary is a non-empty subset of all coefficients.
        summ = v2.posterior_summary()
        assert summ and set(summ) <= set(C.COEFFICIENTS)

    def test_evaluate_reports_per_language(self):
        v = C.fit_calibrator(_fixture_df(), draws=DRAWS, tune=TUNE, random_seed=0)
        m = C.evaluate(v, _fixture_df())
        assert "by_lang" in m and {"en", "nb", "fr"} <= set(m["by_lang"])
        assert 0.0 <= m["precision"] <= 1.0


class TestCalibratedRegression:
    """The load-bearing A5/A4 guarantees, under the untrained config prior."""

    def test_R3_fabrication_denied(self):
        v = _prior_verdict()
        src = [("s.txt", "Totally unrelated content about ocean weather systems.")]
        m = G.ground(
            "qz zztop kv", src, semantic_grounder=FakeGrounder(0.70, 0.88), calibrated_verdict=v
        )
        assert m.match_type == "none"
        assert m.verdict_probability < 0.5

    def test_R4_crosslingual_confirmed(self):
        v = _prior_verdict()
        src = [("s.txt", "Totally unrelated content about ocean weather systems.")]
        m = G.ground(
            "qz zztop kv", src, semantic_grounder=FakeGrounder(0.86, 0.88), calibrated_verdict=v
        )
        assert m.match_type != "none"
        assert m.verdict_probability >= 0.5


class TestGroundCalibratedIntegration:
    def test_lexical_default_is_active(self):
        # The bundled config ships engine=lexical at the medium tier, so the
        # default verdict head is the shipped frozen-weight manifold: an exact
        # match still wins and the verdict sets verdict_probability in [0, 1].
        G._LEXICAL_VERDICT_CACHE.clear()
        try:
            m = G.ground(
                "the estate has three walled gardens",
                [("s.txt", "The estate has three walled gardens.")],
            )
        finally:
            G._LEXICAL_VERDICT_CACHE.clear()
        assert m.match_type == "exact"
        assert 0.0 <= m.verdict_probability <= 1.0

    def test_deterministic_mode_is_backcompat_optin(self):
        # Opt-in back-compat: flip calibration.engine to "deterministic" and the
        # verdict head reverts to the deterministic cascade - exact wins and
        # verdict_probability stays the -1.0 sentinel (no verdict engine used).
        from stellars_claude_code_plugins.document_processing import calibration as _C

        orig = _C.load_calibration_from_config

        def _deterministic_engine(path=None):
            b = dict(orig(path) or {})
            b["engine"] = "deterministic"
            return b

        _C.load_calibration_from_config = _deterministic_engine
        G._LEXICAL_VERDICT_CACHE.clear()
        try:
            m = G.ground(
                "the estate has three walled gardens",
                [("s.txt", "The estate has three walled gardens.")],
            )
        finally:
            _C.load_calibration_from_config = orig
            G._LEXICAL_VERDICT_CACHE.clear()
        assert m.match_type == "exact"
        assert m.verdict_probability == -1.0

    def test_calibrated_exact_confirmed_and_fields_exposed(self):
        v = _prior_verdict()
        m = G.ground(
            "the estate has three walled gardens",
            [("s.txt", "The estate has three walled gardens.")],
            calibrated_verdict=v,
        )
        assert m.match_type == "exact"
        assert m.verdict_probability > 0.5
        assert set(C.PREDICTORS) <= set(m.verdict_features)


class TestConfigTransferRoundtrip:
    """E6: train -> config set-calibrator -> ground() auto-uses the weights."""

    def test_train_then_config_then_ground(self, tmp_path, monkeypatch):
        import yaml

        from stellars_claude_code_plugins.document_processing import cli

        # 1. train + save a profile
        v = C.fit_calibrator(_fixture_df(), draws=DRAWS, tune=TUNE, random_seed=0)
        prof = tmp_path / "cal.json"
        v.save(prof)

        # 2. transfer learned weights into a project config under a temp CWD
        monkeypatch.chdir(tmp_path)
        assert cli.main(["config", "set-calibrator", "--profile", str(prof)]) == 0
        cfgfile = tmp_path / ".stellars-plugins" / "config_document_processing.yaml"
        assert cfgfile.is_file()
        block = yaml.safe_load(cfgfile.read_text())["calibration"]
        assert block["engine"] == "calibrated" and block["weights"]

        # 3. ground() from this CWD auto-detects the calibrated engine from config
        G._VERDICT_CACHE.clear()
        m = G.ground(
            "the estate has three walled gardens",
            [("s.txt", "The estate has three walled gardens.")],
        )
        assert m.verdict_probability != -1.0  # calibrated engine activated from config alone


class TestEndToEndSimulation:
    """E5 (CI-level gate): the whole loop hits the target metrics on the shipped
    multilingual fixture. The real-data gate (the user's en/nb/fr corpus) is a
    separate, manual run - this proves the machinery reaches the targets when
    the signal is there.
    """

    def test_targets_met_on_fixture(self):
        df = _fixture_df()
        train = df[df.index % 2 == 0].reset_index(drop=True)
        test = df[df.index % 2 == 1].reset_index(drop=True)
        cal = C.fit_calibrator(train, draws=300, tune=300, random_seed=0)
        m = C.evaluate(cal, test)
        # AC targets: >=0.90 CONFIRMED precision, >=0.80 recall.
        assert m["precision"] >= 0.90, m
        assert m["recall"] >= 0.80, m
        # per-language parity present and each language non-degenerate.
        for lang in ("en", "nb", "fr"):
            assert m["by_lang"][lang]["n"] > 0
        # calibrated must not be worse than the untrained prior.
        assert m["accuracy"] >= C.evaluate(_prior_verdict(), test)["accuracy"]


class TestImbalanceBalancing:
    """Class-balancing for imbalanced label sets (minority oversampling)."""

    @staticmethod
    def _skewed() -> pd.DataFrame:
        # 8 grounded vs 2 not - a 4:1 imbalance, predictors vary within class.
        rows = []
        for _ in range(8):
            rows.append(
                {
                    "exact": 1.0,
                    "fuzzy": 0.9,
                    "bm25_recall": 0.8,
                    "semantic": 0.6,
                    "voters": 0.75,
                    "lexical_cosupport": 1.0,
                    "entity_absent": 0.0,
                    "nli_entail": 0.9,
                    "nli_contra": 0.02,
                    "grounded": 1.0,
                }
            )
        for _ in range(2):
            rows.append(
                {
                    "exact": 0.0,
                    "fuzzy": 0.1,
                    "bm25_recall": 0.05,
                    "semantic": 0.1,
                    "voters": 0.0,
                    "lexical_cosupport": 0.0,
                    "entity_absent": 1.0,
                    "nli_entail": 0.02,
                    "nli_contra": 0.9,
                    "grounded": 0.0,
                }
            )
        return pd.DataFrame(rows)

    def test_balance_equalises_counts(self):
        out = C._balance_classes(self._skewed(), seed=0)
        pos = int((out["grounded"] >= 0.5).sum())
        neg = int((out["grounded"] < 0.5).sum())
        assert pos == neg == 8
        assert len(out) == 16  # 10 originals + 6 duplicated minority rows

    def test_balance_is_deterministic(self):
        df = self._skewed()
        assert C._balance_classes(df, seed=7).equals(C._balance_classes(df, seed=7))

    def test_balance_noop_when_balanced_or_single_class(self):
        bal = C._balance_classes(self._skewed(), seed=0)
        assert C._balance_classes(bal, seed=0).equals(bal)  # already balanced
        pos_only = self._skewed().query("grounded >= 0.5")
        assert len(C._balance_classes(pos_only, seed=0)) == len(pos_only)  # single class

    def test_fit_balanced_runs_and_predicts(self):
        cal = C.fit_calibrator(
            self._skewed(),
            draws=DRAWS,
            tune=TUNE,
            random_seed=0,
            include_anchor=True,
            balance="balanced",
        )
        archetype = pd.DataFrame(
            [
                {
                    "exact": 1.0,
                    "fuzzy": 0.9,
                    "bm25_recall": 0.8,
                    "semantic": 0.6,
                    "voters": 0.75,
                    "lexical_cosupport": 1.0,
                    "entity_absent": 0.0,
                    "nli_entail": 0.9,
                    "nli_contra": 0.02,
                }
            ]
        ).reindex(columns=C.PREDICTORS, fill_value=0.0)
        assert cal.predict_proba(archetype)[0] >= 0.5

    def test_fit_rejects_unknown_balance(self):
        with pytest.raises(ValueError):
            C.fit_calibrator(self._skewed(), draws=DRAWS, tune=TUNE, balance="bogus")


class TestVitaminCComposite:
    """One composite end-to-end pin: the calibrated verdict + NLI grounding over
    a FIXED slice of the public grounding dataset (VitaminC dev) must reproduce
    the benchmark confusion matrix exactly.

    This is the high-value regression that ties calibration and grounding to a
    real dataset - it earns its place where the thin per-piece tests did not.
    Network/model-gated: downloads VitaminC dev.jsonl + the mDeBERTa NLI model
    on first use, skips cleanly when unavailable. Deterministic: fixed slice,
    ONNX fp32 CPU argmax, prior-mean calibrated verdict.
    """

    def test_calibrated_nli_grounding_reproduces_benchmark(self):
        import collections

        pytest.importorskip("onnxruntime")
        pytest.importorskip("transformers")
        hf = pytest.importorskip("huggingface_hub")
        from stellars_claude_code_plugins.document_processing import nli as nli_mod

        if not nli_mod.is_available():
            pytest.skip("NLI extras not installed")
        try:
            path = hf.hf_hub_download("tals/vitaminc", "dev.jsonl", repo_type="dataset")
            nli = nli_mod.NLIGrounder()
        except Exception as exc:  # noqa: BLE001 - skip on no network / missing weights
            pytest.skip(f"VitaminC / NLI model unavailable: {exc}")

        gold = {"SUPPORTS": "grounded", "REFUTES": "contradicted", "NOT ENOUGH INFO": "unconfirmed"}
        rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
        by_label: dict[str, list] = {k: [] for k in gold}
        for r in rows:
            if r.get("label") in by_label and r.get("claim") and r.get("evidence"):
                by_label[r["label"]].append(r)
        per = 15
        sample = (
            by_label["SUPPORTS"][:per]
            + by_label["REFUTES"][:per]
            + by_label["NOT ENOUGH INFO"][:per]
        )
        assert len(sample) == 3 * per  # fixed, deterministic slice

        # "Calibration": the deployed prior-mean calibrated verdict (config prior).
        spec = C.load_prior_spec()
        verdict = C.CalibratedVerdict.from_weights(
            {k: mu for k, (mu, _sd) in spec.items()}, threshold=0.5
        )

        def bucket(match_type: str) -> str:
            if match_type == "contradicted":
                return "contradicted"
            return "grounded" if match_type in ("exact", "fuzzy", "bm25", "semantic") else "unconfirmed"

        conf: collections.Counter = collections.Counter()
        for r in sample:
            m = G.ground(
                r["claim"],
                [(str(r.get("page", "src")), r["evidence"])],
                nli_grounder=nli,
                calibrated_verdict=verdict,
            )
            conf[(gold[r["label"]], bucket(m.match_type))] += 1

        # Golden confusion matrix for this exact (slice, models, prior) - the
        # "same numbers as the result". Re-pin if the slice or models change.
        expected = {
            ("grounded", "grounded"): 8,
            ("grounded", "contradicted"): 3,
            ("grounded", "unconfirmed"): 4,
            ("contradicted", "grounded"): 1,
            ("contradicted", "contradicted"): 13,
            ("contradicted", "unconfirmed"): 1,
            ("unconfirmed", "grounded"): 3,
            ("unconfirmed", "contradicted"): 8,
            ("unconfirmed", "unconfirmed"): 4,
        }
        assert {k: conf[k] for k in expected} == expected
        # contradiction recall - the headline NLI win this test guards.
        assert conf[("contradicted", "contradicted")] / per >= 0.80
