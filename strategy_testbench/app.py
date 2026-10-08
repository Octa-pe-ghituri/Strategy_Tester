from __future__ import annotations

from pathlib import Path
import sys
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .parser import format_summary, parse_backtester_output
from .runner import RunResult, run_backtester, validate_run_paths
from .validator import read_strategy_owner_id, validate_event_file


APP_ID = "io.github.strategytestbench"

CSS = b"""
window, box, notebook, stack, scrolledwindow {
    background-color: #090b0d;
    color: #e7ebef;
}

label {
    color: #d7dce2;
}

label.title {
    color: #ffffff;
    font-size: 24px;
    font-weight: 700;
}

label.subtitle {
    color: #89939e;
}

label.status-ready {
    color: #a9b1ba;
    font-weight: 700;
}

label.status-running {
    color: #e9bd45;
    font-weight: 700;
}

label.status-success {
    color: #57d38c;
    font-weight: 700;
}

label.status-error {
    color: #ff6b74;
    font-weight: 700;
}

entry, textview, textview text {
    background-color: #11151a;
    color: #eef2f6;
    border-color: #2b323a;
}

button {
    background: #1a2026;
    color: #f2f5f7;
    border: 1px solid #343c45;
    border-radius: 4px;
    padding: 7px 14px;
}

button:hover {
    background: #242c34;
}

button.run-button {
    background: #16643c;
    border-color: #258c58;
    font-weight: 700;
    padding: 9px 24px;
}

button.run-button:hover {
    background: #1d7a4a;
}

notebook header, notebook tab {
    background: #0e1216;
    color: #aeb7c0;
}

notebook tab:checked {
    color: #ffffff;
    border-bottom: 2px solid #57d38c;
}
"""


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title="Strategy Testbench")
        self.set_default_size(940, 700)
        self.set_size_request(760, 560)

        self._apply_styles()
        self._build_ui()

    def _apply_styles(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        root.set_border_width(22)
        self.add(root)

        title = Gtk.Label(label="STRATEGY TESTBENCH")
        title.set_xalign(0)
        title.get_style_context().add_class("title")
        root.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(
            label="Run the built-in FairPriceStrategy against a selected market dataset."
        )
        subtitle.set_xalign(0)
        subtitle.get_style_context().add_class("subtitle")
        root.pack_start(subtitle, False, False, 0)

        form = Gtk.Grid(column_spacing=10, row_spacing=10)
        root.pack_start(form, False, False, 4)

        self.backtester_entry = self._add_file_row(
            form, 0, "Backtester", "SELECT", self._choose_backtester
        )

        strategy_label = Gtk.Label(label="Strategy")
        strategy_label.set_xalign(0)
        form.attach(strategy_label, 0, 1, 1, 1)
        strategy_value = Gtk.Entry()
        strategy_value.set_text("FairPriceStrategy (built-in)")
        strategy_value.set_editable(False)
        strategy_value.set_hexpand(True)
        form.attach(strategy_value, 1, 1, 1, 1)

        fixed_label = Gtk.Label(label="FIXED")
        fixed_label.get_style_context().add_class("subtitle")
        form.attach(fixed_label, 2, 1, 1, 1)

        self.data_entry = self._add_file_row(
            form, 2, "Market data", "IMPORT", self._choose_data
        )
        self.config_entry = self._add_file_row(
            form, 3, "Configuration", "SELECT", self._choose_config
        )

        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        root.pack_start(action_row, False, False, 2)

        self.run_button = Gtk.Button(label="RUN TEST")
        self.run_button.get_style_context().add_class("run-button")
        self.run_button.connect("clicked", self._on_run_clicked)
        action_row.pack_start(self.run_button, False, False, 0)

        self.status_label = Gtk.Label(label="READY")
        self.status_label.set_xalign(0)
        self.status_label.get_style_context().add_class("status-ready")
        action_row.pack_start(self.status_label, True, True, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_hexpand(True)
        self.notebook.set_vexpand(True)
        root.pack_start(self.notebook, True, True, 0)

        self.summary_view = self._add_output_page("SUMMARY")
        self.log_view = self._add_output_page("RUN LOG")
        self.errors_view = self._add_output_page("ERRORS")

        self._set_text(
            self.summary_view,
            "Select the backtester, market data, and configuration, then run the test.",
        )
        self._set_text(self.log_view, "No run output yet.")
        self._set_text(self.errors_view, "No errors reported.")

    def _add_file_row(
        self,
        grid: Gtk.Grid,
        row: int,
        label_text: str,
        button_text: str,
        callback,
    ) -> Gtk.Entry:
        label = Gtk.Label(label=label_text)
        label.set_xalign(0)
        label.set_size_request(120, -1)
        grid.attach(label, 0, row, 1, 1)

        entry = Gtk.Entry()
        entry.set_editable(False)
        entry.set_hexpand(True)
        grid.attach(entry, 1, row, 1, 1)

        button = Gtk.Button(label=button_text)
        button.connect("clicked", callback)
        grid.attach(button, 2, row, 1, 1)
        return entry

    def _add_output_page(self, title: str) -> Gtk.TextView:
        view = Gtk.TextView()
        view.set_editable(False)
        view.set_cursor_visible(False)
        view.set_monospace(True)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.set_left_margin(12)
        view.set_right_margin(12)
        view.set_top_margin(12)
        view.set_bottom_margin(12)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(view)
        self.notebook.append_page(scroller, Gtk.Label(label=title))
        return view

    def _choose_file(
        self,
        title: str,
        entry: Gtk.Entry,
        patterns: tuple[str, ...] = (),
    ) -> Path | None:
        dialog = Gtk.FileChooserDialog(
            title=title,
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            "Cancel",
            Gtk.ResponseType.CANCEL,
            "Select",
            Gtk.ResponseType.OK,
        )

        if patterns:
            file_filter = Gtk.FileFilter()
            file_filter.set_name("Supported files")
            for pattern in patterns:
                file_filter.add_pattern(pattern)
            dialog.add_filter(file_filter)

            all_files = Gtk.FileFilter()
            all_files.set_name("All files")
            all_files.add_pattern("*")
            dialog.add_filter(all_files)

        selected: Path | None = None
        if dialog.run() == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            if filename:
                selected = Path(filename).resolve()
                entry.set_text(str(selected))

        dialog.destroy()
        return selected

    def _choose_backtester(self, _button: Gtk.Button) -> None:
        selected = self._choose_file("Select backtester executable", self.backtester_entry)
        if selected is not None:
            self._discover_project_files(selected)

    def _choose_data(self, _button: Gtk.Button) -> None:
        self._choose_file("Import market data", self.data_entry, ("*.txt", "*.dat"))

    def _choose_config(self, _button: Gtk.Button) -> None:
        self._choose_file("Select backtest configuration", self.config_entry, ("*.cfg",))

    def _discover_project_files(self, executable: Path) -> None:
        candidates = (executable.parent, *executable.parents)
        for directory in candidates:
            config = directory / "config/backtest.cfg"
            data = directory / "data/lesson07_simulation_events_adapted.txt"

            if not self.config_entry.get_text() and config.is_file():
                self.config_entry.set_text(str(config.resolve()))

            if not self.data_entry.get_text() and data.is_file():
                self.data_entry.set_text(str(data.resolve()))

            if self.config_entry.get_text() and self.data_entry.get_text():
                break

    def _on_run_clicked(self, _button: Gtk.Button) -> None:
        executable = Path(self.backtester_entry.get_text())
        data_file = Path(self.data_entry.get_text())
        config_file = Path(self.config_entry.get_text())

        path_errors = validate_run_paths(executable, data_file, config_file)
        if path_errors:
            self._show_preflight_failure(path_errors)
            return

        reserved_owner_id = read_strategy_owner_id(config_file)
        validation = validate_event_file(
            data_file,
            reserved_owner_id=reserved_owner_id,
        )
        if not validation.valid:
            self._show_preflight_failure(validation.errors)
            return

        self.run_button.set_sensitive(False)
        self._set_status("RUNNING", "status-running")
        self._set_text(self.summary_view, "Backtest is running...")
        self._set_text(self.log_view, "Waiting for process output...")
        self._set_text(self.errors_view, "No errors reported.")

        worker = threading.Thread(
            target=self._run_worker,
            args=(executable, data_file, config_file, validation.event_count),
            daemon=True,
        )
        worker.start()

    def _run_worker(
        self,
        executable: Path,
        data_file: Path,
        config_file: Path,
        event_count: int,
    ) -> None:
        try:
            result = run_backtester(executable, data_file, config_file)
        except Exception as exc:  # Keep unexpected process failures inside the GUI.
            GLib.idle_add(self._finish_unexpected_error, str(exc))
            return

        GLib.idle_add(self._finish_run, result, event_count)

    def _finish_run(self, result: RunResult, event_count: int) -> bool:
        parsed = parse_backtester_output(result.stdout)
        summary = format_summary(
            parsed,
            return_code=result.return_code,
            duration_seconds=result.duration_seconds,
            validated_events=event_count,
            timed_out=result.timed_out,
        )

        self._set_text(self.summary_view, summary)
        self._set_text(self.log_view, result.stdout.strip() or "No stdout output.")

        error_text = result.stderr.strip()
        if not error_text and not result.successful:
            error_text = f"Backtester exited with code {result.return_code}."
        self._set_text(self.errors_view, error_text or "No errors reported.")

        if result.successful:
            self._set_status("SUCCESS", "status-success")
            self.notebook.set_current_page(0)
        else:
            self._set_status("FAILED", "status-error")
            self.notebook.set_current_page(2)

        self.run_button.set_sensitive(True)
        return False

    def _finish_unexpected_error(self, message: str) -> bool:
        self._set_text(self.summary_view, "RESULT: FAILED")
        self._set_text(self.errors_view, message)
        self._set_status("FAILED", "status-error")
        self.notebook.set_current_page(2)
        self.run_button.set_sensitive(True)
        return False

    def _show_preflight_failure(self, errors: tuple[str, ...]) -> None:
        self._set_text(self.summary_view, "RESULT: VALIDATION FAILED")
        self._set_text(self.errors_view, "\n".join(errors))
        self._set_status("VALIDATION FAILED", "status-error")
        self.notebook.set_current_page(2)

    def _set_status(self, text: str, style_class: str) -> None:
        context = self.status_label.get_style_context()
        for candidate in (
            "status-ready",
            "status-running",
            "status-success",
            "status-error",
        ):
            context.remove_class(candidate)
        context.add_class(style_class)
        self.status_label.set_text(text)

    @staticmethod
    def _set_text(view: Gtk.TextView, text: str) -> None:
        view.get_buffer().set_text(text)


class StrategyTestbenchApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)

    def do_activate(self) -> None:
        window = self.get_active_window()
        if window is None:
            window = MainWindow(self)
        window.show_all()
        window.present()


def main() -> int:
    application = StrategyTestbenchApplication()
    return application.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
