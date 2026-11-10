# Test runners

The verifier runs whatever command your policy gives it. To decide whether a
base-run failure is real evidence (a test that detected the change) or just an
environment problem (missing dependency, collection error), it scans the output
for well-known failure signatures.

The built-in markers cover Python/`pytest` out of the box. For other runners,
set `runner` in `.vrc.toml` so the right signature set is selected. You can also
append project-specific patterns with `assertion_markers` /
`environment_markers`; the built-in markers are **never** removed.

A failure that matches no marker is classified `unknown` and the receipt yields
`NEEDS_RERUN` — it fails closed, so a runner we don't recognise yet is safe, just
not yet `VERIFIED`.

## Supported `runner` values

| `runner` | Example command | Assertion signature used |
| --- | --- | --- |
| `pytest` (default) | `python -m pytest -q` | `AssertionError`, `assert `, `1 failed`, `= failures =` |
| `jest` | `npx jest` | `✕`, `expect(`, `Tests: … failed`, `Expected/Received` |
| `vitest` | `npx vitest run` | `×`, `expect(`, `AssertionError`, `Tests …` |
| `go-test` | `go test ./...` | `--- FAIL:`, `panic:`, `Expected:/Got:` |
| `mocha` | `npx mocha` | `failing`, `AssertionError`, `expected … to` |
| `npm` | `npm test` | failing test output plus `AssertionError` |

Unknown runner names are ignored (the defaults still apply).

## Examples

### Python / pytest (default)

```toml
command = ["python", "-m", "pytest", "-q"]
test_paths = ["tests/"]
timeout_seconds = 300
```

### Jest

```toml
command = ["npx", "jest", "--ci"]
test_paths = ["__tests__/", "src/"]
runner = ["jest"]
timeout_seconds = 300
```

```yaml
- uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0
  with:
    persist-credentials: false
    fetch-depth: 0
- uses: AaronG18/verifiable-contributions@v0.2.1
  with:
    base: ${{ github.event.pull_request.base.sha }}
    head: ${{ github.event.pull_request.head.sha }}
    setup-command: npm ci
    fail-on: NEEDS_EVIDENCE,NEEDS_RERUN
```

### Vitest

```toml
command = ["npx", "vitest", "run"]
test_paths = ["src/"]
runner = ["vitest"]
timeout_seconds = 300
```

### Go (`go test`)

```toml
command = ["go", "test", "./..."]
test_paths = ["."]
runner = ["go-test"]
timeout_seconds = 600
```

### Mocha

```toml
command = ["npx", "mocha"]
test_paths = ["test/"]
runner = ["mocha"]
timeout_seconds = 300
```

### A custom runner

If your runner isn't listed, append its signature directly; the built-ins stay:

```toml
command = ["my-runner", "test"]
runner = []   # no preset
assertion_markers = ["my-runner: FAILED", "my-runner: expectation violated"]
environment_markers = ["my-runner: could not start", "my-runner: missing config"]
```

## A note on `setup-command`

Non-Python projects install their dependencies in `setup-command` before replay
(`npm ci`, `go mod download`, etc.). Keep it to dependency installation only —
the test command itself comes from the policy.
