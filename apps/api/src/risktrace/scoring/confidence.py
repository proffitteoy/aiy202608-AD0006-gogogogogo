import math
from collections.abc import Sequence

from risktrace.scoring.schemas import ScoreInterval


def _require_unit_interval(name: str, value: float) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be a finite number between 0 and 1")


def quantile(samples: Sequence[float], probability: float) -> float:
    _require_unit_interval("probability", probability)
    if not samples:
        raise ValueError("at least one sample is required")
    if any(not math.isfinite(value) for value in samples):
        raise ValueError("samples must be finite")
    ordered = sorted(samples)
    position = (len(ordered) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered[lower_index]
    fraction = position - lower_index
    return ordered[lower_index] + fraction * (ordered[upper_index] - ordered[lower_index])


def credible_interval(samples: Sequence[float], credible_mass: float = 0.90) -> ScoreInterval:
    if not math.isfinite(credible_mass) or not 0.0 < credible_mass < 1.0:
        raise ValueError("credible_mass must be a finite number between 0 and 1")
    tail = (1.0 - credible_mass) / 2.0
    return ScoreInterval(
        lower=quantile(samples, tail),
        upper=quantile(samples, 1.0 - tail),
    )


def posterior_confidence(
    interval: ScoreInterval,
    quality_cap: float,
    evidence_strength: float,
    reference_width: float = 0.50,
    evidence_saturation: float = 4.0,
) -> float:
    _require_unit_interval("quality_cap", quality_cap)
    if not math.isfinite(reference_width) or reference_width <= 0.0:
        raise ValueError("reference_width must be positive and finite")
    if not math.isfinite(evidence_strength) or evidence_strength < 0.0:
        raise ValueError("evidence_strength must be non-negative and finite")
    if not math.isfinite(evidence_saturation) or evidence_saturation <= 0.0:
        raise ValueError("evidence_saturation must be positive and finite")
    concentration = 1.0 - min(interval.width / reference_width, 1.0)
    evidence_coverage = 1.0 - math.exp(-evidence_strength / evidence_saturation)
    return quality_cap * concentration * evidence_coverage
