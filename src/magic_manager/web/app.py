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
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from .. import api, sets as sets_mod, tabs as tabs_engine, undo as undo_engine, cart as cart_engine, deck_edit, edhrec as edhrec_engine, features as features_engine, scryfall
from ..api import deals as deals_api, undo as undo_api, cart as cart_api, cards as cards_api, collection as collection_api, explore as explore_api, decks as decks_api, edhrec as edhrec_api, ingest as ingest_api, jobs as jobs_api, market as market_api, trueup as trueup_api
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
    # One restore point, taken before the first write of each session.
    guard = undo_engine.SessionGuard()

    def write(label: str):
        return Depends(lambda: guard.before_write(label))

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
            spec = jobs_api.get(name)
            if spec.mutates:
                guard.before_write(f"before {spec.title.lower()}")
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

    # ---------- deals (internal) ----------

    @app.get("/api/deals/tabs", response_model=deals_api.OpenTabsOut, tags=["deals"])
    def deals_tabs(browser: Annotated[Literal["chrome", "safari"], Query()] = "chrome"):
        try:
            return deals_api.open_tabs(browser)
        except features_engine.FeatureDisabled as e:
            raise HTTPException(403, str(e)) from e
        except tabs_engine.TabsUnavailable as e:
            raise HTTPException(503, str(e)) from e

    @app.post("/api/deals/match", response_model=deals_api.PriceOut, tags=["deals"], dependencies=[write("before confirming a listing")])
    def deals_match(req: deals_api.ConfirmIn):
        try:
            return deals_api.confirm(req)
        except features_engine.FeatureDisabled as e:
            raise HTTPException(403, str(e)) from e

    @app.post("/api/deals/watch", response_model=deals_api.WatchOut, tags=["deals"], dependencies=[write("before watching a product")])
    def deals_watch(req: deals_api.WatchIn):
        try:
            return deals_api.watch(req)
        except features_engine.FeatureDisabled as e:
            raise HTTPException(403, str(e)) from e
        except (LookupError, ValueError) as e:
            raise HTTPException(422, str(e)) from e

    @app.delete("/api/deals/watch", response_model=deals_api.WatchOut, tags=["deals"], dependencies=[write("before unwatching a product")])
    def deals_unwatch(url: Annotated[str, Query(min_length=8)]):
        try:
            return deals_api.unwatch(url)
        except features_engine.FeatureDisabled as e:
            raise HTTPException(403, str(e)) from e

    @app.get("/api/deals/watched", response_model=list[deals_api.WatchedOut], tags=["deals"])
    def deals_watched():
        try:
            return deals_api.watched()
        except features_engine.FeatureDisabled as e:
            raise HTTPException(403, str(e)) from e

    # ---------- undo (one restore point) ----------

    @app.get("/api/undo", response_model=undo_api.UndoOut | None, tags=["undo"])
    def undo_info():
        return undo_api.info()

    @app.post("/api/undo/restore", response_model=undo_api.UndoOut, tags=["undo"])
    def undo_restore():
        try:
            return undo_api.restore()
        except undo_engine.UndoError as e:
            raise HTTPException(409, str(e)) from e

    # ---------- features + cart (internal) ----------

    @app.get("/api/features", response_model=cart_api.FeaturesOut, tags=["features"])
    def features_route():
        return cart_api.flags()

    @app.get("/api/cart/setup", response_model=cart_api.CartSetupOut, tags=["cart"])
    def cart_setup():
        try:
            return cart_api.setup()
        except features_engine.FeatureDisabled as e:
            raise HTTPException(403, str(e)) from e

    @app.post("/api/cart/check", response_model=cart_api.CartAuditOut, tags=["cart"])
    def cart_check(req: cart_api.CartIn):
        try:
            return cart_api.check(req)
        except features_engine.FeatureDisabled as e:
            raise HTTPException(403, str(e)) from e
        except (cart_engine.CartFormatError, LookupError) as e:
            raise HTTPException(422, str(e)) from e

    # ---------- market ----------

    @app.get("/api/market/products", response_model=market_api.FamilyProductsOut, tags=["market"])
    def market_products(code: Annotated[str, Query(min_length=2)]):
        try:
            return market_api.family_products(code)
        except LookupError as e:
            raise HTTPException(404, str(e)) from e

    @app.get("/api/market/value", response_model=market_api.ProductValueOut, tags=["market"])
    def market_value(set: Annotated[str, Query(min_length=2)], name: Annotated[str, Query(min_length=1)]):
        return market_api.value_product(set, name)

    @app.get("/api/market/product-tree", response_model=market_api.TreeNodeOut, tags=["market"])
    def market_product_tree(set: Annotated[str, Query(min_length=2)], name: Annotated[str, Query(min_length=1)]):
        try:
            return market_api.product_tree(set, name)
        except LookupError as e:
            raise HTTPException(404, str(e)) from e

    @app.get("/api/market/product-cost", response_model=market_api.ProductCostOut, tags=["market"])
    def market_product_cost(kind: Annotated[Literal["sealed", "sld"], Query()], set: Annotated[str, Query(min_length=2)],
                            name: Annotated[str, Query(min_length=1)], finish: Annotated[str | None, Query()] = None):
        try:
            return market_api.product_cost(kind, set, name, finish)
        except LookupError as e:
            raise HTTPException(404, str(e)) from e

    @app.get("/api/market/secret-lair", response_model=market_api.SldDropsOut, tags=["market"])
    def market_secret_lair(limit: Annotated[int, Query(ge=1, le=200)] = 30):
        try:
            return market_api.sld_drops(limit)
        except RuntimeError as e:  # MtgJsonError: the catalogue couldn't be read
            raise HTTPException(502, f"Couldn't list Secret Lair drops: {e}") from e

    @app.get("/api/market/cards", response_model=market_api.FamilyCardsOut, tags=["market"])
    def market_cards(code: Annotated[str, Query(min_length=2)]):
        try:
            return market_api.family_cards(code)
        except LookupError as e:
            raise HTTPException(404, str(e)) from e

    @app.get("/api/market/deck", response_model=market_api.DeckCostOut, tags=["market"])
    def market_deck(slug: Annotated[str, Query(min_length=1)]):
        try:
            return market_api.deck_cost(slug)
        except LookupError as e:
            raise HTTPException(404, str(e)) from e

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

    @app.post("/api/collection/checklist", response_model=collection_api.ChecklistOut, tags=["collection"], dependencies=[write("before saving a checklist")])
    def collection_checklist(body: collection_api.ChecklistIn):
        try:
            return collection_api.save_checklist(body)
        except sets_mod.StaleCounts as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        except sets_mod.BelowPledged as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

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

    @app.post("/api/decks", response_model=decks_api.ActionOut, status_code=201, tags=["decks"], dependencies=[write("before creating a deck")])
    def deck_create(body: decks_api.NewDeckIn):
        return _deck_call(decks_api.create, body)

    @app.post("/api/decks/import", response_model=decks_api.ImportOut, tags=["decks"], dependencies=[write("before importing a deck")])
    def deck_import(body: decks_api.ImportIn):
        return _deck_call(decks_api.import_deck, body)

    @app.get("/api/decks/{slug}/build-plan", response_model=decks_api.BuildPlanOut, tags=["decks"])
    def deck_build_plan(slug: str):
        return _deck_call(decks_api.build_plan, slug)

    @app.post("/api/decks/{slug}/build", response_model=decks_api.ActionOut, tags=["decks"], dependencies=[write("before building a deck")])
    def deck_build(slug: str, body: decks_api.BuildIn):
        return _deck_call(decks_api.build, slug, body)

    @app.post("/api/decks/{slug}/break-down", response_model=decks_api.ActionOut, tags=["decks"], dependencies=[write("before breaking down a deck")])
    def deck_break_down(slug: str):
        return _deck_call(decks_api.break_down, slug)

    @app.post("/api/decks/{slug}/copy", response_model=decks_api.ActionOut, status_code=201, tags=["decks"], dependencies=[write("before copying a deck")])
    def deck_copy(slug: str, body: decks_api.CopyIn):
        return _deck_call(decks_api.copy, slug, body)

    @app.post("/api/decks/{slug}/preview", response_model=decks_api.PreviewOut, tags=["decks"])
    def deck_preview(slug: str, body: decks_api.DraftIn):
        return _deck_call(decks_api.preview, slug, body)

    @app.post("/api/decks/{slug}/check", response_model=decks_api.CheckOut, tags=["decks"])
    def deck_check(slug: str, body: decks_api.CheckIn):
        return _deck_call(decks_api.check, slug, body)

    @app.put("/api/decks/{slug}", response_model=decks_api.SaveOut, tags=["decks"], dependencies=[write("before saving a deck")])
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

    @app.post("/api/ingest/commit", response_model=ingest_api.CommitOut, tags=["ingest"], dependencies=[write("before adding cards")])
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
