"""Checks on project rules, not on calculations."""
import ast
import subprocess
import sys
from pathlib import Path

import pandas as pd

from clientprofit import schema

REPO = Path(__file__).resolve().parent.parent


def test_model_code_never_imports_generator():
    """D-08: src/clientprofit must not import the generator or its settings."""
    offenders = []
    for path in (REPO / "src" / "clientprofit").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            offenders += [f"{path.name}: {n}" for n in names if n.split(".")[0] == "generator"]
    assert offenders == []


def test_call_graph_is_current():
    run = subprocess.run([sys.executable, "scripts/gen_callgraph.py", "--check"],
                         cwd=REPO, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr


def test_hand_calc_files_use_schema_columns():
    folder = REPO / "tests" / "fixtures" / "hand_calc"
    for table, cols in schema.TABLES.items():
        headers = list(pd.read_csv(folder / f"{table}.csv", nrows=0).columns)
        assert headers == list(cols)
