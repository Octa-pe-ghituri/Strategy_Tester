from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re


EVENT_NAMES = {
    0: "accepted",
    1: "rejected",
    2: "filled",
    3: "partially filled",
    4: "cancelled",
    5: "cancel failed",
    6: "modified",
    7: "modify failed",
    8: "modify accepted",
    9: "expired",
}

EVENT_PATTERN = re.compile(r"\bevent=(\d+)\b")
POSITION_PATTERN = re.compile(
    r"^position\[(?P<symbol>.+?)\]=(?P<position>-?\d+)"
    r"(?:\s+mark=(?P<mark>\S+))?"
    r"(?:\s+value=(?P<value>\S+))?$"
)


@dataclass(frozen=True)
class PositionSummary:
    symbol: str
    position: int
    mark: float | None
    value: float | None


@dataclass(frozen=True)
class ParsedSummary:
    cash: float | None
    positions: tuple[PositionSummary, ...]
    equity: float | None
    final_pnl_ticks: float | None
    event_counts: dict[str, int]

    @property
    def complete(self) -> bool:
        return self.cash is not None and self.final_pnl_ticks is not None


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "unavailable":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_backtester_output(output: str) -> ParsedSummary:
    cash: float | None = None
    equity: float | None = None
    final_pnl_ticks: float | None = None
    positions: list[PositionSummary] = []
    counts: Counter[str] = Counter()

    for raw_line in output.splitlines():
        line = raw_line.strip()

        event_match = EVENT_PATTERN.search(line)
        if event_match:
            code = int(event_match.group(1))
            counts[EVENT_NAMES.get(code, f"unknown event {code}")] += 1

        if line.startswith("cash="):
            cash = _optional_float(line.removeprefix("cash="))
        elif line.startswith("equity="):
            equity = _optional_float(line.removeprefix("equity="))
        elif line.startswith("finalPnlTicks="):
            final_pnl_ticks = _optional_float(line.removeprefix("finalPnlTicks="))
        else:
            position_match = POSITION_PATTERN.match(line)
            if position_match:
                positions.append(
                    PositionSummary(
                        symbol=position_match.group("symbol"),
                        position=int(position_match.group("position")),
                        mark=_optional_float(position_match.group("mark")),
                        value=_optional_float(position_match.group("value")),
                    )
                )

    return ParsedSummary(
        cash=cash,
        positions=tuple(positions),
        equity=equity,
        final_pnl_ticks=final_pnl_ticks,
        event_counts=dict(counts),
    )


def format_summary(
    parsed: ParsedSummary,
    *,
    return_code: int | None,
    duration_seconds: float,
    validated_events: int,
    timed_out: bool = False,
) -> str:
    if timed_out:
        result = "TIMEOUT"
    elif return_code == 0:
        result = "SUCCESS"
    else:
        result = "FAILED"

    lines = [
        f"RESULT: {result}",
        "Strategy: FairPriceStrategy (built-in)",
        f"Validated market events: {validated_events}",
        f"Duration: {duration_seconds:.3f} seconds",
        f"Exit code: {return_code if return_code is not None else 'n/a'}",
        "",
        "BACKTEST SUMMARY",
    ]

    if parsed.cash is None:
        lines.append("Cash: unavailable")
    else:
        lines.append(f"Cash: {parsed.cash:g}")

    for position in parsed.positions:
        mark = "unavailable" if position.mark is None else f"{position.mark:g}"
        value = "unavailable" if position.value is None else f"{position.value:g}"
        lines.append(
            f"Position {position.symbol}: {position.position} | mark: {mark} | value: {value}"
        )

    lines.append(
        "Equity: unavailable" if parsed.equity is None else f"Equity: {parsed.equity:g}"
    )
    lines.append(
        "Final P&L (ticks): unavailable"
        if parsed.final_pnl_ticks is None
        else f"Final P&L (ticks): {parsed.final_pnl_ticks:g}"
    )

    if parsed.event_counts:
        lines.extend(("", "LOGGED RESPONSES"))
        for event_name, count in sorted(parsed.event_counts.items()):
            lines.append(f"{event_name.title()}: {count}")

    return "\n".join(lines)

