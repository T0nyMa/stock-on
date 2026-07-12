import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_project_spec_check_passes():
    result = subprocess.run(
        [sys.executable, "scripts/check_project_spec.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "specification valid",
        "generated documentation current",
        "11 workflows registered",
    ]
