# Unit Ledger Spec

This document defines the Unit Ledger format and the rules for creating
it.

A Unit Ledger is a language-agnostic inventory of atomic facts about one
source unit (a Python module, a Java compilation unit, a Kotlin file,
etc.). It is designed so both humans and AI can use it to:

* Write high-quality unit tests, including full branch coverage when
  possible.
* Capture integration facts (interunit edges and boundary crossings)
  that can later be used to derive a flow ledger and integration test
  plans.
* Support documentation, conformance checks, and porting work.

If you only remember one idea, remember this:

> **The ledger stores facts, not stories.**

## Goals

* Language agnostic structure.
* Evolvable format that can change without breaking old ledgers.
* Deterministic IDs so diffs are meaningful.
* High signal detail so AI can generate strong tests quickly.
* Integration facts that enable later flow and integration planning.

## Non goals

* This is not the flow ledger. Sequences and narratives are derived
  later.
* This is not an AST dump.
* This does not prove you captured every branch. Coverage tools do that.

## Core rules

### Observed vs inferred

There are two kinds of information:

* Observed: literally present in the source (decorators, keywords,
  condition text, signature text).
* Inferred: derived from observed facts plus language rules.

The default mode is to include observed information only.

If inferred facts are desired, put them under an `inferred` map and
nowhere else. If you are unsure, omit. Do not guess.

Guidance:

* `extra` is for unknown or future extension fields.
* `inferred` is for known derived facts that you intentionally want to
  carry without confusing them with an observed source.

### No placeholders

Do not emit placeholders like:

* `...`
* `???`
* `TBD`
* `TODO`
* `maybe`
* trailing `?` markers

If something is unknown or not present in the code, omit the field.

### Omit empty optionals

To keep files readable, omit optional fields when they would be empty:

* `null`
* `[]`
* `{}`
* empty string ""

Required fields must still be present.

### Determinism

IDs are assigned deterministically in a top-down traversal. The ledger is
designed so you can regenerate and compare consistently.

## File format

A Unit Ledger file is a multi-document YAML file.

It contains exactly three required YAML documents separated by `---`, and
one optional third YAML document.

* Document 1: Derived ID Map (generated).
* Document 2: Unit Ledger (the main inventory).
* Document 3: Ledger Generation Review (required, even without findings).

## Document 1: Derived ID Map

Purpose: record the deterministic assignment of IDs for entries and
branches.

This document is generated from a top-down traversal. It should be safe
to discard and regenerate, ending up with the same result.

### Required fields

* `assigned.branches`: list of branch addresses and their IDs
* `assigned.entries`: list of structural entries and their IDs
* `docKind`: must be `derived-ids`
* `schemaVersion`: schema version string (start with "1")
* `unit.language`: `python`, `java`, `kotlin`, etc
* `unit.name`: stable unit name (unit path, file stem, etc.)
* `unit.unitId`: always `C000`

### Address rule

Each assignment item includes an `address`. It is a stable selector for
where the item came from. The exact format is flexible, but it must be
stable enough for your use.

Acceptable address styles include:

* qualified name plus first line number
* qualified name plus signature text
* AST path

### Example

```yaml
docKind: derived-ids
schemaVersion: "1"

unit:
  name: "project_resolution_engine.internal.resolvelib"
  language: "python"
  unitId: "C000"

assigned:
  entries:
    - id: C000F001
      kind: callable
      name: _expand_tags_for_context
      address: "C000::_expand_tags_for_context@L12"
    - id: C001
      kind: class
      name: ProjectResolutionProvider
      address: "C000::ProjectResolutionProvider@L44"
    - id: C001M001
      kind: callable
      name: __init__
      address: "C000::ProjectResolutionProvider.__init__@L45"

  branches:
    - id: C001M003B0001
      parent: C001M003
      address: "C000::ProjectResolutionProvider._best_hash@if hashes@L88"
      summary: "hashes empty"
```

## Document 2: Unit Ledger

Purpose: the real inventory. This is what humans review and what AI uses
to generate tests.

The structure is a tree of entries. That tree is the primary hierarchy
that keeps the ledger readable, contextually organized, and language
agnostic.

### Required fields

* `docKind`: must be `ledger`
* `schemaVersion`: schema version string
* `unit`: an Entry (root entry)

## Shapes

Every shape section below:

* explains the object
* defines how to populate it
* ends with a full shape template

Templates show all fields. Real ledgers should omit empty optionals.

### Entry

An Entry is a structural node in the unit. The whole unit is an entry.
Classes are entries. Callables are entries.

Required fields:

* `id`: string
* `kind`: enum string
* `name`: string

Common `kind` values:

* `callable`
* `class`
* `constant`
* `enum`
* `field`
* `interface`
* `other`
* `property`
* `unit`

Optional fields (omit if empty):

* `callable`: CallableSpec (only when `kind: callable`)
* `children`: list[Entry] (child nodes)
* `decorators`: list[Decorator] (observed syntax only)
* `extra`: map
* `inferred`: map (only if enabled)
* `modifiers`: list[string] (observed keyword modifiers only)
* `notes`: string
* `signature`: string (callables only, observed)
* `test`: TestGuide
* `type`: TypeRef (for non callables when meaningful)
* `visibility`: `public`, `protected`, `private`, `package`, `internal`
  (observed where available)

#### Entry Full Shape Template

```yaml
callable: null
children: []
decorators: []
extra: {}
id: "C000"
inferred: {}
kind: "unit"
modifiers: []
name: "example"
notes: ""
signature: ""
test: null
type: null
visibility: null
```

### Decorator

Decorator captures observed decorator (for example `@staticmethod` in
Python) or annotation syntax (for example `@Deprecated` in Java).

Required:

* `name`: string, copy the exact token, like `staticmethod` or `Deprecated`

Optional (omit if empty):

* `args`: list, only if syntactically present
* `extra`: map
* `kwargs`: map, only if syntactically present
* `notes`: string

Rule: do not put keyword modifiers here.

#### Decorator Full Shape Template

```yaml
args: []
extra: {}
kwargs: {}
name: ""
notes: ""
```

### Modifiers

`modifiers` is only for observed keyword modifiers, for example:

* `abstract`, `final`, `private`, `protected`, `public`, `static`

Python note: Python usually has no keyword modifiers. Do not invent them.

### TypeRef

TypeRef describes a type.

Do not force or fabricate structure. If you only have a type string,
then `name` is enough.

Required:

* `name`: string (type text)

Optional (omit if empty):

* `args`: list[TypeRef] (only if you have structured generics)
* `extra`: map
* `notes`: string
* `qualname`: string (fully qualified name, if known)
* `unit`: string (where the type comes from, if known)

#### TypeRef Full Shape Template

```yaml
args: []
extra: {}
name: ""
notes: ""
qualname: null
unit: null
```

### CallableSpec

`callable` exists only on entries where `kind: callable`.

Required fields:

* `branches`: list[BranchSpec] (always present, even for a single path)
* `params`: list[ParamSpec] (can be empty for parameterless callables)

Optional fields (omit if empty):

* `extra`: map
* `inferred`: map (only if enabled)
* `integration`: IntegrationSection (facts only, optional)
* `notes`: string
* `returnType`: TypeRef (observed when available)
* `test`: TestGuide
* `throws`: list[TypeRef] (observed where language supports it)

#### CallableSpec Full Shape Template

```yaml
extra: {}
branches: []
inferred: {}
integration: null
notes: ""
params: []
returnType: null
test: null
throws: []
```

### ParamSpec

Required:

* `name`: string

Optional (omit if empty):

* `decorators`: list[Decorator] (observed if language supports it)
* `default`: any (observed literal)
* `extra`: map
* `modifiers`: list[string] (observed, for languages that support it)
* `notes`: string
* `test`: TestGuide
* `type`: TypeRef (observed)

#### ParamSpec Full Shape Template

```yaml
decorators: []
default: null
extra: {}
modifiers: []
name: "param_name"
notes: ""
test: null
type: null
```

### BranchSpec

Branches are the core of unit test generation.

Required:

* `condition`: string, copy close from code
* `id`: string
* `outcome`: string, observable in tests

Optional (omit if empty):

* `extra`: map
* `inferred`: map (only if enabled)
* `notes`: string
* `precondition`: string
* `test`: TestGuide

#### What counts as a branch

Capture explicit control flow:

* `if`, `elif`, `else`
* `match`, `case`
* `try`, `except`, `else`, `finally`
* loops: zero iterations vs. one or more iterations, plus `break` and
  `continue`
* short circuit and early exits: conditional `return`, `raise`, `yield`
* important: also singular execution paths

If you adopt extra rules, write them down and apply them consistently.
Otherwise, stick to the explicit control flow.

#### Outcome must be observable

Examples:

* return value category or shape
* exception type and key message substring
* yielded values
* mutation of an output object
* call made to a mocked dependency

Unreachable branches:

* set `outcome: UNREACHABLE (reason: ...)`
* do not write tests for unreachable branches

#### BranchSpec Full Shape Template

```yaml
condition: ""
extra: {}
id: ""
inferred: {}
notes: ""
outcome: ""
precondition: ""
test: null
```

### IntegrationSection

The `integration` section captures facts that model how information flows
between units, or to and from boundaries, and allows later derivation of
a flow ledger and integration test candidates.

Two buckets:

* `integration.interunit`: calls or touches to targets outside the
  current unit but within the project graph
* `integration.boundaries`: calls or touches that cross an external
  boundary surface

The two lists are modeled symmetrically.

Optional fields (omit if empty):

* `boundaries`: list[IntegrationFact]
* `extra`: map
* `interunit`: list[IntegrationFact]
* `notes`: string
* `test`: TestGuide

#### IntegrationSection Full Shape Template

```yaml
boundaries: []
extra: {}
interunit: []
notes: ""
test: null
```

### IntegrationFact

This section describes the details of an integration fact.

An important feature that should not be overlooked is the `executionPaths`
field, which lists all possible minimal and direct code paths that must be
executed for the integration to be invoked. For every path in `executionPaths`,
the final element must be the integration Branch ID. If this is ever empty, it
means that the integration is not executable. This indicates that the
integration branch is unreachable/dead code, and it must be reported in the
findings presented in Document 3.

In the situation where the integration is always called within its callable,
without conditions, then the `executionPaths` field may be populated with a
single path containing only the Branch ID of the integration.

Required:

* `executionPaths`: list[list[string]], lists of execution paths, where each
  execution path is a list of Branch IDs that comprise code paths that **must**
  end with the integration Branch ID, and result in the integration being
  invoked
* `id`: string, the value of the `BranchSpec` `id` field that represents the
  integration invocation branch, and **prefixed with the letter "I"**
* `target`: string, stable logical identifier, prefer fully qualified

Optional (omit if empty):

* `boundary`: BoundarySummary
* `condition`: string, only if conditional
* `contract`: ContractSummary
* `extra`: map
* `inferred`: map (only if enabled)
* `kind`: `call`, `construct`, `import`, `dispatch`, `io`, `other`
* `notes`: string
* `signature`: string, only if readily available, do not guess
* `test`: TestGuide
* `via`: string, intermediary helper name if meaningful

Boundary note: boundary crossings still happen via calls. The boundary bucket is
classification, not a different mechanic.

#### IntegrationFact Full Shape Template

```yaml
boundary: null
condition: null
contract: null
executionPaths: []
extra: {}
id: ""
inferred: {}
kind: ""
notes: ""
signature: ""
target: ""
test: null
via: null
```

### ContractSummary

ContractSummary is a language agnostic summary of an integration target's call
contract. Use it when the signature level facts are known and useful, but do not
guess.

This shape is used in `IntegrationFact.contract`.

Optional (omit if empty):

* `extra`: map
* `interaction`: string, one of `request_response`, `fire_and_forget`,
  `stream_out`, `stream_in`, `pubsub`, `async_job`, `other`
* `notes`: string
* `params`: list[ContractParam]
* `raises`: list[TypeRef]
* `returnType`: TypeRef
* `signature`: string, human readable contract signature

#### ContractSummary Full Shape Template

```yaml
extra: {}
interaction: null
notes: ""
params: []
raises: []
returnType: null
signature: ""
```

### ContractParam

ContractParam is a contract level parameter summary. It is independent of the
declaring callable's ParamSpec list because it describes the integration target
contract, not the caller.

This shape is used in `ContractSummary.params`.

Required:

* `name`: string

Optional (omit if empty):

* `extra`: map
* `notes`: string
* `type`: TypeRef

#### ContractParam Full Shape Template

```yaml
extra: {}
name: ""
notes: ""
type: null
```

### BoundarySummary

BoundarySummary describes what external surface is implicated by an integration
fact. Boundary crossings still occur via calls, but this captures the external
system metadata.

This shape is used in `IntegrationFact.boundary`.

Required:

* `kind`: string, one of `filesystem`, `database`, `network`,
  `subprocess`, `message_bus`, `clock`, `randomness`, `env`, `other`

Optional (omit if empty):

* `endpoint`: string, host, service, url, topic, queue, etc.
* `extra`: map
* `notes`: string
* `operation`: string, query, read, write, publish, consume, execute, etc.
* `protocol`: string, http, grpc, sql, amqp, kafka, etc.
* `resource`: string, table, bucket, path, collection, etc.
* `system`: string, postgres, s3, kafka, http-service-name, etc.

#### BoundarySummary Full Shape Template

```yaml
endpoint: null
extra: {}
kind: ""
notes: ""
operation: null
protocol: null
resource: null
system: null
```

### TestGuide

The test guide section allows the specification of test-related hints or
other information to facilitate or guide test generation.

Omit unless populated.

Suggested fields:

* `extra`: map
* `fakes`: list[string|FakeSpec]
* `fixtures`: list[string]
* `mocks`: list[MockDirective]
* `notes`: string
* `proof`: list[ProofPoint]
* `setup`: string

#### TestGuide Full Shape Template

```yaml
extra: {}
fakes: []
fixtures: []
mocks: []
notes: ""
proof: []
setup: ""
```

### FakeSpec

FakeSpec describes a fake implementation used by tests. This is not tied
to any framework. It is a compact inventory entry, so humans and AI can
use the same fake consistently.

This shape is used in `TestGuide.fakes`.

Required:

* `name`: string, short stable name for the fake (often the class name)

Optional (omit if empty):

* `constructor`: string, how it is constructed (signature or factory name)
* `extra`: map
* `kind`: string, one of `class`, `object`, `function`, `module`, `other`
* `language`: string, if the fake is in a different language than the unit
* `location`: string, where it lives (file path, module path, package)
* `notes`: string
* `params`: list[ContractParam], constructor or factory params
* `provides`: list[string], key behaviors or capabilities it provides
* `target`: string, what this fake stands in for (prefer fully qualified)

#### FakeSpec Full Shape Template

```yaml
constructor: ""
extra: {}
name: ""
kind: ""
language: ""
location: ""
notes: ""
params: []
provides: []
target: ""
```

### MockDirective

MockDirective is a small, tooling agnostic way to say: mock this target with
this behavior. It is intentionally not tied to pytest, mockk, Mockito, or
anything else.

This shape is used in `TestGuide.mocks`.

Required:

* `behavior`: string, one of `return`, `raise`, `yield`, `side_effect`, `patch`
* `target`: string, import path, or conceptual target

Optional (omit if empty):

* `argsShape`: string, brief description of expected args
* `count`: int, expected call count
* `extra`: map
* `notes`: string
* `value`: any, returned value or raised exception detail

#### MockDirective Full Shape Template

```yaml
argsShape: ""
behavior: ""
count: null
extra: {}
notes: ""
target: ""
value: null
```

### ProofPoint

ProofPoint is a small, tooling agnostic description of what observation proves a
branch. Think of it as an assertion spec, without binding to a test framework.

This shape is used in `TestGuide.proof`.

Required:

* `kind`: string, one of `raises`, `returns`, `calls`, `mutates`, `logs`,
`other`

Optional (omit if empty):

* `category`: string, semantic category (invalid_argument, not_found, etc.)
* `extra`: map
* `messageContains`: list[string], substrings expected in a message
* `notes`: string
* `target`: string, target of call, mutation, or log
* `type`: TypeRef, expected type (exception type or return type)
* `valueShape`: string, high level description of value shape

#### ProofPoint Full Shape Template

```yaml
category: ""
extra: {}
kind: ""
messageContains: []
notes: ""
target: ""
type: null
valueShape: ""
```

## Field placement contract

This is the primary guardrail for putting the right values in the right fields.

### Decorators vs. modifiers

* `decorators`: observed decorator or annotation syntax

  * Python: any `@something` line applied to an entry
  * Java and Kotlin: any `@Annotation` applied to an entry
  * Store as Decorator objects
  * Never put keyword modifiers here

* `modifiers`: observed keyword modifiers

  * Java and Kotlin: `public`, `private`, `static`, `final`, etc
  * Python: generally omit, do not invent them
  * Never put decorator names here (`staticmethod`, `classmethod`, `dataclass`,
    etc.)

### Inferred semantics

Default is observed only.

If and only if inferred semantics are enabled for a workflow, inferred facts
must live under `inferred`. They must not be placed into `modifiers`,
`decorators`, or other observed fields.

## Branch IDs and deterministic numbering

This section is non-negotiable. If IDs are sloppy, the ledger loses most of its
power.

The whole point of this enumeration is that an AI (or a human) can walk a list
and write tests for every branch, which tends to drive you toward 100% branch
coverage. A coverage tool is still the proof, but the ledger is what makes the
work predictable, reliable, and fast.

### Branch entry format

Even though the YAML format stores branches as objects, think of every branch
entry as this mini spec:

* `<branch_id>: <exact condition or pattern> -> <observable outcome>`

Each entry describes a location in the code (by unique ID), the branch condition
or pattern (copied close to source), and the expected outcome in a test.

### Abbreviations

Use the following abbreviations:

* `C000` = unit ID (constant; always the current unit)
* `Cxxx` = class ID (starts at `C001`)
* `Fxxx` = unit level function ID (def at file scope)
* `Mxxx` = method ID (def inside a class)
* `Bxxxx` = branch ID
* `Nxxx` = nested ID (applies to classes and defs)

### Fully qualified IDs only

ID format is always fully qualified (scoped). Do not use unscoped IDs like
`F001B0001`.

* Use `C000F001B0001, C000F001B0002, ..., C000F003B0001, ...` for unit-level
  functions.
* Use `C001M001B0001, C001M001B0002, ..., C002M003B0001, ...` for class methods.

### Numbering scheme per ledger

#### Units (File, Module, etc.)

* The unit is always `C000` (constant).
* `C000` prefixes are used only for unit level callables (def at file scope).
* Do not prefix classes with `C000`. See the Classes section for class IDs.
* If you see an ID that begins with `C000Mxxx`, that is invalid (methods are
  never unit scoped).
* If you see an ID that begins with `C000Cxxx`, that is invalid (classes do not
  use the unit prefix).
* This ensures all unit level function branch IDs are fully namespaced and
  unique.

#### Classes

* Classes are numbered starting at `C001`.
* Assigned in file order, top to bottom.
* Required for all classes; without them, method IDs would be ambiguous.

#### Unit level functions

* Unit functions are numbered starting at `F001` within the unit (`C000`).
* Assigned in file order, top to bottom.
* Required for all unit level functions.

#### Methods

* Methods are numbered starting at `M001` within each class (`Cxxx`).
* Assigned in the order within the class definition, top to bottom.
* Required for all class methods.

#### Branches

* Branches are numbered starting at `B0001` within each function or method.
* Assigned in order of appearance in the code.

#### Nesting

Use `Nxxx` appended to the parent designator.

Classes:

* For class `C001`, the first nested class is designated `C001N001`.
* Reminder: classes within their unit do not require the unit (`C000`) prefix.

Unit level functions:

* For unit function `C000F001`, the first nested def is designated
  `C000F001N001`.

Methods:

* For method `C001M001`, the first nested def is designated `C001M001N001`.

Branches:

* Nesting does not apply to branches, but the branch ID is still appended to the
  end (for example `C001M001N001B0001`).

When to use nested IDs:

* Use `Nxxx` only for named nested defs (def or class) that are referenced as
  objects or meaningfully testable in isolation.
* If the nested def is purely an implementation detail and not directly
  targeted, treat its control flow as branches of the parent and do not assign
  an `Nxxx`.

#### Leading zeros

* Leading zeros are used to maintain a consistent length.
* Leading zeros are mandatory.

#### Composition order and grammar

IDs must be composed in this order:

1. Scope (`C000` for the unit, or `Cxxx` for classes)
2. Nested scope (`Nxxx` as needed for classes, appended immediately after its
   parent scope: `CxxxNxxx`)
3. Callable (`Fxxx` for unit functions, or `Mxxx` for class methods)
4. Nested callable (`Nxxx` as needed, appended immediately after its parent
   callable)
5. Branch (`Bxxxx`)

Grammar, where a preceding question mark indicates optional:

* Unit level: `C000<function_id><?nested_id><branch_id>`
* Class level: `<class_id><?nested_class_id><method_id><?nested_id><branch_id>`

Full examples:

* First branch of first unit function: `C000F001B0001`.
* First branch of first nested def inside first unit function:
  `C000F001N001B0001`.
* First branch of first method in first class: `C001M001B0001`.
* First branch of first nested def inside first method of first nested class:
  `C001N001M001N001B0001`.

This ensures that:

* all branch IDs will be unique per ledger.
* IDs deterministically indicate the exact location in the code.
* edits to one function or method do not force renumbering across the entire
  ledger.

Apply this scheme consistently across the entire unit ledger.

## Document 3: Ledger Generation Review (Required)

Purpose: record noteworthy items produced or noticed during ledger creation that
require reviewer attention. This document is for review signals, not for the
main inventory. The document must be present, even if there are no findings.

### Required fields

* `docKind`: must be `ledger-generation-review`
* `schemaVersion`: schema version string (start with "1")
* `unit.name`: stable unit name (unit path, file stem, etc.)
* `unit.language`: `python`, `java`, `kotlin`, etc

### Optional fields (omit if empty)

* `extra`: map
* `notes`: string

### Findings

`findings` is the only list in this document. It contains small, structured
review items. Each finding should be written so a human can understand it
quickly and decide whether action is needed.

Optional (omit if empty):

* `findings`: list[Finding]

#### Finding

Required:

* `category`: `deviation`, `assumption`, `ambiguity`, `gap`, `anomaly`
* `message`: string, short and specific
* `severity`: `info`, `warn`, `error`

Optional (omit if empty):

* `appliesTo`: string or list[string]
  * prefer ledger IDs (Entry IDs, Branch IDs, etc.)
  * if no ID applies, use a stable address selector
* `evidence`: Evidence
* `extra`: map
* `notes`: string
* `recommendedAction`: string

##### Finding Full Shape Template

```yaml
appliesTo: null
category: "assumption"
evidence: null
extra: {}
message: ""
notes: ""
recommendedAction: ""
severity: "info"
```

#### Evidence

Evidence exists to point a reviewer at the source quickly.

Optional (omit if empty):

* `address`: string
  * same concept as Document 1 addresses
  * examples: qualified name plus line number, signature text, AST path
* `lineEnd`: int
* `lineStart`: int
* `snippet`: string, short excerpt (do not paste large blocks)

##### Evidence Full Shape Template

```yaml
address: ""
lineEnd: null
lineStart: null
snippet: ""
```

### Document 3 example

```yaml
docKind: ledger-generation-review
schemaVersion: "1"
unit:
  name: "project_resolution_engine.internal.resolvelib"
  language: "python"
findings:
  - severity: warn
    category: ambiguity
    message: "Decorator arguments could not be parsed reliably"
    appliesTo: C001M003
    evidence:
      address: "C000::ProjectResolutionProvider._best_hash@L81"
      lineStart: 79
      lineEnd: 84
    recommendedAction: "Confirm decorator args or omit them"
```

## Ledger generation procedure

### 1) Identify scope

One unit only:

* all top-level classes in file order
* all unit level callables in file order
* all methods in class body order
* allow multiple classes in one file

### 2) Assign IDs (doc 1)

Assign IDs deterministically:

* class IDs in file order
* unit function IDs in file order
* method IDs in class body order
* branch IDs in appearance order per callable

### 3) Emit structure (doc 2)

Create the entry tree:

* `unit.entries` includes unit level callables and type entries
* type entries include method entries under `entries`
* callables include `callable` with `params` and `branches`

### 4) Enumerate branches per callable

Walk top down and capture every branch per the branch rules above.

### 5) Capture integration facts

Capture integration facts:

* record interunit edges and boundary crossings as atomic facts
* do not record sequences
* do not invent signatures

### 6) Enumerate review findings (doc 3, optional)

If there were notable deviations, ambiguities, gaps, or anomalies, emit Document
3 with `findings`.

### 7) Use it

* Generate unit tests from branches.
* Use coverage tools as the proof.
* When unit tests are stable, use integration facts to derive a flow ledger and
  integration test plans.

## Minimal example

```yaml
docKind: derived-ids
schemaVersion: "1"
unit:
  name: "example"
  language: "python"
  unitId: "C000"
assigned:
  entries:
    - id: C000F001
      kind: callable
      name: do_thing
      address: "C000::do_thing@L1"
  branches:
    - id: C000F001B0001
      parent: C000F001
      address: "C000::do_thing@if x@L2"
      summary: "x truthy"
---
docKind: ledger
schemaVersion: "1"
unit:
  id: C000
  name: "example"
  kind: unit
  children:
    - id: C000F001
      name: do_thing
      kind: callable
      signature: "do_thing(x)"
      callable:
        params:
          - name: x
        branches:
          - id: C000F001B0001
            condition: "if x"
            outcome: "returns 1"
          - id: C000F001B0002
            condition: "else"
            outcome: "returns 0"
---
docKind: ledger-generation-review
schemaVersion: "1"
unit:
  name: "example"
  language: "python"
findings:
  - severity: info
    category: assumption
    message: "No notable findings"
```
