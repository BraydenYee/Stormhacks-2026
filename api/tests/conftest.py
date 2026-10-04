"""Lets tests add a section to the end-of-run report: `report("title", ["line", ...])`."""

import pytest

_SECTIONS: list[tuple[str, list[str]]] = []


@pytest.fixture
def report():
    def add(title: str, lines: list[str]):
        _SECTIONS.append((title, lines))

    return add


def pytest_terminal_summary(terminalreporter):
    for title, lines in _SECTIONS:
        terminalreporter.section(title)
        for line in lines:
            terminalreporter.write_line(line)
