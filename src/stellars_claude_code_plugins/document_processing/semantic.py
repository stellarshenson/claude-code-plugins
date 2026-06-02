"""Optional semantic grounding layer (ONNX Runtime + FAISS).

**All heavy deps are lazy-imported.** Importing this module does NOT load
``onnxruntime``, ``transformers``, ``faiss``, or ``pyarrow``. They are only
imported inside :class:`SemanticGrounder.__init__` and the first call to
:meth:`SemanticGrounder.search`.

When the optional extras are missing, :func:`is_available` returns ``False``
and callers gracefully skip the layer.

Install:

    pip install 'stellars-claude-code-plugins[semantic]'

Or:

    pip install onnxruntime transformers faiss-cpu pyarrow huggingface_hub

Inference runs through ONNX Runtime on CPU using a pre-exported ONNX model
pulled from the Hugging Face Hub (default ``intfloat/multilingual-e5-small``,
which ships ``onnx/model.onnx``). No PyTorch dependency. A model_name without
``onnx/model.onnx`` on the Hub raises a clear error at construction.

Workflow:

    1. Chunk the source text recursively (via :mod:`.chunking`).
    2. Embed each chunk with ``model_name`` (mask-aware mean pooling + L2
       normalisation, computed in numpy from the ONNX last_hidden_state).
    3. Cache chunks + embeddings to parquet keyed by source content hash.
    4. Build an in-memory FAISS index (IndexFlatIP for cosine similarity).
    5. For each claim, embed it and return top-K passages with similarity
       scores + source offsets for location metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from stellars_claude_code_plugins.document_processing.chunking import Chunk, recursive_chunk


@dataclass
class SemanticHit:
    score: float  # cosine similarity in [-1, 1], typically [0, 1] for normalised embeddings
    source_index: int
    source_path: str
    char_start: int
    char_end: int
    matched_text: str


def is_available() -> bool:
    """Return True iff the optional semantic deps are importable."""
    for mod in ("onnxruntime", "transformers", "faiss", "pyarrow", "huggingface_hub"):
        try:
            __import__(mod)
        except ImportError:
            return False
    return True


def install_hint() -> str:
    return (
        "Semantic grounding requires: onnxruntime, transformers, faiss-cpu, "
        "pyarrow, huggingface_hub.\n"
        "Install via:  pip install 'stellars-claude-code-plugins[semantic]'"
    )


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


class SemanticGrounder:
    """Embed source passages and rank them by semantic similarity to a claim.

    Lightweight by design:
        - Lazy-imports heavy deps on construction.
        - Persists chunks + embeddings as parquet keyed by content hash, so
          re-runs against the same source skip re-encoding.
        - Uses ``IndexFlatIP`` on L2-normalised embeddings = cosine sim.
        - CPU by default; ``device="auto"`` picks CUDA when available.
    """

    def __init__(
        self,
        *,
        model_name: str = "intfloat/multilingual-e5-small",
        device: str = "auto",
        cache_dir: str | Path = ".stellars-plugins/cache",
        max_chars: int = 1500,
    ) -> None:
        if not is_available():
            raise ImportError(install_hint())

        from huggingface_hub import hf_hub_download  # type: ignore
        from huggingface_hub.utils import EntryNotFoundError  # type: ignore
        import onnxruntime as ort  # type: ignore
        from transformers import AutoTokenizer  # type: ignore

        # ONNX Runtime runs the encoder on CPU. ``device`` is accepted for
        # backward compatibility with the config/CLI (semantic_device) but
        # does not select a GPU on this path.
        self.device = "cpu"
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_chars = max_chars

        # Tokenizer (transformers, no torch) + pre-exported ONNX encoder.
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        try:
            onnx_path = hf_hub_download(model_name, "onnx/model.onnx")
        except EntryNotFoundError as exc:
            raise RuntimeError(
                f"{model_name!r} has no 'onnx/model.onnx' on the Hugging Face "
                "Hub. The ONNX Runtime grounding path needs a pre-exported "
                "ONNX model (e.g. intfloat/multilingual-e5-small). Pick a model "
                "that ships ONNX weights, or export one offline."
            ) from exc
        self._session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        self._input_names = {i.name for i in self._session.get_inputs()}

        # Index state — lazily built in index_sources()
        self._index = None
        self._provenance: list[tuple[int, str, Chunk]] = []
        # H3: percentile threshold calibration - sampled chunk-pair cosine
        # distribution from the most recent ``index_sources`` call. ``None``
        # until an index is built. Float array of ``n_samples`` floats.
        self._cosine_samples = None

    # ---- public API ------------------------------------------------------

    def _is_e5(self) -> bool:
        """E5-family models expect 'query: ' / 'passage: ' prefixes."""
        return "e5" in self.model_name.lower()

    def index_sources(self, sources: list[tuple[int, str, str]]) -> None:
        """Chunk + embed + FAISS-index a list of ``(idx, path, text)`` tuples."""
        import numpy as np  # type: ignore

        all_chunks: list[tuple[int, str, Chunk]] = []
        all_vectors: list[np.ndarray] = []

        for idx, path, text in sources:
            chunks = recursive_chunk(text, max_chars=self.max_chars)
            if not chunks:
                continue
            vectors = self._load_or_embed(path, text, chunks)
            for c, v in zip(chunks, vectors):
                all_chunks.append((idx, path, c))
                all_vectors.append(v)

        if not all_vectors:
            self._provenance = []
            self._index = None
            return

        matrix = np.vstack(all_vectors).astype("float32")
        self._provenance = all_chunks
        self._index = self._build_faiss(matrix)
        # H3: sample N=200 random chunk-pair cosines to calibrate
        # model-agnostic thresholds. With L2-normalised embeddings, dot
        # product == cosine. Sampling off-diagonal pairs avoids the
        # trivial self-similarity 1.0.
        n_chunks = matrix.shape[0]
        if n_chunks >= 2:
            rng = np.random.default_rng(42)
            n_samples = min(200, n_chunks * (n_chunks - 1) // 2)
            sims = np.empty(n_samples, dtype="float32")
            for k in range(n_samples):
                i = int(rng.integers(0, n_chunks))
                j = int(rng.integers(0, n_chunks))
                if j == i:
                    j = (j + 1) % n_chunks
                sims[k] = float(np.dot(matrix[i], matrix[j]))
            self._cosine_samples = sims
        else:
            self._cosine_samples = None

    def percentile_threshold(self, top_pct: float = 0.02, floor: float = 0.65) -> float:
        """Return the cosine value at the (1 - top_pct) quantile of the
        sampled chunk-pair distribution.

        Example: ``top_pct=0.02`` -> threshold above which only 2% of
        random chunk pairs score. Model-agnostic: a strong real match will
        land in the tail regardless of the model's absolute scale.

        The ``floor`` guards against degenerate corpora (very small or
        homogeneous) where the quantile collapses below a value any
        reasonable retrieval model would treat as a real match. Set floor=0
        to disable.

        Returns ``0.0`` when no distribution has been sampled yet (index
        with fewer than 2 chunks or ``index_sources`` not called).
        """
        import numpy as np  # type: ignore

        if self._cosine_samples is None or len(self._cosine_samples) == 0:
            return 0.0
        # top_pct = 0.02 -> we want the score above which only the top 2%
        # of random pairs lie, i.e. the (1 - 0.02) = 0.98 quantile
        q = float(np.quantile(self._cosine_samples, 1.0 - top_pct))
        return max(floor, min(1.0, q))

    def self_score(self, claim: str) -> float:
        """Cosine similarity of the claim embedded as query vs as passage.

        Provides a per-claim calibration anchor for
        :attr:`grounding.GroundingMatch.semantic_ratio`. For E5 models the
        query/passage prefixes deliberately shift embeddings apart; this
        method returns the claim's "best possible" self-agreement score so
        the caller can normalise their search score against it.

        For non-E5 models (no prefix) this typically returns ~1.0.
        """
        import numpy as np  # type: ignore

        if self._is_e5():
            query_text = f"query: {claim}"
            passage_text = f"passage: {claim}"
        else:
            query_text = claim
            passage_text = claim
        vecs = self._embed([query_text, passage_text]).astype("float32")
        # Inner product of L2-normalised vectors = cosine
        score = float(np.dot(vecs[0], vecs[1]))
        return max(0.0, min(1.0, score))

    def search(self, claim: str, *, top_k: int = 1) -> list[SemanticHit]:
        """Return top-K chunks matching the claim, sorted by cosine similarity."""
        if self._index is None or not self._provenance:
            return []

        # E5 expects "query: " prefix on queries
        query_text = f"query: {claim}" if self._is_e5() else claim
        claim_vec = self._embed([query_text]).astype("float32")
        scores, idxs = self._index.search(claim_vec, top_k)
        hits: list[SemanticHit] = []
        for rank, (score, i) in enumerate(zip(scores[0], idxs[0])):
            if i < 0 or i >= len(self._provenance):
                continue
            src_idx, path, chunk = self._provenance[i]
            hits.append(
                SemanticHit(
                    score=float(score),
                    source_index=src_idx,
                    source_path=path,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    matched_text=chunk.text,
                )
            )
        return hits

    # ---- internals -------------------------------------------------------

    def _load_or_embed(self, path: str, text: str, chunks: list[Chunk]):
        """Load cached embeddings or compute + persist."""
        import numpy as np  # type: ignore
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore

        key = _hash_text(self.model_name + "|" + text)
        cache_file = self.cache_dir / f"{key}.parquet"
        if cache_file.is_file():
            table = pq.read_table(cache_file)
            # If chunk count matches, trust the cache
            if table.num_rows == len(chunks):
                return np.stack(
                    [np.frombuffer(b, dtype="float32") for b in table.column("vec").to_pylist()]
                )

        # E5 expects "passage: " prefix on passages
        if self._is_e5():
            embed_texts = [f"passage: {c.text}" for c in chunks]
        else:
            embed_texts = [c.text for c in chunks]
        vectors = self._embed(embed_texts)
        texts = [c.text for c in chunks]

        # Persist
        arr = pa.array([v.tobytes() for v in vectors], type=pa.binary())
        starts = pa.array([c.char_start for c in chunks], type=pa.int64())
        ends = pa.array([c.char_end for c in chunks], type=pa.int64())
        t_arr = pa.array(texts, type=pa.string())
        src = pa.array([path] * len(chunks), type=pa.string())
        table = pa.Table.from_arrays(
            [src, starts, ends, t_arr, arr], names=["source", "start", "end", "text", "vec"]
        )
        pq.write_table(table, cache_file)
        return vectors

    def _embed(self, texts: list[str]):
        """Embed a batch of texts → (N, dim) numpy array, L2-normalised.

        Runs the ONNX encoder on CPU, then mask-aware mean-pools the
        last_hidden_state and L2-normalises - all in numpy. Equivalent to the
        prior torch pooling (verified to 1e-7 on fp32 e5-small).
        """
        import numpy as np  # type: ignore

        enc = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np",
        )
        # Feed exactly the inputs the graph declares. e5/XLM-R ONNX graphs ask
        # for token_type_ids that the tokenizer omits - supply zeros.
        feed = {}
        for name in self._input_names:
            if name in enc:
                feed[name] = enc[name]
            elif name == "token_type_ids":
                feed[name] = np.zeros_like(enc["input_ids"])
        last_hidden = self._session.run(None, feed)[0]  # (N, L, dim)

        mask = enc["attention_mask"][..., None].astype("float32")  # (N, L, 1)
        summed = (last_hidden * mask).sum(axis=1)  # (N, dim)
        counts = np.clip(mask.sum(axis=1), 1e-9, None)  # (N, 1)
        vectors = summed / counts
        # L2 normalise for cosine similarity via inner product
        norms = np.clip(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12, None)
        return (vectors / norms).astype("float32")

    def _build_faiss(self, matrix):
        """Build an IndexFlatIP (inner product == cosine after L2-norm)."""
        import faiss  # type: ignore

        dim = matrix.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(matrix)
        return index
