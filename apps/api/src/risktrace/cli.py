import argparse
import asyncio
import json
from datetime import UTC, datetime

from risktrace.core.config import get_settings
from risktrace.db.session import create_db_engine, create_session_factory
from risktrace.ingestion.adapters.http import HttpTransport
from risktrace.ingestion.pull_live import (
    IngestionApiClient,
    LivePullRunner,
    available_live_adapter_names,
    build_live_adapter,
)
from risktrace.ingestion.repository import SqlAlchemySourceRuntimeRepository
from risktrace.seed.importer import SeedImporter


async def run_import() -> None:
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        importer = SeedImporter(session, checkpoint_path="seed_checkpoint.json")
        stats = await importer.import_all()
        print(f"导入完成: {stats}")
    await engine.dispose()


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("时间参数必须带时区，例如 2026-08-05T09:30:00+08:00")
    return parsed.astimezone(UTC)


async def run_live_pull(
    *,
    adapter_name: str,
    cursor: str | None,
    start_time: str | None,
    end_time: str | None,
    skip_healthcheck: bool,
) -> None:
    settings = get_settings()
    adapter = build_live_adapter(adapter_name, settings)
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            try:
                runtime_repository = SqlAlchemySourceRuntimeRepository(session)
                poster = IngestionApiClient(
                    base_url=settings.live_pull_api_base_url,
                    token=settings.ingestion_api_token,
                    transport=HttpTransport(
                        timeout_seconds=settings.live_pull_request_timeout_seconds
                    ),
                )
                runner = LivePullRunner(
                    adapter=adapter,
                    poster=poster,
                    runtime_repository=runtime_repository,
                    tenant_id=settings.ingestion_tenant_id,
                )
                summary = await runner.run(
                    cursor=cursor,
                    start_time=_parse_datetime(start_time),
                    end_time=_parse_datetime(end_time),
                    skip_healthcheck=skip_healthcheck,
                )
                await session.commit()
                print(json.dumps(summary.__dict__, ensure_ascii=False, indent=2))
            except Exception:
                await session.commit()
                raise
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="RiskTrace CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("import-seed", help="导入固定历史场景种子数据")
    pull_parser = subparsers.add_parser(
        "pull-live",
        help="拉取真实来源并通过 /api/v1/ingestion/items 入库",
    )
    pull_parser.add_argument(
        "--adapter",
        required=True,
        choices=available_live_adapter_names(),
        help="真实来源 adapter 名称",
    )
    pull_parser.add_argument("--cursor", help="覆盖数据库中的 checkpoint", default=None)
    pull_parser.add_argument(
        "--start-time",
        help="可选起始时间，必须带时区，例如 2026-08-05T09:30:00+08:00",
        default=None,
    )
    pull_parser.add_argument(
        "--end-time",
        help="可选结束时间，必须带时区，例如 2026-08-05T10:30:00+08:00",
        default=None,
    )
    pull_parser.add_argument(
        "--skip-healthcheck",
        action="store_true",
        help="跳过 adapter 预检查，直接拉取",
    )

    args = parser.parse_args()
    if args.command == "import-seed":
        asyncio.run(run_import())
    elif args.command == "pull-live":
        asyncio.run(
            run_live_pull(
                adapter_name=args.adapter,
                cursor=args.cursor,
                start_time=args.start_time,
                end_time=args.end_time,
                skip_healthcheck=args.skip_healthcheck,
            )
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
