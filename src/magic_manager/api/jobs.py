"""Job contract: every long-running engine operation as ``typed inputs -> artifacts``.

A :class:`JobSpec` is the delivery-agnostic description of one runnable
operation: a Pydantic input model (the single typed contract — the web layer
derives its form + OpenAPI schema from it) and a synchronous
``run(inputs, progress) -> JobResult`` that calls the engine. Specs hold NO
engine logic; they only adapt an existing ``magic_manager`` function's
signature to this shape.

The registry is the one place a delivery layer discovers what it can run, so
adding a job = register one spec; the web chassis (enqueue → stream progress →
render artifacts) picks it up with no per-job route.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pydantic import BaseModel


@dataclass(frozen=True)
class ProgressEvent:
    """One progress tick. ``total`` is None when unknown (indeterminate)."""
    done: int
    total: int | None
    message: str
    level: Literal["info", "warn", "error"] = "info"


ProgressFn = Callable[[ProgressEvent], None]


@dataclass
class Artifact:
    """A job output. ``kind='json'`` carries ``data`` inline; ``kind='file'``
    points at a path written via ``util.output_dir``."""
    kind: Literal["json", "file"]
    label: str
    data: Any = None
    path: str | None = None


@dataclass
class JobResult:
    summary: str
    artifacts: list[Artifact] = field(default_factory=list)


@dataclass(frozen=True)
class JobSpec:
    name: str
    title: str
    description: str
    input_model: type[BaseModel]
    run: Callable[[Any, ProgressFn], JobResult]
    mutates: bool = False  # writes user data (vs cache-only / read)


_REGISTRY: dict[str, JobSpec] = {}


def register(spec: JobSpec) -> JobSpec:
    if spec.name in _REGISTRY:
        raise ValueError(f"job {spec.name!r} already registered")
    _REGISTRY[spec.name] = spec
    return spec


def get(name: str) -> JobSpec:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown job {name!r}") from None


def all_specs() -> list[JobSpec]:
    return list(_REGISTRY.values())
