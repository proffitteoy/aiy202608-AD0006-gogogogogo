from math import prod

from risktrace.scoring.schemas import EvidenceWeightComponents


def information_weight(components: EvidenceWeightComponents) -> float:
    """Combine traceable evidence dimensions without a non-zero floor."""

    return prod(
        (
            components.source_reliability,
            components.independence,
            components.score_relevance,
            components.freshness,
            components.data_quality,
        )
    )
