"""FastAPI app: the web adapter over ``magic_manager.api``.

Routes only marshal — every computation is an ``api`` call. Read endpoints are
plain ``def`` (FastAPI runs them in a threadpool, matching the sync engine);
long-running work goes through the generic job chassis
(``POST /api/jobs/{name}`` → ``GET /api/jobs/{id}/events`` SSE).

When ``web/dist`` exists (``npm run build``), it is served as the SPA with an
index.html fallback so client-side routes deep-link.
"""
from __future__ import annotations

from collections.abc import AsyncIterable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from .. import api, deck_edit, edhrec as edhrec_engine, scryfall
from ..api import cards as cards_api, collection as collection_api, explore as explore_api, decks as decks_api, edhrec as edhrec_api, ingest as ingest_api, jobs as jobs_api
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
        yield
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
    def compare(a: Annotated[str, Query(min_length=1)], b: Annotated[str | None, Query(min_length=1)] = None):
        try:
            return edhrec_api.compare(a, b)
        except edhrec_engine.EdhrecError as e:
            raise HTTPException(422, str(e)) from e
        except scryfall.ScryfallError as e:
            raise HTTPException(502, f"Scryfall lookup failed: {e}") from e

    # ---------- explore ----------

    @app.get("/api/explore/search", response_model=list[explore_api.CardOptionOut], tags=["explore"])
    def explore_search(q: Annotated[str, Query(min_length=1)], limit: Annotated[int, Query(ge=1, le=50)] = 20):
        return explore_api.search(q, limit=limit)

    @app.get("/api/explore/card", response_model=explore_api.CardExploreOut, tags=["explore"])
    def explore_card(a: Annotated[str, Query(min_length=1)], b: Annotated[str | None, Query(min_length=1)] = None):
        try:
            return explore_api.card(a, b)
        except edhrec_engine.EdhrecError as e:
            raise HTTPException(422, str(e)) from e
        except scryfall.ScryfallError as e:
            raise HTTPException(502, f"Scryfall lookup failed: {e}") from e

    # ---------- collection ----------

    @app.get("/api/collection/families", response_model=list[collection_api.FamilyOption], tags=["collection"])
    def collection_families():
        return collection_api.families()

    @app.get("/api/collection", response_model=collection_api.CollectionOut, tags=["collection"])
    def collection(families: Annotated[list[str], Query(min_length=1)]):
        return collection_api.family_view(families)

    @app.post("/api/collection/buy-list", response_model=collection_api.BuyListOut, tags=["collection"])
    def collection_buy_list(body: collection_api.BuyListIn):
        return collection_api.buy_list(body)

    # ---------- decks ----------

    @app.get("/api/decks", response_model=list[decks_api.DeckSummaryOut], tags=["decks"])
    def deck_list():
        return decks_api.summaries()

    @app.get("/api/decks/{slug}", response_model=decks_api.DeckDetailOut, tags=["decks"])
    def deck_detail(slug: str):
        try:
            return decks_api.detail(slug)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    def _deck_call(fn, *args):
        try:
            return fn(*args)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except deck_edit.ReadOnlyDeck as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        except deck_edit.StaleDraft as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        except deck_edit.Shortfall as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    @app.post("/api/decks", response_model=decks_api.ActionOut, status_code=201, tags=["decks"])
    def deck_create(body: decks_api.NewDeckIn):
        return _deck_call(decks_api.create, body)

    @app.post("/api/decks/import", response_model=decks_api.ImportOut, tags=["decks"])
    def deck_import(body: decks_api.ImportIn):
        return _deck_call(decks_api.import_deck, body)

    @app.get("/api/decks/{slug}/build-plan", response_model=decks_api.BuildPlanOut, tags=["decks"])
    def deck_build_plan(slug: str):
        return _deck_call(decks_api.build_plan, slug)

    @app.post("/api/decks/{slug}/build", response_model=decks_api.ActionOut, tags=["decks"])
    def deck_build(slug: str, body: decks_api.BuildIn):
        return _deck_call(decks_api.build, slug, body)

    @app.post("/api/decks/{slug}/break-down", response_model=decks_api.ActionOut, tags=["decks"])
    def deck_break_down(slug: str):
        return _deck_call(decks_api.break_down, slug)

    @app.post("/api/decks/{slug}/copy", response_model=decks_api.ActionOut, status_code=201, tags=["decks"])
    def deck_copy(slug: str, body: decks_api.CopyIn):
        return _deck_call(decks_api.copy, slug, body)

    @app.post("/api/decks/{slug}/preview", response_model=decks_api.PreviewOut, tags=["decks"])
    def deck_preview(slug: str, body: decks_api.DraftIn):
        return _deck_call(decks_api.preview, slug, body)

    @app.post("/api/decks/{slug}/check", response_model=decks_api.CheckOut, tags=["decks"])
    def deck_check(slug: str, body: decks_api.CheckIn):
        return _deck_call(decks_api.check, slug, body)

    @app.put("/api/decks/{slug}", response_model=decks_api.SaveOut, tags=["decks"])
    def deck_save(slug: str, body: decks_api.SaveIn):
        return _deck_call(decks_api.save, slug, body)

    @app.get("/api/decks-suggestions", response_model=decks_api.SuggestionsOut, tags=["decks"])
    def deck_suggestions(commander: Annotated[str, Query(min_length=1)]):
        try:
            return decks_api.suggestions(commander)
        except edhrec_engine.EdhrecError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    # ---------- cards ----------

    @app.get("/api/cards/{scryfall_id}/holdings", response_model=cards_api.HoldingsOut, tags=["cards"])
    def card_holdings(scryfall_id: str):
        return cards_api.holdings(scryfall_id)

    # ---------- add cards (ingest) ----------

    @app.get("/api/ingest/search", response_model=ingest_api.SearchOut, tags=["ingest"])
    def ingest_search(q: Annotated[str, Query(min_length=2, max_length=120)], limit: Annotated[int, Query(ge=1, le=200)] = 60):
        return ingest_api.search(q, limit)

    @app.post("/api/ingest/resolve", response_model=ingest_api.ResolveOut, tags=["ingest"])
    def ingest_resolve(body: ingest_api.ResolveIn):
        return ingest_api.resolve(body)

    @app.post("/api/ingest/commit", response_model=ingest_api.CommitOut, tags=["ingest"])
    def ingest_commit(body: ingest_api.CommitIn):
        try:
            return ingest_api.commit(body)
        except LookupError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    @app.get("/api/ingest/precons", response_model=list[ingest_api.PreconOptionOut], tags=["ingest"])
    def ingest_precons(q: str = "", limit: Annotated[int, Query(ge=1, le=200)] = 50):
        return ingest_api.precons(q, limit)

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
