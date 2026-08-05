from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class TimestampOverride:
    value: str
    precision: str
    basis: str


@dataclass(frozen=True, slots=True)
class ReplayConfig:
    mode: str
    interval_ms: int


@dataclass(frozen=True, slots=True)
class ScenarioManifest:
    path: Path
    schema_version: str
    id: str
    name: str
    description: str
    source_document: Path
    timezone: str
    collected_at: str
    collection_method: str
    license_scope: str
    provenance_status: str
    data_quality: dict[str, str]
    replay: ReplayConfig
    published_at_overrides: dict[str, TimestampOverride]


def load_manifest(path: Path) -> ScenarioManifest:
    path = path.resolve()
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "demo-scenario-v1":
        raise ValueError(f"unsupported manifest schema: {raw.get('schema_version')!r}")

    replay = raw.get("replay", {})
    if replay.get("mode") != "fixed_interval":
        raise ValueError("only fixed_interval replay is supported")
    interval_ms = replay.get("interval_ms")
    if not isinstance(interval_ms, int) or interval_ms <= 0:
        raise ValueError("replay.interval_ms must be a positive integer")

    source_document = (path.parent / raw["source_document"]).resolve()
    data_root = path.parents[2] / "data"
    if not source_document.is_relative_to(data_root):
        raise ValueError(f"source document must stay under {data_root}")
    if not source_document.is_file():
        raise ValueError(f"source document does not exist: {source_document}")

    overrides = {
        heading: TimestampOverride(
            value=value["value"],
            precision=value["precision"],
            basis=value["basis"],
        )
        for heading, value in raw.get("published_at_overrides", {}).items()
    }
    data_quality = raw.get("data_quality", {})
    if data_quality.get("market") != "unavailable":
        raise ValueError("historical demo manifests must explicitly mark market unavailable")

    return ScenarioManifest(
        path=path,
        schema_version=raw["schema_version"],
        id=raw["id"],
        name=raw["name"],
        description=raw["description"],
        source_document=source_document,
        timezone=raw["timezone"],
        collected_at=raw["collected_at"],
        collection_method=raw["collection_method"],
        license_scope=raw["license_scope"],
        provenance_status=raw["provenance_status"],
        data_quality=dict(data_quality),
        replay=ReplayConfig(mode=replay["mode"], interval_ms=interval_ms),
        published_at_overrides=overrides,
    )
