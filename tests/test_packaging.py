"""Installed-wheel smoke test, from a directory that is not the checkout."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def built_wheel(tmp_path: Path) -> Path:
    """Build an sdist and wheel without touching the checkout's dist/."""
    out = tmp_path / "dist"
    subprocess.check_call(
        [sys.executable, "-m", "hatchling", "build", "-d", str(out)],
        cwd=ROOT,
    )
    wheels = list(out.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0]


def test_wheel_contains_datasets(built_wheel: Path) -> None:
    """Packaged JSON travels inside the wheel."""
    import zipfile

    with zipfile.ZipFile(built_wheel) as archive:
        names = archive.namelist()
    names_expected = (
        "fortunes.json",
        "dark.json",
        "corporate.json",
        "oracle.json",
        "lucky_numbers.json",
    )
    for filename in names_expected:
        assert any(name.endswith(f"data/{filename}") for name in names)


def test_installed_entry_points_agree(built_wheel: Path, tmp_path: Path) -> None:
    """The console script and module entry agree when run away from the repo."""
    target = tmp_path / "install"
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--target",
            str(target),
            str(built_wheel),
            "--no-deps",
            "--upgrade",
        ]
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(target)
    work = tmp_path / "elsewhere"
    work.mkdir()
    module = subprocess.run(
        [sys.executable, "-m", "lupaxa.fortune", "--seed", "7", "--plain", "--category", "friday"],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    script = target / "bin" / "fortune-cookie"
    if os.name == "nt":
        script = target / "Scripts" / "fortune-cookie.exe"
    assert script.is_file()
    console = subprocess.run(
        [str(script), "--seed", "7", "--plain", "--category", "friday"],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert module.returncode == 0, module.stderr
    assert console.returncode == 0, console.stderr
    assert module.stdout == console.stdout
    assert module.stdout.strip()
    shutil.rmtree(target)
