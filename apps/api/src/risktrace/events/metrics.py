import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


def _unit_interval(name: str, value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


def normalized_log_volume(count: int, saturation_count: int = 1_000) -> float:
    if count < 0 or saturation_count <= 0:
        raise ValueError("counts must be non-negative and saturation_count positive")
    return min(math.log1p(count) / math.log1p(saturation_count), 1.0)


def growth_anomaly(
    count: int,
    baseline_mean: float,
    baseline_std: float,
    *,
    epsilon: float = 1e-6,
) -> float:
    if count < 0 or baseline_mean < 0 or baseline_std < 0:
        raise ValueError("growth inputs cannot be negative")
    return (count - baseline_mean) / (baseline_std + epsilon)


def sigmoid_growth(z_score: float, sensitivity: float = 1.0) -> float:
    if sensitivity <= 0:
        raise ValueError("sensitivity must be positive")
    scaled = max(min(sensitivity * z_score, 60.0), -60.0)
    return 1.0 / (1.0 + math.exp(-scaled))


def source_diversity(source_counts: Mapping[str, int]) -> float | None:
    positive_counts = [count for count in source_counts.values() if count > 0]
    total = sum(positive_counts)
    if total == 0:
        return None
    if len(positive_counts) == 1:
        return 0.0
    entropy = -sum((count / total) * math.log(count / total) for count in positive_counts)
    return entropy / math.log(len(positive_counts))


def mean_optional(values: Sequence[float]) -> float | None:
    if not values:
        return None
    for value in values:
        _unit_interval("factor", value)
    return sum(values) / len(values)


def max_optional(values: Sequence[float]) -> float | None:
    if not values:
        return None
    for value in values:
        _unit_interval("factor", value)
    return max(values)


def _weighted_available(
    values: Mapping[str, float | None],
    weights: Mapping[str, float],
) -> tuple[float | None, float]:
    available = {name: value for name, value in values.items() if value is not None}
    available_weight = sum(weights[name] for name in available)
    if available_weight == 0:
        return None, 0.0
    score = sum(weights[name] * value for name, value in available.items()) / available_weight
    return score, available_weight / sum(weights.values())


@dataclass(frozen=True, slots=True)
class EventMetricInputs:
    message_count_5m: int
    message_count_1h: int
    baseline_mean_5m: float
    baseline_std_5m: float
    engagement_percentiles: tuple[float, ...]
    source_counts: Mapping[str, int]
    authority_scores: tuple[float, ...]
    covered_platform_count: int
    expected_platform_count: int | None
    previous_heat: float | None
    source_quality: float
    independent_source_ratio: float
    novelty: float
    market_relevance: float
    potential_impact: float
    market_response: float | None
    data_completeness: float


@dataclass(frozen=True, slots=True)
class EventMetricResult:
    volume: float
    growth_z: float
    growth: float
    engagement: float | None
    diversity: float | None
    authority: float | None
    coverage: float | None
    heat: float
    heat_completeness: float
    momentum: float | None
    raw_score: float
    scoring_completeness: float
    scoring_version: str


@dataclass(frozen=True, slots=True)
class MetricPolicy:
    version: str = "deterministic-scoring-v1"
    volume_weight: float = 0.20
    growth_weight: float = 0.25
    engagement_weight: float = 0.15
    diversity_weight: float = 0.15
    authority_weight: float = 0.15
    coverage_weight: float = 0.10
    source_quality_score_weight: float = 0.12
    independent_source_score_weight: float = 0.10
    heat_score_weight: float = 0.12
    momentum_score_weight: float = 0.08
    novelty_score_weight: float = 0.08
    market_relevance_score_weight: float = 0.15
    potential_impact_score_weight: float = 0.20
    market_response_score_weight: float = 0.10
    data_completeness_score_weight: float = 0.05
    volume_saturation_count: int = 1_000
    growth_sensitivity: float = 1.0

    def __post_init__(self) -> None:
        heat_weight = (
            self.volume_weight
            + self.growth_weight
            + self.engagement_weight
            + self.diversity_weight
            + self.authority_weight
            + self.coverage_weight
        )
        score_weight = (
            self.source_quality_score_weight
            + self.independent_source_score_weight
            + self.heat_score_weight
            + self.momentum_score_weight
            + self.novelty_score_weight
            + self.market_relevance_score_weight
            + self.potential_impact_score_weight
            + self.market_response_score_weight
            + self.data_completeness_score_weight
        )
        if not math.isclose(heat_weight, 1.0, abs_tol=1e-9):
            raise ValueError("heat weights must sum to 1")
        if not math.isclose(score_weight, 1.0, abs_tol=1e-9):
            raise ValueError("scoring weights must sum to 1")
        if self.volume_saturation_count <= 0 or self.growth_sensitivity <= 0:
            raise ValueError("metric scale parameters must be positive")

    def calculate(self, inputs: EventMetricInputs) -> EventMetricResult:
        if inputs.message_count_5m < 0 or inputs.message_count_1h < 0:
            raise ValueError("message counts cannot be negative")
        if inputs.message_count_5m > inputs.message_count_1h:
            raise ValueError("5 minute count cannot exceed 1 hour count")
        if inputs.covered_platform_count < 0:
            raise ValueError("covered_platform_count cannot be negative")
        volume = normalized_log_volume(inputs.message_count_5m, self.volume_saturation_count)
        z_score = growth_anomaly(
            inputs.message_count_5m,
            inputs.baseline_mean_5m,
            inputs.baseline_std_5m,
        )
        growth = sigmoid_growth(z_score, self.growth_sensitivity)
        engagement = mean_optional(inputs.engagement_percentiles)
        diversity = source_diversity(inputs.source_counts)
        authority = max_optional(inputs.authority_scores)
        coverage = self._coverage(inputs.covered_platform_count, inputs.expected_platform_count)
        heat, heat_completeness = _weighted_available(
            {
                "volume": volume,
                "growth": growth,
                "engagement": engagement,
                "diversity": diversity,
                "authority": authority,
                "coverage": coverage,
            },
            {
                "volume": self.volume_weight,
                "growth": self.growth_weight,
                "engagement": self.engagement_weight,
                "diversity": self.diversity_weight,
                "authority": self.authority_weight,
                "coverage": self.coverage_weight,
            },
        )
        if heat is None:
            raise ValueError("volume and growth must make heat calculable")
        if inputs.previous_heat is not None:
            _unit_interval("previous_heat", inputs.previous_heat)
        momentum = None if inputs.previous_heat is None else heat - inputs.previous_heat
        raw_score, scoring_completeness = self._score(inputs, heat, momentum)
        return EventMetricResult(
            volume=volume,
            growth_z=z_score,
            growth=growth,
            engagement=engagement,
            diversity=diversity,
            authority=authority,
            coverage=coverage,
            heat=heat,
            heat_completeness=heat_completeness,
            momentum=momentum,
            raw_score=raw_score,
            scoring_completeness=scoring_completeness,
            scoring_version=self.version,
        )

    def _coverage(self, covered: int, expected: int | None) -> float | None:
        if expected is None:
            return None
        if expected <= 0 or covered > expected:
            raise ValueError("platform coverage counts are inconsistent")
        return covered / expected

    def _score(
        self,
        inputs: EventMetricInputs,
        heat: float,
        momentum: float | None,
    ) -> tuple[float, float]:
        factors = {
            "source_quality": inputs.source_quality,
            "independent_sources": inputs.independent_source_ratio,
            "heat": heat,
            "momentum": None if momentum is None else (momentum + 1.0) / 2.0,
            "novelty": inputs.novelty,
            "market_relevance": inputs.market_relevance,
            "potential_impact": inputs.potential_impact,
            "market_response": inputs.market_response,
            "data_completeness": inputs.data_completeness,
        }
        for name, value in factors.items():
            if value is not None:
                _unit_interval(name, value)
        score, completeness = _weighted_available(
            factors,
            {
                "source_quality": self.source_quality_score_weight,
                "independent_sources": self.independent_source_score_weight,
                "heat": self.heat_score_weight,
                "momentum": self.momentum_score_weight,
                "novelty": self.novelty_score_weight,
                "market_relevance": self.market_relevance_score_weight,
                "potential_impact": self.potential_impact_score_weight,
                "market_response": self.market_response_score_weight,
                "data_completeness": self.data_completeness_score_weight,
            },
        )
        if score is None:
            raise ValueError("required Rule 3 factors must make raw_score calculable")
        return score, completeness
