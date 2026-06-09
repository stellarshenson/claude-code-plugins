"""Native OpenVINO INT8 SaT sentence segmenter (replaces the onnxruntime wtpsplit-lite path).

Vendored from wtpsplit-lite (MIT, Superlinear; see LICENSE) with the inference backend swapped
to OpenVINO. ``SaTSegmenter().split(text)`` reproduces ``wtpsplit_lite.SaT("sat-3l-sm").split``.
"""

from stellars_claude_code_plugins.document_processing.sat.segmenter import SaTSegmenter

__all__ = ["SaTSegmenter"]
