# Strategy Testbench

Strategy Testbench is a small Python desktop application for running and inspecting the
[Event Backtester](https://github.com/Octa-pe-ghituri/Event-backtester). It keeps the C++
engine unchanged and adds a simple graphical workflow for selecting data, running a test,
and reading the result.

## What it does

- selects an existing `event_backtester` executable;
- uses the built-in `FairPriceStrategy`;
- imports a compatible market-event dataset;
- validates the dataset before starting the process;
- launches the C++ backtester without blocking the window;
- captures standard output, errors, and the process exit code;
- extracts cash, positions, equity, final P&L, and response counts.

The interface intentionally stays minimal: a dark window, three file selections, one Run
button, and separate Summary, Run Log, and Errors pages.

## Requirements

- Python 3.10 or newer;
- GTK 3 Python bindings (`python3-gi` and `gir1.2-gtk-3.0` on Ubuntu/Pop!_OS);
- a compiled copy of Event Backtester.

Pop!_OS normally includes the required GTK bindings. Verify them with:

```bash
python3 -c 'import gi; gi.require_version("Gtk", "3.0")'
```

## Run

From the project directory:

```bash
python3 -m strategy_testbench
```

In the window:

1. Select the compiled `event_backtester` file.
2. Select or import the market data file.
3. Select `config/backtest.cfg`.
4. Press **Run Test**.

When the executable is located inside the Event Backtester project, the application tries
to find its default data and configuration files automatically.

## Why no C++ change is required

The current C++ executable expects its data at the relative path
`data/lesson07_simulation_events_adapted.txt`. For each run, Strategy Testbench creates a
temporary isolated directory and copies the selected dataset to that expected path. It then
runs the executable with the selected configuration file. The temporary directory is removed
automatically afterward; neither the original data nor the C++ project is modified.

## Supported data format

Each non-empty line must contain exactly eight fields:

```text
time SYMBOL TYPE order_id owner_id SIDE quantity price
```

Supported order types are `ADD`, `CANCEL`, `MODIFY`, `MOD`, `IOC`, and `MARKET`. Sides are
`BUY` and `SELL`.

## Tests

The test suite covers data validation, output parsing, successful runs, process errors, data
staging, and timeouts:

```bash
python3 -m unittest discover -s tests -v
```

## Current scope

The selected C++ executable still contains the strategy implementation, so the first version
shows `FairPriceStrategy (built-in)` as a fixed value. Runtime strategy plugins are outside the
scope of this small companion project.
