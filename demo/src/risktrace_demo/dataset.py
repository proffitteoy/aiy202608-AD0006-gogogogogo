from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .manifest import ScenarioManifest, load_manifest
from .models import SourceRecord


@dataclass(frozen=True, slots=True)
class ScenarioDataset:
    manifest: ScenarioManifest
    records: tuple[SourceRecord, ...]
    fingerprint: str

    @classmethod
    def load(cls, manifest_path: Path) -> ScenarioDataset:
        manifest = load_manifest(manifest_path)
        records_path = manifest.path.parent / "records.jsonl"
        if not records_path.is_file():
            raise ValueError(f"converted dataset does not exist: {records_path}")

        records: list[SourceRecord] = []
        raw_lines: list[str] = []
        for line_number, line in enumerate(
            records_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            try:
                records.append(SourceRecord.from_dict(json.loads(line)))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                raise ValueError(
                    f"invalid record at {records_path}:{line_number}: {error}"
                ) from error
            raw_lines.append(line)

        if not records:
            raise ValueError(f"dataset contains no valid records: {records_path}")
        if len({record.external_id for record in records}) != len(records):
            raise ValueError(f"dataset contains duplicate external_id values: {records_path}")
        expected_order = sorted(
            records,
            key=lambda record: (record.published_at, record.metadata["source_order"]),
        )
        if records != expected_order:
            raise ValueError(f"dataset is not sorted by published_at: {records_path}")

        fingerprint = hashlib.sha256("\n".join(raw_lines).encode("utf-8")).hexdigest()
        return cls(manifest=manifest, records=tuple(records), fingerprint=fingerprint)


def discover_manifests(demo_root: Path) -> list[Path]:
    return sorted((demo_root / "scenarios").glob("*/manifest.json"))


def find_manifest(demo_root: Path, scenario_id: str) -> Path:
    matches = [
        path
        for path in discover_manifests(demo_root)
        if json.loads(path.read_text(encoding="utf-8")).get("id") == scenario_id
    ]
    if not matches:
        raise ValueError(f"unknown scenario: {scenario_id}")
    if len(matches) > 1:
        raise ValueError(f"duplicate scenario id: {scenario_id}")
    return matches[0]
