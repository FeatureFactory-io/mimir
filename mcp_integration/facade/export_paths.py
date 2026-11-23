from __future__ import annotations

from pathlib import Path
from typing import Sequence


def confined_export_path(root: Path, relative_path: str) -> Path:
    """Resolve one export child without escaping its approved root.

    :param root: Approved absolute root as Path. Example: Path("/tmp/export").
    :param relative_path: Relative destination as str. Example: "BPE/task.md".
    :return: Confined absolute Path. Example: Path("/tmp/export/BPE/task.md").
    :raises ValueError: If empty, absolute, traversing, or resolving outside root.
    """
    raise NotImplementedError()


def validate_export_destinations(
    destinations: Sequence[tuple[Path, str]],
) -> tuple[Path, ...]:
    """Preflight all requested destinations before any filesystem mutation.

    :param destinations: Approved root/child pairs. Example: ((root, "a.md"),).
    :return: Immutable resolved destinations. Example: (root / "a.md",).
    :raises ValueError: If any destination escapes its approved root.
    """
    raise NotImplementedError()
