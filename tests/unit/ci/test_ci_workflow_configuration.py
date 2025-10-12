from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


def test_ci_workflow_defines_segmented_pytest_jobs() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "Run unit suite" in content, "CI workflow should include a dedicated unit test step."
    assert 'pytest -m "unit' in content, "Unit job must call pytest with the unit marker filter."

    assert "Run integration suite" in content, "CI workflow should include a dedicated integration test step."
    assert 'pytest -m "integration' in content, "Integration job must call pytest with the integration marker filter."

    assert "Run ui suite" in content or "Run UI suite" in content, (
        "CI workflow should include a dedicated UI test step."
    )
    assert 'pytest -m "ui' in content, "UI job must call pytest with the ui marker filter."


def test_pyproject_enforces_cov_gate_and_markers() -> None:
    config = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    pytest_options = config["tool"]["pytest"]["ini_options"]

    addopts = pytest_options["addopts"]
    assert any("--cov-fail-under=90" in opt for opt in addopts), "Coverage gate must remain at 90%."

    markers = pytest_options["markers"]
    assert any(marker.startswith("ui:") for marker in markers), "UI marker must be registered in pytest config."
