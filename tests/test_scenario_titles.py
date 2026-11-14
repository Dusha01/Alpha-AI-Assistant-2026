from __future__ import annotations

import ast
from pathlib import Path

from tests.scenarios.progress import TITLES

_ROOT = Path(__file__).resolve().parent / "scenarios"


def test_every_scenario_has_a_report_title() -> None:
    missing: list[str] = []
    for path in sorted(_ROOT.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("test_"):
                key = f"{path.name}::{node.name}"
                if key not in TITLES:
                    missing.append(key)
    assert missing == []
