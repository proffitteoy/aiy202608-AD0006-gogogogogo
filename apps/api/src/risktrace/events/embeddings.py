from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    @property
    def model_version(self) -> str: ...

    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


class SentenceTransformerEmbeddingProvider:
    """Lazy adapter around the vendored Sentence Transformers implementation."""

    def __init__(
        self,
        model_name_or_path: str,
        *,
        revision: str | None = None,
        device: str | None = None,
    ) -> None:
        if not model_name_or_path.strip():
            raise ValueError("model_name_or_path is required")
        self._model_name_or_path = model_name_or_path
        self._revision = revision
        self._device = device
        self._model: object | None = None

    @property
    def model_version(self) -> str:
        revision = self._revision or "default"
        return f"{self._model_name_or_path}@{revision}"

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        embeddings = model.encode(  # type: ignore[attr-defined]
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [[float(value) for value in row] for row in embeddings]

    def _load_model(self) -> object:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self._model_name_or_path,
                revision=self._revision,
                device=self._device,
            )
        return self._model
