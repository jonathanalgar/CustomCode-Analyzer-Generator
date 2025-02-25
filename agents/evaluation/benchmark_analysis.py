from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

import ipywidgets as widgets
import pandas as pd
from IPython.display import clear_output, display

from agents.evaluation.benchmark import BenchmarkResults


@dataclass
class BenchmarkRun:
    """Represents a single run of a benchmark analysis."""

    folder_name: str
    timestamp: datetime
    results: BenchmarkResults
    parquet_path: Path


class BenchmarkAnalyzer:
    """Analyze benchmark runs stored in parquet files within a specified folder."""

    def __init__(self, benchmark_folder: Path, default_limit: int = 5):
        self.benchmark_folder = Path(benchmark_folder)
        self.default_limit = default_limit
        self._runs_data: List[BenchmarkRun] = []
        self.showing_all = False

        self.load_runs()

        self.output_area = widgets.Output()
        self.html_widget = widgets.HTML(value="")
        self.checklist: List[widgets.Checkbox] = []
        self.checkbox_container = widgets.VBox([])

        button_layout = widgets.Layout(width="auto")
        self.display_button = widgets.Button(description="Analyze runs", layout=button_layout)
        if not hasattr(self, "_callback_registered"):
            self.display_button.on_click(self._on_display_button_clicked)
            self._callback_registered = True

        self.show_all_button = None
        if len(self._runs_data) > self.default_limit:
            self.show_all_button = widgets.Button(description="Show all available runs", layout=button_layout)
            self.show_all_button.on_click(self._on_show_all_clicked)

        self.ui = None

    def create_ui(self) -> None:
        """Create and initialize the UI components."""
        buttons = [self.display_button]
        if self.show_all_button:
            buttons.append(self.show_all_button)
        button_box = widgets.HBox(buttons, layout=widgets.Layout(padding="10px 0px"))
        self._update_checkboxes()
        self.ui = widgets.VBox(
            [self.checkbox_container, button_box, self.html_widget, self.output_area],
            layout=widgets.Layout(width="100%", padding="10px"),
        )

    def show(self) -> None:
        """Create and display the benchmark analysis UI."""
        self.create_ui()
        display(self.ui)

    def load_runs(self) -> None:
        """Load all benchmark runs from parquet files in the benchmark folder."""
        parquet_files = list({p.resolve() for p in self.benchmark_folder.rglob("benchmark_*.parquet")})
        runs = []
        for pfile in parquet_files:
            try:
                results = BenchmarkResults.load(pfile)
                if results.timestamp is None:
                    raise ValueError(f"Benchmark results in {pfile} missing required timestamp")
                run = BenchmarkRun(
                    folder_name=pfile.parent.name,
                    timestamp=results.timestamp,
                    results=results,
                    parquet_path=pfile,
                )
                runs.append(run)
            except Exception as e:
                print(f"Error loading {pfile}:\n{e}")
        runs.sort(key=lambda x: x.timestamp, reverse=True)
        self._runs_data = runs

    def _get_run_label(self, run: BenchmarkRun) -> str:
        return (
            f"{run.folder_name} | "
            f"{run.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"{run.results.code_generation_llm}"
        )

    def _on_display_button_clicked(self, _: widgets.Button) -> None:
        if getattr(self, "_is_processing", False):
            return
        self._is_processing = True
        try:
            output_html = ""
            selected_runs = []
            for cbox, run in zip(self.checklist, self._get_visible_runs()):
                if cbox.value:
                    selected_runs.append(run)
                    output_html += f"<h3>🏃 {run.folder_name}</h3>"
                    output_html += run.results._repr_html_() + "<hr>"
            if not selected_runs:
                output_html += "<p><em>No runs selected.</em></p>"
            else:
                output_html += "<h3>Consolidated results</h3>"
                summary_df = self._create_summary_table(selected_runs)
                output_html += summary_df.to_html()
                legend_html = """
                    <div style="margin-top: 10px; margin-bottom: 10px;">
                        <div style="display: inline-block; border: 1px solid #ccc; padding: 5px 10px;">
                            <b>Legend</b>
                            <br>✓ = Build success &amp; all ground truth tests pass
                            <br>O = Build success
                            <br>✗ = Build fail
                        </div>
                    </div>
                    """
                output_html += legend_html
                with open(Path("../../benchmark_results/runs.html"), "w", encoding="utf-8") as f:
                    f.write(output_html)

            self.html_widget.value = f'<div style="font-size:18px;">{output_html}</div>'
        finally:
            self._is_processing = False

    def _create_summary_table(self, selected_runs: list) -> pd.DataFrame:
        test_cases = set()
        models = []
        for run in selected_runs:
            test_cases.update(run.results.df.index.get_level_values("Test case").unique())
            models.append(run.results.code_generation_llm)

        sorted_test_cases = sorted(test_cases)
        data = []
        for test_case in sorted_test_cases:
            row = []
            for run in selected_runs:
                test_runs = run.results.df.loc[test_case]
                build_success = False
                full_pass = False
                partial_pass = False

                for _, test_run in test_runs.iterrows():
                    if test_run["Build success?"] == "✓":
                        build_success = True
                        rate = test_run["Ground truth test pass rate"]
                        if rate != "-":
                            passed, total = map(int, rate.split("/"))
                            if passed == total:
                                full_pass = True
                                break
                            else:
                                partial_pass = True

                if not build_success:
                    status = "✗"
                elif full_pass:
                    status = "✓"
                elif partial_pass:
                    status = "O"
                else:
                    status = "✗"
                row.append(status)
            data.append(row)

        df = pd.DataFrame(data, columns=[f"{model}" for model in models], index=sorted_test_cases)
        styled_df = df.style.set_table_styles(
            [
                {
                    "selector": "th, td",
                    "props": [
                        ("max-width", "500px"),
                        ("white-space", "normal"),
                        ("overflow-wrap", "break-word"),
                        ("word-break", "normal"),
                    ],
                }
            ]
        ).set_properties(
            **{
                "text-align": "center",
                "padding": "8px",
            }
        )
        return styled_df

    def _on_show_all_clicked(self, _: widgets.Button) -> None:
        self.showing_all = not self.showing_all
        self._update_checkboxes()
        if self.show_all_button:
            self.show_all_button.description = "Show less" if self.showing_all else "Show all available runs"

    def _get_visible_runs(self) -> List[BenchmarkRun]:
        return self._runs_data if self.showing_all else self._runs_data[: self.default_limit]

    def _update_checkboxes(self) -> None:
        self.checklist = []
        for run in self._get_visible_runs():
            label = self._get_run_label(run)
            cbox = widgets.Checkbox(
                value=True,
                description=label,
                style={"description_width": "initial"},
                layout=widgets.Layout(width="auto", max_width="100%", padding="2px 0px"),
            )
            self.checklist.append(cbox)
        self.checkbox_container.children = self.checklist


def display_benchmark_analysis(benchmark_folder: str | Path) -> None:
    """Create and display the benchmark analysis interface."""
    clear_output(wait=True)
    analyzer = BenchmarkAnalyzer(Path(benchmark_folder))
    analyzer.show()
