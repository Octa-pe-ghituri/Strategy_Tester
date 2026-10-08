from pathlib import Path
import os
import tempfile
import textwrap
import unittest

from strategy_testbench.runner import run_backtester


class BacktesterRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.data = self.root / "source-events.txt"
        self.data.write_text("0 AAPL ADD 100 20 BUY 10 9951\n", encoding="utf-8")
        self.config = self.root / "backtest.cfg"
        self.config.write_text("strategy_owner_id = 1\n", encoding="utf-8")

    def _script(self, body: str) -> Path:
        path = self.root / f"fake-{len(list(self.root.glob('fake-*')))}.py"
        path.write_text(
            "#!/usr/bin/env python3\n" + textwrap.dedent(body),
            encoding="utf-8",
        )
        path.chmod(path.stat().st_mode | 0o111)
        return path

    def test_stages_selected_data_at_the_path_expected_by_cpp(self) -> None:
        executable = self._script(
            """
            from pathlib import Path
            data = Path("data/lesson07_simulation_events_adapted.txt").read_text()
            print(f"loaded={data.strip()}")
            print("cash=0")
            print("equity=0")
            print("finalPnlTicks=0")
            """
        )

        result = run_backtester(executable, self.data, self.config)

        self.assertTrue(result.successful)
        self.assertIn("loaded=0 AAPL ADD 100 20 BUY 10 9951", result.stdout)

    def test_captures_nonzero_exit_and_stderr(self) -> None:
        executable = self._script(
            """
            import sys
            print("invalid config", file=sys.stderr)
            raise SystemExit(3)
            """
        )

        result = run_backtester(executable, self.data, self.config)

        self.assertEqual(result.return_code, 3)
        self.assertIn("invalid config", result.stderr)
        self.assertFalse(result.successful)

    @unittest.skipIf(os.name == "nt", "The fake executable fixture uses a Unix shebang.")
    def test_reports_timeout(self) -> None:
        executable = self._script(
            """
            import time
            time.sleep(2)
            """
        )

        result = run_backtester(
            executable,
            self.data,
            self.config,
            timeout_seconds=0.05,
        )

        self.assertTrue(result.timed_out)
        self.assertIsNone(result.return_code)
        self.assertIn("timeout", result.stderr)


if __name__ == "__main__":
    unittest.main()

