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
import logging
import threading
import time
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from taskiq import InMemoryBroker

from .. import analytics
from ..analytics import catalog as analytics_catalog
from ..analytics import consent as analytics_consent
from ..api import jobs as jobs_api

log = logging.getLogger("magic_manager.web")

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
    error_code: str | None = None
    events: list[JobEvent] = field(default_factory=list, repr=False)
    # The submitting request's analytics context (request/session ids); never public.
    ctx: analytics.Context = field(default_factory=analytics.Context, repr=False)

    def public(self) -> dict:
        d = asdict(self)
        d.pop("events")
        d.pop("ctx")
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
                        inputs=inputs.model_dump(), ctx=analytics.current())
        self._jobs[rec.id] = rec
        self._trim()
        self._emit(rec, "status", {"status": rec.status})
        await self._task.kiq(rec.id)
        await asyncio.to_thread(analytics.record, "job.started", {"job": rec.name, "job_id": rec.id}, ctx=rec.ctx)
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

        t0 = time.monotonic()
        try:
            result = await asyncio.to_thread(body)
        except Exception as e:  # noqa: BLE001 — surface any job failure to the client
            rec.status, rec.finished_at = "failed", _now()
            log.exception("job %s (%s) failed", rec.id, rec.name)
            if analytics_consent.mode() == "hosted":
                # str(e)/traceback can carry SQL or paths: type only, detail stays in the log.
                rec.error = f"{type(e).__name__}: job failed (see server log)"
                trace = None
            else:
                rec.error = f"{type(e).__name__}: {e}"
                trace = traceback.format_exc(limit=5)
            rec.error_code = analytics_catalog.to_code(type(e).__name__)
            self._emit(rec, "error", {"error": rec.error, "code": rec.error_code, "trace": trace})
            self._emit(rec, "status", {"status": rec.status})
            await asyncio.to_thread(analytics.record, "job.failed", {
                "job": rec.name, "code": rec.error_code, "job_id": rec.id,
                "duration_ms": int((time.monotonic() - t0) * 1000)}, ctx=rec.ctx)
            return
        rec.status, rec.finished_at = "succeeded", _now()
        rec.summary = result.summary
        rec.artifacts = [asdict(a) for a in result.artifacts]
        self._emit(rec, "result", {"summary": rec.summary, "artifacts": rec.artifacts})
        self._emit(rec, "status", {"status": rec.status})
        await asyncio.to_thread(analytics.record, "job.succeeded", {
            "job": rec.name, "job_id": rec.id, "duration_ms": int((time.monotonic() - t0) * 1000)}, ctx=rec.ctx)

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
