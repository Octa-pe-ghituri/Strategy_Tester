from pathlib import Path
import tempfile
import unittest

from strategy_testbench.validator import validate_event_file


class EventFileValidationTests(unittest.TestCase):
    def _write(self, contents: str) -> Path:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        path = Path(temporary_directory.name) / "events.txt"
        path.write_text(contents, encoding="utf-8")
        return path

    def test_accepts_valid_events(self) -> None:
        path = self._write(
            "0 AAPL ADD 100 20 BUY 10 9951\n"
            "1 AAPL CANCEL 100 20 BUY 0 0\n"
        )

        report = validate_event_file(path, reserved_owner_id=1)

        self.assertTrue(report.valid)
        self.assertEqual(report.event_count, 2)

    def test_reports_invalid_columns_type_side_and_integer(self) -> None:
        path = self._write(
            "0 AAPL UNKNOWN 100 20 LEFT 10 9951\n"
            "bad AAPL ADD 101 20 BUY 10\n"
        )

        report = validate_event_file(path)

        self.assertFalse(report.valid)
        self.assertTrue(any("unknown order type" in error for error in report.errors))
        self.assertTrue(any("unknown side" in error for error in report.errors))
        self.assertTrue(any("expected 8 columns" in error for error in report.errors))

    def test_rejects_reserved_strategy_owner(self) -> None:
        path = self._write("0 AAPL ADD 100 1 BUY 10 9951\n")

        report = validate_event_file(path, reserved_owner_id=1)

        self.assertFalse(report.valid)
        self.assertIn("reserved for the strategy", report.errors[0])


if __name__ == "__main__":
    unittest.main()

