# tests/test_go_parser.py

Unit tests for the Go tree-sitter parser.

## Tests
- `test_extract_functions` — verifies `main()` and `helper()` are found
- `test_extract_structs` — verifies `Server` struct is found
- `test_extract_methods` — verifies `Start` method on `*Server` is found with parent
- `test_extract_imports` — verifies `"fmt"` import edge exists
- `test_extract_calls` — verifies `fmt.Println`, `helper`, and `Start` call edges exist

## Fixture
- `tests/fixtures/go_sample/main.go` — small Go file with all required constructs
