"""SaT sliding-window logit extraction. Vendored from wtpsplit-lite (MIT, Superlinear); see
LICENSE. The onnxruntime backend (`SaTORTWrapper`) and the tqdm progress bar are removed - the
model is any callable exposing ``config`` and ``__call__(input_ids, attention_mask) -> {"logits"}``
(see ``ov_backend.OVSegModel``)."""
# ruff: noqa: C901, PLR0913, PLR0912, PLR0915, PLR2004, B905

import math
import sys
from typing import Literal

import numpy as np

from stellars_claude_code_plugins.document_processing.sat._tokenizer import XLMRobertaTokenizerFast
from stellars_claude_code_plugins.document_processing.sat._utils import hash_encode


def extract(
    batch_of_texts: list[str],
    model,
    stride: int,
    max_block_size: int,
    batch_size: int,
    lang_code: str | None = None,
    pad_last_batch: bool = False,
    weighting: Literal["uniform", "hat"] = "uniform",
    verbose: bool = False,
    tokenizer: XLMRobertaTokenizerFast | None = None,
):
    """Compute per-character logits by slicing the text into overlapping blocks, running each
    through the model forward, and averaging overlapping predictions back together."""
    if "xlm" in model.config.model_type:
        use_subwords = True
        if tokenizer is None:
            tokenizer = XLMRobertaTokenizerFast.from_pretrained("facebookAI/xlm-roberta-base")
        tokens = tokenizer(
            batch_of_texts, return_offsets_mapping=True, verbose=False, add_special_tokens=False
        )
        batch_of_texts = tokens["input_ids"]
        offset_mapping = tokens["offset_mapping"]
        cls_token_id = tokenizer.cls_token_id
        sep_token_id = tokenizer.sep_token_id
        pad_token_id = tokenizer.pad_token_id
    else:
        pad_token_id = 0
        use_subwords = False

    text_lengths = [len(text) for text in batch_of_texts]
    block_size = min(max_block_size, max(text_lengths))
    if use_subwords and block_size > 510:
        overflow_length = block_size - 510
        block_size -= overflow_length  # account for CLS and SEP tokens

    downsampling_rate = getattr(model.config, "downsampling_rate", 1)
    block_size = math.ceil(block_size / downsampling_rate) * downsampling_rate

    num_chunks = sum(math.ceil(max(length - block_size, 0) / stride) + 1 for length in text_lengths)

    if not use_subwords:
        input_hashes = np.zeros(
            (num_chunks, block_size, model.config.num_hash_functions), dtype=np.int64
        )
        attention_mask = np.zeros((num_chunks, block_size), dtype=np.float32)
    else:
        input_ids = np.zeros((num_chunks, block_size + 2), dtype=np.int64)
        attention_mask = np.zeros((num_chunks, block_size + 2), dtype=np.float32)

    locs = np.zeros((num_chunks, 3), dtype=np.int32)

    if not use_subwords:
        codec = "utf-32-le" if sys.byteorder == "little" else "utf-32-be"
        ordinals = np.frombuffer(bytearray("".join(batch_of_texts), encoding=codec), dtype=np.int32)
        flat_hashed_ids = hash_encode(
            ordinals,
            num_hashes=model.config.num_hash_functions,
            num_buckets=model.config.num_hash_buckets,
        )
    offset = 0
    current_chunk = 0

    for i in range(len(batch_of_texts)):
        for j in range(0, text_lengths[i], stride):
            start, end = j, j + block_size
            done = False
            if end >= text_lengths[i]:
                end = text_lengths[i]
                start = max(end - block_size, 0)
                done = True
            if not use_subwords:
                input_hashes[current_chunk, : end - start] = flat_hashed_ids[
                    offset + start : offset + end
                ]
                attention_mask[current_chunk, : end - start] = 1
            else:
                chunk = [cls_token_id] + batch_of_texts[i][start:end] + [sep_token_id]
                input_ids[current_chunk, : len(chunk)] = chunk
                attention_mask[current_chunk, : len(chunk)] = 1
            locs[current_chunk, :] = [i, start, end]
            current_chunk += 1
            if done:
                break
        offset += text_lengths[i]

    assert current_chunk == num_chunks
    n_batches = math.ceil(len(attention_mask) / batch_size)

    all_logits = [
        np.zeros((length, model.config.num_labels), dtype=np.float16) for length in text_lengths
    ]
    all_counts = [np.zeros(length, dtype=np.float16) for length in text_lengths]

    for batch_idx in range(n_batches):
        start, end = batch_idx * batch_size, min(len(attention_mask), (batch_idx + 1) * batch_size)
        if not use_subwords:
            batch_input_hashes = input_hashes[start:end]
        else:
            batch_input_ids = input_ids[start:end]
        batch_attention_mask = attention_mask[start:end]

        if len(batch_attention_mask) < batch_size and pad_last_batch:
            n_missing = batch_size - len(batch_attention_mask)
            if not use_subwords:
                batch_input_hashes = np.pad(batch_input_hashes, ((0, n_missing), (0, 0), (0, 0)))
            else:
                batch_input_ids = np.pad(
                    batch_input_ids, ((0, n_missing), (0, 0)), constant_values=pad_token_id
                )
            batch_attention_mask = np.pad(batch_attention_mask, ((0, n_missing), (0, 0)))

        kwargs = {}
        if use_subwords:
            kwargs["input_ids"] = batch_input_ids
        else:
            kwargs["hashed_ids"] = batch_input_hashes

        logits = model(attention_mask=batch_attention_mask, **kwargs)["logits"]

        if use_subwords:
            logits = logits[:, 1:-1, :]  # remove CLS and SEP tokens

        if weighting == "uniform":
            weights = np.ones(block_size, dtype=np.float16)
        elif weighting == "hat":
            x = np.linspace(-(1 - 1 / block_size), 1 - 1 / block_size, block_size, dtype=np.float16)
            weights = 1 - np.abs(x)
        for i in range(start, end):
            original_idx, start_char_idx, end_char_idx = locs[i]
            n = end_char_idx - start_char_idx
            all_logits[original_idx][start_char_idx:end_char_idx] += (
                weights[:n, np.newaxis] * logits[i - start, :n]
            )
            all_counts[original_idx][start_char_idx:end_char_idx] += weights[:n]

    all_logits = [
        (logits / counts[:, None]).astype(np.float16)
        for logits, counts in zip(all_logits, all_counts)
    ]

    return (
        all_logits,
        offset_mapping if use_subwords else None,
        tokenizer if use_subwords else None,
        tokens if use_subwords else None,
    )
