from __future__ import annotations

import pytest


def emit_lines(config: pytest.Config, lines: list[str]) -> None:
    """Печатает строки в терминал, минуя перехват вывода pytest."""
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    capman = config.pluginmanager.get_plugin("capturemanager")

    def write() -> None:
        if reporter is None:
            for line in lines:
                print(line, flush=True)
            return
        for line in lines:
            reporter.write_line(line)
        reporter.flush()

    if capman is None:
        write()
        return
    with capman.global_and_fixture_disabled():
        write()
