"""CLI behaviour, exit codes, and entry points."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from lupaxa.fortune.cli import main
from lupaxa.fortune.exceptions import DatasetError, InvalidOptionError
from lupaxa.fortune.generator import FortuneGenerator
from lupaxa.fortune.version import __version__

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _code(argv: list[str]) -> int:
    try:
        return main(argv)
    except SystemExit as exc:
        code = exc.code
    if not isinstance(code, int):
        raise AssertionError(code)
    return code


def test_default_is_decorative(capsys: pytest.CaptureFixture[str]) -> None:
    """A bare command prints one decorated fortune and a final newline."""
    assert main(["--seed", "1"]) == 0
    output = capsys.readouterr().out
    assert output.startswith("🥠 Your fortune:\n")
    assert "Lucky numbers:" in output
    assert output.endswith("\n")
    assert not output.endswith("\n\n")


def test_batch_is_separated(capsys: pytest.CaptureFixture[str]) -> None:
    """Several plain fortunes are separated by one blank line."""
    assert main(["--count", "2", "--plain", "--no-numbers", "--seed", "2"]) == 0
    blocks = capsys.readouterr().out.split("\n\n")
    assert len(blocks) == 2
    assert "🥠" not in blocks[0]
    assert "Lucky numbers" not in blocks[0]


def test_modes_and_seed(capsys: pytest.CaptureFixture[str]) -> None:
    """Dark, corporate, oracle, and a repeated seed behave as documented."""
    assert main(["--dark", "--seed", "3"]) == 0
    assert capsys.readouterr().out.startswith("🌑 Your dark fortune:")
    assert main(["--corporate", "--plain", "--seed", "4"]) == 0
    assert "💼" not in capsys.readouterr().out
    assert main(["--oracle", "--count", "2", "--seed", "123", "--no-numbers"]) == 0
    oracle = capsys.readouterr().out
    assert "Risk level:" in oracle
    assert "Recommended action:" in oracle
    assert "Lucky numbers" not in oracle
    assert main(["--seed", "42", "--numbers"]) == 0
    first = capsys.readouterr().out
    assert main(["--seed", "42", "--numbers"]) == 0
    assert capsys.readouterr().out == first


def test_categories(capsys: pytest.CaptureFixture[str]) -> None:
    """Category listing is canonical and has no header."""
    assert main(["--categories"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "wisdom",
        "warning",
        "prediction",
        "ominous",
        "encouragement",
        "devops",
        "code",
        "career",
        "friday",
    ]


@pytest.mark.parametrize(
    "argv",
    [
        ["--categories", "--count", "1"],
        ["--categories", "--plain"],
        ["--categories", "--seed", "1"],
        ["--categories", "--numbers"],
        ["--dark", "--category", "wisdom"],
        ["--dark", "--corporate"],
        ["--numbers", "--no-numbers"],
        ["--count", "0"],
        ["--count", "-3"],
        ["--count", "nope"],
        ["--seed", "nope"],
        ["--category", "Wisdom"],
        ["--nope"],
    ],
)
def test_invalid_arguments(argv: list[str]) -> None:
    """Bad combinations and values exit 2."""
    assert _code(argv) == 2


def test_help_version_and_categories_without_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inspection commands do not read the datasets."""

    def boom(self: FortuneGenerator) -> object:
        raise AssertionError("dataset loaded")

    monkeypatch.setattr(FortuneGenerator, "_catalogue", boom)
    assert _code(["--help"]) == 0
    assert _code(["--version"]) == 0
    assert main(["--categories"]) == 0


def test_version_text(capsys: pytest.CaptureFixture[str]) -> None:
    """Version output uses the lupaxa-fortune prefix."""
    assert _code(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"lupaxa-fortune {__version__}"


def test_dataset_error_has_no_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A broken catalogue exits 1 with a prefixed message and no traceback."""

    def boom(self: FortuneGenerator) -> object:
        raise DatasetError("broken catalogue")

    monkeypatch.setattr(FortuneGenerator, "_catalogue", boom)
    assert main(["--seed", "1"]) == 1
    error = capsys.readouterr().err
    assert error.startswith("lupaxa-fortune: error: broken catalogue")
    assert "Traceback" not in error


def test_unexpected_error_is_not_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    """Programmer errors still propagate."""

    def boom(self: FortuneGenerator, **_kwargs: object) -> object:
        raise RuntimeError("programmer error")

    monkeypatch.setattr(FortuneGenerator, "generate", boom)
    with pytest.raises(RuntimeError, match="programmer error"):
        main(["--seed", "1"])


def test_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ctrl-C exits 130."""

    def boom(self: FortuneGenerator, **_kwargs: object) -> object:
        raise KeyboardInterrupt

    monkeypatch.setattr(FortuneGenerator, "generate", boom)
    assert main(["--seed", "1"]) == 130


def test_stdout_oserror(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An ordinary write failure exits 1."""

    def fail(*_args: object, **_kwargs: object) -> int:
        raise OSError("disk full")

    monkeypatch.setattr(sys.stdout, "write", fail)
    assert main(["--seed", "1", "--plain", "--no-numbers"]) == 1
    assert "disk full" in capsys.readouterr().err


def test_broken_pipe_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """A closed pipe is a quiet success and does not close the test runner."""
    read_fd, write_fd = os.pipe()

    class ClosedPipe:
        """Stand-in stdout whose write fails like a closed pipe."""

        def write(self, _text: str) -> int:
            raise BrokenPipeError

        def flush(self) -> None:
            return None

        def fileno(self) -> int:
            return write_fd

    monkeypatch.setattr(sys, "stdout", ClosedPipe())
    try:
        assert main(["--seed", "1", "--plain", "--no-numbers"]) == 0
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_option_error_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A library option error is a prefixed stderr message and exit 2."""

    def boom(self: FortuneGenerator, **_kwargs: object) -> object:
        raise InvalidOptionError("bad option")

    monkeypatch.setattr(FortuneGenerator, "generate", boom)
    assert main(["--seed", "1"]) == 2
    error = capsys.readouterr().err
    assert error.startswith("lupaxa-fortune: error: bad option")
    assert "Traceback" not in error


def test_broken_pipe_subprocess(tmp_path: Path) -> None:
    """A consumer that closes stdout early does not see a traceback."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    proc = subprocess.Popen(
        [sys.executable, "-m", "lupaxa.fortune", "--count", "30", "--seed", "1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_path,
        env=env,
    )
    assert proc.stdout is not None
    proc.stdout.close()
    code = proc.wait(timeout=20)
    assert proc.stderr is not None
    error = proc.stderr.read().decode()
    assert code == 0
    assert "Traceback" not in error


def test_dunder_main_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running the package as a module exits with the CLI status."""
    import runpy

    monkeypatch.setattr(sys, "argv", ["lupaxa.fortune", "--categories"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("lupaxa.fortune", run_name="__main__")
    assert exc.value.code == 0


def test_module_entry_agrees(tmp_path: Path) -> None:
    """``python -m lupaxa.fortune`` matches the library entry for one seed."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    first = subprocess.run(
        [sys.executable, "-m", "lupaxa.fortune", "--seed", "9", "--plain", "--no-numbers"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    second = subprocess.run(
        [sys.executable, "-m", "lupaxa.fortune", "--seed", "9", "--plain", "--no-numbers"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert first.returncode == 0
    assert first.stdout == second.stdout
    assert main(["--seed", "9", "--plain", "--no-numbers"]) == 0
