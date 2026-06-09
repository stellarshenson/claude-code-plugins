"""SaT utilities (token->char probs, sentence reconstruction). Vendored from wtpsplit-lite
(MIT, Superlinear); see LICENSE. Trimmed to the subword-SaT split path - the language-table
and punctuation properties (unused on this path) are dropped."""
# ruff: noqa: N802, N806

import numpy as np

# same as in CANINE
PRIMES = [31, 43, 59, 61, 73, 97, 103, 113, 137, 149, 157, 173, 181, 193, 211, 223]


class ConstantsClass:
    NEWLINE_INDEX = 0
    AUX_OFFSET = 1


Constants = ConstantsClass()


def hash_encode(encoding, num_hashes=8, num_buckets=8192):
    if num_hashes > len(PRIMES):
        raise ValueError(f"`num_hashes` must be <= {len(PRIMES)}")
    hash_ids = np.zeros((len(encoding), num_hashes), dtype=np.int64)
    for i in range(num_hashes):
        shard_ids = (encoding + 1) * PRIMES[i]
        hash_ids[:, i] = shard_ids % num_buckets
    return hash_ids


def indices_to_sentences(text, indices, strip_whitespace=False):
    sentences = []
    offset = 0
    idx = 0
    for idx in indices:
        idx = idx + 1
        while idx < len(text) and text[idx].isspace():
            idx += 1
        sentence = text[offset:idx]
        if strip_whitespace:
            sentence = sentence.strip()
        if len(sentence) > 0:
            sentences.append(sentence)
        offset = idx
    if idx != len(text):
        last_sentence = text[idx:]
        if strip_whitespace:
            last_sentence = last_sentence.strip()
        if len(last_sentence) > 0:
            sentences.append(last_sentence)
    return sentences


def sigmoid(x):
    return 1 / (1 + np.exp(-x.astype(np.float32)))  # fp32 for better precision


def get_token_spans(tokenizer, offsets_mapping, tokens):
    valid_indices = np.array(
        [
            idx
            for idx, token in enumerate(tokens)
            if token not in [tokenizer.cls_token, tokenizer.sep_token, tokenizer.pad_token]
            and idx < len(offsets_mapping)
        ]
    )
    valid_offsets = np.array(offsets_mapping)[valid_indices]
    return valid_indices, valid_offsets


def token_to_char_probs(text, tokens, token_logits, tokenizer, offsets_mapping):
    """Map token probabilities to character probabilities."""
    char_probs = np.full((len(text), token_logits.shape[1]), -np.inf)
    valid_indices, valid_offsets = get_token_spans(tokenizer, offsets_mapping, tokens)
    for i in range(valid_offsets.shape[0]):
        start, end = valid_offsets[i]
        char_probs[end - 1] = token_logits[valid_indices[i]]
    return char_probs
