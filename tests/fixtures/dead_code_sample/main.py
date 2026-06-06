"""Main entry point for the dead-code sample fixture.

Docs: main.doc.md
"""

from utils import helper, parse_json


def main():
    """CLI entry point."""
    data = parse_json('{"x": 1}')
    helper(data)


def helper(name):
    """Help out — calls unused."""
    result = unused(name)
    return result


def unused(x):
    """Never called externally; only helper uses it."""
    return x
