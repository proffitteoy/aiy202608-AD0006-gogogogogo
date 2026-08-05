from __future__ import annotations

__all__ = ["TransmissionGraphAgent"]


def __getattr__(name: str):
    if name == "TransmissionGraphAgent":
        from risktrace.agents.transmission import TransmissionGraphAgent

        return TransmissionGraphAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
