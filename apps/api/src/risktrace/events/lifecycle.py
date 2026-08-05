from dataclasses import dataclass
from datetime import timedelta

from risktrace.events.schemas import AdmissionDecision, LifecycleStatus


def initial_status_for(decision: AdmissionDecision) -> LifecycleStatus | None:
    if decision is AdmissionDecision.WAIT:
        return LifecycleStatus.CANDIDATE
    if decision is AdmissionDecision.ADMIT:
        return LifecycleStatus.CONFIRMED
    return None


@dataclass(frozen=True, slots=True)
class LifecyclePolicy:
    version: str = "event-lifecycle-v1"
    active_heat_threshold: float = 0.60
    cooling_heat_threshold: float = 0.35
    reactivation_heat_threshold: float = 0.60
    reactivation_momentum_threshold: float = 0.20
    cooling_after: timedelta = timedelta(hours=6)
    close_after: timedelta = timedelta(hours=24)

    def advance(
        self,
        current: LifecycleStatus,
        *,
        heat: float,
        momentum: float | None,
        low_heat_for: timedelta,
        confirmation_score: float | None = None,
        confirmation_threshold: float = 0.70,
    ) -> LifecycleStatus:
        if not 0.0 <= heat <= 1.0:
            raise ValueError("heat must be between 0 and 1")
        if low_heat_for < timedelta(0):
            raise ValueError("low_heat_for cannot be negative")
        if current is LifecycleStatus.CANDIDATE:
            if confirmation_score is None:
                return current
            if not 0.0 <= confirmation_score <= 1.0:
                raise ValueError("confirmation_score must be between 0 and 1")
            return (
                LifecycleStatus.CONFIRMED
                if confirmation_score >= confirmation_threshold
                else current
            )
        if current is LifecycleStatus.CONFIRMED:
            return LifecycleStatus.ACTIVE if heat >= self.active_heat_threshold else current
        if current is LifecycleStatus.ACTIVE:
            if (
                heat < self.cooling_heat_threshold
                and momentum is not None
                and momentum < 0
                and low_heat_for >= self.cooling_after
            ):
                return LifecycleStatus.COOLING
            return current
        if current in {LifecycleStatus.COOLING, LifecycleStatus.CLOSED} and (
            heat >= self.reactivation_heat_threshold
            or (momentum is not None and momentum >= self.reactivation_momentum_threshold)
        ):
            return LifecycleStatus.ACTIVE
        if current is LifecycleStatus.COOLING and low_heat_for >= self.close_after:
            return LifecycleStatus.CLOSED
        return current
