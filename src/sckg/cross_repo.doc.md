# src/sckg/cross_repo.py

Cross-repository edge detection for SCKG v0.3.0.

## What it does
- `detect_subprocess_calls(file)` — parses a Python file with `ast`, finds
  `subprocess.run`, `subprocess.call`, `subprocess.Popen`, and `os.system`
  calls, extracts the binary name from the first argument, and creates a
  ``cross_repo_call`` edge when the binary is in ``KNOWN_TOOLS``.
- `detect_imports(file, known_packages)` — parses a Python file with `ast`,
  finds `import` and `from ... import` statements, and creates a
  ``cross_repo_import`` edge when the top-level package name matches a known
  cross-repo package.
- `build_cross_repo_graph(repo_paths, known_packages)` — indexes all repos,
  then adds cross-repo edges and synthetic repo nodes for D3 rendering.
- `find_repos_in_workspace(dir)` — discovers repo roots inside a workspace by
  looking for ``.git``, ``pyproject.toml``, ``go.mod``, or ``package.json``.

## Why AST-based
- Accurate: resolves string literals inside lists (``subprocess.run(["ibd", ...])``)
  and shell commands (``os.system("poc verify ...")``).
- Safe: uses the ``ast`` module, no code execution.
- Fast: single-pass walk with `ast.walk`.

## Files that import / touch it
- `cli.py` — `cross_repo` and `index --workspace` commands invoke
  `build_cross_repo_graph` and `find_repos_in_workspace`.
- `html_generator.py` — renders ``cross_repo_call`` / ``cross_repo_import``
  edges as purple dashed lines.
- `test_cross_repo.py` — unit tests for subprocess detection, import matching,
  unknown-binary filtering, and workspace graph building.

## Known limitations
- Only positional ``args`` are inspected; ``subprocess.run(args=[...])`` is not
  yet detected.
- ``KNOWN_TOOLS`` is hardcoded; future versions can auto-detect by scanning the
  sibling directory layout.
- `os.system` parsing relies on `shlex.split`; malformed shell strings fall
  back to naive whitespace split.
