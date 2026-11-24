from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path, PureWindowsPath


def confined_export_path(root: Path, relative_path: str) -> Path:
    """Resolve one export child without escaping its approved root.

    :param root: Approved absolute root as Path. Example: Path("/tmp/export").
    :param relative_path: Relative destination as str. Example: "BPE/task.md".
    :return: Confined absolute Path. Example: Path("/tmp/export/BPE/task.md").
    :raises ValueError: If empty, absolute, traversing, or resolving outside root.
    """
    if not isinstance(root, Path) or not root.is_absolute():
        raise ValueError("An absolute export root is required.")
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("A nonempty relative export destination is required.")
    if "\0" in relative_path or "\0" in str(root):
        raise ValueError("Invalid export destination.")
    native, windows = Path(relative_path), PureWindowsPath(relative_path)
    if (
        not native.parts
        or native.anchor
        or windows.anchor
        or ".." in native.parts
        or ".." in windows.parts
    ):
        raise ValueError(
            "Export destinations must be relative and cannot traverse parents."
        )
    try:
        resolved_root = root.resolve()
        destination = (resolved_root / native).resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError("Invalid export destination.") from exc
    if destination == resolved_root or not destination.is_relative_to(resolved_root):
        raise ValueError("Export destination escapes its approved root.")
    return destination


def validate_export_destinations(
    destinations: Sequence[tuple[Path, str]],
) -> tuple[Path, ...]:
    """Preflight all requested destinations before any filesystem mutation.

    :param destinations: Approved root/child pairs. Example: ((root, "a.md"),).
    :return: Immutable resolved destinations. Example: (root / "a.md",).
    :raises ValueError: If any destination escapes its approved root.
    """
    return tuple(confined_export_path(root, child) for root, child in destinations)
