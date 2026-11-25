"""Fixed benchmark identities and bounded public-export contracts; no cloud APIs."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

import contract
import remote
from benchmark_metrics import MAX_DIAGNOSTIC_BYTES, parse_browser_diagnostic

ACCOUNT = "411113550285"
SOURCE = "04c9432bce7eac5ec34a090bc5e8ec4fa06f409d"
BUILD = "45516980492"
_REGISTRY = f"{ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/mimir@sha256:"
IMAGES = {
    "web": _REGISTRY
    + "e7f6e2170fd6250a9b6c3f635ceb2b90d0dfbe81ed337c10180c0a903ca5e1ba",
    "browser": _REGISTRY
    + "a74104c8fb4ff8a02dd053ee2584868d91dd4273f058b690faf0875684c5e368",
    "postgres": "postgres@sha256:07abc3f43c9395b0bdbbab36bc25ddb0e8d83cd4fcafb5fb7d6abe14ff156dd8",
}
RUNTIME_FILES = (
    "remote.py",
    "contract.py",
    "bootstrap.py",
    "browser.py",
    "experts_staging_settings.py",
    "verify_image.py",
    "web_entry.py",
    "aggregate.py",
    "benchmark_observer.py",
    "benchmark_metrics.py",
)
_PUBLIC_NAMES = {
    "benchmark-result.json",
    "benchmark-source.json",
    "benchmark-memory.json",
    "browser-memory.json",
    "browser-diagnostic.json",
}
_MAX_FILE_BYTES = 2 * 1024 * 1024
_MAX_EXPORT_BYTES = 128 * 1024 * 1024

_PLAN_KEYS = {
    "status",
    "nonce",
    "account",
    "bucket",
    "source_revision",
    "runner_revision",
    "build_run_id",
    "build_receipt",
    "web_image",
    "fixture_sha256",
}


def read_json(path: Path) -> dict[str, Any]:
    """Read a bounded unlinked JSON object from an explicitly named file.

    :param path: Absolute actual input path.
    :return: Parsed object.
    :raises ValueError: Unsafe path, links, size or JSON shape.
    """
    if not path.is_absolute() or path.resolve() != path or not path.is_file():
        raise ValueError("An absolute unlinked actual input file is required.")
    if path.stat().st_nlink != 1 or path.stat().st_size > _MAX_FILE_BYTES:
        raise ValueError("Input must be an unlinked bounded regular file.")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("JSON object required.")  # noqa: TRY004 - input boundary.
    return value


def validate_prepared(
    prepared: Path, repository: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Match actual prepared identities and current application source bytes.

    :param prepared: Existing controller.prepare output directory.
    :param repository: Immutable checked-out repository.
    :return: Validated plan and source manifest.
    :raises ValueError: Fixed identity, runner or actual application bytes differ.
    """
    plan = read_json(prepared / "prepared-plan.json")
    source = read_json(prepared / "source.json")
    validate_plan_shape(plan, source)
    revision = git_text(repository, "rev-parse", "HEAD").strip()
    if plan["runner_revision"] != revision or not isinstance(source["files"], dict):
        raise ValueError("Prepared runner identity differs from actual checkout.")
    contract.validate_source_files(repository, source["files"])
    fixture = source["files"]["test-data/experts/cedar-rfp-01.json"]
    if plan["fixture_sha256"] != fixture:
        raise ValueError("Prepared fixture bytes differ.")
    image = contract.validate_receipt(plan["build_receipt"], SOURCE, BUILD, ACCOUNT)
    if image != IMAGES["web"]:
        raise ValueError("Prepared image differs from the fixed candidate.")
    return plan, source


def validate_cache(rows: dict[str, Any]) -> dict[str, int]:
    """Require positive exact local immutable Linux/amd64 images; never pull.

    :param rows: Actual curated local Docker image metadata.
    :return: Actual bounded engine sizes, independent of other engine sizes.
    :raises ValueError: Any image is absent, partial or mismatched.
    """
    if not isinstance(rows, dict) or set(rows) != set(IMAGES):
        raise ValueError("Every exact benchmark image must already be cached.")
    if not all(
        contract.cached_image_matches(image, rows[role])
        for role, image in IMAGES.items()
    ):
        raise ValueError("Actual cached image identity/platform/size differs.")
    return {role: rows[role]["Size"] for role in IMAGES}


def safe_export(source: Path, destination: Path) -> list[dict[str, Any]]:
    """Copy only exact allowlisted public evidence, never private runtime.

    :param source: Invocation-owned public evidence directory.
    :param destination: Existing fresh public destination.
    :return: Original copied paths, sizes and SHA-256 hashes.
    :raises ValueError: Unsafe input or a container-supplied host result.
    """
    files = checked_export_files(source)
    if any(path.name == "benchmark-result.json" for path in files):
        raise ValueError("The host result cannot originate from a container.")
    if destination.resolve() != destination or not destination.is_dir():
        raise ValueError("An actual unlinked public destination is required.")
    admitted = diagnostic_snapshots(files)
    return [
        copy_public_file(
            path, destination, path.relative_to(source), admitted.get(path)
        )
        for path in files
    ]


def checked_export_files(source: Path) -> list[Path]:
    """Validate every export member before copying any bytes.

    :param source: Owned actual evidence directory.
    :return: Fully validated regular public files.
    :raises ValueError: Links, unknown names or size bounds are unsafe.
    """
    if source.resolve() != source or not source.is_dir():
        raise ValueError("An actual public evidence directory is required.")
    files = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if path.is_symlink() or path.resolve() != path:
            raise ValueError("Linked evidence cannot be exported.")
        if path.is_dir():
            if str(relative) not in {"screenshots", "video"}:
                raise ValueError("Unknown evidence directory.")
            continue
        if not path.is_file() or path.stat().st_nlink != 1 or not public_name(relative):
            raise ValueError("Unknown or linked evidence file.")
        files.append(path)
    if sum(path.stat().st_size for path in files) > _MAX_EXPORT_BYTES:
        raise ValueError("Evidence exceeds the fixed public export bound.")
    return files


def validate_plan_shape(plan: dict[str, Any], source: dict[str, Any]) -> None:
    """Require the exact public preparation schema and fixed approved identities.

    :param plan: Actual controller plan object.
    :param source: Actual application source object.
    :return: None after all immutable selectors agree.
    :raises ValueError: Unexpected fields or identities.
    """
    if set(plan) != _PLAN_KEYS or set(source) != {"source_revision", "files"}:
        raise ValueError("Unexpected prepared input fields.")
    selectors = {
        "status": "PREPARED_SOURCE_ONLY_NOT_DEPLOYED",
        "account": ACCOUNT,
        "source_revision": SOURCE,
        "build_run_id": BUILD,
        "web_image": IMAGES["web"],
        "bucket": f"elasticbeanstalk-us-east-1-{ACCOUNT}",
    }
    if (
        any(plan[key] != value for key, value in selectors.items())
        or source["source_revision"] != SOURCE
    ):
        raise ValueError("Prepared input differs from the fixed experiment.")
    contract.owner_record(plan["nonce"])


def public_name(relative: Path) -> bool:
    """Admit only exact numeric receipts and the core's unchanged public names.

    :param relative: Relative evidence member, e.g. ``health.json``.
    :return: Whether this exact name is declared.
    """
    return str(relative) in _PUBLIC_NAMES or remote.allowed_evidence_name(relative)


def reviewed_bytes(repository: Path, path: Path) -> bytes:
    """Require actual unlinked control bytes equal to the checked-out Git commit.

    :param repository: Actual immutable repository root.
    :param path: Named runtime/control file below that repository.
    :return: Exact reviewed UTF-8 source bytes.
    :raises ValueError: Path, size or committed source differs.
    """
    if path.resolve() != path or not path.is_file():
        raise ValueError("Actual unlinked runtime source required.")
    if path.stat().st_nlink != 1 or path.stat().st_size > _MAX_FILE_BYTES:
        raise ValueError("Runtime source exceeds fixed regular-file bounds.")
    data = path.read_bytes()
    relative = str(path.relative_to(repository))
    committed = git_text(repository, "show", f"HEAD:{relative}").encode()
    if data != committed:
        raise ValueError("Actual runtime source differs from the reviewed Git commit.")
    return data


def publish_owner(output: Path) -> None:
    """Return only the fresh validated public artifacts to their workspace owner.

    :param output: Newly allocated public directory; private roots are excluded.
    :return: None after safe files/directories become readable by artifact upload.
    :raises ValueError: Linked, foreign or nonprivate entries are unsafe.
    :raises OSError: Ownership cannot be transferred.
    """
    checked_export_files(output)
    entries = [output, *output.rglob("*")]
    for path in entries:
        mode = path.stat().st_mode
        if path.stat().st_uid != os.getuid() or mode & 0o077:
            raise ValueError(
                "Only invocation-owned private public artifacts may change owner."
            )
        if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise ValueError("Only real public files/directories may change owner.")
    owner = output.parent.stat()
    for path in reversed(entries):
        os.chown(path, owner.st_uid, owner.st_gid)


def git_text(repository: Path, *arguments: str) -> str:
    """Read exact Git objects while explicitly trusting only the owned checkout.

    :param repository: Actual checked-out repository, also valid for clean sudo.
    :param arguments: Fixed read-only Git operation and validated selectors.
    :return: Actual UTF-8 object/output text.
    :raises RuntimeError: Git rejects the actual read.
    """
    command = ["git", "-c", f"safe.directory={repository}", "-C", str(repository)]
    return remote.command([*command, *arguments])


def copy_public_file(
    path: Path, destination: Path, relative: Path, admitted: bytes | None = None
) -> dict[str, Any]:
    """Copy one prevalidated file exclusively, preserving exact original bytes.

    :param path: Prevalidated regular source.
    :param destination: Invocation-owned new public directory.
    :param relative: Exact allowlisted relative path.
    :param admitted: Previously validated canonical snapshot for the diagnostic.
    :return: Public original-byte content hash and size.
    :raises OSError: Existing destination, alias or write failure.
    """
    target = destination / relative
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    data = path.read_bytes() if admitted is None else admitted
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
    return {
        "path": str(relative),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def rejected_export_shapes(source: Path) -> list[dict[str, Any]]:
    """Describe only rejected member shapes, never names, paths or contents.

    :param source: Actual owned public evidence directory.
    :return: At most16 closed shape records, or an empty result when inaccessible.
    """
    if source.resolve() != source or not source.is_dir():
        return []
    result = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        metadata = path.lstat()
        linked = stat.S_ISLNK(metadata.st_mode) or path.resolve() != path
        directory = stat.S_ISDIR(metadata.st_mode)
        unknown_directory = directory and str(relative) not in {"screenshots", "video"}
        unsafe_file = not directory and (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or not public_name(relative)
        )
        if linked or unknown_directory or unsafe_file:
            result.append(export_shape(path, relative))
        if len(result) == 16:
            break
    return result


def export_shape(path: Path, relative: Path) -> dict[str, Any]:
    """Project an unknown member onto a closed category, kind, depth and extension.

    :param path: Actual member, read only for its metadata.
    :param relative: Relative member; raw strings never leave this function.
    :return: Fixed enums and bounded numeric depth only.
    """
    kind = member_kind(path.lstat().st_mode)
    parts = relative.parts
    category = (
        parts[0]
        if parts[0] in {"screenshots", "video"}
        else "root_file" if len(parts) == 1 and kind == "file" else "other"
    )
    extension = relative.suffix.lstrip(".")
    if extension not in {"json", "png", "zip", "webm"}:
        extension = "other" if extension else "none"
    return {
        "top_category": category,
        "kind": kind,
        "depth": min(len(parts), 32),
        "extension": extension,
        "rejections": export_rejection_kinds(path, relative),
    }


def member_kind(mode: int) -> str:
    """Classify only the actual file type, without exporting metadata or names.

    :param mode: Actual lstat mode bits.
    :return: Closed file/directory/symlink/other enum.
    """
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISDIR(mode):
        return "directory"
    return "file" if stat.S_ISREG(mode) else "other"


def diagnostic_snapshots(files: list[Path]) -> dict[Path, bytes]:
    """Admit every diagnostic's raw canonical bytes before any mixed file copy.

    :param files: Metadata-checked export file list.
    :return: Immutable admitted original bytes for the one exact diagnostic name.
    :raises ValueError: Any diagnostic's raw bytes are invalid; nothing is copied.
    """
    return {
        path: validated_diagnostic_bytes(path)
        for path in files
        if path.name == "browser-diagnostic.json"
    }


def validated_diagnostic_bytes(path: Path) -> bytes:
    """Read one bounded regular unlinked diagnostic and admit its exact raw bytes.

    :param path: Exact actual observer receipt.
    :return: Original canonical bytes, safe to snapshot and copy unchanged.
    :raises ValueError: Any path, link, type, size, schema or raw byte is rejected.
    :raises OSError: Safe regular-file read fails.
    """
    if not path.is_absolute() or path.resolve() != path or not path.is_file():
        raise ValueError("An absolute unlinked actual input file is required.")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("Input must be an unlinked bounded regular file.")
        data = stream.read(MAX_DIAGNOSTIC_BYTES + 1)
    parse_browser_diagnostic(data)
    return data


def export_rejection_kinds(path: Path, relative: Path) -> list[str]:
    """Classify actual failed admission predicates without publishing filenames.

    :param path: Owned member, metadata read through lstat only.
    :param relative: Member path used privately by the unchanged allowlist.
    :return: Closed reason enums, never names, paths, contents or guessed cause.
    """
    metadata = path.lstat()
    mode = metadata.st_mode
    result = []
    if stat.S_ISLNK(mode):
        result.append("SYMLINK")
    elif path.resolve() != path:
        result.append("PATH_ALIAS")
    if stat.S_ISDIR(mode):
        if str(relative) not in {"screenshots", "video"}:
            result.append("DIRECTORY_NOT_ADMITTED")
    elif not stat.S_ISREG(mode):
        if not stat.S_ISLNK(mode):
            result.append("FILE_TYPE_NOT_REGULAR")
    else:
        if metadata.st_nlink != 1:
            result.append("HARDLINK_COUNT_NOT_ONE")
        if not public_name(relative):
            result.append("NAME_PATTERN_MISMATCH")
    return result
