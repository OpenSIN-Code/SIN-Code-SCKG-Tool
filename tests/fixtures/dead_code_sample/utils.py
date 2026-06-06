"""Utility functions for the dead-code sample fixture.

Docs: utils.doc.md
"""


def format_data(data):
    """Format data — never called by any other symbol."""
    return data.upper()


def parse_json(raw):
    """Parse JSON — called by main.py::main."""
    import json
    return json.loads(raw)
