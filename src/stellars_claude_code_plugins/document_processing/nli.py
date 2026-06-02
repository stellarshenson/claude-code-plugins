"""NLI / entailment grounding via a multilingual cross-encoder (ONNX Runtime).

Proper grounding is **entailment**: does the evidence support the claim? A
cross-encoder NLI model scores (premise = evidence, hypothesis = claim) into
{entailment, neutral, contradiction}, mapping directly onto our verdict
{grounded, unconfirmed, contradicted}. The default model is multilingual
(mDeBERTa MNLI+XNLI), so cross-lingual claims work - the case lexical matching
and embedding similarity both failed.

Torch-free: runs through ONNX Runtime (a core dep) with the transformers
tokenizer; no PyTorch. The model ships ``onnx/model.onnx`` on the Hub and is
downloaded + cached on first use. ``is_available`` gates on the optional deps;
the model is heavy (~560 MB), so this is an opt-in layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

DEFAULT_MODEL = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"


def is_available() -> bool:
    """True iff onnxruntime + transformers + huggingface_hub are importable."""
    for mod in ("onnxruntime", "transformers", "huggingface_hub"):
        try:
            __import__(mod)
        except ImportError:
            return False
    return True


def install_hint() -> str:
    return (
        "NLI grounding requires: onnxruntime, transformers, huggingface_hub "
        "(all in the core install). The model "
        f"({DEFAULT_MODEL}) downloads on first use (~560 MB)."
    )


@dataclass
class NLIGrounder:
    """Cross-encoder NLI verdict over (evidence, claim). Lazy-loads the model.

    ``scores`` returns the softmax over {entailment, neutral, contradiction};
    ``verdict`` collapses it to grounded / contradicted / unconfirmed.
    """

    model_name: str = DEFAULT_MODEL
    max_length: int = 256
    _session: object = field(default=None, repr=False)
    _tokenizer: object = field(default=None, repr=False)
    _input_names: set = field(default_factory=set, repr=False)
    _id2label: dict = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not is_available():
            raise ImportError(install_hint())
        from huggingface_hub import hf_hub_download
        import onnxruntime as ort
        from transformers import AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        onnx_path = hf_hub_download(self.model_name, "onnx/model.onnx")
        self._session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        self._input_names = {i.name for i in self._session.get_inputs()}
        cfg = json.loads(Path(hf_hub_download(self.model_name, "config.json")).read_text("utf-8"))
        self._id2label = {int(k): v.lower() for k, v in cfg["id2label"].items()}

    def scores(self, premise: str, hypothesis: str) -> dict[str, float]:
        """Softmax probabilities over {entailment, neutral, contradiction}."""
        import numpy as np

        enc = self._tokenizer(
            premise,
            hypothesis,
            truncation=True,
            max_length=self.max_length,
            return_tensors="np",
        )
        feed = {n: enc[n] for n in self._input_names if n in enc}
        logits = self._session.run(None, feed)[0][0]
        ex = np.exp(logits - logits.max())
        p = ex / ex.sum()
        return {self._id2label[i]: float(p[i]) for i in range(len(p))}

    def verdict(self, evidence: str, claim: str) -> str:
        """grounded (entailment) / contradicted / unconfirmed (neutral)."""
        s = self.scores(evidence, claim)
        top = max(s, key=s.get)
        return {
            "entailment": "grounded",
            "contradiction": "contradicted",
            "neutral": "unconfirmed",
        }.get(top, "unconfirmed")
