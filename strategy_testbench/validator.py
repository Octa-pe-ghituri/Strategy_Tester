from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ALLOWED_ORDER_TYPES = frozenset({"ADD", "CANCEL", "MODIFY", "MOD", "IOC", "MARKET"})
ALLOWED_SIDES = frozenset({"BUY", "SELL"})
INTEGER_COLUMNS = {
    0: "time",
    3: "order_id",
    4: "owner_id",
    6: "quantity",
    7: "price",
}


@dataclass(frozen=True)
class ValidationReport:
    event_count: int
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def read_strategy_owner_id(config_path: Path) -> int | None:
    """Read strategy_owner_id when possible; the C++ app remains authoritative."""
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            for raw_line in config_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = (part.strip() for part in line.split("=", 1))
                if key == "strategy_owner_id":
                    return int(value)
    except (OSError, ValueError):
        return None

    return None


def validate_event_file(
    path: Path,
    *,
    reserved_owner_id: int | None = None,
    max_errors: int = 20,
) -> ValidationReport:
    errors: list[str] = []
    event_count = 0

    try:
        event_file = path.open("r", encoding="utf-8")
    except OSError as exc:
        return ValidationReport(0, (f"Could not open market data: {exc}",))

    with event_file:
        for line_number, raw_line in enumerate(event_file, start=1):
            line = raw_line.strip()
            if not line:
                continue

            columns = line.split()
            if len(columns) != 8:
                errors.append(
                    f"Line {line_number}: expected 8 columns, found {len(columns)}."
                )
                if len(errors) >= max_errors:
                    break
                continue

            event_count += 1

            for index, column_name in INTEGER_COLUMNS.items():
                try:
                    int(columns[index])
                except ValueError:
                    errors.append(
                        f"Line {line_number}: {column_name} must be an integer "
                        f"(found {columns[index]!r})."
                    )

            if columns[2] not in ALLOWED_ORDER_TYPES:
                errors.append(
                    f"Line {line_number}: unknown order type {columns[2]!r}."
                )

            if columns[5] not in ALLOWED_SIDES:
                errors.append(f"Line {line_number}: unknown side {columns[5]!r}.")

            if reserved_owner_id is not None:
                try:
                    owner_id = int(columns[4])
                except ValueError:
                    owner_id = None

                if owner_id == reserved_owner_id:
                    errors.append(
                        f"Line {line_number}: owner_id {owner_id} is reserved for the strategy."
                    )

            if len(errors) >= max_errors:
                break

    if event_count == 0 and not errors:
        errors.append("The market data file contains no events.")

    if len(errors) >= max_errors:
        errors.append(f"Validation stopped after {max_errors} errors.")

    return ValidationReport(event_count, tuple(errors))

