"""Product coverage surface of the typed API: which products your loose cards
came from (scene boxes, precon / jumpstart decks, land packs, complete Secret
Lair drops), reviewed and recorded from the web.

Adapts :mod:`magic_manager.trueup`. Both operations are jobs: the scan reads
every candidate decklist (slow the first time), and recording writes provenance.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .. import trueup
from .jobs import Artifact, JobResult, JobSpec, ProgressEvent, ProgressFn, register


class ProductOut(BaseModel):
    fileName: str
    name: str
    type: str | None = None
    code: str | None = None
    release_date: str | None = None
    recipe_qty: int = Field(description="Cards in the product's list.")
    usd: float = Field(description="Its cards at local market prices.")


class ConflictOut(ProductOut):
    lost_to: list[str] = Field(default_factory=list, description="Products that took the shared cards.")


class UnreadOut(BaseModel):
    ref: str = Field(description="fileName, or set:<code> / sld for a whole list of products.")
    name: str
    error: str


class ScanOut(BaseModel):
    ready: list[ProductOut] = Field(description="Products your loose cards fully cover.")
    conflicts: list[ConflictOut] = Field(description="Covered, but a shared card went to a higher-priority product.")
    unread: list[UnreadOut] = Field(default_factory=list, description="Product lists that couldn't be read, so weren't checked.")
    applied: bool = False
    registered: int = 0
    reattributed: int = 0


class ScanInput(BaseModel):
    refute: list[str] = Field(default_factory=list, max_length=500, description="fileNames you did not buy.")
    picks: list[str] = Field(default_factory=list, max_length=500, description="fileNames to win contested cards; the latest wins between picks.")


class ApplyInput(BaseModel):
    expect: list[str] = Field(min_length=1, max_length=500, description="fileNames the user reviewed and confirmed.")
    picks: list[str] = Field(default_factory=list, max_length=500, description="fileNames to win contested cards; the latest wins between picks.")


def _out(result: dict) -> ScanOut:
    conflicts = [
        ConflictOut(**{k: v for k, v in c.items() if k != "lost"},
                    lost_to=sorted({w for lo in c.get("lost", []) for w in lo.get("lost_to", [])}))
        for c in result["conflicts"]
    ]
    return ScanOut(ready=[ProductOut(**p) for p in result["ready"]], conflicts=conflicts,
                   unread=[UnreadOut(**u) for u in result.get("unread", [])],
                   applied=bool(result.get("applied")), registered=result.get("registered", 0),
                   reattributed=result.get("reattributed", 0))


def _tick(progress: ProgressFn):
    return lambda i, n, name: progress(ProgressEvent(i, n, name))


def _run_scan(inp: ScanInput, progress: ProgressFn) -> JobResult:
    progress(ProgressEvent(0, None, "Reading product lists…"))
    out = _out(trueup.plan(refute=set(inp.refute), picks=inp.picks, progress=_tick(progress)))
    return JobResult(
        summary=f"{len(out.ready)} products your cards complete"
        + (f" · {len(out.conflicts)} lost a shared card" if out.conflicts else "")
        + (f" · {len(out.unread)} lists could not be read" if out.unread else ""),
        artifacts=[Artifact(kind="json", label="scan", data=out.model_dump())],
    )


def _check_reviewed(preview: dict, keep: set[str]) -> None:
    """Refuse unless the re-check covers exactly the reviewed products — naming
    unreadable lists rather than blaming a collection change on them."""
    ready = {p["fileName"] for p in preview["ready"]}
    if ready == keep:
        return
    missing = keep - ready
    # A missing product is explained by its own unread list, or by a whole list
    # of products (a set's, or the Secret Lair drops) that couldn't be read.
    unread = [u for u in preview.get("unread") or []
              if u["ref"] in missing or u["ref"] == "sld" or u["ref"].startswith("set:")]
    if missing and unread:
        names = ", ".join(u["name"] for u in unread[:3]) + ("…" if len(unread) > 3 else "")
        raise ValueError(f"Couldn’t read the product lists again ({names}) — nothing was recorded. Try again in a moment.")
    raise ValueError("Your cards changed since the scan — scan again and review the list.")


def _run_apply(inp: ApplyInput, progress: ProgressFn) -> JobResult:
    """Re-plan with the user's decisions and record only if the covered set is
    exactly what they reviewed — the collection may have changed since."""
    progress(ProgressEvent(0, None, "Checking the products again…"))
    keep, picks = set(inp.expect), inp.picks
    preview = trueup.plan(only=keep, picks=picks, progress=_tick(progress))
    _check_reviewed(preview, keep)
    out = _out(trueup.plan(only=keep, picks=picks, apply=True, require=keep))
    return JobResult(
        summary=f"Recorded {out.registered} products · {out.reattributed} cards now traced to them",
        artifacts=[Artifact(kind="json", label="scan", data=out.model_dump())],
    )


SCAN = register(JobSpec(
    name="trueup.scan",
    title="Find products in your cards",
    description="Match your loose cards to the products they came from (read-only).",
    input_model=ScanInput,
    run=_run_scan,
    scope="user",
))

APPLY = register(JobSpec(
    name="trueup.apply",
    title="Record products",
    description="Record the reviewed products as bought, tracing their cards to them.",
    input_model=ApplyInput,
    run=_run_apply,
    mutates=True,
    scope="user",
))
