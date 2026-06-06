"""Main Python application that calls a Go binary and imports a TypeScript component.

Docs: python_app.doc.md
"""

import subprocess


def run_go_binary() -> None:
    """Execute the Go binary via subprocess."""
    subprocess.run(["go_binary", "--help"])


def main() -> None:
    """Entry point."""
    run_go_binary()
