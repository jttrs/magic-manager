"""Job runtime: enqueue a registered JobSpec, track its lifecycle, fan progress out.

Execution goes through a Taskiq broker (``InMemoryBroker`` for the local,
single-process app; swap for a Redis broker + a shared store in the multi-user
phase without touching job code). The engine is synchronous and SQLite-backed,
so each job body runs in a worker thread and jobs are serialized (one writer).

Users (§25.3): a job records the user bound when it was submitted (the signed-in
user in hosted mode; ``None`` locally) and its worker binds that user, so its
connection opens that user's file. A job is visible (get / list / events) only
in a context bound to the same user. All jobs share ONE run lock, which
serializes writes per user file AND catalog syncs globally (H8) — strictly more
than required, and simple. The user-data lock (mutating jobs vs. Undo) is per user.

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
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from taskiq import InMemoryBroker

from .. import analytics
from .. import layout as _layout
from ..analytics import catalog as analytics_catalog
from ..analytics import consent as analytics_consent
from ..api import jobs as jobs_api

log = logging.getLogger("magic_manager.web")


def _mutates(name: str) -> bool:
    try:
        return bool(getattr(jobs_api.get(name), "mutates", False))
    except KeyError:
        return False


class JobsBusy(RuntimeError):
    """A (mutating) job is queued or running, or the user's account is being deleted."""

    def __init__(self, title: str) -> None:
        super().__init__(title)
        self.title = title

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
    # Whose data the job reads and writes (the bound user at submit); never public.
    user: str | None = field(default=None, repr=False)

    def public(self) -> dict:
        d = asdict(self)
        d.pop("events")
        d.pop("ctx")
        d.pop("user")
        return d


class JobManager:
    def __init__(self, *, max_history: int = 200) -> None:
        self.broker = InMemoryBroker()
        self._jobs: dict[str, JobRecord] = {}
        self._subs: dict[str, list[asyncio.Queue]] = {}
        self._run_lock = threading.Lock()     # SQLite: one writer at a time (every user + the catalog)
        # Per user: held while that user's mutating job runs and while their Undo
        # restores — a job must never write on top of (or underneath) a restore.
        self._user_locks: dict[str | None, threading.Lock] = {}
        self._user_locks_guard = threading.Lock()
        self._closing: set[str | None] = set()   # users whose account is being deleted
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
                        inputs=inputs.model_dump(), ctx=analytics.current(), user=_layout.bound_user())
        with self._user_locks_guard:  # atomic with closing_user's mark + scan
            if rec.user in self._closing:
                raise JobsBusy("deleting your account")
            self._jobs[rec.id] = rec
        self._trim()
        self._emit(rec, "status", {"status": rec.status})
        await self._task.kiq(rec.id)
        await asyncio.to_thread(analytics.record, "job.started", {"job": rec.name, "job_id": rec.id}, ctx=rec.ctx)
        return rec

    def _user_lock(self, user: str | None) -> threading.Lock:
        with self._user_locks_guard:
            return self._user_locks.setdefault(user, threading.Lock())

    @contextmanager
    def no_mutating_jobs(self) -> Iterator[None]:
        """Hold off the bound user's mutating jobs for the body; :class:`JobsBusy`
        if one is queued or running (so its writes can't land on top of the body's)."""
        user = _layout.bound_user()
        lock = self._user_lock(user)
        if not lock.acquire(blocking=False):
            raise JobsBusy(self._busy_title(user) or "a job")
        try:
            title = self._busy_title(user)
            if title:
                raise JobsBusy(title)
            yield
        finally:
            lock.release()

    @contextmanager
    def closing_user(self, user: str) -> Iterator[None]:
        """Account deletion: :class:`JobsBusy` if ANY job of ``user`` is queued or
        running; for the body, that user can't submit a job (and their mutating
        jobs can't start)."""
        lock = self._user_lock(user)
        if not lock.acquire(blocking=False):
            raise JobsBusy(self._busy_title(user, any_job=True) or "a job")
        try:
            with self._user_locks_guard:
                self._closing.add(user)
                title = self._busy_title(user, any_job=True)
            if title:
                raise JobsBusy(title)
            yield
        finally:
            with self._user_locks_guard:
                self._closing.discard(user)
            lock.release()

    def _busy_title(self, user: str | None, *, any_job: bool = False) -> str:
        for r in list(self._jobs.values()):  # snapshot: the loop thread may add jobs
            if r.user == user and r.status in ("queued", "running") and (any_job or _mutates(r.name)):
                return r.title
        return ""

    def get(self, job_id: str) -> JobRecord:
        """The job, if the user bound to this context started it (KeyError otherwise,
        so another user's job is indistinguishable from an unknown one)."""
        rec = self._jobs[job_id]
        if rec.user != _layout.bound_user():
            raise KeyError(job_id)
        return rec

    def list(self) -> list[JobRecord]:
        """The bound user's jobs, newest first."""
        user = _layout.bound_user()
        return sorted((r for r in list(self._jobs.values()) if r.user == user),
                      key=lambda r: r.created_at, reverse=True)

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
            mutating = getattr(spec, "mutates", False)
            with self._run_lock, (self._user_lock(rec.user) if mutating else nullcontext()), _layout.as_user(rec.user):
                rec.status, rec.started_at = "running", _now()
                self._emit(rec, "status", {"status": rec.status})
                return spec.run(inputs, progress)

        t0 = time.monotonic()
        try:
            result = await asyncio.to_thread(body)
        except Exception as e:  # noqa: BLE001 — surface any job failure to the client
            rec.status, rec.finished_at = "failed", _now()
            log.exception("job %s (%s) failed", rec.id, rec.name)
            coded = getattr(type(e), "error_code", None)  # e.g. owner_machine.OwnerOnly: a plain, safe message
            if isinstance(coded, str):
                rec.error, trace = str(e), None
            elif analytics_consent.mode() == "hosted":
                # str(e)/traceback can carry SQL or paths: type only, detail stays in the log.
                rec.error = f"{type(e).__name__}: job failed (see server log)"
                trace = None
            else:
                rec.error = f"{type(e).__name__}: {e}"
                trace = traceback.format_exc(limit=5)
            rec.error_code = coded if isinstance(coded, str) else analytics_catalog.to_code(type(e).__name__)
            self._emit(rec, "error", {"error": rec.error, "code": rec.error_code, "trace": trace})
            # Recorded before the terminal status: that event ends every SSE stream, so a client
            # that has seen the job finish can rely on its job.* record being there.
            try:
                await asyncio.to_thread(analytics.record, "job.failed", {
                    "job": rec.name, "code": rec.error_code, "job_id": rec.id,
                    "duration_ms": int((time.monotonic() - t0) * 1000)}, ctx=rec.ctx)
            finally:
                self._emit(rec, "status", {"status": rec.status})
            return
        rec.status, rec.finished_at = "succeeded", _now()
        rec.summary = result.summary
        rec.artifacts = [asdict(a) for a in result.artifacts]
        self._emit(rec, "result", {"summary": rec.summary, "artifacts": rec.artifacts})
        try:
            await asyncio.to_thread(analytics.record, "job.succeeded", {
                "job": rec.name, "job_id": rec.id, "duration_ms": int((time.monotonic() - t0) * 1000)}, ctx=rec.ctx)
        finally:
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
        rec = self.get(job_id)
        with self._events_lock:
            return rec.events[seq:]

    def _trim(self) -> None:
        # Per user: one user's many jobs never push another's out of history.
        kept: dict[str | None, int] = {}
        done = sorted((r for r in list(self._jobs.values()) if r.status in TERMINAL),
                      key=lambda r: r.created_at, reverse=True)
        for r in done:
            kept[r.user] = kept.get(r.user, 0) + 1
            if kept[r.user] <= self._max_history:
                continue
            self._jobs.pop(r.id, None)
            self._subs.pop(r.id, None)
