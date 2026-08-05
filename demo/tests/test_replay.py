from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT / "src"))

from risktrace_demo.dataset import ScenarioDataset  # noqa: E402
from risktrace_demo.models import ReplayState  # noqa: E402
from risktrace_demo.replay import (  # noqa: E402
    DemoReplayProvider,
    InvalidReplayTransition,
)
from risktrace_demo.sinks import (  # noqa: E402
    DeliveryError,
    DeliveryReceipt,
    HttpIngestionSink,
    TransportResponse,
)


def load_dataset() -> ScenarioDataset:
    return ScenarioDataset.load(DEMO_ROOT / "scenarios" / "deepseek-r1" / "manifest.json")


class CollectingSink:
    def __init__(self) -> None:
        self.deliveries: list[tuple[str, int]] = []

    async def send(self, record, *, replay_at, scenario_id, sequence):
        self.deliveries.append((record.external_id, sequence))
        return DeliveryReceipt(record.external_id, 201)


class FailingSink:
    async def send(self, record, *, replay_at, scenario_id, sequence):
        raise DeliveryError("source unavailable")


class ControlledSleeper:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def __call__(self, seconds: float) -> None:
        self.started.set()
        await self.release.wait()


async def no_sleep(seconds: float) -> None:
    return None


class DemoReplayProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_pause_blocks_next_delivery_until_resume(self) -> None:
        dataset = load_dataset()
        sink = CollectingSink()
        sleeper = ControlledSleeper()
        provider = DemoReplayProvider(dataset, sink, sleeper=sleeper)
        provider.set_speed(1)

        task = asyncio.create_task(provider.start())
        await sleeper.started.wait()
        self.assertEqual(len(sink.deliveries), 1)

        provider.pause()
        sleeper.release.set()
        await asyncio.sleep(0)
        self.assertEqual(provider.state, ReplayState.PAUSED)
        self.assertEqual(len(sink.deliveries), 1)

        provider.resume()
        await task
        self.assertEqual(provider.state, ReplayState.COMPLETED)
        self.assertEqual(len(sink.deliveries), len(dataset.records))

    async def test_failure_is_degraded_and_cursor_only_advances_after_success(self) -> None:
        dataset = load_dataset()
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            provider = DemoReplayProvider(
                dataset,
                FailingSink(),
                checkpoint_path=checkpoint,
                sleeper=no_sleep,
            )

            with self.assertRaises(DeliveryError):
                await provider.start()

            self.assertEqual(provider.state, ReplayState.DEGRADED)
            self.assertEqual(provider.cursor, 0)
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            self.assertEqual(saved["state"], "DEGRADED")
            self.assertIn("source unavailable", saved["last_error"])

            sink = CollectingSink()
            restored = DemoReplayProvider(
                dataset,
                sink,
                checkpoint_path=checkpoint,
                sleeper=no_sleep,
            )
            self.assertEqual(restored.state, ReplayState.STOPPED)
            await restored.start()
            self.assertEqual(restored.state, ReplayState.COMPLETED)
            self.assertEqual(len(sink.deliveries), len(dataset.records))

    async def test_seek_speed_reset_and_double_start_guard(self) -> None:
        dataset = load_dataset()
        sink = CollectingSink()
        sleeper = ControlledSleeper()
        provider = DemoReplayProvider(dataset, sink, sleeper=sleeper)
        provider.seek(2)
        provider.set_speed(25)

        task = asyncio.create_task(provider.start())
        await sleeper.started.wait()
        with self.assertRaises(InvalidReplayTransition):
            await provider.start()
        with self.assertRaises(InvalidReplayTransition):
            provider.reset()
        provider.stop()
        sleeper.release.set()
        await task

        self.assertEqual(provider.state, ReplayState.STOPPED)
        self.assertEqual(provider.cursor, 3)
        provider.reset()
        self.assertEqual(provider.cursor, 0)
        self.assertEqual(provider.interval_ms, 25)

    async def test_explicit_reset_replaces_a_stale_checkpoint(self) -> None:
        dataset = load_dataset()
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            checkpoint.write_text(
                json.dumps(
                    {
                        "scenario_id": dataset.manifest.id,
                        "dataset_fingerprint": "stale",
                        "cursor": 4,
                        "interval_ms": 5000,
                    }
                ),
                encoding="utf-8",
            )
            provider = DemoReplayProvider(
                dataset,
                CollectingSink(),
                checkpoint_path=checkpoint,
                sleeper=no_sleep,
                restore_checkpoint=False,
            )
            provider.reset()

            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            self.assertEqual(saved["cursor"], 0)
            self.assertEqual(saved["dataset_fingerprint"], dataset.fingerprint)


class HttpIngestionSinkTests(unittest.IsolatedAsyncioTestCase):
    async def test_documented_payload_and_duplicate_response(self) -> None:
        record = load_dataset().records[0]
        captured: list[dict] = []

        def transport(endpoint, body, timeout, idempotency_key):
            captured.append(json.loads(body))
            self.assertEqual(idempotency_key, record.external_id)
            return TransportResponse(200, b'{"outcome":"duplicate"}')

        sink = HttpIngestionSink(
            "http://127.0.0.1:8000/api/v1/ingestion/items",
            transport=transport,
        )
        replay_at = datetime(2026, 8, 5, 4, 0, tzinfo=UTC)
        receipt = await sink.send(
            record,
            replay_at=replay_at,
            scenario_id="deepseek-r1",
            sequence=0,
        )

        self.assertTrue(receipt.duplicate)
        self.assertEqual(captured[0]["replay_at"], "2026-08-05T04:00:00Z")
        self.assertNotIn("received_at", captured[0])
        self.assertEqual(captured[0]["source"]["stream"], "demo:deepseek-r1")
        forbidden = {"tenant_id", "event_id", "sentiment", "risk", "topic"}
        self.assertTrue(forbidden.isdisjoint(captured[0]))

    async def test_transient_status_retries_but_client_error_does_not(self) -> None:
        record = load_dataset().records[0]
        statuses = iter([503, 201])
        calls = 0

        def retrying_transport(endpoint, body, timeout, idempotency_key):
            nonlocal calls
            calls += 1
            return next(statuses)

        sink = HttpIngestionSink(
            "http://localhost/api/v1/ingestion/items",
            max_attempts=2,
            backoff_seconds=0,
            transport=retrying_transport,
        )
        await sink.send(
            record,
            replay_at=datetime.now(tz=UTC),
            scenario_id="deepseek-r1",
            sequence=0,
        )
        self.assertEqual(calls, 2)

        rejected_calls = 0

        def rejected_transport(endpoint, body, timeout, idempotency_key):
            nonlocal rejected_calls
            rejected_calls += 1
            return 409

        rejected_sink = HttpIngestionSink(
            "http://localhost/api/v1/ingestion/items",
            max_attempts=3,
            backoff_seconds=0,
            transport=rejected_transport,
        )
        with self.assertRaises(DeliveryError):
            await rejected_sink.send(
                record,
                replay_at=datetime.now(tz=UTC),
                scenario_id="deepseek-r1",
                sequence=0,
            )
        self.assertEqual(rejected_calls, 1)


if __name__ == "__main__":
    unittest.main()
