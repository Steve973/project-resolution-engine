# Testing Contract

This document defines the rules and workflow for writing unit tests in this repository.

## Goal

Achieve **100% complete branch coverage** for the **unit under test**.

Branch coverage means:
- Every `if/elif/else` path is exercised at least once
- Every exception path is exercised where possible
- Every early exit (`return`, `raise`, `yield`, generator termination) is exercised
- Loop behavior covers both “0 iterations” and “≥ 1 iteration” when relevant

---

## Hard rules (non-negotiable)

### These are unit tests

- **Unit under test = code defined in THIS MODULE only.**
  - Do not call upstream orchestrators.
  - Mock or stub everything outside the module under test.

- **Mock or stub ALL external influences**, including but not limited to:
  - network / HTTP / PyPI
  - filesystem (except narrowly scoped `tmp_path` where Path behavior is required)
  - time / randomness
  - environment variables
  - entry points / plugin discovery
  - resolvelib
  - zipfile I/O
  - subprocesses, threads, async scheduling, etc.

- If you are about to introduce an unmocked external dependency: **STOP** and refactor the test to mock it.

- **No real HTTP. No real PyPI.**
- **No real temp dirs** unless the unit itself requires Path behavior, and then confine it to `tmp_path` with no external side effects.

### Test structure rules

- Do **not** use classes for test cases.
- Use plain `def test_...():` functions only.
- **Parameterize**: Prefer `pytest.mark.parametrize` over copy/paste tests.

### Selection behavior rule (tags, wheels, candidates)

If the code selects a “best” item (tags, wheels, candidates, etc.):
- Never rely on lexical sorting as a proxy for preference.
- Selection must follow the explicit preference order provided by the code under test.

### Unreachable branches

If you cannot hit a branch without violating unit boundaries or requiring impossible state:
- Mark it **UNREACHABLE** and explain why.
- Do not write fake tests.

---

## Mandatory workflow: ledger first

You must generate a branch ledger **before writing any tests**. If you start writing
tests before the ledger, **STOP** and redo.

For Ledger generation instructions:
- See the [branch ledger specification](BRANCH_LEDGER_SPEC.md) for details.

---

## Only after the ledger: case matrix, then tests

### 7) Case matrix

Build a parameter table first (list of dicts or tuples, not classes). Each row must include:
- inputs
- expected output or expected exception substring
- `covers = ["<branch_id_1>", "<branch_id_2>", ...]`

Delete any row that does not cover a new branch.

### 8) Test writing rules

- **Important**: Prefer `pytest.mark.parametrize` **whenever possible**.
- Do **not** use an array of items and test multiple cases in a loop!
- Each test must state which branch IDs it covers (comment is fine).
- Mock external dependencies at the call site used by the unit under test.

### 9) Assertions

- For error cases: assert **key substrings**, not full stack traces.
- Prefer user meaningful wording: project, version, strategy name, URL, policy mode.
- Assert behavior, not implementation details, unless branch coverage requires it.

---

## Module notes (optional guidance)

This section is intentionally high level. It exists to help identify common branch categories.

### Provider or resolver modules (high churn, high branch count)

Common branch buckets:
- requirement shape: URI requirement vs named requirement
- scheme handling: file, http/https, bare path handling (if supported)
- candidate enumeration: missing project, empty file list, missing versions
- file filtering: skip non-wheel, incompatible tags, hash policy, yanked policy
- selection: multiple compatible candidates -> deterministic preference selection
- hashes: sha256 present, fallback hash, no allowed hashes

### Strategy or orchestration modules

Common branch buckets:
- strategy disabled vs enabled
- StrategyNotApplicable vs other errors
- final error aggregation includes causes list
- debug callback present vs None

### Planning or DI modules (strategy planning, ctor validation, topo sort)

Common branch buckets:
- discovery: builtin vs. entrypoint
- config binding and defaults
- singleton / prototype policy enforcement
- duplicate instance ids
- ctor validation: accepts `**kwargs` vs strict signature
- dependency scanning in nested structures
- topo sort: unknown dependency, cycle detection
- criticality: imperative closure rules
