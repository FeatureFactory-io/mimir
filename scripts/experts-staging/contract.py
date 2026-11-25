"""Pure contracts for the owned Cedar companion; no AWS or Docker side effects."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

_FORMAT = "mimir-experts-owned-postgres-v1"
_SOURCE_PREFIXES = (
    "accounts/",
    "methodology/",
    "mimir/",
    "mcp_integration/",
    "templates/",
    "static/",
    "tests/support/",
    "test-data/experts/",
    "tests/uat/e2e-uat-flow.feature",
    "tests/e2e/test_expert_cards.py",
)
_RUNTIME_KEYS = {
    "nonce",
    "account",
    "source_revision",
    "build_run_id",
    "build_receipt",
    "web_image",
    "browser_image",
    "postgres_image",
    "bucket",
    "fixture_sha256",
    "image_sizes",
}
MIN_AVAILABLE_MEMORY = 1400 * 1024 * 1024
MIN_AVAILABLE_DISK = 4 * 1024 * 1024 * 1024
LIVE_DISK_RESERVE = 1024**3
MAX_IMAGE_SIZE = 20 * 1024**3


def image_cache_reserve(
    manifest: Mapping[str, Any], observations: Mapping[str, Any]
) -> int:
    """Budget existing image bytes only after complete exact local-cache proof.

    :param manifest: Validated candidate images and actual CI sizes.
    :param observations: Whitelisted Docker metadata keyed by all three roles.
    :return: OneGiB for a complete match, otherwise the unchanged cold budget.
    :raises ValueError: The candidate manifest itself is invalid.
    """
    cold = validate_runtime_manifest(manifest)
    if not isinstance(observations, Mapping) or set(observations) != {
        "web",
        "browser",
        "postgres",
    }:
        return cold
    matched = all(
        cached_image_matches(manifest[f"{role}_image"], observations[role])
        for role in manifest["image_sizes"]
    )
    return LIVE_DISK_RESERVE if matched else cold


def cached_image_matches(reference: str, actual: Mapping[str, Any]) -> bool:
    """Check immutable Linux/amd64 identity with bounded actual host metadata.

    :param reference: Exact validated image digest reference.
    :param actual: Whitelisted real Docker image metadata.
    :return: Whether digest/platform match and the host's own size is bounded.
    """
    if not isinstance(actual, Mapping) or not isinstance(reference, str):
        return False
    identity, digests = actual.get("Id"), actual.get("RepoDigests")
    return (
        type(actual.get("Size")) is int
        and 0 < actual["Size"] < MAX_IMAGE_SIZE
        and actual.get("Os") == "linux"
        and actual.get("Architecture") == "amd64"
        and isinstance(identity, str)
        and re.fullmatch(r"sha256:[a-f0-9]{64}", identity) is not None
        and isinstance(digests, list)
        and all(isinstance(item, str) for item in digests)
        and reference in digests
    )


def validate_pull_capacity(memory: int, disk: int, reserve: int) -> None:
    """Preserve memory protection and admit only computed cold or cached budgets.

    :param memory: Actual current available memory bytes.
    :param disk: Actual current free Docker-storage bytes.
    :param reserve: Budget returned by image_cache_reserve, never a manifest flag.
    :return: None after unchanged memory and actual storage reserve checks.
    :raises ValueError: Any typed bound, budget or measured capacity is unsafe.
    """
    if any(type(value) is not int for value in (memory, disk, reserve)):
        raise ValueError("Fresh integer capacity and computed reserve are required.")
    if reserve != LIVE_DISK_RESERVE and reserve < MIN_AVAILABLE_DISK:
        raise ValueError("Storage reserve is not a computed cold or cached budget.")
    if memory < MIN_AVAILABLE_MEMORY or disk < reserve:
        raise ValueError(
            "Idle host cannot safely fit the unchanged memory/storage reserve."
        )


def validate_receipt(
    receipt: Mapping[str, Any], revision: str, run_id: str, account: str
) -> str:
    """Validate the exact successful build's source and immutable ECR address.

    :param receipt: Actual candidate-image-identities.json from the build run.
    :param revision: Expected full Git SHA, e.g. forty lowercase hex characters.
    :param run_id: Expected numeric GitHub Actions run ID.
    :param account: Existing twelve-digit AWS account identifier.
    :return: Immutable web image address, e.g. registry/mimir@sha256:<64hex>.
    :raises ValueError: If any identity differs or lacks a digest.
    """
    if not isinstance(receipt, Mapping) or any(
        type(value) is not str for value in (revision, run_id, account)
    ):
        raise ValueError("Typed build identity selectors are required.")
    if (
        not re.fullmatch(r"[a-f0-9]{40}", revision)
        or not re.fullmatch(r"[1-9][0-9]*", run_id)
        or not re.fullmatch(r"[0-9]{12}", account)
        or receipt.get("source_revision") != revision
        or str(receipt.get("run_id")) != run_id
        or receipt.get("web_image")
        != f"{account}.dkr.ecr.us-east-1.amazonaws.com/mimir"
        or not re.fullmatch(r"sha256:[a-f0-9]{64}", str(receipt.get("web_digest", "")))
        or not isinstance(receipt.get("platforms"), list)
        or "linux/amd64" not in receipt.get("platforms", [])
    ):
        raise ValueError(
            "Candidate build receipt does not match the approved source/run/ECR identity."
        )
    return f"{receipt['web_image']}@{receipt['web_digest']}"


def owner_record(nonce: str) -> dict[str, str]:
    """Create the exact non-secret importer ownership declaration.

    :param nonce: Cryptographically allocated 32-character lowercase hex identity.
    :return: Marker for one dedicated role/database, e.g. experts_cedar_<nonce>.
    :raises ValueError: If the nonce is malformed.
    """
    if not isinstance(nonce, str) or not re.fullmatch(r"[a-f0-9]{32}", nonce):
        raise ValueError("Cedar requires a random 32-hex ownership identity.")
    name = f"experts_cedar_{nonce}"
    return {
        "format": _FORMAT,
        "fixture": "CEDAR-RFP-01",
        "owner_id": nonce,
        "database": name,
        "role": name,
        "host": "cedar-db",
        "port": "5432",
    }


def select_idle(environments: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Resolve the existing idle environment using the actual live CNAME.

    :param environments: Exact describe-environments response rows.
    :return: Existing Ready idle row; never the environment holding live CNAME.
    :raises ValueError: If names, application, state or CNAME ownership is ambiguous.
    """
    if not isinstance(environments, (list, tuple)) or any(
        not isinstance(row, Mapping) for row in environments
    ):
        raise ValueError("Actual environment rows are required.")
    names = {row.get("EnvironmentName") for row in environments}
    if len(environments) != 2 or names != {"mimir-prod", "mimir-idle"}:
        raise ValueError("Expected exactly the two existing Mimir environments.")
    for row in environments:
        if (
            row.get("ApplicationName") != "mimir"
            or row.get("Status") != "Ready"
            or not row.get("EnvironmentId")
            or not re.fullmatch(
                r"mimir-[a-z0-9.-]+\.us-east-1\.elasticbeanstalk\.com",
                str(row.get("CNAME", "")),
            )
        ):
            raise ValueError("Mimir environment identity/state is unsafe.")
    live = [row for row in environments if "mimir-prod.eba-" in row["CNAME"]]
    if len(live) != 1:
        raise ValueError("Live CNAME ownership is ambiguous.")
    return next(row for row in environments if row is not live[0])


def validate_source_files(root: Path, files: Mapping[str, str]) -> None:
    """Match actual candidate bytes with mandatory app/guard/fixture coverage.

    :param root: Actual immutable application root, e.g. /app.
    :param files: Trusted exact Git source path/SHA map.
    :return: None after every selected source matches.
    :raises ValueError: Required coverage, safe path or actual bytes differ.
    """
    required = {
        "mimir/settings/base.py",
        "methodology/models/karma_award.py",
        "tests/support/experts_data.py",
        "test-data/experts/cedar-rfp-01.json",
        "tests/uat/e2e-uat-flow.feature",
        "tests/e2e/test_expert_cards.py",
    }
    if not required <= files.keys():
        raise ValueError(
            "Source identity lacks mandatory application/guard/fixture coverage."
        )
    for name, expected in files.items():
        validate_source_file(root, name, expected)


def validate_source_file(root: Path, name: str, expected: str) -> None:
    """Check one real image file without following aliases or accepting traversal.

    :param root: Actual image application root.
    :param name: Safe relative candidate Git path.
    :param expected: Exact candidate SHA-256.
    :return: None only for the expected real source bytes.
    :raises ValueError: Unsafe path/digest, symlink or changed source bytes.
    :raises TypeError: A path or expected hash has the wrong type.
    """
    if not isinstance(name, str) or not isinstance(expected, str):
        raise TypeError("Typed source paths and hashes are required.")
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or not (name in _SOURCE_PREFIXES[-2:] or name.startswith(_SOURCE_PREFIXES[:-2]))
        or not re.fullmatch(r"[a-f0-9]{64}", expected)
    ):
        raise ValueError("Unsafe source identity path/digest.")
    actual = root / name
    if (
        not actual.is_file()
        or actual.resolve() != actual
        or not actual.resolve().is_relative_to(root.resolve())
    ):
        raise ValueError("Source identity requires actual non-symlink image files.")
    if hashlib.sha256(actual.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Candidate image source differs: {name}")


def validate_capacity(memory: int, disk: int) -> None:
    """Fail before image pulls or container creation if host reserve is insufficient.

    :param memory: Actual MemAvailable bytes, e.g. 1600*1024*1024.
    :param disk: Actual free Docker-root filesystem bytes.
    :return: None when bounded web/PG/browser and reserve can fit.
    :raises ValueError: If fresh capacity is below either fixed threshold.
    """
    validate_pull_capacity(memory, disk, MIN_AVAILABLE_DISK)


def validate_runtime_manifest(manifest: Mapping[str, Any]) -> int:
    """Validate public runtime identity and conservative actual pull reserve.

    :param manifest: CI-authenticated public contract, never credentials/bearer URLs.
    :return: Required free image-storage bytes, including oneGiB reserve.
    :raises ValueError: Any source/image/role/bucket/size identity differs.
    """
    if not isinstance(manifest, Mapping) or not _RUNTIME_KEYS <= manifest.keys():
        raise ValueError("Complete typed runtime identities are required.")
    owner_record(manifest.get("nonce", ""))
    image = validate_receipt(
        manifest["build_receipt"],
        manifest["source_revision"],
        manifest["build_run_id"],
        manifest["account"],
    )
    validate_runtime_images(manifest, image)
    sizes = manifest.get("image_sizes", {})
    if set(sizes) != {"web", "browser", "postgres"} or any(
        type(size) is not int or not 0 < size < MAX_IMAGE_SIZE
        for size in sizes.values()
    ):
        raise ValueError("Actual positive image sizes are required before host pulls.")
    return max(MIN_AVAILABLE_DISK, sum(sizes.values()) + 1024**3)


def validate_runtime_images(manifest: Mapping[str, Any], image: str) -> None:
    """Require owned registry digests and the existing transport bucket only.

    :param manifest: Public immutable runtime identities.
    :param image: Already validated actual candidate build image.
    :return: None when no image or S3 identity can redirect execution.
    :raises ValueError: An image, fixture digest or transport bucket is unsafe.
    """
    registry = f"{manifest['account']}.dkr.ecr.us-east-1.amazonaws.com/mimir"
    if (
        image != manifest.get("web_image")
        or not re.fullmatch(
            re.escape(registry) + r"@sha256:[a-f0-9]{64}",
            str(manifest.get("browser_image", "")),
        )
        or not re.fullmatch(
            r"postgres@sha256:[a-f0-9]{64}", str(manifest.get("postgres_image", ""))
        )
        or manifest.get("bucket") != f"elasticbeanstalk-us-east-1-{manifest['account']}"
        or not re.fullmatch(r"[a-f0-9]{64}", str(manifest.get("fixture_sha256", "")))
    ):
        raise ValueError("Unsafe runtime image/source/artifact identity.")


def allow_browser_request(url: str, method: str) -> bool:
    """Allow actual app reads and only the shell assets observed in native traces.

    :param url: Browser request URL, e.g. https://fonts.gstatic.com/font.woff2.
    :param method: Actual HTTP method.
    :return: Whether the unmodified network request may continue.
    """
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (ValueError, TypeError):
        return False
    if parsed.username or parsed.password or parsed.scheme != "https":
        return False
    if parsed.hostname == "cedar-web" and port == 8443:
        return method in {"GET", "HEAD"}
    hosts = {
        "cdn.jsdelivr.net",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "kit.fontawesome.com",
        "ka-p.fontawesome.com",
        "unpkg.com",
    }
    return (
        parsed.hostname in hosts and port in {None, 443} and method in {"GET", "HEAD"}
    )
