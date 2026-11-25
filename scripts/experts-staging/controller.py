"""CI preparation and explicit owned-run dispatch using existing GitHub/AWS access."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4

import boto3

from contract import select_idle, validate_receipt, validate_runtime_manifest

_REQUIRED_ARGUMENTS = {
    "prepare": ("receipt", "revision", "run_id", "account"),
    "execute": ("images",),
}
_REPO = "FeatureFactory-io/mimir"
_RUNTIME_FILES = (
    "remote.py",
    "contract.py",
    "bootstrap.py",
    "browser.py",
    "experts_staging_settings.py",
    "verify_image.py",
    "web_entry.py",
)
_SOURCE_PREFIXES = (
    "accounts/",
    "methodology/",
    "mimir/",
    "mcp_integration/",
    "templates/",
    "static/",
    "tests/support/",
    "test-data/experts/",
)


def github(path: str) -> dict[str, Any]:
    """Read one exact repository API resource using CI's existing read-only token.

    :param path: Fixed API resource suffix built from validated numeric IDs.
    :return: Parsed JSON; no credentials or raw HTTP headers are persisted.
    :raises ValueError: Unexpected or excessively large response.
    """
    request = urllib.request.Request(
        f"https://api.github.com/repos/{_REPO}/{path}",
        headers={
            "Authorization": "Bearer " + os.environ["GH_TOKEN"],
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(2 * 1024 * 1024 + 1)
    if len(payload) > 2 * 1024 * 1024:
        raise ValueError("GitHub run metadata exceeded its fixed bound.")
    return json.loads(payload)


def verify_build_run(run_id: str, revision: str) -> None:
    """Require the actual source's successful build-only workflow jobs.

    :param run_id: Numeric GitHub Actions ID.
    :param revision: Full candidate source SHA.
    :return: None only with positive successful build/test and skipped deploy proof.
    :raises ValueError: Source, workflow, repository or job identity differs.
    """
    if not re.fullmatch(r"[1-9][0-9]*", run_id):
        raise ValueError("Numeric candidate run ID required.")
    run = github(f"actions/runs/{run_id}")
    verify_run_identity(run, revision)
    verify_job_results(github(f"actions/runs/{run_id}/jobs?per_page=100"))


def verify_run_identity(run: dict[str, Any], revision: str) -> None:
    """Check actual run metadata against the approved iteration source.

    :param run: GitHub API run result, never caller-supplied status prose.
    :param revision: Exact expected candidate SHA.
    :return: None after every identity matches.
    :raises ValueError: The workflow is not a completed successful branch dispatch.
    """
    expected = {
        "head_sha": revision,
        "status": "completed",
        "conclusion": "success",
        "event": "workflow_dispatch",
        "path": ".github/workflows/build-and-deploy.yml",
        "head_branch": "iteration/experts-replay",
    }
    if (
        any(run.get(key) != value for key, value in expected.items())
        or run.get("repository", {}).get("full_name") != _REPO
    ):
        raise ValueError(
            "Candidate is not an actual successful iteration build-only run."
        )


def verify_job_results(payload: dict[str, Any]) -> None:
    """Require actual job results and complete response coverage.

    :param payload: Exact GitHub Actions jobs response.
    :return: None after tests/build succeeded and normal idle deployment skipped.
    :raises ValueError: Any required job or coverage differs.
    """
    jobs = {job["name"]: job.get("conclusion") for job in payload["jobs"]}
    required = {
        "Run Tests": "success",
        "Build and Push Docker Images": "success",
        "Deploy to Idle EB env (staging smoke)": "skipped",
    }
    if payload["total_count"] != len(payload["jobs"]) or any(
        jobs.get(name) != state for name, state in required.items()
    ):
        raise ValueError(
            "Candidate test/build/deployment job proof is incomplete or unsafe."
        )


def git_bytes(repository: Path, *arguments: str) -> bytes:
    """Read exact Git objects without consulting any environment/credential files.

    :param repository: Existing immutable CI checkout.
    :param arguments: Fixed read-only Git operation and validated object/path arguments.
    :return: Exact captured bytes.
    :raises CalledProcessError: The requested source object is absent.
    """
    return subprocess.check_output(["git", *arguments], cwd=repository)


def source_manifest(repository: Path, revision: str) -> dict[str, Any]:
    """Hash the actual candidate application's Docker-included Git source.

    :param repository: Real checkout holding the exact candidate object.
    :param revision: Validated full source SHA.
    :return: Source identity and complete selected file SHA map.
    :raises ValueError: Mandatory app/guard/fixture coverage is absent.
    """
    files = source_hashes(repository, revision)
    required = {
        "mimir/settings/base.py",
        "methodology/models/karma_award.py",
        "tests/support/experts_data.py",
        "test-data/experts/cedar-rfp-01.json",
    }
    if not required <= files.keys():
        raise ValueError("Candidate source is incomplete.")
    return {"source_revision": revision, "files": files}


def source_hashes(repository: Path, revision: str) -> dict[str, str]:
    """Read immutable Git object bytes for all selected actual application inputs.

    :param repository: Real Git checkout, not the original dirty user worktree.
    :param revision: Exact candidate SHA.
    :return: Relative paths to SHA-256 values.
    :raises CalledProcessError: A candidate blob is missing.
    """
    names = (
        git_bytes(repository, "ls-tree", "-rz", "--name-only", revision)
        .decode()
        .split("\0")
    )
    selected = [
        name
        for name in names
        if name.startswith(_SOURCE_PREFIXES)
        and Path(name).suffix in {".py", ".html", ".css", ".js", ".json"}
    ]
    return {
        name: hashlib.sha256(
            git_bytes(repository, "show", f"{revision}:{name}")
        ).hexdigest()
        for name in selected
    }


def prepare(arguments: argparse.Namespace) -> None:
    """Prepare public source/build proof without AWS access or mutation.

    :param arguments: Expected source/run/account and exact local receipt path.
    :return: None after reviewable plan/source files are written.
    :raises ValueError: Candidate run or artifact identity differs.
    """
    receipt = json.loads(arguments.receipt.read_text())
    image = validate_receipt(
        receipt, arguments.revision, arguments.run_id, arguments.account
    )
    verify_build_run(arguments.run_id, arguments.revision)
    source = source_manifest(arguments.repository, arguments.revision)
    output = arguments.output.resolve()
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    (output / "source.json").write_text(json.dumps(source, indent=2) + "\n")
    plan = prepared_plan(arguments, receipt, image, source)
    (output / "prepared-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    write_workflow_outputs(plan)
    print(
        json.dumps(
            {
                "status": plan["status"],
                "source_revision": arguments.revision,
                "verified_git_files": len(source["files"]),
            }
        )
    )


def prepared_plan(
    arguments: argparse.Namespace,
    receipt: dict[str, Any],
    image: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    """Create public review metadata; no app/provider/database secret is generated.

    :param arguments: Validated runner arguments.
    :param receipt: Actual successful candidate build receipt.
    :param image: Verified immutable ECR address.
    :param source: Exact candidate file SHA map.
    :return: Clearly labeled source-only preparation record.
    """
    return {
        "status": "PREPARED_SOURCE_ONLY_NOT_DEPLOYED",
        "nonce": uuid4().hex,
        "account": arguments.account,
        "bucket": f"elasticbeanstalk-us-east-1-{arguments.account}",
        "source_revision": arguments.revision,
        "runner_revision": git_bytes(arguments.repository, "rev-parse", "HEAD")
        .decode()
        .strip(),
        "build_run_id": arguments.run_id,
        "build_receipt": receipt,
        "web_image": image,
        "fixture_sha256": source["files"]["test-data/experts/cedar-rfp-01.json"],
    }


def write_workflow_outputs(plan: dict[str, Any]) -> None:
    """Publish only safe validated image and nonce outputs to the workflow.

    :param plan: Verified public source-only plan.
    :return: None; no credential, URL bearer token or app secret is written.
    """
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
            stream.write(f"web_image={plan['web_image']}\nnonce={plan['nonce']}\n")


def resolve_host(session: boto3.Session) -> tuple[dict[str, Any], str]:
    """Resolve current idle identity and verify its sole actual online instance.

    :param session: Existing CI AWS connection.
    :return: Dynamically resolved idle row and exact existing EC2 instance ID.
    :raises ValueError: Any CNAME, host ownership or readiness check differs.
    """
    idle, instance_id = resolve_idle_instance(session)
    verify_ec2_owner(session, idle, instance_id)
    online = session.client("ssm").describe_instance_information(
        Filters=[{"Key": "InstanceIds", "Values": [instance_id]}]
    )["InstanceInformationList"]
    if len(online) != 1 or online[0]["PingStatus"] != "Online":
        raise ValueError("Existing idle host is not SSM Online.")
    return idle, instance_id


def resolve_idle_instance(session: boto3.Session) -> tuple[dict[str, Any], str]:
    """Read current CNAME ownership and require one already-existing idle instance.

    :param session: Existing CI account connection.
    :return: Actual idle environment and sole existing instance ID.
    :raises ValueError: Ambiguous topology or absent host; no host is created/woken.
    """
    eb = session.client("elasticbeanstalk")
    rows = eb.describe_environments(
        ApplicationName="mimir", EnvironmentNames=["mimir-prod", "mimir-idle"]
    )["Environments"]
    idle = dict(select_idle(rows))
    resources = eb.describe_environment_resources(EnvironmentId=idle["EnvironmentId"])[
        "EnvironmentResources"
    ]["Instances"]
    if len(resources) != 1:
        raise ValueError(
            "Exactly one existing idle host required; this runner never creates/wakes hosts."
        )
    return idle, resources[0]["Id"]


def verify_ec2_owner(
    session: boto3.Session, idle: dict[str, Any], instance_id: str
) -> None:
    """Verify real running x86_64 host tags match the current idle environment.

    :param session: Existing CI AWS connection.
    :param idle: Dynamically resolved idle environment row.
    :param instance_id: Existing environment-resource instance ID.
    :return: None after actual ownership/architecture checks.
    :raises ValueError: Actual EC2 identity differs.
    """
    reservations = session.client("ec2").describe_instances(InstanceIds=[instance_id])[
        "Reservations"
    ]
    hosts = [host for reservation in reservations for host in reservation["Instances"]]
    if (
        len(hosts) != 1
        or hosts[0]["State"]["Name"] != "running"
        or hosts[0]["Architecture"] != "x86_64"
    ):
        raise ValueError("Existing idle host is not one running x86_64 instance.")
    tags = {item["Key"]: item["Value"] for item in hosts[0].get("Tags", [])}
    if tags.get("elasticbeanstalk:environment-id") != idle["EnvironmentId"]:
        raise ValueError(
            "EC2 ownership differs from dynamically resolved idle environment."
        )


def make_bundle(output: Path, manifest: dict[str, Any]) -> tuple[Path, str]:
    """Bundle only trusted non-secret runtime code/source/run declarations.

    :param output: CI-owned output directory holding prepared source metadata.
    :param manifest: Fully validated public run contract.
    :return: New tarball path and exact SHA-256.
    :raises ValueError: Runtime package exceeds its conservative transport bound.
    """
    files = {
        name: (Path(__file__).parent / name).read_bytes() for name in _RUNTIME_FILES
    }
    files["source.json"] = (output / "source.json").read_bytes()
    files["run.json"] = json.dumps(manifest).encode()
    if sum(len(data) for data in files.values()) > 2 * 1024 * 1024:
        raise ValueError("Runtime source package exceeds the fixed transport bound.")
    target = output / "runtime-bundle.tar.gz"
    with tarfile.open(target, "w:gz") as package:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o600
            package.addfile(info, io.BytesIO(data))
    return target, hashlib.sha256(target.read_bytes()).hexdigest()


def launcher(manifest: dict[str, Any], digest: str) -> str:
    """Create a small fixed SSM program; no bearer URL/credential is transmitted.

    :param manifest: Validated public run identity.
    :param digest: Exact bundle SHA-256 carried in the authenticated command.
    :return: Safely quoted launcher for one private directory and one S3 key.
    :raises ValueError: Any transport identity is invalid.
    """
    validate_runtime_manifest(manifest)
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("Exact runtime package digest required.")
    payload = json.dumps(
        {
            "nonce": manifest["nonce"],
            "bucket": manifest["bucket"],
            "sha256": digest,
            "members": [*_RUNTIME_FILES, "source.json", "run.json"],
        }
    )
    return (
        "python3 - <<'CEDAR_OWNED_LAUNCHER'\n"
        + _LAUNCHER.replace("__PUBLIC_PAYLOAD__", repr(payload))
        + "\nCEDAR_OWNED_LAUNCHER"
    )


_LAUNCHER = """import hashlib,json,os,subprocess,tarfile
from pathlib import Path
record=json.loads(__PUBLIC_PAYLOAD__)
root=Path('/var/tmp')/('mimir-experts-'+record['nonce'])
root.mkdir(mode=0o700,exist_ok=False)
(root/'controller-owner.json').write_text(json.dumps({'nonce':record['nonce']}))
(root/'controller-owner.json').chmod(0o600)
source='s3://'+record['bucket']+'/experts-uat/'+record['nonce']+'/runtime-bundle.tar.gz'
subprocess.run(['aws','s3','cp',source,str(root/'bundle.tar.gz'),'--only-show-errors'],check=True,capture_output=True)
archive=root/'bundle.tar.gz'
assert archive.stat().st_size<=2*1024*1024 and hashlib.sha256(archive.read_bytes()).hexdigest()==record['sha256']
runtime=root/'runtime';runtime.mkdir(mode=0o700)
with tarfile.open(archive,'r:gz') as package:
    members=package.getmembers()
    assert len(members)==len(record['members']) and {m.name for m in members}==set(record['members'])
    assert all(m.isfile() and m.size<=2*1024*1024 for m in members) and sum(m.size for m in members)<=2*1024*1024
    for member in members:
        data=package.extractfile(member).read()
        destination=runtime/member.name
        descriptor=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(descriptor,'wb') as stream:stream.write(data)
probe=root/'transport-probe.json';probe.write_text('{"owned_transport_probe":true}')
subprocess.run(['aws','s3','cp',str(probe),'s3://'+record['bucket']+'/experts-uat/'+record['nonce']+'/transport-probe.json','--sse','AES256','--only-show-errors'],check=True,capture_output=True)
subprocess.run(['python3',str(runtime/'remote.py')],check=True)
"""


def wait_command(ssm: Any, command_id: str, instance_id: str) -> dict[str, Any]:
    """Wait within the fixed owned-run deadline and retain only safe command fields.

    :param ssm: Existing authenticated SSM client.
    :param command_id: Actual SendCommand identifier.
    :param instance_id: Previously verified existing idle instance.
    :return: Terminal command response; raw stderr is never published.
    :raises TimeoutError: The bounded command has not finished after twenty minutes.
    """
    for _ in range(120):
        try:
            result = ssm.get_command_invocation(
                CommandId=command_id, InstanceId=instance_id
            )
        except ssm.exceptions.InvocationDoesNotExist:
            time.sleep(2)
            continue
        if result["Status"] not in {"Pending", "InProgress", "Delayed", "Cancelling"}:
            return result
        time.sleep(10)
    raise TimeoutError("Owned SSM run exceeded its fixed deadline.")


def download_evidence(
    s3: Any, output: Path, manifest: dict[str, Any], result: dict[str, Any]
) -> None:
    """Retrieve only the exact owned evidence object, checking the remote digest.

    :param s3: Existing CI S3 client.
    :param output: CI-owned artifact destination.
    :param manifest: Validated invocation identity.
    :param result: Actual SSM response containing the safe final artifact receipt.
    :return: None after immutable evidence bytes are verified locally.
    :raises ValueError: No trustworthy artifact receipt, size or digest is available.
    """
    expected_key = f"experts-uat/{manifest['nonce']}/evidence.tar.gz"
    receipts = []
    for line in result.get("StandardOutputContent", "").splitlines():
        if line.startswith("{"):
            row = json.loads(line)
            if row.get("evidence_key") == expected_key:
                receipts.append(row)
    if len(receipts) != 1 or not 0 < receipts[0]["bytes"] <= 128 * 1024 * 1024:
        raise ValueError("Owned evidence export has no unique bounded receipt.")
    target = output / "idle-browser-evidence.tar.gz"
    s3.download_file(manifest["bucket"], expected_key, str(target))
    if (
        target.stat().st_size != receipts[0]["bytes"]
        or hashlib.sha256(target.read_bytes()).hexdigest() != receipts[0]["sha256"]
    ):
        raise ValueError("Owned evidence download differs from its remote receipt.")
    (output / "artifact-receipt.json").write_text(
        json.dumps(receipts[0], indent=2) + "\n"
    )


def execute(arguments: argparse.Namespace) -> None:
    """Explicitly run one reviewed companion, retaining actual evidence and verdict.

    :param arguments: CI-only prepared plan and exact immutable image-size receipts.
    :return: None after real core readiness, evidence download and owned cleanup.
    :raises ValueError: Any actual runtime/identity/transport gate fails.
    """
    output = arguments.output.resolve()
    manifest = execution_manifest(output, arguments.images)
    verify_build_run(manifest["build_run_id"], manifest["source_revision"])
    session = boto3.Session(region_name="us-east-1")
    if session.client("sts").get_caller_identity()["Account"] != manifest["account"]:
        raise ValueError(
            "AWS account differs from candidate registry/transport identity."
        )
    idle, instance_id = resolve_host(session)
    try:
        run_and_retrieve(session, output, manifest, idle, instance_id)
    finally:
        cleanup_after(session, output, manifest, instance_id)


def run_and_retrieve(
    session: boto3.Session,
    output: Path,
    manifest: dict[str, Any],
    idle: dict[str, Any],
    instance_id: str,
) -> None:
    """Execute the actual run and retain only verified safe result fields.

    :param session: Existing CI deployment connection.
    :param output: CI-owned metadata/evidence directory.
    :param manifest: Checked public run contract.
    :param idle: Dynamically resolved existing idle row.
    :param instance_id: Exact existing idle instance.
    :return: None after evidence download and actual status checks.
    :raises ValueError: Runtime or transport observations fail.
    """
    bundle, digest = make_bundle(output, manifest)
    result = dispatch_companion(session, manifest, idle, instance_id, bundle, digest)
    safe = {
        "CommandId": result["CommandId"],
        "InstanceId": instance_id,
        "Status": result["Status"],
        "ResponseCode": result["ResponseCode"],
        "environment_id": idle["EnvironmentId"],
    }
    (output / "ssm-receipt.json").write_text(json.dumps(safe, indent=2))
    finalize_transport(session, output, manifest, idle, instance_id, result)


def cleanup_after(
    session: boto3.Session, output: Path, manifest: dict[str, Any], instance_id: str
) -> None:
    """Reconcile exact owned resources in a separate SSM command after any outcome.

    :param session: Existing SendCommand connection; no new permission is needed.
    :param output: CI-owned safe result directory.
    :param manifest: Validated public run identity.
    :param instance_id: Exact verified host; removal still checks every owner label.
    :return: None after actual bounded cleanup succeeds or finds no owned root.
    :raises ValueError: Actual cleanup fails; never conceal retained resources.
    """
    ssm = session.client("ssm")
    parameters = {"commands": [cleanup_launcher(manifest)], "executionTimeout": ["360"]}
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Comment="Reconcile only exact owned Cedar companions",
        Parameters=parameters,
    )
    result = wait_command(ssm, response["Command"]["CommandId"], instance_id)
    safe = {key: result[key] for key in ("CommandId", "Status", "ResponseCode")}
    (output / "final-owned-cleanup.json").write_text(json.dumps(safe, indent=2))
    if result["Status"] != "Success" or result["ResponseCode"] != 0:
        raise ValueError(
            "Owned companion cleanup failed; retained state requires reconciliation."
        )


def cleanup_launcher(manifest: dict[str, Any]) -> str:
    """Build exact-owner cleanup, authenticating local helper bytes before import.

    :param manifest: Validated public owner/source contract.
    :return: Safe literal SSM cleanup program; never a wildcard/global prune.
    :raises ValueError: The run identity is invalid.
    """
    validate_runtime_manifest(manifest)
    files = {
        name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
        for name in ("remote.py", "contract.py")
    }
    payload = json.dumps({"nonce": manifest["nonce"], "files": files})
    return (
        "python3 - <<'CEDAR_OWNED_CLEANUP'\n"
        + _CLEANUP.replace("__PUBLIC_PAYLOAD__", repr(payload))
        + "\nCEDAR_OWNED_CLEANUP"
    )


_CLEANUP = """import hashlib,json,os,shutil,sys
from pathlib import Path
record=json.loads(__PUBLIC_PAYLOAD__)
root=Path('/var/tmp')/('mimir-experts-'+record['nonce'])
if not root.exists():sys.exit(0)
assert root.resolve()==root and root.stat().st_uid==os.getuid() and root.stat().st_mode&0o777==0o700
marker=root/'controller-owner.json'
assert not marker.is_symlink() and json.loads(marker.read_text())['nonce']==record['nonce']
for name,digest in record['files'].items():
    source=root/'runtime'/name
    assert not source.is_symlink() and hashlib.sha256(source.read_bytes()).hexdigest()==digest
sys.path.insert(0,str(root/'runtime'))
import remote
remote.verify_root(root,record['nonce'])
remote.cleanup(root,record['nonce'],remote.resource_names(record['nonce']))
remote.verify_root(root,record['nonce'])
shutil.rmtree(root)
"""


def execution_manifest(output: Path, images_path: Path) -> dict[str, Any]:
    """Combine only allowed actual image fields with the prepared source contract.

    :param output: CI-owned prepared plan directory.
    :param images_path: Actual Docker digest/size receipt.
    :return: Fully checked public runtime contract.
    :raises ValueError: Extra fields or unsafe identities are supplied.
    """
    manifest = json.loads((output / "prepared-plan.json").read_text())
    images = json.loads(images_path.read_text())
    if set(images) != {"browser_image", "postgres_image", "image_sizes"}:
        raise ValueError("Image receipt contains unexpected runtime fields.")
    manifest.update(images)
    validate_runtime_manifest(manifest)
    return manifest


def dispatch_companion(
    session: boto3.Session,
    manifest: dict[str, Any],
    idle: dict[str, Any],
    instance_id: str,
    bundle: Path,
    digest: str,
) -> dict[str, Any]:
    """Dispatch only after a second fresh idle-ownership check.

    :param session: Existing deployment connection.
    :param manifest: Validated public run identity.
    :param idle: Previously resolved physical idle row.
    :param instance_id: Sole verified idle host.
    :param bundle: Exact non-secret runtime archive.
    :param digest: Exact SHA-256 of the runtime archive.
    :return: Actual terminal SSM result; no fabricated execution verdict.
    :raises ValueError: Current idle identity changed.
    """
    s3, ssm = session.client("s3"), session.client("ssm")
    key = f"experts-uat/{manifest['nonce']}/runtime-bundle.tar.gz"
    s3.upload_file(
        str(bundle),
        manifest["bucket"],
        key,
        ExtraArgs={"ServerSideEncryption": "AES256"},
    )
    current, current_instance = resolve_host(session)
    if (
        current["EnvironmentId"] != idle["EnvironmentId"]
        or current_instance != instance_id
    ):
        raise ValueError("Idle ownership changed before dispatch.")
    response = send_owned_command(ssm, manifest, digest, instance_id)
    return wait_command(ssm, response["Command"]["CommandId"], instance_id)


def send_owned_command(
    ssm: Any, manifest: dict[str, Any], digest: str, instance_id: str
) -> dict[str, Any]:
    """Send one bounded literal command without transmitting credentials or URLs.

    :param ssm: Existing deployment SSM client.
    :param manifest: Validated public runtime contract.
    :param digest: Exact non-secret runtime archive SHA-256.
    :param instance_id: Sole positively verified idle host.
    :return: Actual SendCommand response.
    """
    parameters = {
        "commands": [launcher(manifest, digest)],
        "executionTimeout": ["1200"],
    }
    return ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Comment="Owned Cedar companion readiness; no EB/shared DB changes",
        Parameters=parameters,
    )


def finalize_transport(
    session: boto3.Session,
    output: Path,
    manifest: dict[str, Any],
    idle: dict[str, Any],
    instance_id: str,
    result: dict[str, Any],
) -> None:
    """Verify downloaded actual evidence and current idle identity before cleanup.

    :param session: Existing deployment connection.
    :param output: Owned local artifact directory.
    :param manifest: Exact public run identity.
    :param idle: Original dynamic environment identity.
    :param instance_id: Original verified physical idle host.
    :param result: Actual completed SSM result.
    :return: None after only the three exact owned S3 objects are deleted.
    :raises ValueError: Actual readiness or host identity differs.
    """
    s3 = session.client("s3")
    download_evidence(s3, output, manifest, result)
    if result["Status"] != "Success" or result["ResponseCode"] != 0:
        raise ValueError(
            "Owned readiness failed; retained artifacts cannot certify staging."
        )
    after, after_instance = resolve_host(session)
    if after["EnvironmentId"] != idle["EnvironmentId"] or after_instance != instance_id:
        raise ValueError("Idle ownership changed during companion run.")
    for name in ("runtime-bundle.tar.gz", "transport-probe.json", "evidence.tar.gz"):
        s3.delete_object(
            Bucket=manifest["bucket"], Key=f"experts-uat/{manifest['nonce']}/{name}"
        )


def main() -> None:
    """Select explicit preparation or execution; preparation has no AWS mutation.

    :return: None after the selected concrete phase.
    :raises ValueError: Required identity/source/runtime arguments are invalid.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "execute"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--revision")
    parser.add_argument("--run-id")
    parser.add_argument("--account")
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--images", type=Path)
    arguments = parser.parse_args()
    required = _REQUIRED_ARGUMENTS[arguments.mode]
    if any(getattr(arguments, name) is None for name in required):
        parser.error("The selected phase requires: " + ", ".join(required))
    if arguments.mode == "prepare":
        prepare(arguments)
    else:
        execute(arguments)


if __name__ == "__main__":
    main()
