"""Scryfall Tagger surface of the typed API: the tag-cache sync job.

Thin adapter over :mod:`magic_manager.scryfall_tags` — no engine logic here.
"""
from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel, Field

from .. import scryfall_tags
from .jobs import Artifact, JobResult, JobSpec, ProgressEvent, ProgressFn, register


class SyncTagsInput(BaseModel):
    """Refresh the local Scryfall Tagger tag cache (oracle + art)."""
    refresh: bool = Field(False, description="Re-check Scryfall's bulk listing and rewrite even if current.")


def _run_sync_tags(inp: SyncTagsInput, progress: ProgressFn) -> JobResult:
    steps = 0

    def _say(msg: str) -> None:
        nonlocal steps
        steps += 1
        progress(ProgressEvent(steps, None, msg))

    results = scryfall_tags.sync_kinds(refresh=inp.refresh, progress=_say)
    summary = " · ".join(
        f"{name}: {r.tags} tags/{r.taggings} taggings "
        f"({'already current' if r.skipped else 'synced'})" for name, r in results.items())
    return JobResult(summary=summary, artifacts=[
        Artifact(kind="json", label="result", data={**asdict(results["oracle"]),
                                                   **{n: asdict(r) for n, r in results.items() if n != "oracle"}}),
    ])


SYNC_TAGS = register(JobSpec(
    name="scryfall.sync_tags",
    title="Sync Scryfall tags",
    description="Download Scryfall's official oracle_tags + art_tags bulk files and rebuild the local Tagger cache.",
    input_model=SyncTagsInput,
    run=_run_sync_tags,
))
