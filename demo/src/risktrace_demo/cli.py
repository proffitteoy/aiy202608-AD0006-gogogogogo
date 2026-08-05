from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from .dataset import ScenarioDataset, discover_manifests, find_manifest
from .docx_source import convert_manifest, write_conversion
from .manifest import load_manifest
from .replay import DemoReplayProvider
from .sinks import HttpIngestionSink, JsonLineSink


def default_demo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="risktrace-demo",
        description="Convert and replay RiskTrace historical source documents.",
    )
    parser.add_argument(
        "--demo-root",
        type=Path,
        default=default_demo_root(),
        help="demo directory containing data/ and scenarios/",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list configured demo scenarios")
    list_parser.set_defaults(handler=_list_scenarios)

    convert_parser = subparsers.add_parser("convert", help="convert DOCX sources to JSONL")
    convert_parser.add_argument("scenario", nargs="?", help="scenario id; omit to convert all")
    convert_parser.add_argument(
        "--strict",
        action="store_true",
        help="return a non-zero exit code when any source record is rejected",
    )
    convert_parser.set_defaults(handler=_convert)

    replay_parser = subparsers.add_parser("replay", help="replay one converted scenario")
    replay_parser.add_argument("scenario", help="scenario id")
    replay_parser.add_argument("--endpoint", help="unified ingestion endpoint URL")
    replay_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="write ingestion payloads as JSONL instead of sending HTTP requests",
    )
    replay_parser.add_argument("--interval-ms", type=int, help="override fixed release interval")
    replay_parser.add_argument("--start-index", type=int, help="seek before replay")
    replay_parser.add_argument(
        "--reset",
        action="store_true",
        help="reset the persisted replay cursor before starting",
    )
    replay_parser.add_argument(
        "--no-checkpoint",
        action="store_true",
        help="do not restore or persist the replay cursor",
    )
    replay_parser.set_defaults(handler=_replay)
    return parser


def _list_scenarios(args: argparse.Namespace) -> int:
    rows = []
    for path in discover_manifests(args.demo_root.resolve()):
        manifest = load_manifest(path)
        records_path = path.parent / "records.jsonl"
        rejected_path = path.parent / "rejected.jsonl"
        providers = (
            sorted({record.source.provider for record in ScenarioDataset.load(path).records})
            if records_path.is_file()
            else []
        )
        rows.append(
            {
                "id": manifest.id,
                "name": manifest.name,
                "converted": records_path.is_file(),
                "rejected_available": rejected_path.is_file(),
                "market": manifest.data_quality["market"],
                "providers": providers,
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def _selected_manifests(args: argparse.Namespace) -> list[Path]:
    demo_root = args.demo_root.resolve()
    if args.scenario:
        return [find_manifest(demo_root, args.scenario)]
    manifests = discover_manifests(demo_root)
    if not manifests:
        raise ValueError(f"no scenario manifests found under {demo_root}")
    return manifests


def _convert(args: argparse.Namespace) -> int:
    summaries = []
    rejected_total = 0
    for path in _selected_manifests(args):
        manifest = load_manifest(path)
        result = convert_manifest(manifest)
        write_conversion(manifest, result)
        rejected_total += len(result.rejected)
        summaries.append(
            {
                "scenario_id": manifest.id,
                "source_records": len(result.records) + len(result.rejected),
                "accepted": len(result.records),
                "rejected": len(result.rejected),
                "records_path": str(path.parent / "records.jsonl"),
                "rejected_path": str(path.parent / "rejected.jsonl"),
            }
        )
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 2 if args.strict and rejected_total else 0


def _replay(args: argparse.Namespace) -> int:
    if not args.dry_run and not args.endpoint:
        raise ValueError("--endpoint is required unless --dry-run is used")
    if not args.dry_run and not os.getenv("RISKTRACE_INGESTION_API_TOKEN", "").strip():
        raise ValueError("RISKTRACE_INGESTION_API_TOKEN is required unless --dry-run is used")
    if args.interval_ms is not None and args.interval_ms <= 0:
        raise ValueError("--interval-ms must be positive")
    return asyncio.run(_run_replay(args))


async def _run_replay(args: argparse.Namespace) -> int:
    demo_root = args.demo_root.resolve()
    manifest_path = find_manifest(demo_root, args.scenario)
    manifest = load_manifest(manifest_path)
    conversion = convert_manifest(manifest)
    write_conversion(manifest, conversion)
    dataset = ScenarioDataset.load(manifest_path)

    checkpoint_path = None
    if not args.no_checkpoint:
        checkpoint_path = demo_root.parent / "runtime" / "demo" / f"{manifest.id}.json"
    sink = (
        JsonLineSink()
        if args.dry_run
        else HttpIngestionSink(
            args.endpoint,
            bearer_token=os.environ["RISKTRACE_INGESTION_API_TOKEN"],
        )
    )
    provider = DemoReplayProvider(
        dataset,
        sink,
        checkpoint_path=checkpoint_path,
        restore_checkpoint=not args.reset,
    )

    if args.reset:
        provider.reset()
    if args.start_index is not None:
        provider.seek(args.start_index)
    if args.interval_ms is not None:
        provider.set_speed(args.interval_ms)

    try:
        await provider.start()
    finally:
        print(json.dumps(provider.status(), ensure_ascii=False), file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"risktrace-demo: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
