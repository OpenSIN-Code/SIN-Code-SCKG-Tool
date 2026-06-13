# tests/test_agents_md.py — Conformance guard for AGENTS.md

## What it does
Pytest module that asserts `AGENTS.md` at the repo root contains all 8
mandatory sections of the SIN-Code standard (issue #40).

## Why it exists
- sin-brain uses the section headers to discover rules. If any header is
  missing, sin-brain silently ignores the repo.
- sin-context-bridge queries anchor on `## Architecture` and
  `## Key Endpoints / Commands`.
- A unit test is the cheapest guard against future drift.

## Key exports
- `MANDATORY_SECTIONS` — tuple of 8 expected substrings.
- `test_agents_md_has_section` — parametrized over the 8 sections.
- `test_agents_md_is_markdown` — sanity floor (≥ 60 lines).
- `test_agents_md_preserves_gitnexus_block_if_present` — invariant for the
  GitNexus index markers.

## Verification
- `pytest tests/test_agents_md.py -v` — 3 tests pass (parametrized expands
  the 8 sections into 8 sub-cases for `test_agents_md_has_section`).
