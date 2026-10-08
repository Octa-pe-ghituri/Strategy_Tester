import unittest

from strategy_testbench.parser import format_summary, parse_backtester_output


SAMPLE_OUTPUT = """\
t=10 symbol=AAPL order=1 owner=1 event=0 qty=1 price=100
t=11 symbol=AAPL order=1 owner=1 event=2 qty=1 price=100
cash=299.1
position[AAPL]=0 mark=10000 value=0
equity=299.1
finalPnlTicks=299.1
"""


class OutputParserTests(unittest.TestCase):
    def test_extracts_summary_positions_and_event_counts(self) -> None:
        parsed = parse_backtester_output(SAMPLE_OUTPUT)

        self.assertEqual(parsed.cash, 299.1)
        self.assertEqual(parsed.equity, 299.1)
        self.assertEqual(parsed.final_pnl_ticks, 299.1)
        self.assertEqual(parsed.positions[0].symbol, "AAPL")
        self.assertEqual(parsed.positions[0].position, 0)
        self.assertEqual(parsed.event_counts["accepted"], 1)
        self.assertEqual(parsed.event_counts["filled"], 1)
        self.assertTrue(parsed.complete)

    def test_formats_human_readable_result(self) -> None:
        parsed = parse_backtester_output(SAMPLE_OUTPUT)

        summary = format_summary(
            parsed,
            return_code=0,
            duration_seconds=0.125,
            validated_events=720,
        )

        self.assertIn("RESULT: SUCCESS", summary)
        self.assertIn("Final P&L (ticks): 299.1", summary)
        self.assertIn("Validated market events: 720", summary)


if __name__ == "__main__":
    unittest.main()

