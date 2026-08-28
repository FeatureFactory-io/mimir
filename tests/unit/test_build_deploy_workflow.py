"""Contract tests for the release build-and-deploy workflow."""

from pathlib import Path


BUILD_AND_DEPLOY = (
    Path(__file__).resolve().parents[2] / ".github/workflows/build-and-deploy.yml"
)


def test_release_workflow_installs_ripgrep_for_factory_contract_tests():
    workflow = BUILD_AND_DEPLOY.read_text()

    install_position = workflow.find("apt-get install -y ripgrep")
    test_position = workflow.find("pytest tests/ -v")

    assert install_position != -1, "release CI must install the rg command"
    assert install_position < test_position, "ripgrep must be installed before tests run"
