"""Main entry point for the sample project.

Docs: main.doc.md
"""

from utils import helper, UtilityClass


class MainClass:
    """The main class that orchestrates work."""

    def __init__(self) -> None:
        self.value = 42

    def run(self) -> None:
        """Execute the main workflow."""
        helper("world")
        inst = UtilityClass()
        inst.do_something()


def main() -> None:
    """CLI entry point."""
    app = MainClass()
    app.run()
