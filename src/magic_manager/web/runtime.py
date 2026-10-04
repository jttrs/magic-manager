"""Job runtime: enqueue a registered JobSpec, track its lifecycle, fan progress out.

Execution goes through a Taskiq broker (``InMemoryBroker`` for the local,
single-process app; swap for a Redis broker + a shared store in the multi-user
phase without touching job code). The engine is synchronous and SQLite-backed,
so each job body runs in a worker thread and jobs are serialized (one writer).

Progress fan-out: the job's ``events`` history is the single source of truth.
Every event is appended under a lock at the moment it is produced (from any
thread), which fixes its ``seq`` in true order. Subscriber queues carry only
wake-up signals; an SSE stream re-reads history from its last ``seq`` — so a
late or reconnecting subscriber replays from ``Last-Event-ID`` and cross-thread
delivery order can never reorder events.
"""
from __future__ import annotations

import asyncio
import threading
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from taskiq import InMemoryBroker

from ..api import jobs as jobs_api

Status = Literal["queued", "running", "succeeded", "failed"]
TERMINAL: frozenset[str] = frozenset({"succeeded", "failed"})


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class JobEvent:
    seq: int
    type: Literal["status", "progress", "result", "error"]
    data: dict


@dataclass
class JobRecord:
    id: str
    name: str
    title: str
    inputs: dict
    status: Status = "queued"
    created_at: str = field(default_factory=_now)
    started_at: str | None = None
    finished_at: str | None = None
    progress: dict | None = None
    summary: str | None = None
    artifacts: list[dict] = field(default_factory=list)
    error: str | None = None
    events: list[JobEvent] = field(default_factory=list, repr=False)

    def public(self) -> dict:
        d = asdict(self)
        d.pop("events")
        return d


class JobManager:
    def __init__(self, *, max_history: int = 200) -> None:
        self.broker = InMemoryBroker()
        self._jobs: dict[str, JobRecord] = {}
        self._subs: dict[str, list[asyncio.Queue]] = {}
        self._run_lock = threading.Lock()     # SQLite: one writer at a time
        self._events_lock = threading.Lock()  # orders event seqs across threads
        self._max_history = max_history
        self._loop: asyncio.AbstractEventLoop | None = None

        async def run_job(job_id: str) -> None:
            await self._execute(job_id)

        self._task = self.broker.register_task(run_job, task_name="mm.run_job")

    # ---------- lifecycle ----------

    async def startup(self) -> None:
        self._loop = asyncio.get_running_loop()
        await self.broker.startup()

    async def shutdown(self) -> None:
        await self.broker.shutdown()

    # ---------- public API ----------

    async def submit(self, name: str, raw_inputs: dict) -> JobRecord:
        spec = jobs_api.get(name)                       # KeyError → 404
        inputs = spec.input_model.model_validate(raw_inputs)  # ValidationError → 422
        rec = JobRecord(id=uuid.uuid4().hex, name=spec.name, title=spec.title,
                        inputs=inputs.model_dump())
        self._jobs[rec.id] = rec
        self._trim()
        self._emit(rec, "status", {"status": rec.status})
        await self._task.kiq(rec.id)
        return rec

    def get(self, job_id: str) -> JobRecord:
        return self._jobs[job_id]

    def list(self) -> list[JobRecord]:
        return sorted(self._jobs.values(), key=lambda r: r.created_at, reverse=True)

    def subscribe(self, job_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.setdefault(job_id, []).append(q)
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue) -> None:
        subs = self._subs.get(job_id, [])
        if q in subs:
            subs.remove(q)

    # ---------- execution ----------

    async def _execute(self, job_id: str) -> None:
        rec = self._jobs[job_id]
        spec = jobs_api.get(rec.name)
        inputs = spec.input_model.model_validate(rec.inputs)

        def progress(ev: jobs_api.ProgressEvent) -> None:
            rec.progress = asdict(ev)
            self._emit(rec, "progress", rec.progress)

        def body() -> jobs_api.JobResult:
            with self._run_lock:
                rec.status, rec.started_at = "running", _now()
                self._emit(rec, "status", {"status": rec.status})
                return spec.run(inputs, progress)

        try:
            result = await asyncio.to_thread(body)
        except Exception as e:  # noqa: BLE001 — surface any job failure to the client
            rec.status, rec.finished_at = "failed", _now()
            rec.error = f"{type(e).__name__}: {e}"
            self._emit(rec, "error", {"error": rec.error, "trace": traceback.format_exc(limit=5)})
            self._emit(rec, "status", {"status": rec.status})
            return
        rec.status, rec.finished_at = "succeeded", _now()
        rec.summary = result.summary
        rec.artifacts = [asdict(a) for a in result.artifacts]
        self._emit(rec, "result", {"summary": rec.summary, "artifacts": rec.artifacts})
        self._emit(rec, "status", {"status": rec.status})

    # ---------- fan-out ----------

    def _emit(self, rec: JobRecord, type_: str, data: dict[str, Any]) -> None:
        with self._events_lock:
            rec.events.append(JobEvent(seq=len(rec.events) + 1, type=type_, data=data))  # type: ignore[arg-type]
        for q in list(self._subs.get(rec.id, [])):
            self._wake(q)

    def _wake(self, q: asyncio.Queue) -> None:
        try:
            on_app_loop = asyncio.get_running_loop() is self._loop
        except RuntimeError:
            on_app_loop = False
        if self._loop is None or on_app_loop:
            q.put_nowait(None)
        else:
            self._loop.call_soon_threadsafe(q.put_nowait, None)

    def events_after(self, job_id: str, seq: int) -> list[JobEvent]:
        rec = self._jobs[job_id]
        with self._events_lock:
            return rec.events[seq:]

    def _trim(self) -> None:
        done = [r for r in self.list() if r.status in TERMINAL]
        for r in done[self._max_history:]:
            self._jobs.pop(r.id, None)
            self._subs.pop(r.id, None)
