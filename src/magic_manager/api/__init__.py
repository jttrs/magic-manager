"""Typed, delivery-agnostic API over the ``magic_manager`` engine.

The third adapter's contract (sibling of ``cli.py`` and the skills): reads return
Pydantic models; long-running operations are registered :class:`~.jobs.JobSpec`
s (``typed inputs -> artifacts`` with a progress callback). No engine logic
lives here — every module only adapts an existing engine function.

Importing this package registers every job.
"""
from . import card_diff, edhrec, jobs  # noqa: F401  (edhrec registers its jobs)

__all__ = ["card_diff", "edhrec", "jobs"]
