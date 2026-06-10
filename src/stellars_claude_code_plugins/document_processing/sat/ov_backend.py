"""Native OpenVINO INT8 backend for the SaT segmenter.

Replaces wtpsplit-lite's onnxruntime ``SaTORTWrapper``: loads the INT8 OpenVINO IR
and exposes the same ``config`` + ``__call__(input_ids, attention_mask) -> {"logits"}``
interface that ``extract()`` expects. Compiled with the LATENCY performance hint -
the grounder segments one short claim at a time, so single-inference latency is the
target (not throughput). No onnxruntime."""

import os
from pathlib import Path

import numpy as np

# IR source: a local override (set SAT_OV_IR to a local .xml) wins; otherwise the
# INT8 IR is downloaded from the HF repo below and cached like the MT models.
OV_IR_ENV = "SAT_OV_IR"
OV_HF_REPO = "stellars/sat-3l-sm-openvino-int8"  # native OpenVINO INT8 SaT
OV_IR_XML = "openvino_model.xml"
OV_IR_BIN = "openvino_model.bin"

_CORE = None
_COMPILED: dict = {}


def resolve_ir() -> str:
    """Path to the INT8 IR ``.xml`` (local override or HF download; .bin fetched alongside)."""
    local = os.environ.get(OV_IR_ENV)
    if local:
        return str(local)
    from huggingface_hub import hf_hub_download

    try:
        hf_hub_download(OV_HF_REPO, OV_IR_BIN)  # cache the weights next to the graph
        return hf_hub_download(OV_HF_REPO, OV_IR_XML)
    except Exception as exc:
        raise RuntimeError(
            f"could not download SaT OpenVINO IR from Hugging Face ({OV_HF_REPO}): {exc}; "
            f"set {OV_IR_ENV}=path/to/{OV_IR_XML} to bypass the HF download"
        ) from exc


def _compiled(ir_xml: str):
    global _CORE
    import openvino as ov

    if _CORE is None:
        _CORE = ov.Core()
    key = str(Path(ir_xml).resolve())
    if key not in _COMPILED:
        _COMPILED[key] = _CORE.compile_model(
            _CORE.read_model(ir_xml), "CPU", {"PERFORMANCE_HINT": "LATENCY"}
        )
    return _COMPILED[key]


class OVSegModel:
    """SaT forward on OpenVINO. Mirrors wtpsplit's SaTORTWrapper interface."""

    def __init__(self, config, ir_xml: str):
        self.config = config
        self._cm = _compiled(ir_xml)

    def __call__(self, input_ids, attention_mask):
        res = self._cm(
            {
                "input_ids": input_ids.astype(np.int64),
                "attention_mask": attention_mask.astype(np.float32),
            }
        )
        return {"logits": list(res.values())[0]}
