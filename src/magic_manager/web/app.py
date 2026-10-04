"""FastAPI app: the web adapter over ``magic_manager.api``.

Routes only marshal — every computation is an ``api`` call. Read endpoints are
plain ``def`` (FastAPI runs them in a threadpool, matching the sync engine);
long-running work goes through the generic job chassis
(``POST /api/jobs/{name}`` → ``GET /api/jobs/{id}/events`` SSE).

When ``web/dist`` exists (``npm run build``), it is served as the SPA with an
index.html fallback so client-side routes deep-link.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from .. import api, edhrec as edhrec_engine, scryfall
from ..api import card_diff as card_diff_api, edhrec as edhrec_api, jobs as jobs_api
from .runtime import TERMINAL, JobManager

REPO_ROOT = Path(__file__).resolve().parents[3]
DIST_DIR = REPO_ROOT / "web" / "dist"


class JobSpecOut(BaseModel):
    name: str
    title: str
    description: str
    mutates: bool
    input_schema: dict


class JobOut(BaseModel):
    id: str
    name: str
    title: str
    inputs: dict
    status: str
    created_at: str
    started_at: str | None
    finished_at: str | None
    progress: dict | None
    summary: str | None
    artifacts: list[dict]
    error: str | None


def create_app(*, serve_frontend: bool = True) -> FastAPI:
    manager = JobManager()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await manager.startup()
        # Warm the slow family list off the request path (best-effort).
        warm = asyncio.create_task(asyncio.to_thread(card_diff_api.families))
        yield
        warm.cancel()
        await manager.shutdown()

    app = FastAPI(title="magic-manager", version="0.1.0", lifespan=lifespan,
                  generate_unique_id_function=lambda route: route.name)
    app.state.jobs = manager
    assert api  # registers jobs

    # ---------- jobs chassis ----------

    @app.get("/api/jobs/specs", response_model=list[JobSpecOut], tags=["jobs"])
    def job_specs():
        return [
            JobSpecOut(name=s.name, title=s.title, description=s.description,
                       mutates=s.mutates, input_schema=s.input_model.model_json_schema())
            for s in jobs_api.all_specs()
        ]

    @app.post("/api/jobs/{name}", response_model=JobOut, status_code=202, tags=["jobs"])
    async def submit_job(name: str, body: dict):
        try:
            rec = await manager.submit(name, body)
        except KeyError as e:
            raise HTTPException(404, str(e)) from e
        except ValidationError as e:
            raise HTTPException(422, e.errors(include_url=False, include_context=False)) from e
        return rec.public()

    @app.get("/api/jobs", response_model=list[JobOut], tags=["jobs"])
    def list_jobs():
        return [r.public() for r in manager.list()]

    @app.get("/api/jobs/{job_id}", response_model=JobOut, tags=["jobs"])
    def get_job(job_id: str):
        try:
            return manager.get(job_id).public()
        except KeyError as e:
            raise HTTPException(404, f"unknown job {job_id!r}") from e

    @app.get("/api/jobs/{job_id}/events", response_class=EventSourceResponse, tags=["jobs"])
    async def job_events(job_id: str, request: Request) -> AsyncIterable[ServerSentEvent]:
        try:
            manager.get(job_id)
        except KeyError as e:
            raise HTTPException(404, f"unknown job {job_id!r}") from e
        seen = int(request.headers.get("last-event-id") or 0)
        q = manager.subscribe(job_id)  # subscribe BEFORE reading history: no missed wake-ups
        try:
            # History is the source of truth; the queue only signals "new events".
            # Replays everything after Last-Event-ID, then streams until the
            # terminal status event.
            while True:
                for ev in manager.events_after(job_id, seen):
                    seen = ev.seq
                    yield ServerSentEvent(data=ev.data, event=ev.type, id=str(ev.seq))
                    if ev.type == "status" and ev.data.get("status") in TERMINAL:
                        return  # the terminal status is always the final event
                await q.get()
        finally:
            manager.unsubscribe(job_id, q)

    # ---------- EDHREC ----------

    @app.get("/api/edhrec/commanders", response_model=list[edhrec_api.CommanderOption], tags=["edhrec"])
    def commanders(q: Annotated[str, Query(min_length=1)], limit: int = 20):
        return edhrec_api.search_commanders(q, limit=limit)

    @app.get("/api/edhrec/compare", response_model=edhrec_api.CompareOut, tags=["edhrec"])
    def compare(a: Annotated[str, Query(min_length=1)], b: Annotated[str, Query(min_length=1)]):
        try:
            return edhrec_api.compare(a, b)
        except edhrec_engine.EdhrecError as e:
            raise HTTPException(422, str(e)) from e
        except scryfall.ScryfallError as e:
            raise HTTPException(502, f"Scryfall lookup failed: {e}") from e

    # ---------- card diff ----------

    @app.get("/api/card-diff/families", response_model=list[card_diff_api.FamilyOption], tags=["card-diff"])
    def card_diff_families():
        return card_diff_api.families()

    @app.get("/api/card-diff", response_model=card_diff_api.CardDiffOut, tags=["card-diff"])
    def card_diff(
        families: Annotated[list[str], Query(min_length=1)],
        pools: Annotated[list[card_diff_api.PoolKey] | None, Query()] = None,
        chase: card_diff_api.ChaseMode = "exclude",
    ):
        return card_diff_api.diff(families, pools=pools, chase=chase)

    # ---------- SPA ----------

    if serve_frontend and DIST_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404)
            f = DIST_DIR / path
            if path and f.is_file() and DIST_DIR in f.resolve().parents:
                return FileResponse(f)
            return FileResponse(DIST_DIR / "index.html")

    return app
