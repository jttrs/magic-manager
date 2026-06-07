"""Prune accumulated artifacts in ``queries/``.

The ``queries/`` directory holds several artifact types produced by ``mm
query`` commands. All are timestamped, regenerable, and gitignored — they
accumulate without bound until something cleans them up. This script is
that something.

| Artifact | Filename pattern | Source |
|---|---|---|
| Missing checklist (XLSX)        | ``missing-<code>-checklist-<ts>.xlsx``           | ``mm query missing-set <CODE>`` |
| ManaPool bulk-add (.txt)        | ``missing-<code>-manapool-<ts>.txt``             | ``mm query missing-set <CODE>`` |
| TCGplayer Mass Entry, nonfoil   | ``missing-<code>-tcgplayer-nonfoil-<ts>.txt``    | ``mm query missing-set <CODE>`` |
| TCGplayer Mass Entry, foil      | ``missing-<code>-tcgplayer-foil-<ts>.txt``       | ``mm query missing-set <CODE>`` |
| Ad-hoc query (XLSX)             | ``<slug>-<ts>.xlsx``                             | ``mm query xlsx '<selector>' [--name SLUG]`` |

The ``<ts>`` suffix is always ``YYYY-MM-DD-HHMMSS``.

Default behavior: for each ``missing-<code>-*`` group, keep the most recent
file and delete the rest. Ad-hoc XLSX files are left alone unless
``--include-adhoc`` is passed (they're often hand-named for specific reports
the user wants to keep around).

Older artifact patterns (kept for backward-compat with already-archived
files):

- ``missing-<code>-manapool-<ts>.md`` — pre-2026-06-06 ManaPool bulk-add
  files used a fenced-markdown layout; current artifacts are plain text.
  Cleaned up identically.

Usage
-----

    uv run python -m scripts.cleanup_queries [OPTIONS]

Common invocations::

    # Default: keep newest of each missing-* group, dry-run reports what
    # WOULD be deleted but doesn't touch anything.
    uv run python -m scripts.cleanup_queries --dry-run

    # Apply the default cleanup (keep newest of each missing-* group).
    uv run python -m scripts.cleanup_queries

    # Keep the 3 newest of each group instead of just 1.
    uv run python -m scripts.cleanup_queries --keep 3

    # Also prune ad-hoc query XLSXs (default keeps them all).
    uv run python -m scripts.cleanup_queries --include-adhoc

    # Time-based purge: delete every artifact older than 7 days regardless
    # of group. Composes with --keep (the keep-newest rule still runs first).
    uv run python -m scripts.cleanup_queries --older-than 7d

    # Only act on a specific set's missing-* artifacts.
    uv run python -m scripts.cleanup_queries --pattern 'missing-fin-*'

Exit codes
----------

    0  — success (whether or not anything was deleted).
    1  — partial failure (some files couldn't be deleted; details on stderr).
    2  — bad arguments / queries/ directory missing.

The script never reaches outside ``queries/`` and never touches any file that
doesn't match the documented patterns.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

# The script lives at <repo>/scripts/cleanup_queries.py, so the repo root is
# its parent's parent. Resolve once and use absolute paths from there to make
# behavior independent of the caller's CWD.
REPO_ROOT = Path(__file__).resolve().parent.parent
QUERIES_DIR = REPO_ROOT / "queries"

# Filename patterns. Group key = everything up to and including the artifact's
# logical identity, before the timestamp suffix. The timestamp is the last
# 19 characters before the extension (``YYYY-MM-DD-HHMMSS``).
#
# The "kind" suffix per group:
#   - missing-<code>-checklist           -> kind "missing-checklist"
#   - missing-<code>-manapool            -> kind "missing-manapool"
#   - missing-<code>-tcgplayer-nonfoil   -> kind "missing-tcgplayer-nonfoil"
#   - missing-<code>-tcgplayer-foil      -> kind "missing-tcgplayer-foil"
#   - <anything else>                    -> kind "adhoc"
TIMESTAMP_SUFFIX_RE = re.compile(
    r"^(?P<base>.+)-(?P<ts>\d{4}-\d{2}-\d{2}-\d{6})\.(?P<ext>xlsx|md|txt)$"
)


def _parse_older_than(spec: str) -> float:
    """Parse a human-readable duration into seconds. Accepts ``Nd`` / ``Nh``
    / ``Nm`` (days / hours / minutes), or a bare integer (interpreted as
    days). Raises ``argparse.ArgumentTypeError`` on garbage input.
    """
    s = spec.strip().lower()
    if not s:
        raise argparse.ArgumentTypeError("--older-than requires a value")
    if s.isdigit():
        return int(s) * 86400.0  # bare int = days
    m = re.fullmatch(r"(\d+)([dhm])", s)
    if not m:
        raise argparse.ArgumentTypeError(
            f"--older-than {spec!r}: expected forms are 'Nd', 'Nh', 'Nm', or bare integer (days)"
        )
    n, unit = int(m.group(1)), m.group(2)
    return n * {"d": 86400.0, "h": 3600.0, "m": 60.0}[unit]


def _classify(path: Path) -> tuple[str, str] | None:
    """Return (group_key, kind) for a file in queries/, or None if it doesn't
    match a recognized pattern. ``group_key`` is the per-set logical group
    (e.g. ``missing-fin-checklist``); ``kind`` is one of
    ``missing-checklist``, ``missing-manapool``, ``missing-tcgplayer-nonfoil``,
    ``missing-tcgplayer-foil``, ``adhoc``.
    """
    m = TIMESTAMP_SUFFIX_RE.match(path.name)
    if not m:
        return None
    base = m.group("base")
    if base.startswith("missing-"):
        if base.endswith("-checklist"):
            return (base, "missing-checklist")
        if base.endswith("-manapool"):
            return (base, "missing-manapool")
        if base.endswith("-tcgplayer-nonfoil"):
            return (base, "missing-tcgplayer-nonfoil")
        if base.endswith("-tcgplayer-foil"):
            return (base, "missing-tcgplayer-foil")
    return (base, "adhoc")


def _collect_groups(
    queries_dir: Path, pattern: str | None
) -> dict[str, list[Path]]:
    """Walk queries/ and group files by logical identity.

    Returns a dict ``group_key -> [Path, ...]`` sorted newest-first within
    each group (by mtime descending). ``pattern``, if given, is a glob
    applied against filenames as a pre-filter.
    """
    groups: dict[str, list[Path]] = defaultdict(list)
    iter_paths = (
        queries_dir.glob(pattern) if pattern else queries_dir.iterdir()
    )
    for p in iter_paths:
        if not p.is_file():
            continue
        cls = _classify(p)
        if cls is None:
            continue
        group_key, _kind = cls
        groups[group_key].append(p)
    for key in groups:
        groups[key].sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return groups


def _select_for_deletion(
    groups: dict[str, list[Path]],
    keep: int,
    include_adhoc: bool,
    older_than_seconds: float | None,
) -> list[Path]:
    """Apply the keep-N + age rules and return files to delete.

    Logic order:
        1. Within each group, mark the newest ``keep`` files as KEEP.
           Older files are candidates for deletion.
        2. Ad-hoc files are skipped entirely unless ``include_adhoc`` is set.
        3. ``older_than_seconds``, if given, is an additional filter: the file
           must ALSO be older than the cutoff to be deleted. So the rules
           compose as 'older than the keep-N threshold AND older than the
           age threshold'.

    Returns the list of paths to delete, in deterministic order (sorted by
    path name).
    """
    now = time.time()
    cutoff = now - older_than_seconds if older_than_seconds is not None else None
    candidates: list[Path] = []
    for group_key, files in groups.items():
        # Determine kind from one representative member (all files in a group
        # share the same kind by construction).
        cls = _classify(files[0])
        kind = cls[1] if cls else "adhoc"
        if kind == "adhoc" and not include_adhoc:
            continue
        # Files past the keep threshold (newest-first ordering means anything
        # at index >= keep is older than the keep frontier).
        for p in files[keep:]:
            if cutoff is not None and p.stat().st_mtime > cutoff:
                continue  # too recent for the age filter; skip
            candidates.append(p)
    candidates.sort(key=lambda p: p.name)
    return candidates


def _human_size(n: int) -> str:
    """Render a byte count like '12.3 KB'."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cleanup_queries",
        description=(
            "Prune accumulated artifacts in queries/. Default: keep the newest "
            "missing-* file in each group; leave ad-hoc query files untouched."
        ),
        epilog=(
            "Examples:\n"
            "  uv run python -m scripts.cleanup_queries --dry-run\n"
            "  uv run python -m scripts.cleanup_queries --keep 3\n"
            "  uv run python -m scripts.cleanup_queries --include-adhoc --older-than 7d\n"
            "  uv run python -m scripts.cleanup_queries --pattern 'missing-fin-*'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--keep", type=int, default=1, metavar="N",
        help="Keep the N newest files in each (set, kind) group. Default 1.",
    )
    parser.add_argument(
        "--include-adhoc", action="store_true",
        help="Also prune ad-hoc query XLSX files (default: leave them alone, "
             "since they're often hand-named outputs the user wants to keep).",
    )
    parser.add_argument(
        "--older-than", type=_parse_older_than, default=None, metavar="SPEC",
        help="Additional filter: only delete files older than this. Accepts "
             "'Nd'/'Nh'/'Nm' or a bare integer (days). Composes with --keep "
             "(both must hold for a file to be deleted).",
    )
    parser.add_argument(
        "--pattern", default=None, metavar="GLOB",
        help="Restrict consideration to filenames matching GLOB (e.g. "
             "'missing-fin-*'). Applied before the keep/age rules.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what WOULD be deleted but don't touch anything. "
             "Exit code is still 0 on success.",
    )
    parser.add_argument(
        "--queries-dir", default=str(QUERIES_DIR), metavar="PATH",
        help=f"Override the queries/ directory location. Default: {QUERIES_DIR}",
    )
    args = parser.parse_args(argv)

    if args.keep < 0:
        print(f"error: --keep must be >= 0, got {args.keep}", file=sys.stderr)
        return 2

    queries_dir = Path(args.queries_dir).resolve()
    if not queries_dir.is_dir():
        print(f"error: queries directory not found: {queries_dir}", file=sys.stderr)
        return 2

    groups = _collect_groups(queries_dir, args.pattern)
    if not groups:
        print(f"(no recognized artifacts in {queries_dir})")
        return 0

    to_delete = _select_for_deletion(
        groups,
        keep=args.keep,
        include_adhoc=args.include_adhoc,
        older_than_seconds=args.older_than,
    )

    # Always print a summary table so the user sees what's there even on a
    # no-op run.
    total_files = sum(len(v) for v in groups.values())
    keep_count = total_files - len(to_delete)
    total_bytes_deleted = sum(p.stat().st_size for p in to_delete)
    print(
        f"queries/ inventory: {total_files} files across {len(groups)} groups."
    )
    print(
        f"  Will keep:   {keep_count}"
    )
    print(
        f"  Will delete: {len(to_delete)} ({_human_size(total_bytes_deleted)})"
        + (" [DRY RUN]" if args.dry_run else "")
    )
    if not to_delete:
        return 0

    print()
    for p in to_delete:
        size = _human_size(p.stat().st_size)
        print(f"  {'[would delete]' if args.dry_run else '[deleting]':<14} {p.name} ({size})")

    if args.dry_run:
        print()
        print("Dry run — nothing deleted. Re-run without --dry-run to apply.")
        return 0

    failures: list[tuple[Path, str]] = []
    for p in to_delete:
        try:
            p.unlink()
        except OSError as e:
            failures.append((p, str(e)))

    if failures:
        print(file=sys.stderr)
        print(f"warning: {len(failures)} file(s) could not be deleted:", file=sys.stderr)
        for p, err in failures:
            print(f"  {p.name}: {err}", file=sys.stderr)
        return 1

    print()
    print(
        f"Deleted {len(to_delete)} file(s), freed {_human_size(total_bytes_deleted)}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
