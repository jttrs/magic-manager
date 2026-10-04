"""Scryfall Tagger surface of the typed API: the tag-cache sync job.

Thin adapter over :mod:`magic_manager.scryfall_tags` — no engine logic here.
"""
from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel, Field

from .. import scryfall_tags
from .jobs import Artifact, JobResult, JobSpec, ProgressEvent, ProgressFn, register


class SyncTagsInput(BaseModel):
    """Refresh the local Scryfall Tagger oracle-tag cache."""
    refresh: bool = Field(False, description="Re-check Scryfall's bulk listing and rewrite even if current.")


def _run_sync_tags(inp: SyncTagsInput, progress: ProgressFn) -> JobResult:
    steps = 0

    def _say(msg: str) -> None:
        nonlocal steps
        steps += 1
        progress(ProgressEvent(steps, None, msg))

    res = scryfall_tags.sync(refresh=inp.refresh, progress=_say)
    state = "already current" if res.skipped else "synced"
    summary = f"{res.tags} tags · {res.taggings} taggings · {state} ({res.source})"
    return JobResult(summary=summary, artifacts=[
        Artifact(kind="json", label="result", data=asdict(res)),
    ])


SYNC_TAGS = register(JobSpec(
    name="scryfall.sync_tags",
    title="Sync Scryfall tags",
    description="Download Scryfall's official oracle_tags bulk file and rebuild the local Tagger cache.",
    input_model=SyncTagsInput,
    run=_run_sync_tags,
))
