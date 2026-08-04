import argparse
import asyncio

from risktrace.core.config import get_settings
from risktrace.db.session import create_db_engine, create_session_factory
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


def main() -> None:
    parser = argparse.ArgumentParser(description="RiskTrace CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("import-seed", help="导入固定历史场景种子数据")

    args = parser.parse_args()
    if args.command == "import-seed":
        asyncio.run(run_import())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
