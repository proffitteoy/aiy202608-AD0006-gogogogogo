from __future__ import annotations

__all__ = [
    "EntityExtractionAgent",
    "OpinionExtractionAgent",
    "TransmissionGraphAgent",
]


def __getattr__(name: str):
    if name == "TransmissionGraphAgent":
        from risktrace.agents.transmission import TransmissionGraphAgent

        return TransmissionGraphAgent
    if name == "EntityExtractionAgent":
        from risktrace.agents.entities import EntityExtractionAgent

        return EntityExtractionAgent
    if name == "OpinionExtractionAgent":
        from risktrace.agents.opinions import OpinionExtractionAgent

        return OpinionExtractionAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
