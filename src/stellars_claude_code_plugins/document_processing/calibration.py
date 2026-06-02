"""Bayesian calibrated grounding verdict (bambi / PyMC).

Fit **and** predict go through bambi / PyMC - the Bayesian library does the
work end to end:

- **Fit**: Bayesian logistic regression over the per-layer grounding
  features, with informative priors (or the previous posterior, for
  incremental updates).
- **Predict**: bambi's posterior-predictive mean gives a calibrated
  ``P(grounded)`` per claim, and its spread across posterior draws is the
  predictive uncertainty.
- **Incremental**: a new fit seeds its priors from the previous posterior
  summary (posterior-as-prior), so feedback accumulates instead of resetting.

No Bayesian math is hand-written here - bambi/PyMC/arviz own it. The
predictor order is the contract with :mod:`grounding`, which extracts these
features from a :class:`grounding.GroundingMatch`.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

PREDICTORS: list[str] = [
    "exact",
    "fuzzy",
    "bm25_recall",
    "semantic",  # ramped semantic_ratio - model/language-portable meaning signal
    "voters",  # n_voters / 4, in [0, 1]
    "lexical_cosupport",  # 0/1
    "entity_absent",  # fraction of claim entities absent from the source
]
RESPONSE = "grounded"
_MEAN_VAR = "p"  # bambi's name for the bernoulli mean-probability parameter

# Model coefficients = intercept + the predictors. Used for posterior
# summaries / serialisation / point-weight reconstruction.
COEFFICIENTS: list[str] = ["Intercept", *PREDICTORS]

# NOTE: the Bayesian PRIOR is NOT hardcoded here. It lives in the bundled
# config (`config_document_processing.yaml` -> `calibration.prior`) and is read
# via :func:`load_prior_spec` - yaml is the single source of truth. See that
# function and the config block for the per-coefficient Normal(mu, sigma).


def load_prior_spec(path: str | Path | None = None) -> dict[str, tuple[float, float]]:
    """Read the per-coefficient Normal prior (mu, sigma) from config.

    Resolution: the active ``calibration.prior`` block (project/user override
    or bundled, via the normal 4-layer order); if an override omits it, fall
    back to the bundled config (still yaml, never a Python hardcode). Raises if
    no config carries it.
    """
    import yaml

    from stellars_claude_code_plugins.config import PACKAGE_ROOT

    block = load_calibration_from_config(path)
    prior = (block or {}).get("prior")
    if not prior:
        bundled = PACKAGE_ROOT / "config_document_processing.yaml"
        raw = yaml.safe_load(bundled.read_text(encoding="utf-8")) or {}
        prior = (raw.get("calibration") or {}).get("prior")
    if not prior:
        raise RuntimeError(
            "calibration.prior missing from config_document_processing.yaml - "
            "the calibrator prior is config-driven, not hardcoded"
        )
    return {name: (float(v["mu"]), float(v["sigma"])) for name, v in prior.items()}


def _formula() -> str:
    return f"{RESPONSE} ~ " + " + ".join(PREDICTORS)


def _build_priors(spec: dict[str, tuple[float, float]]):
    import bambi as bmb

    return {k: bmb.Prior("Normal", mu=mu, sigma=sigma) for k, (mu, sigma) in spec.items()}


def _as_df(feat):
    """Coerce a dict / list-of-dicts / DataFrame to a predictor-only DataFrame."""
    import pandas as pd

    if hasattr(feat, "columns"):  # already a DataFrame
        return feat
    rows = [feat] if isinstance(feat, dict) else list(feat)
    return pd.DataFrame([{k: float(r.get(k, 0.0)) for k in PREDICTORS} for r in rows])


def _schema_df():
    """Minimal reference frame (both classes) to rebuild the bambi model on load."""
    import pandas as pd

    data = {k: [0.0, 1.0] for k in PREDICTORS}
    data[RESPONSE] = [0, 1]
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Calibrated verdict (wraps the fitted bambi model + posterior)
# ---------------------------------------------------------------------------


@dataclass
class CalibratedVerdict:
    """A fitted Bayesian calibrator. Prediction is delegated to bambi."""

    model: object  # bambi.Model
    idata: object  # arviz.InferenceData (posterior)
    threshold: float = 0.5

    def _posterior_mean_da(self, df):
        """Posterior of the mean probability for each row (dims: chain, draw, obs)."""
        try:
            pred = self.model.predict(self.idata, data=df, inplace=False, kind="response_params")
        except (TypeError, ValueError):
            # Older bambi: the mean kind was called "mean".
            pred = self.model.predict(self.idata, data=df, inplace=False, kind="mean")
        post = pred.posterior
        if _MEAN_VAR in post.data_vars:
            return post[_MEAN_VAR]
        # Fallback: the one var present after predict that wasn't in the fit.
        for v in post.data_vars:
            if v not in self.idata.posterior.data_vars:
                return post[v]
        raise KeyError("calibration: could not locate the mean-probability variable")

    def predict_proba(self, feat):
        """Calibrated P(grounded) per row. Returns an ndarray."""
        da = self._posterior_mean_da(_as_df(feat))
        return da.mean(dim=("chain", "draw")).values

    def predict_with_uncertainty(self, feat):
        """Return (p_mean, p_std) arrays - the posterior-predictive spread is
        the calibration uncertainty (wide => borderline, flag for review)."""
        da = self._posterior_mean_da(_as_df(feat))
        return da.mean(dim=("chain", "draw")).values, da.std(dim=("chain", "draw")).values

    def confirmed(self, feat) -> bool:
        """Single-row convenience: P(grounded) >= threshold."""
        return bool(self.predict_proba(feat)[0] >= self.threshold)

    def posterior_summary(self) -> dict[str, tuple[float, float]]:
        """Per-coefficient (mean, sd) via arviz - used to seed the next prior."""
        import arviz as az

        s = az.summary(self.idata, var_names=COEFFICIENTS, kind="stats")
        return {
            n: (float(s.loc[n, "mean"]), float(s.loc[n, "sd"]))
            for n in COEFFICIENTS
            if n in s.index
        }

    # -- persistence --------------------------------------------------------

    def save(self, path: str | Path) -> None:
        """Persist the posterior coefficient samples + threshold to one JSON.

        Stored as samples (not a netCDF) so reload needs no HDF5 backend - the
        posterior is small (chains x draws x a handful of coefficients).
        """
        import numpy as np

        p = Path(path)
        if p.suffix != ".json":
            p.mkdir(parents=True, exist_ok=True)
            p = p / "calibrator.json"
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
        post = self.idata.posterior
        samples = {
            n: np.asarray(post[n].values).tolist() for n in COEFFICIENTS if n in post.data_vars
        }
        payload = {
            "threshold": float(self.threshold),
            "predictors": PREDICTORS,
            "response": RESPONSE,
            "posterior_samples": samples,  # each shaped (chain, draw)
            "posterior_summary": self.posterior_summary(),
        }
        p.write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> CalibratedVerdict:
        import arviz as az
        import bambi as bmb
        import numpy as np

        p = Path(path)
        if p.is_dir():
            p = p / "calibrator.json"
        payload = json.loads(p.read_text(encoding="utf-8"))
        posterior = {k: np.asarray(v) for k, v in payload["posterior_samples"].items()}
        idata = az.from_dict({"posterior": posterior})
        # Rebuild the (cheap) model graph; predict() rebuilds the design matrix
        # from new data, so a schema-only reference frame is enough.
        model = bmb.Model(_formula(), _schema_df(), family="bernoulli")
        return cls(model=model, idata=idata, threshold=float(payload.get("threshold", 0.5)))

    @classmethod
    def from_weights(cls, weights: dict, threshold: float = 0.5) -> CalibratedVerdict:
        """Build a verdict from point weights (e.g. config-provided learned means).

        Reconstructs a degenerate single-draw posterior so prediction still
        runs through bambi - no hand-rolled scoring. Predictive uncertainty is
        zero (point estimate); load a full profile when you need intervals.
        Coefficient names are ``Intercept`` plus :data:`PREDICTORS`; any missing
        weight defaults to 0.
        """
        import arviz as az
        import bambi as bmb
        import numpy as np

        posterior = {n: np.array([[float(weights.get(n, 0.0))]]) for n in COEFFICIENTS}
        idata = az.from_dict({"posterior": posterior})
        model = bmb.Model(_formula(), _schema_df(), family="bernoulli")
        return cls(model=model, idata=idata, threshold=float(threshold))


# ---------------------------------------------------------------------------
# Fitting
# ---------------------------------------------------------------------------


def default_prior_spec() -> dict[str, tuple[float, float]]:
    """The config-defined prior (mu, sigma) per coefficient."""
    return load_prior_spec()


def fit_calibrator(
    df,
    *,
    prior_spec: dict[str, tuple[float, float]] | None = None,
    threshold: float = 0.5,
    include_anchor: bool = False,
    draws: int = 1000,
    tune: int = 1000,
    chains: int = 2,
    cores: int = 1,
    random_seed: int = 0,
) -> CalibratedVerdict:
    """Fit the Bayesian calibrator with bambi / PyMC.

    ``df`` carries the :data:`PREDICTORS` columns plus ``grounded`` (0/1 hard
    labels, or a probability in [0, 1] for LLM-soft labels). ``prior_spec``
    seeds the coefficient priors; omit it to use the interpretable default.

    ``include_anchor`` appends the small anchor set (prior pseudo-observations)
    to the evidence. Use it for small/degenerate batches: it guarantees every
    predictor varies (bambi rejects a constant predictor) and keeps
    untrained-region behaviour sane. With large real evidence its influence is
    proportionally small.
    """
    import bambi as bmb
    import pandas as pd

    spec = prior_spec or load_prior_spec()
    cols = PREDICTORS + [RESPONSE]
    train = df[cols] if set(cols).issubset(df.columns) else df
    if include_anchor:
        train = pd.concat([train[cols], _anchor_frame()[cols]], ignore_index=True)
    model = bmb.Model(_formula(), train, family="bernoulli", priors=_build_priors(spec))
    idata = model.fit(
        draws=draws,
        tune=tune,
        chains=chains,
        cores=cores,
        random_seed=random_seed,
        progressbar=False,
    )
    return CalibratedVerdict(model=model, idata=idata, threshold=threshold)


def update_calibrator(prior_verdict: CalibratedVerdict, df, **fit_kwargs) -> CalibratedVerdict:
    """Incremental Bayesian update: seed priors from the previous posterior."""
    base = load_prior_spec()
    prev = prior_verdict.posterior_summary()
    spec = {k: prev.get(k, base[k]) for k in base}
    fit_kwargs.setdefault("threshold", prior_verdict.threshold)
    return fit_calibrator(df, prior_spec=spec, **fit_kwargs)


def _anchor_frame():
    """Small synthetic anchor set encoding the prior's intended behaviour.

    Used to materialise a usable default calibrator (it needs a posterior to
    predict from). Each row is a stylised case: exact / lexical hits and
    strong cross-lingual semantic matches are grounded; weak topical signals
    and entity-absent fabrications are not.
    """
    import pandas as pd

    def row(grounded, exact=0, fuzzy=0.0, bm25=0.0, sem=0.0, voters=0.0, cosup=0, eabs=0.0):
        return {
            "exact": float(exact),
            "fuzzy": fuzzy,
            "bm25_recall": bm25,
            "semantic": sem,
            "voters": voters,
            "lexical_cosupport": float(cosup),
            "entity_absent": eabs,
            "grounded": grounded,
        }

    rows = []
    # exact / strong lexical hits -> grounded
    for _ in range(4):
        rows.append(row(1, exact=1, fuzzy=0.95, bm25=0.8, sem=0.6, voters=0.75, cosup=1))
        rows.append(row(1, fuzzy=0.9, bm25=0.7, sem=0.5, voters=0.5, cosup=1))
    # strong cross-lingual semantic, no lexical -> grounded
    for _ in range(4):
        rows.append(row(1, sem=0.85, voters=0.25))
        rows.append(row(1, sem=0.78, voters=0.25))
    # weak topical / fabrication (low ramped semantic), no lexical -> not grounded
    for _ in range(4):
        rows.append(row(0, sem=0.18, voters=0.25))
        rows.append(row(0, sem=0.05))
    # entity-absent fabrication -> not grounded
    for _ in range(4):
        rows.append(row(0, sem=0.3, voters=0.25, eabs=1.0))
    return pd.DataFrame(rows)


def default_calibrator(threshold: float = 0.5, **fit_kwargs) -> CalibratedVerdict:
    """A usable, untrained-from-real-data calibrator: the interpretable prior
    fit against a small synthetic anchor set so it has a posterior to predict
    from. This is the shipped default until real feedback calibrates it."""
    return fit_calibrator(_anchor_frame(), threshold=threshold, **fit_kwargs)


# ---------------------------------------------------------------------------
# Evaluation (plain metric counting)
# ---------------------------------------------------------------------------


def evaluate(verdict: CalibratedVerdict, df, *, group_col: str | None = "lang") -> dict:
    """Precision / recall / F1 of the calibrated verdict against labels.

    A per-group breakdown (e.g. per language) is included when ``group_col``
    is a column, for parity checks.
    """
    proba = verdict.predict_proba(df[PREDICTORS])
    y_pred = [1 if p >= verdict.threshold else 0 for p in proba]
    y_true = [1 if float(g) >= 0.5 else 0 for g in df[RESPONSE].tolist()]
    metrics = _prf(y_true, y_pred)
    if group_col and group_col in df.columns:
        groups: dict[str, dict] = {}
        for g, yt, yp in zip(df[group_col].tolist(), y_true, y_pred):
            groups.setdefault(str(g), {"t": [], "p": []})
            groups[str(g)]["t"].append(yt)
            groups[str(g)]["p"].append(yp)
        metrics["by_" + group_col] = {g: _prf(v["t"], v["p"]) for g, v in groups.items()}
    return metrics


def load_calibration_from_config(path: str | Path | None = None) -> dict | None:
    """Read the optional ``calibration:`` block from the document-processing config.

    Returns ``{"engine": ..., "threshold": float, "weights": {coef: float}}``
    or ``None`` when no block is present. Uses the same 4-layer config
    resolution as :func:`config.load_document_processing_config`, so a
    project-local override wins over the bundled default.
    """
    import yaml

    from stellars_claude_code_plugins.config import _resolve_config_path

    p = _resolve_config_path("document_processing", path)
    if not Path(p).is_file():
        return None
    raw = yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
    block = raw.get("calibration")
    return block if isinstance(block, dict) else None


def verdict_from_config(path: str | Path | None = None) -> CalibratedVerdict | None:
    """Build a :class:`CalibratedVerdict` from config-provided learned weights.

    Returns ``None`` when the config has no ``calibration.weights`` block - the
    caller then falls back to the deterministic classifier (or
    :func:`default_calibrator`). This is the "locally domain-calibrated, weights
    live in the config" path: calibrate once, transfer the learned weights into
    the config, and every run uses them with no fitting.
    """
    block = load_calibration_from_config(path)
    if not block or block.get("engine") != "calibrated" or not block.get("weights"):
        return None
    return CalibratedVerdict.from_weights(
        block["weights"], threshold=float(block.get("threshold", 0.5))
    )


def _prf(y_true: list[int], y_pred: list[int]) -> dict:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    acc = (tp + tn) / len(y_true) if y_true else 0.0
    return {
        "n": len(y_true),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(acc, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }
