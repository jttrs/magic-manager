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


class ScanOut(BaseModel):
    ready: list[ProductOut] = Field(description="Products your loose cards fully cover.")
    conflicts: list[ConflictOut] = Field(description="Covered, but a shared card went to a higher-priority product.")
    applied: bool = False
    registered: int = 0
    reattributed: int = 0


class ScanInput(BaseModel):
    refute: list[str] = Field(default_factory=list, max_length=500, description="fileNames you did not buy.")
    picks: list[str] = Field(default_factory=list, max_length=500, description="fileNames to win contested cards.")


class ApplyInput(BaseModel):
    expect: list[str] = Field(min_length=1, max_length=500, description="fileNames the user reviewed and confirmed.")
    picks: list[str] = Field(default_factory=list, max_length=500, description="fileNames to win contested cards.")


def _out(result: dict) -> ScanOut:
    conflicts = [
        ConflictOut(**{k: v for k, v in c.items() if k != "lost"},
                    lost_to=sorted({w for lo in c.get("lost", []) for w in lo.get("lost_to", [])}))
        for c in result["conflicts"]
    ]
    return ScanOut(ready=[ProductOut(**p) for p in result["ready"]], conflicts=conflicts,
                   applied=bool(result.get("applied")), registered=result.get("registered", 0),
                   reattributed=result.get("reattributed", 0))


def _tick(progress: ProgressFn):
    return lambda i, n, name: progress(ProgressEvent(i, n, name))


def _run_scan(inp: ScanInput, progress: ProgressFn) -> JobResult:
    progress(ProgressEvent(0, None, "Reading product lists…"))
    out = _out(trueup.plan(refute=set(inp.refute), picks=set(inp.picks), progress=_tick(progress)))
    return JobResult(
        summary=f"{len(out.ready)} products your cards complete" + (f" · {len(out.conflicts)} lost a shared card" if out.conflicts else ""),
        artifacts=[Artifact(kind="json", label="scan", data=out.model_dump())],
    )


def _run_apply(inp: ApplyInput, progress: ProgressFn) -> JobResult:
    """Re-plan with the user's decisions and record only if the covered set is
    exactly what they reviewed — the collection may have changed since."""
    progress(ProgressEvent(0, None, "Checking the products again…"))
    keep, picks = set(inp.expect), set(inp.picks)
    preview = trueup.plan(only=keep, picks=picks, progress=_tick(progress))
    if {p["fileName"] for p in preview["ready"]} != keep:
        raise ValueError("Your cards changed since the scan — scan again and review the list.")
    out = _out(trueup.plan(only=keep, picks=picks, apply=True))
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
))

APPLY = register(JobSpec(
    name="trueup.apply",
    title="Record products",
    description="Record the reviewed products as bought, tracing their cards to them.",
    input_model=ApplyInput,
    run=_run_apply,
    mutates=True,
))
