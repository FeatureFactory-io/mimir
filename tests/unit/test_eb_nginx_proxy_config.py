"""Contract tests for EB nginx bootstrap ebextension."""

from pathlib import Path

CONFIG = (Path(__file__).resolve().parents[2] / ".ebextensions" / "01_nginx_proxy.config").read_text()


def test_nginx_fix_bootstraps_when_upstream_missing() -> None:
    assert "Bootstrapping EB nginx proxy" in CONFIG
    assert "127.0.0.1:8080" in CONFIG
    assert "proxy_pass            http://docker" in CONFIG


def test_nginx_fix_runs_on_every_deploy() -> None:
    assert "container_commands:" in CONFIG
    assert "01_run_nginx_fix_after_deploy" in CONFIG


def test_nginx_fix_patches_staging_upstream_and_reloads_gracefully() -> None:
    assert "STAGING_UP=/var/proxy/staging/nginx/conf.d" in CONFIG
    assert "_reload_or_start_nginx" in CONFIG
    assert "docker-proxy may still hold :80" in CONFIG
