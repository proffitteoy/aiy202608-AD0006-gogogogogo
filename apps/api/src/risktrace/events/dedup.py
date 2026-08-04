import hashlib
import re
import unicodedata
from collections.abc import Iterable

_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]")


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = _URL_PATTERN.sub(" ", normalized)
    return " ".join(normalized.split())


def exact_content_hash(value: str) -> str:
    return hashlib.sha256(normalize_text(value).encode("utf-8")).hexdigest()


def _features(value: str) -> tuple[str, ...]:
    tokens = _TOKEN_PATTERN.findall(normalize_text(value))
    if len(tokens) < 3:
        return tuple(tokens)
    return tuple("".join(tokens[index : index + 3]) for index in range(len(tokens) - 2))


def simhash64(value: str) -> int:
    features = _features(value)
    if not features:
        return 0
    vector = [0] * 64
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        feature_hash = int.from_bytes(digest, "big")
        for bit in range(64):
            vector[bit] += 1 if feature_hash & (1 << bit) else -1
    result = 0
    for bit, value_at_bit in enumerate(vector):
        if value_at_bit >= 0:
            result |= 1 << bit
    return result


def simhash_similarity(left: int, right: int) -> float:
    distance = (left ^ right).bit_count()
    return 1.0 - distance / 64


def is_near_duplicate(left: str, right: str, threshold: float = 0.95) -> bool:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    if exact_content_hash(left) == exact_content_hash(right):
        return True
    return simhash_similarity(simhash64(left), simhash64(right)) >= threshold


def first_duplicate_index(
    values: Iterable[str], candidate: str, threshold: float = 0.95
) -> int | None:
    candidate_hash = simhash64(candidate)
    for index, existing in enumerate(values):
        if exact_content_hash(existing) == exact_content_hash(candidate):
            return index
        if simhash_similarity(simhash64(existing), candidate_hash) >= threshold:
            return index
    return None
