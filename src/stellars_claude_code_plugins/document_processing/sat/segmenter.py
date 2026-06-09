"""SaT sentence segmenter on native OpenVINO INT8.

The split path (tokenise -> sliding-window extract -> token->char probs -> threshold ->
sentence reconstruction) is vendored from wtpsplit-lite (MIT, Superlinear; see LICENSE),
reduced to the single-text use the MT bridge needs and pointed at the OpenVINO INT8 backend
instead of onnxruntime. Defaults reproduce wtpsplit's ``SaT("sat-3l-sm").split(text)``:
threshold 0.25, stride 64, block size 512.
"""

import numpy as np

from stellars_claude_code_plugins.document_processing.sat._config import SubwordXLMConfig
from stellars_claude_code_plugins.document_processing.sat._tokenizer import XLMRobertaTokenizerFast
from stellars_claude_code_plugins.document_processing.sat._utils import (
    Constants,
    sigmoid,
    token_to_char_probs,
)
from stellars_claude_code_plugins.document_processing.sat.extract import extract
from stellars_claude_code_plugins.document_processing.sat.ov_backend import OVSegModel, resolve_ir

CONFIG_REPO = "segment-any-text/sat-3l-sm"        # config.json (SubwordXLMConfig)
TOKENIZER_REPO = "facebookAI/xlm-roberta-base"    # tokenizer.json
DEFAULT_THRESHOLD = 0.25                           # sat-3l-sm default sentence threshold
STRIDE = 64
BLOCK_SIZE = 512


class SaTSegmenter:
    """Sentence-splits text with the INT8 OpenVINO SaT. ``split`` mirrors wtpsplit's API."""

    def __init__(self, ir_xml: str | None = None):
        self.config = SubwordXLMConfig.from_pretrained(CONFIG_REPO)
        self.tokenizer = XLMRobertaTokenizerFast.from_pretrained(TOKENIZER_REPO)
        self.model = OVSegModel(self.config, ir_xml or resolve_ir())

    def newline_probs(self, text: str) -> np.ndarray:
        """Per-character P(sentence boundary) over ``text``."""
        logits, _offsets, tok, tok_out = extract(
            [text], self.model, stride=STRIDE, max_block_size=BLOCK_SIZE, batch_size=32,
            tokenizer=self.tokenizer,
        )
        char_logits = token_to_char_probs(
            text, tok_out["input_ids"][0], logits[0], tok, tok_out["offset_mapping"][0]
        )
        return sigmoid(char_logits[:, Constants.NEWLINE_INDEX])

    def split(self, text: str, threshold: float | None = None) -> list[str]:
        """Sentences in ``text`` (boundary where P > threshold). Empty/short text -> single chunk."""
        from stellars_claude_code_plugins.document_processing.sat._utils import (
            indices_to_sentences,
        )

        if not text or not text.strip():
            return [text] if text else []
        thr = DEFAULT_THRESHOLD if threshold is None else threshold
        probs = self.newline_probs(text)
        return indices_to_sentences(text, np.where(probs > thr)[0])
