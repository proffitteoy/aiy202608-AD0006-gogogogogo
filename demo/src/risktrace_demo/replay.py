from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .dataset import ScenarioDataset
from .models import ReplayState, format_datetime
from .sinks import RecordSink

Clock = Callable[[], datetime]
Sleeper = Callable[[float], Awaitable[None]]


class InvalidReplayTransition(RuntimeError):
    pass


class DemoReplayProvider:
    def __init__(
        self,
        dataset: ScenarioDataset,
        sink: RecordSink,
        *,
        checkpoint_path: Path | None = None,
        clock: Clock | None = None,
        sleeper: Sleeper | None = None,
        restore_checkpoint: bool = True,
    ) -> None:
        self.dataset = dataset
        self.sink = sink
        self.checkpoint_path = checkpoint_path
        self.clock = clock or (lambda: datetime.now(tz=UTC))
        self.sleeper = sleeper or asyncio.sleep
        self.state = ReplayState.STOPPED
        self.cursor = 0
        self.interval_ms = dataset.manifest.replay.interval_ms
        self.last_external_id: str | None = None
        self.last_error: str | None = None
        self._active = False
        self._stop_requested = False
        self._resume_event = asyncio.Event()
        self._resume_event.set()
        if restore_checkpoint:
            self._restore_checkpoint()

    @property
    def total(self) -> int:
        return len(self.dataset.records)

    async def start(self) -> None:
        if self._active:
            raise InvalidReplayTransition("replay is already active")
        if self.cursor >= self.total:
            self.state = ReplayState.COMPLETED
            self._save_checkpoint()
            return

        self._active = True
        self._stop_requested = False
        self.last_error = None
        self.state = ReplayState.RUNNING
        self._resume_event.set()
        self._save_checkpoint()

        try:
            first_delivery = True
            while self.cursor < self.total and not self._stop_requested:
                await self._resume_event.wait()
                if not first_delivery:
                    await self.sleeper(self.interval_ms / 1000)
                    await self._resume_event.wait()
                if self._stop_requested:
                    break

                record = self.dataset.records[self.cursor]
                replay_at = self.clock()
                await self.sink.send(
                    record,
                    replay_at=replay_at,
                    scenario_id=self.dataset.manifest.id,
                    sequence=self.cursor,
                )
                self.last_external_id = record.external_id
                self.cursor += 1
                first_delivery = False
                self._save_checkpoint()

            if self.cursor >= self.total:
                self.state = ReplayState.COMPLETED
            elif self._stop_requested:
                self.state = ReplayState.STOPPED
            self._save_checkpoint()
        except asyncio.CancelledError:
            self.state = ReplayState.STOPPED
            self._save_checkpoint()
            raise
        except Exception as error:
            self.state = ReplayState.DEGRADED
            self.last_error = f"{type(error).__name__}: {error}"
            self._save_checkpoint()
            raise
        finally:
            self._active = False

    def pause(self) -> None:
        if not self._active or self.state is not ReplayState.RUNNING:
            raise InvalidReplayTransition("only a running replay can be paused")
        self.state = ReplayState.PAUSED
        self._resume_event.clear()
        self._save_checkpoint()

    def resume(self) -> None:
        if not self._active or self.state is not ReplayState.PAUSED:
            raise InvalidReplayTransition("only an active paused replay can be resumed")
        self.state = ReplayState.RUNNING
        self._resume_event.set()
        self._save_checkpoint()

    def stop(self) -> None:
        if not self._active or self.state not in {ReplayState.RUNNING, ReplayState.PAUSED}:
            raise InvalidReplayTransition("only an active replay can be stopped")
        self._stop_requested = True
        self.state = ReplayState.STOPPED
        self._resume_event.set()
        self._save_checkpoint()

    def reset(self) -> None:
        self._require_inactive("reset")
        self.cursor = 0
        self.last_external_id = None
        self.last_error = None
        self.state = ReplayState.STOPPED
        self._save_checkpoint()

    def seek(self, position: int) -> None:
        self._require_inactive("seek")
        if position < 0 or position > self.total:
            raise ValueError(f"seek position must be between 0 and {self.total}")
        self.cursor = position
        self.last_external_id = (
            self.dataset.records[position - 1].external_id if position > 0 else None
        )
        self.last_error = None
        self.state = ReplayState.COMPLETED if position == self.total else ReplayState.STOPPED
        self._save_checkpoint()

    def set_speed(self, interval_ms: int) -> None:
        if interval_ms <= 0:
            raise ValueError("interval_ms must be positive")
        self.interval_ms = interval_ms
        self._save_checkpoint()

    def status(self) -> dict[str, Any]:
        return {
            "scenario_id": self.dataset.manifest.id,
            "state": self.state.value,
            "cursor": self.cursor,
            "total": self.total,
            "interval_ms": self.interval_ms,
            "last_external_id": self.last_external_id,
            "last_error": self.last_error,
            "dataset_fingerprint": self.dataset.fingerprint,
        }

    def _require_inactive(self, operation: str) -> None:
        if self._active:
            raise InvalidReplayTransition(f"cannot {operation} while replay is active")

    def _restore_checkpoint(self) -> None:
        if self.checkpoint_path is None or not self.checkpoint_path.is_file():
            return
        raw = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        if raw.get("scenario_id") != self.dataset.manifest.id:
            raise ValueError("checkpoint belongs to a different scenario")
        if raw.get("dataset_fingerprint") != self.dataset.fingerprint:
            raise ValueError("checkpoint dataset fingerprint does not match current records")
        cursor = raw.get("cursor")
        if not isinstance(cursor, int) or not 0 <= cursor <= self.total:
            raise ValueError("checkpoint cursor is invalid")
        interval_ms = raw.get("interval_ms")
        if not isinstance(interval_ms, int) or interval_ms <= 0:
            raise ValueError("checkpoint interval_ms is invalid")
        self.cursor = cursor
        self.interval_ms = interval_ms
        self.last_external_id = raw.get("last_external_id")
        self.last_error = raw.get("last_error")
        self.state = ReplayState.COMPLETED if cursor == self.total else ReplayState.STOPPED

    def _save_checkpoint(self) -> None:
        if self.checkpoint_path is None:
            return
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.checkpoint_path.with_suffix(self.checkpoint_path.suffix + ".tmp")
        payload = {
            **self.status(),
            "updated_at": format_datetime(self.clock()),
        }
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary_path.replace(self.checkpoint_path)
