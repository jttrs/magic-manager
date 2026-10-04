"""Typed, delivery-agnostic API over the ``magic_manager`` engine.

The third adapter's contract (sibling of ``cli.py`` and the skills): reads return
Pydantic models; long-running operations are registered :class:`~.jobs.JobSpec`
s (``typed inputs -> artifacts`` with a progress callback). No engine logic
lives here — every module only adapts an existing engine function.

Importing this package registers every job.
"""
from . import collection, edhrec, jobs, scryfall_tags  # noqa: F401  (registers jobs)

__all__ = ["collection", "edhrec", "jobs", "scryfall_tags"]
