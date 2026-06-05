"""Machine-translation bridge: CTranslate2 + wtpsplit SaT (ONNX) sentence splitting.

Translation runs on CTranslate2 (int8 CPU); sentence segmentation on wtpsplit-lite's
SaT ONNX model via onnxruntime. Reuses the CTranslate2 + tokenizer models argos
already downloaded under ~/.local/share/argos-translate/packages/. Handles both argos
tokenizer formats - SentencePiece (`sentencepiece.model`) and subword-nmt BPE
(`bpe.model`). This path imports no torch (it replaces argos's stanza segmenter, the
stack's last torch dependency).
"""

from __future__ import annotations

import json
from pathlib import Path

_ARGOS = Path.home() / ".local/share/argos-translate/packages"
_ISO = {"no": "nb", "nn": "nb"}  # langdetect -> argos model code
_MODELS: dict = {}
_SAT = None


def _sat():
    global _SAT
    if _SAT is None:
        from wtpsplit_lite import SaT

        _SAT = SaT("sat-3l-sm")  # ONNX SaT, runs on onnxruntime
    return _SAT


def _find_pkg(src: str) -> Path | None:
    if not _ARGOS.exists():
        return None
    for d in _ARGOS.iterdir():
        meta = d / "metadata.json"
        if meta.exists():
            m = json.loads(meta.read_text())
            if m.get("from_code") == src and m.get("to_code") == "en":
                return d
    return None


def _load(src: str):
    """Load CTranslate2 translator + the package's tokenizer (SentencePiece or BPE)."""
    if src in _MODELS:
        return _MODELS[src]
    import ctranslate2

    d = _find_pkg(src)
    if d is None:
        _MODELS[src] = None
        return None
    tr = ctranslate2.Translator(str(d / "model"), device="cpu", compute_type="int8")
    if (d / "sentencepiece.model").exists():
        import sentencepiece as spm

        sp = spm.SentencePieceProcessor()
        sp.load(str(d / "sentencepiece.model"))
        _MODELS[src] = {"tr": tr, "kind": "spm", "sp": sp}
    elif (d / "bpe.model").exists():
        from sacremoses import MosesDetokenizer, MosesTokenizer
        from subword_nmt.apply_bpe import BPE

        bpe = BPE(open(d / "bpe.model", encoding="utf-8"))
        _MODELS[src] = {"tr": tr, "kind": "bpe", "bpe": bpe,
                        "mtok": MosesTokenizer(lang=src), "detok": MosesDetokenizer(lang="en")}
    else:
        _MODELS[src] = None
    return _MODELS[src]


def translate(text: str, src_iso: str) -> str:
    """Translate text into English. Pass-through for English/unknown/unsupported source."""
    code = _ISO.get(src_iso, src_iso)
    if code in ("en", "und", ""):
        return text
    m = _load(code)
    if m is None:
        return text
    tr = m["tr"]
    out = []
    for s in _sat().split(text) or [text]:
        s = s.strip()
        if not s:
            continue
        if m["kind"] == "spm":
            tokens = m["sp"].encode(s, out_type=str)
            res = tr.translate_batch([tokens], beam_size=2, max_decoding_length=256)
            out.append("".join(res[0].hypotheses[0]).replace("▁", " ").strip())
        else:  # subword-nmt BPE: moses-tokenise -> apply BPE -> translate -> detokenise
            toks = m["bpe"].process_line(m["mtok"].tokenize(s, return_str=True)).split()
            res = tr.translate_batch([toks], beam_size=2, max_decoding_length=256)
            merged = " ".join(res[0].hypotheses[0]).replace("@@ ", "").replace("@@", "")
            out.append(m["detok"].detokenize(merged.split()).strip())
    return " ".join(o for o in out if o).strip() or text
