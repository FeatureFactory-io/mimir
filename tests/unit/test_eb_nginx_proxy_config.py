"""Contract tests for EB nginx bootstrap ebextension."""

from pathlib import Path

CONFIG = (Path(__file__).resolve().parents[2] / ".ebextensions" / "01_nginx_proxy.config").read_text()


def test_nginx_fix_bootstraps_when_upstream_missing() -> None:
    assert "Bootstrapping EB nginx proxy" in CONFIG
    assert "127.0.0.1:8080" in CONFIG
    assert "proxy_pass            http://docker" in CONFIG


def test_nginx_fix_runs_after_app_deploy_not_postbuild() -> None:
    assert "appdeploy/post/99_fix_nginx.sh" in CONFIG
    assert "container_commands:" not in CONFIG
    assert "nginx-eb-proxy-fix.service" in CONFIG


def test_postdeploy_hook_invokes_nginx_fix() -> None:
    hook = (
        Path(__file__).resolve().parents[2]
        / ".platform"
        / "hooks"
        / "postdeploy"
        / "01_nginx_proxy_fix.sh"
    ).read_text()
    assert "99_fix_nginx.sh" in hook


def test_nginx_fix_patches_staging_upstream_and_reloads_gracefully() -> None:
    assert "STAGING_UP=/var/proxy/staging/nginx/conf.d" in CONFIG
    assert "_reload_or_start_nginx" in CONFIG
    assert "docker-proxy may still hold :80" in CONFIG
