import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
from time import perf_counter

import boto3
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from risktrace.core.config import Settings


@dataclass(frozen=True)
class DependencyCheck:
    status: str
    latency_ms: float
    detail: str | None = None


class InfrastructureHealthService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._database: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
        )
        self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self._s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )

    async def readiness(self) -> dict[str, DependencyCheck]:
        database, redis, object_storage = await asyncio.gather(
            self._measure(self._check_database),
            self._measure(self._check_redis),
            self._measure(self._check_object_storage),
        )
        return {
            "database": database,
            "redis": redis,
            "object_storage": object_storage,
        }

    async def close(self) -> None:
        await self._database.dispose()
        await self._redis.aclose()

    async def _measure(self, check: Callable[[], Awaitable[None]]) -> DependencyCheck:
        started_at = perf_counter()
        try:
            async with asyncio.timeout(self._settings.healthcheck_timeout_seconds):
                await check()
        except Exception as exc:  # dependency failures are returned as explicit degraded state
            return DependencyCheck(
                status="down",
                latency_ms=round((perf_counter() - started_at) * 1000, 2),
                detail=type(exc).__name__,
            )
        return DependencyCheck(
            status="up",
            latency_ms=round((perf_counter() - started_at) * 1000, 2),
        )

    async def _check_database(self) -> None:
        async with self._database.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def _check_redis(self) -> None:
        if not await self._redis.ping():
            raise RuntimeError("Redis ping returned a false response")

    async def _check_object_storage(self) -> None:
        await asyncio.to_thread(
            partial(self._s3.head_bucket, Bucket=self._settings.s3_bucket)
        )
