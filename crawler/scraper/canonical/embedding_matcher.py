"""Optional embedding-based fallback for the rule-based matcher.

Only invoked **within an existing block** (same `(manufacturer, size,
pack)`). The rule-based matcher already handles brand/size/pack
discrimination — embeddings can't be trusted with those (the design
spike showed they'll happily merge `Pampers No7` with `Pampers No8`).

Used in the rule-matcher's ambiguous zone, where confidence is in
[0.4, 0.95]. The model used is `intfloat/multilingual-e5-small`. We
lazy-load it so the import-time cost stays out of unit tests and the
batch script can be run without `sentence-transformers` installed when
``--no-embeddings`` is set.
"""

from __future__ import annotations

from typing import Any

from .extractors import ProductFeatures

_MODEL: Any | None = None


def _load_model() -> Any:
    global _MODEL
    if _MODEL is None:
        # Lazy import — keeps the module importable without the optional
        # `sentence-transformers` dependency.
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

        _MODEL = SentenceTransformer("intfloat/multilingual-e5-small")
    return _MODEL


def _e5_query(text: str) -> str:
    # The e5 family expects a "query: " / "passage: " prefix. For symmetric
    # similarity we use "query: " on both sides.
    return f"query: {text}"


def embed_and_score(
    a: ProductFeatures,
    b: ProductFeatures,
    model: Any | None = None,
) -> float:
    """Return cosine similarity in [-1, 1] between the two product names.

    Caller should clamp/scale this however they want; we return the raw
    cosine. ``model`` may be passed in by the batch script to amortise
    model load across many calls.
    """
    model = model or _load_model()
    encoded = model.encode(
        [_e5_query(a.name), _e5_query(b.name)],
        normalize_embeddings=True,
    )
    # cosine similarity == dot product on L2-normalised vectors.
    return float((encoded[0] * encoded[1]).sum())


def embed_batch_score(
    pairs: list[tuple[ProductFeatures, ProductFeatures]],
    model: Any | None = None,
) -> list[float]:
    """Vectorised pairwise scoring. Encodes the entire pair list in one
    forward pass — much cheaper than calling :func:`embed_and_score`
    in a loop."""
    if not pairs:
        return []
    model = model or _load_model()
    texts: list[str] = []
    for a, b in pairs:
        texts.append(_e5_query(a.name))
        texts.append(_e5_query(b.name))
    encoded = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    scores: list[float] = []
    for i in range(0, len(encoded), 2):
        scores.append(float((encoded[i] * encoded[i + 1]).sum()))
    return scores
