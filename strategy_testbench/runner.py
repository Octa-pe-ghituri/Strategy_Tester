from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


EXPECTED_DATA_PATH = Path("data/lesson07_simulation_events_adapted.txt")


@dataclass(frozen=True)
class RunResult:
    return_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def successful(self) -> bool:
        return self.return_code == 0 and not self.timed_out


def validate_run_paths(executable: Path, data_file: Path, config_file: Path) -> tuple[str, ...]:
    errors: list[str] = []

    if not executable.is_file():
        errors.append("Select a valid backtester executable.")
    elif os.name != "nt" and not os.access(executable, os.X_OK):
        errors.append("The selected backtester is not executable.")

    if not data_file.is_file():
        errors.append("Select a valid market data file.")

    if not config_file.is_file():
        errors.append("Select a valid backtest configuration file.")

    return tuple(errors)


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_backtester(
    executable: Path,
    data_file: Path,
    config_file: Path,
    *,
    timeout_seconds: float = 60.0,
) -> RunResult:
    executable = executable.resolve(strict=True)
    data_file = data_file.resolve(strict=True)
    config_file = config_file.resolve(strict=True)

    started_at = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="strategy-testbench-") as temporary_directory:
        run_directory = Path(temporary_directory)
        staged_data = run_directory / EXPECTED_DATA_PATH
        staged_data.parent.mkdir(parents=True)
        shutil.copy2(data_file, staged_data)

        try:
            completed = subprocess.run(
                [str(executable), str(config_file)],
                cwd=run_directory,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - started_at
            stderr = _as_text(exc.stderr)
            timeout_message = f"Backtester exceeded the {timeout_seconds:g} second timeout."
            if stderr and not stderr.endswith("\n"):
                stderr += "\n"
            stderr += timeout_message
            return RunResult(
                return_code=None,
                stdout=_as_text(exc.stdout),
                stderr=stderr,
                duration_seconds=duration,
                timed_out=True,
            )

    return RunResult(
        return_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_seconds=time.monotonic() - started_at,
    )

