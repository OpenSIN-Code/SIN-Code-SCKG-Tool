# tests/test_cross_repo.py

Unit tests for the cross-repo edge detection module.

## Test coverage

- `test_detect_subprocess_call` — Verifies that `subprocess.run(["ibd", ...])` is
  parsed by AST and produces a ``cross_repo_call`` edge targeting ``SIN-Code-IBD-Tool``.
- `test_detect_os_system_call` — Verifies that `os.system("poc verify ...")` is
  parsed by `shlex` and produces a ``cross_repo_call`` edge targeting ``SIN-Code-PoC-Tool``.
- `test_detect_import_cross_repo` — Verifies that `import sin_codocs` and
  `from sin_codocs import checker` both produce ``cross_repo_import`` edges when
  the package is listed in the known-packages map.
- `test_ignore_unknown_binary` — Verifies that `subprocess.run(["ls", "-la"])`
  does **not** create an edge because ``ls`` is not in ``KNOWN_TOOLS``.
- `test_build_workspace_graph` — End-to-end test: creates two temporary repos,
  indexes them with `build_cross_repo_graph`, and asserts that a cross-repo edge
  is found plus that both intra-repo nodes and the synthetic repo node exist.
- `test_find_repos_in_workspace` — Verifies the workspace scanner heuristic
  (``pyproject.toml``, ``.git`` markers).
- `test_known_tools_map` — Sanity check on the hardcoded ``KNOWN_TOOLS`` dict.
