# self-heal

Classify a failing test command by its error output, then retry. ~75 lines,
no dependencies.

There is no LLM in here despite the name. The repair step is two regex-level
heuristics.

## Real output

```python
>>> from self_heal.core import heal
>>> heal(['python3', '-c', 'import nonexistentmodule123'], '/tmp/shdemo', 3)
{'success': False, 'attempts': 3, 'history': [
  {'attempt': 1, 'result': {...}, 'fix_applied': 'pip install nonexistentmodule123'},
  {'attempt': 2, 'result': {...}, 'fix_applied': 'pip install nonexistentmodule123'},
  {'attempt': 3, 'result': {...}, 'fix_applied': 'pip install nonexistentmodule123'},
]}
```

All three attempts ran the *same* command. `pip install` was recorded in
`history` and never executed.

```python
>>> from self_heal.core import run_test, classify_failure
>>> classify_failure(run_test(['python3', '-c', 'import nonexistentmodule123']))
'import'
>>> classify_failure(run_test(['python3', '-c', 'assert 4 == 5']))
'assertion'
>>> classify_failure(run_test(['python3', '-c', 'exit 1']))
'unknown'
```

Via the CLI:

```
$ self-heal pytest test.py
✗ 未能自愈 (3 次尝试)
$ echo $?
1
```

## Install

```bash
pip install -e .
```

Requires Python 3.10+ (uses `str | None`). Installs the `self-heal` script.

## Usage

```bash
self-heal <command> [args...] [--cwd DIR] [--max N]
```

- `command` — `nargs="+"`, so the trailing flags must come after the command, or
  be separated. Example: `self-heal pytest test.py --cwd ./sub --max 5`
- `--cwd` — working directory for both the test run and the file read. Default `.`
- `--max` — max attempts. Default 3.

Exit code is 0 on success, 1 on failure.

## Failure classification

`classify_failure` lowercases `stdout + stderr` and returns the first match:

| category | trigger |
|---|---|
| `assertion` | `"assert"` **and** `"error"` both present |
| `import` | `importerror` or `modulenotfounderror` |
| `runtime` | `syntaxerror` or `typeerror` |
| `timeout` | `timeout` |
| `crash` | `segmentation fault` |
| `unknown` | none of the above |

The `assertion` rule needs both substrings, so a bare `AssertionError` without
the word "assert" elsewhere falls through to `unknown` — which ends the loop
immediately.

## What this is not

- **It does not heal anything.** `attempt_fix` returns a string; `heal` stores
  it in `history[-1]["fix_applied"]` and then loops. No `pip install` is run, no
  source file is written. The loop re-executes the identical command up to
  `--max` times. Verified: an import failure produces three identical
  `fix_applied` entries and three identical runs.
- **The assertion "fix" produces broken code.** It splits the *first* line
  containing both `assert` and `==` on `==` and swaps the halves, then hardcodes
  a 4-space indent. For `  assert compute() == 5` it emits
  `    assert 5 == assert compute()`. It also `return`s inside the loop, so only
  one line is ever touched, and it reads `cwd + "/test_heal_target.py"` — a
  hardcoded filename. Your tests are not named that, so `code` is usually `""`.
- **It does not write to your repo.** Nothing in the package opens a file for
  writing. The repair output is discarded.
- **`attempts` is misreported on failure.** The `return` on the failure path uses
  `max_attempts`, not the loop counter. A failure that breaks on attempt 1 still
  reports 3 (or whatever `--max` was).
- **It only sees the last 2000 characters** of stdout/stderr
  (`proc.stdout[-2000:]`). Pytest puts failures at the end, so this usually
  works, but verbose tracebacks get truncated.
- **120s hard timeout** on the test subprocess; a timeout raises
  `subprocess.TimeoutExpired` and is not caught, so it crashes rather than
  classifying as `timeout`.
- **No LLM, no diff, no patch application, no git integration.** The name
  oversells it: this is a failure-taxonomy logger with a retry counter.
- No tests, no config, no library API (`__init__.py` is empty).

## Requirements

Python 3.10+. No dependencies.

## License

MIT