import sys
from pathlib import Path

import lab
from lab import reports
from lab.calls.call import Call
from lab.environments import TetralithEnvironment

assert reports.Table.add_col
assert reports.Table.get_row
assert reports.Table.set_row_order
assert lab.tools.deprecated
assert lab.tools.get_lab_path

assert Call

TetralithEnvironment.is_present()

sys.path.append(str(Path(__file__).resolve().parents[1] / "examples" / "downward"))
import project  # noqa: E402

assert project.add_scatter_plot_reports
assert project.check_initial_h_value
assert project.check_search_started
assert project.OptimalityCheckFilter
assert project.OptimalityCheckFilter.check_costs
