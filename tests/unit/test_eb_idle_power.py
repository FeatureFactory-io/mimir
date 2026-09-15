"""Contract tests for idle EB scale-to-zero wiring."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POWER = (ROOT / "scripts" / "eb_idle_power.sh").read_text()
DEPLOY = (ROOT / "scripts" / "deploy-idle.sh").read_text()
PROMOTE = (ROOT / "scripts" / "promote-prod.sh").read_text()
MAKEFILE = (ROOT / "Makefile").read_text()


def test_power_script_never_stops_prod_cname() -> None:
    assert "PROD_CNAME_SUBSTRING" in POWER
    assert "will not" in POWER
    assert "suspend-processes" in POWER
    assert "SingleInstance" in POWER
    assert "_idle_already_runnable" in POWER
    assert "_force_asg_one" in POWER
    assert "skipping ASG scale" in POWER


def test_deploy_idle_starts_before_backup() -> None:
    start_pos = DEPLOY.find('eb_idle_power.sh" start')
    backup_pos = DEPLOY.find("run-eb-backup.sh")
    assert start_pos != -1
    assert backup_pos != -1
    assert start_pos < backup_pos
    assert "host network" in (ROOT / "scripts" / "run-eb-backup.sh").read_text()


def test_promote_stops_new_idle_after_success() -> None:
    success_pos = PROMOTE.find("PROMOTE SUCCESS")
    stop_pos = PROMOTE.find('eb_idle_power.sh" stop')
    assert success_pos != -1
    assert stop_pos != -1
    assert success_pos < stop_pos


def test_makefile_has_idle_power_targets() -> None:
    assert "idle-stop:" in MAKEFILE
    assert "idle-start:" in MAKEFILE
