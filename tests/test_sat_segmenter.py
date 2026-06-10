"""Tests for the vendored SaT sentence segmenter (native OpenVINO INT8 backend).

Two layers, following the repo's importorskip + try/except-network skip pattern:

- resolve_ir(): the SAT_OV_IR env override short-circuits the HF download path
  entirely (offline, always runs)
- SaTSegmenter.split(): real INT8 inference on ASCII input - importorskip
  openvino, skip cleanly when the IR / tokenizer / config downloads fail
  (no network)
"""

from __future__ import annotations

import pytest

from stellars_claude_code_plugins.document_processing.sat import ov_backend


class TestResolveIR:
    def test_env_override_short_circuits_hf_download(self, monkeypatch):
        # a set SAT_OV_IR wins unconditionally - no huggingface_hub import/call
        monkeypatch.setenv(ov_backend.OV_IR_ENV, "/some/local/openvino_model.xml")

        def _boom(*a, **k):  # any HF touch is a test failure
            raise AssertionError("hf_hub_download must not be called with SAT_OV_IR set")

        import huggingface_hub

        monkeypatch.setattr(huggingface_hub, "hf_hub_download", _boom)
        assert ov_backend.resolve_ir() == "/some/local/openvino_model.xml"

    def test_download_failure_raises_actionable_runtime_error(self, monkeypatch):
        monkeypatch.delenv(ov_backend.OV_IR_ENV, raising=False)

        import huggingface_hub

        def _fail(*a, **k):
            raise OSError("simulated: no network")

        monkeypatch.setattr(huggingface_hub, "hf_hub_download", _fail)
        with pytest.raises(RuntimeError) as exc:
            ov_backend.resolve_ir()
        # the message must point at the SAT_OV_IR bypass
        assert ov_backend.OV_IR_ENV in str(exc.value)


class TestSaTSplit:
    def test_split_returns_sentences_on_ascii(self):
        pytest.importorskip("openvino")
        from stellars_claude_code_plugins.document_processing.sat import SaTSegmenter

        try:
            seg = SaTSegmenter()  # IR + config + tokenizer auto-download (cached)
        except Exception as exc:  # noqa: BLE001 - skip on no network / hub failure
            pytest.skip(f"SaT model unavailable: {exc}")

        out = seg.split("The manor was built in 1820. It was restored in 1998.")
        assert isinstance(out, list) and len(out) >= 2
        assert "".join(out).replace(" ", "") == (
            "The manor was built in 1820. It was restored in 1998.".replace(" ", "")
        )

    def test_split_empty_and_whitespace(self):
        pytest.importorskip("openvino")
        from stellars_claude_code_plugins.document_processing.sat import SaTSegmenter

        try:
            seg = SaTSegmenter()
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"SaT model unavailable: {exc}")
        assert seg.split("") == []
        assert seg.split("   ") == ["   "]
