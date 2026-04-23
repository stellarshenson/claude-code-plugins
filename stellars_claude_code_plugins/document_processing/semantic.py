"""Optional semantic grounding layer (ModernBERT + FAISS).

**All heavy deps are lazy-imported.** Importing this module does NOT load
``torch``, ``transformers``, ``faiss``, or ``pyarrow``. They are only
imported inside :class:`SemanticGrounder.__init__` and the first call to
:meth:`SemanticGrounder.search`.

When the optional extras are missing, :func:`is_available` returns ``False``
and callers gracefully skip the layer.

Install:

    pip install 'stellars-claude-code-plugins[semantic]'

Or:

    pip install torch transformers faiss-cpu pyarrow

Workflow:

    1. Chunk the source text recursively (via :mod:`.chunking`).
    2. Embed each chunk with ``model_name`` (default ``jhu-clsp/mmBERT-small``).
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
    for mod in ("torch", "transformers", "faiss", "pyarrow"):
        try:
            __import__(mod)
        except ImportError:
            return False
    return True


def install_hint() -> str:
    return (
        "Semantic grounding requires: torch, transformers, faiss-cpu, pyarrow.\n"
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

        import torch  # type: ignore
        from transformers import AutoModel, AutoTokenizer  # type: ignore

        resolved_device = device
        if device == "auto":
            resolved_device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = resolved_device
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_chars = max_chars

        # Load model + tokenizer once; keep on the chosen device.
        # trust_remote_code=True required by mmBERT and other recent models
        # that ship custom modelling code.
        self._tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self._model = AutoModel.from_pretrained(model_name, trust_remote_code=True).to(
            resolved_device
        )
        self._model.eval()

        # Index state — lazily built in index_sources()
        self._index = None
        self._provenance: list[tuple[int, str, Chunk]] = []

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
        """Embed a batch of texts → (N, dim) numpy array, L2-normalised."""
        import torch  # type: ignore

        with torch.no_grad():
            enc = self._tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(self.device)
            outputs = self._model(**enc)
            # Mean-pool hidden states, mask-aware
            mask = enc["attention_mask"].unsqueeze(-1).float()
            hidden = outputs.last_hidden_state * mask
            summed = hidden.sum(dim=1)
            counts = mask.sum(dim=1).clamp(min=1e-9)
            vectors = summed / counts
            # L2 normalise for cosine similarity via inner product
            vectors = torch.nn.functional.normalize(vectors, p=2, dim=1)
        return vectors.cpu().numpy().astype("float32")

    def _build_faiss(self, matrix):
        """Build an IndexFlatIP (inner product == cosine after L2-norm)."""
        import faiss  # type: ignore

        dim = matrix.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(matrix)
        return index
