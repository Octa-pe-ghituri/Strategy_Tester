# Strategy Testbench

Strategy Testbench is a lightweight Python desktop application for running and inspecting
event-driven trading simulations. It provides a graphical interface for the
[Event Backtester](https://github.com/Octa-pe-ghituri/Event-backtester) C++ engine.

## Features

- Select a compiled Event Backtester executable.
- Import market-event datasets.
- Validate input data before each run.
- Run the backtester without freezing the interface.
- View the complete process output and error log.
- Extract cash, positions, equity, final P&L, and response counts automatically.
- Locate the default data and configuration files when the backtester is inside its project
  directory.

## Requirements

- Python 3.10 or newer
- GTK 3 Python bindings
- A compiled copy of
  [Event Backtester](https://github.com/Octa-pe-ghituri/Event-backtester)

On Ubuntu or Pop!_OS, install the GTK bindings with:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0
```

## Getting started

Clone this repository:

```bash
git clone https://github.com/Octa-pe-ghituri/Strategy_Tester.git
cd Strategy_Tester
```

Start the application:

```bash
python3 -m strategy_testbench
```

## Usage

1. Click **Select** and choose the compiled `event_backtester` executable.
2. Click **Import** and choose a compatible market data file.
3. Select the backtester configuration file, such as `config/backtest.cfg`.
4. Click **Run Test**.

The result is organized into three views:

- **Summary** — execution status, cash, positions, equity, P&L, and response counts;
- **Run Log** — complete output produced by the backtester;
- **Errors** — validation errors, process errors, and timeouts.

## Market data format

Each non-empty line must contain eight whitespace-separated fields:

```text
time SYMBOL TYPE order_id owner_id SIDE quantity price
```

Example:

```text
0 AAPL ADD 700000 20 BUY 93 9951
1 AAPL CANCEL 700000 20 BUY 0 0
```

Supported order types:

- `ADD`
- `CANCEL`
- `MODIFY` or `MOD`
- `IOC`
- `MARKET`

Supported sides are `BUY` and `SELL`.

## Run the tests

The project uses Python's built-in `unittest` framework and requires no additional testing
packages:

```bash
python3 -m unittest discover -s tests -v
```

The tests cover data validation, output parsing, successful and failed processes, temporary
data staging, and timeouts.

## Project structure

```text
strategy_testbench/
├── app.py        # GTK desktop interface
├── runner.py     # Backtester process execution
├── parser.py     # Output and summary parsing
└── validator.py  # Market data validation

tests/            # Automated test suite
```

## Current compatibility

The application currently runs the `FairPriceStrategy` included in Event Backtester. Strategy
selection and external strategy plugins are not yet supported.
