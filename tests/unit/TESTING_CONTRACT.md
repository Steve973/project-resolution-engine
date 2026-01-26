# Unit Testing Contract

## Overview

This document defines the rules and workflow for writing unit tests. It is a
contract. If a test violates this contract, then it is not a unit test.

This contract is designed to be used with a Unit Ledger as described in the
[Unit Ledger Specification](./BRANCH_LEDGER_SPEC.md) document. The ledger is the
authoritative inventory of callables and branches. The contract is the
authoritative set of constraints for deriving unit tests from that ledger.

## Goal

Achieve 100% (complete) branch coverage for the unit under test.

Branch coverage means, wherever possible, applicable, or relevant:

- Every conditional branch/path is exercised at least once (e.g., if/else, etc.)
- Every basic/unconditional/sequential statement is exercised at least once
- Every exception path is exercised
- Every early exit is exercised (e.g., return, raise, yield, break, generator
  termination)
- Loop behavior covers both zero and non-zero iteration count

Coverage target applies only to the unit under test. Coverage gained by
exercising external code does not count, and it should be avoided in favor of
other strategies, including mocking, stubbing, or the use of test-specific
implementations (fakes).

---

## Hard rules (non-negotiable)

### These are unit tests

- Unit under test equals code defined in the target unit only.
    - Do not call upstream orchestrators.
    - Do not call adjacent units because it is convenient.
    - Mock or stub everything outside the target unit.

- Mock or stub all external influences, including but not limited to:
    - network and HTTP and external package/dependency/resource registries
    - filesystem and archive IO
    - environment variables
    - dynamic discovery mechanisms (e.g., plugins, services, entrypoints)
    - time and randomness and UUIDs
    - subprocesses, threads, async scheduling
    - third party libraries where behavior is not the unit under test

If you are about to introduce an unmocked external influence, stop and
refactor the test to mock it.

No real HTTP. No real external package/dependency/resource registries.

### Test structure rules

- Do not nest classes for test cases, by default.
    - For python, use plain `def test_...():` functions only.
    - For languages like Java, prefer single-level test classes over nested
      test classes.
    - Projects may explicitly override this rule, but the override must be
      provided in writing as supplemental instructions.
- Parameterize. Prefer the test framework's parameterization mechanism over
  copy/paste test blocks or functions.
- Do not manually test multiple cases in a loop inside a single test function.
  Rely on the framework's parameterization mechanism.

### Selection behavior rule (ordering, candidates, preference)

If the code selects the best item or ranked selection:

- Never rely on lexical sorting as a proxy for preference.
- Selection must follow the explicit preference order provided by the
  code under test.
- If tests need ordering, assert based on the code’s ordering rules, not
  incidental/arbitrary ordering.

### Unreachable branches

If you cannot hit a branch without violating unit boundaries or
requiring impossible state:

- Mark it UNREACHABLE and explain why.
- Do not write fake tests.

---

## Mandatory workflow

### Ledger first

You must generate a Unit Ledger before writing any tests. Ensure that you are
following the unit ledger specification.

If you start writing tests before the ledger exists, stop and redo.

The ledger is the authoritative inventory of:

- callables in the unit
- branches for each callable (by Branch ID)
- constraints needed for unit level isolation (mocks, fakes, boundaries)

### Only after the ledger: test structure, case matrix, then tests

After the Unit Ledger exists, create unit tests using a top down, artifact
driven procedure that produces runnable output early and avoids stalling.

#### File shaping procedure (deterministic)

After the Unit Ledger exists, determine the constituent test case functions
using a deterministic file shaping procedure. This procedure must be mechanical
and must not involve searching for an optimal layout.

This procedure produces a runnable test skeleton early. Later steps may refine
assertions and reduce duplication, but they must not change the ledger-derived
branch-to-case mapping.

##### Step 1: Create a case row for each branch

For each callable in ledger order, create one case row per reachable Branch ID
in Branch ID order. Every reachable Branch ID must appear at least once across
all case rows, minus UNREACHABLE and BLOCKED.

A case row is the smallest unit of test intent. Each case row must include:

- inputs
- expected outcome (return value shape or exception substring)
- covers = ["<branch_id_1>", "<branch_id_2>", ...]

If a branch cannot be mapped to concrete inputs and expectations without
guessing, still create a case row and mark it blocked. Blocked branches must not
prevent shaping or test generation for unblocked branches.

##### Step 2: Partition case rows into buckets using a small harness key

Partition case rows into buckets using a small harness key. The harness key must
be derived from ledger facts and must be intentionally small to avoid
combinatorial churn.

The default harness key is:

- callable ID
- outcome kind: returns vs. raises
- patch targets: a sorted list of patch targets referenced by the ledger test
  guidance for that callable (empty if none)
- If patch targets are not specified for a callable, treat patch targets as an
  empty list and proceed.

Do not backtrack. Once a case row is assigned to a bucket, it must not be moved
during this procedure.

##### Step 3: Convert buckets into test functions

Each bucket becomes one test function.

- If a bucket contains two or more case rows, the bucket may be realized as a
  parameterized test function.
- If a bucket contains exactly one case row, the bucket must be realized as a
  non-parameterized test function.

Each realized test function must reference covers for every case row it
executes, either via case data or via a covers comment.

Immediately after this step, emit a runnable test skeleton for the unit.

##### Step 4: Optional micro review (bounded)

If and only if no case rows are blocked, perform a bounded micro review pass.
This pass is allowed to improve clarity without introducing churn.

Allowed operations:

- merge buckets only when their harness keys are identical
- split a bucket only to isolate a blocked or uncertain case row
- rename test functions for consistency and readability

Forbidden operations:

- searching for an optimal grouping
- revisiting branch to case mapping decisions
- inventing new branches or new case rows
- deep semantic analysis of the unit

The micro review is a single pass over the bucket list. After one pass, stop
and proceed to test implementation.

##### Step 5: Coverage: first-pass implementation

Implement the realized test functions produced by this file shaping procedure.

Constraints:

- Follow the mocking and isolation rules in the Test writing rules section. Do
  not allow external influences to leak into the tests.
- Implement tests, bucket by bucket, in ledger order. Do not skip to later
  callables.
- Cover all reachable Branch IDs. Use the case rows as the source of truth for
  which Branch IDs are covered by which test cases.
- Prefer minimal, non-brittle assertions sufficient to prove the branch outcome.
  Strengthen assertions later during refinement.
- Do not invent expectations. If a branch outcome cannot be asserted without
  guessing, defer assertion strengthening and keep the test at minimal proof.

Deliverable:

- A runnable test unit where all realized test functions execute and
  cover all reachable Branch IDs. If tests are being written by generative AI,
  and if the AI assistant is unable to run the tests, then this may require
  manual intervention by the user. The user should run the tests, then provide
  feedback so that the AI assistant can make corrections, and ultimately,
  provide a runnable test unit.

##### Step 6: Refinement pass (bounded)

After the coverage-first pass is complete, perform a bounded refinement pass.
This is a single-pass refinement bounded in one sweep, and it does not include
structural rewrites.

Constraints:

- Do not change the branch to case mapping established in Step 1.
- Do not change which Branch IDs are covered by which case rows.
- Improvements are limited to:
    - stronger assertions based on explicit unit contract
    - reduced duplication through parameterization or helpers
    - clearer naming and readability
    - improved mock clarity and call site correctness

Stop refinement when improvements lack determinism and would require guessing
or would increase coupling to implementation details.

##### Step 7: Stop condition

Stop expanding when:

- all reachable Branch IDs are covered, and
- unit isolation constraints are satisfied, and
- assertions provide sufficient proof without brittleness or invention

Proceed to the Test writing rules section for detailed constraints on mocking,
assertions, and labeling.

---

## Blocked branch protocol

A blocked branch must not prevent progress. If any Branch IDs cannot be tested
without guessing, the assistant must continue and complete all unblocked
branches, then report blocked branches explicitly.

### Definition of blocked

A Branch ID is blocked if reaching it, or asserting its outcome, requires
missing information that cannot be derived from the unit and the ledger without
guessing.

Commonly blocked causes include:

- unknown callable signature required to call the code
- branch trigger cannot be mapped to inputs or mocks from ledger facts
- the expected exception type or message substring is unavailable and cannot be
  inferred deterministically
- required fakes, fixtures, helpers, or utilities are referenced but not
  available
- the required patch point is ambiguous from the unit and ledger

Blocked condition is determined per Branch ID.

### Required output when Branch ID is blocked

When any Branch IDs are blocked, the generated test unit must include:

1. A BLOCKED BRANCHES comment block, keyed by Branch ID, describing:
    - `why`: reason the branch is blocked
    - `need`: the minimal missing input needed to unblock it. Must name a
      concrete artifact (unit snippet, signature, exception type or message,
      helper fake or fixture, patch target)
    - `impact`: localized to this specific branch, or list other impacted Branch
      IDs and the nature of the impact
    - optional fields: flexibility to include other relevant information
        - `info`: must be short and must not include invented expectations
        - `action`: single-sentence unblock action. Must state what the user can
          provide or change to resolve the block (clear and unambiguous)

2. A placeholder test for each blocked Branch ID, marked as expected failure (or
   skip) by using the appropriate framework mechanism, with a reason that
   references the missing input. The placeholder test must list the Branch ID
   in its covers comment.

The placeholder tests exist to keep blocked work visible and to allow the
user to supply missing inputs and regenerate the tests later.

### Example format

This example uses Python to demonstrate the placeholder test format. Use the
appropriate explicit failure (or skip) mechanisms in the language that the
project tests are written in.

    # BLOCKED BRANCHES
    # - C000F002B0004:
    #     why: trigger mapping not derivable from ledger facts
    #     need: unit snippet for <callable> showing the branch condition
    #     impact: all other reachable branches covered; this one pending
    #     info: ledger does not identify which input controls this branch
    #     action: paste <callable> body or add ledger note mapping the
    #             condition to specific inputs or mocks

    import pytest

    @pytest.mark.xfail(
        reason="Blocked: missing trigger mapping for C000F002B0004"
    )
    def test_blocked_C000F002B0004():
        # covers: C000F002B0004
        assert False

### No stall requirement

If blocked branches exist, do not stop and do not expand analysis. Emit runnable
tests for all unblocked branches first, then emit the blocked branch report and
placeholders.

---

## Test writing rules

### Mocking rules

- Mock at the call site used by the unit under test, using the project’s
  standard mocking mechanism.
- Use project-provided fakes and helpers when available. Do not re-create fakes
  if a helper already exists.

### Assertions

- For error cases: assert key substrings, not full stack traces.
- Prefer user meaningful wording: project, version, strategy name, URL, policy
  mode.
- Assert behavior, not implementation details, unless branch coverage requires
  it.

### Branch coverage labeling

Each test must state which Branch IDs it covers. A comment is sufficient:

    # covers: C000F001B0001, C000F001B0002

---

## Unit notes (optional guidance)

This section is intentionally general. It exists to assist in identifying common
branch categories. If supplemental project- or domain-specific instructions
exist, they should take precedence over this section where applicable.
Supplemental instructions should name the domain concepts and expected branch
buckets explicitly so that the case matrix and tests can cover those conditions.

### High churn units (many branches, many conditionals)

Common branch bucket examples:

- input classification: multiple accepted shapes or encodings
- path and identifier handling: absolute vs. relative, normalization, invalid
  characters, empty values
- mode selection: strict vs. permissive, debug vs. normal, dry run vs. apply
- optional feature gates: enabled vs. disabled
- filtering: keep vs. drop, drop all vs. drop some
- preference ordering: stable deterministic tie breaking
- empty results: no candidates, no matches, no applicable options
- ambiguity: multiple matches vs. exactly one match
- error shaping: specific error type and message contains key context
- caching: cache hit vs. miss, cache invalidation paths
- policy enforcement: allowlist vs. denylist, opt in vs. opt out
- data integrity: missing fields, inconsistent state, duplicates

### Strategy or orchestration units

Common branch bucket examples:

- strategy chosen vs. not chosen
- preconditions pass vs. fail
- early exit vs. full execution
- success vs. handled failure vs. unhandled failure
- optional callback present vs. None
- dependency interaction: dependency raises vs. returns sentinel vs. returns value
- aggregation: multiple errors combined vs. first error stops execution
- fallback: the primary path fails, then the fallback path runs
- idempotency: repeated call yields the same result vs. changes behavior

### Planning or DI units (construction, validation, ordering)

Common branch bucket examples:

- discovery: explicit registration vs. dynamic discovery
- binding: explicit config vs. defaults
- override precedence: user value overrides default vs. ignored vs. rejected
- validation: accepts flexible kwargs vs. strict signature
- duplicate identifiers: allowed vs. rejected
- missing dependency: required missing vs. optional missing
- dependency graph: acyclic vs. cycle detected
- ordering: stable topological order vs. failure to order
- nested structures: shallow vs. deep traversal
- error reporting: single cause vs. multiple causes with context
