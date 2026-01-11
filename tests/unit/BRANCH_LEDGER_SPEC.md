## Ledger generation procedure (must follow exactly)

### 1) Scope

- Identify the unit under test:
  - module name
  - each top-level function
  - each class method defined in the module

- Do not include branches from other modules.

### 2) Per function or method sections

For each top-level function and each class method, create a header:

- `## <name>(<params>)`

### 3) Enumerate branches top to bottom

Walk the code in order and record every code execution path and branch point:

- **all execution paths**
  - even if it is a single statement, and no branches or alternative paths

- **if / elif / else**
  - each `if` condition is a branch
  - each `elif` condition is a branch
  - each `else` block is a branch (describe as inverse of prior conditions)

- **match / case**
  - each `case` arm is a branch
  - copy the case pattern text exactly (example: `case datetime() | date():`)

- **try / except / else / finally**
  - each `except <Type>` handler is a branch
  - `except Exception` is its own branch
  - `else` and `finally` blocks are branches if present

- **loops**
  - every `for` / `while` has at least:
    - loop executes 0 times
    - loop executes ≥ 1 time
  - every `break` and `continue` is its own branch

- **early exit / short circuit**
  - every conditional `return`, `raise`, `yield`, or generator termination path is a branch

- **comprehensions**
  - any `if` filter inside a comprehension counts as a branch

### 4) Branch entry format

This especially helps when you are leveraging generative AI to help you write comprehensive
tests for your code. The ledger, with its meticulously crafted branch enumeration, ensures
that AI can follow a list and ensure that it creates tests for every branch, resulting in
comprehensive (100% branch) coverage. Below, the rules are a detailed and unambiguous guide
for generative AI to create the branch ledger. Humans can iterate with a coverage tool and
end up with 100% coverage, but even if you are writing the tests, yourself, having a ledger
can help with the process. 

For every branch, add an entry exactly like this:

- `<branch_id>: <exact condition or pattern> -> <observable outcome>`

Think of all of these entries like mini test specifications. Each entry describes a location
in the code, by unique identifier, a detail describing that branch, and the expected outcome.

Rules:
- Use the following abbreviations:
  - `C000` = module ID (constant; always the current module)
  - `Cxxx` = class ID (starts at `C001`)
  - `Fxxx` = module-level function ID (functions defined at module scope)
  - `Mxxx` = method ID (functions defined inside a class)
  - `Bxxxx` = branch ID
  - `Nxxx` = nested ID (applies to classes and functions/methods)
- ID format is always fully qualified (scoped). Do NOT use unscoped IDs like `F001B0001`.
  - Use `C000F001B0001, C000F001B0002, ..., C000F003B0001, ...` for module functions.
  - Use `C001M001B0001, C001M001B0002, ..., C002M003B0001, ...` for class methods.
- The numbering scheme per ledger:
  - Modules:
    - The module is always `C000` (constant).
    - `C000` prefixes are used ONLY for module-level callables (i.e., `def ...` at file scope).
    - Do NOT prefix classes with `C000`; see the `Classes` section for class IDs.
    - If you see an ID that begins with `C000Mxxx`, that is invalid (methods are never module scoped).
    - If you see an ID that begins with `C000Cxxx`, that is invalid (classes do not use the module prefix).
    - This ensures all module-level function branch IDs are fully namespaced and unique.
  - Classes:
    - Classes are numbered starting at `C001`.
    - Assigned in file order, top to bottom.
    - Required for all classes; without them, method IDs would be ambiguous.
  - Module-level functions:
    - Module functions are numbered starting at `F001` within the module (`C000`).
    - Assigned in file order, top to bottom.
    - Required for all module-level functions.
  - Methods:
    - Methods are numbered starting at `M001` within each class (`Cxxx`).
    - Assigned in the order within the class definition, top to bottom.
    - Required for all class methods.
  - Branches:
    - Branches are numbered starting at `B0001` within each function/method.
    - Assigned in order of appearance in the code.
  - Nesting: use `Nxxx` appended to the parent designator
    - Classes:
      - For class `C001`, the first nested class would be designated `C001N001`.
      - Reminder: classes within their module do not require the module (`C000`) prefix.
    - Module-level functions:
      - For module function `C000F001`, the first nested def would be designated `C000F001N001`.
    - Methods:
      - For method `C001M001`, the first nested def would be designated `C001M001N001`.
    - Branches:
      - Not applicable for nesting, but the branch ID is still appended to the end
        (e.g., `C001M001N001B0001`).
    - When to use:
      - Use `Nxxx` only for named nested defs (def / class) that are referenced as objects or meaningfully
        testable in isolation.
      - If the nested def is purely an implementation detail and not directly targeted, treat its control
        flow as branches of the parent and do not assign an `Nxxx`.
  - Leading zeros:
    - Leading zeros are used to maintain a consistent length.
    - Leading zeros are mandatory.
  - Ordering:
    - IDs must be composed in this order:
      1. Scope (`C000` for the module, or `Cxxx` for classes)
      2. Nested scope (`Nxxx` as needed for classes, appended immediately after its parent scope: `CxxxNxxx`)
      3. Callable (`Fxxx` for module functions, or `Mxxx` for class methods)
      4. Nested callable (`Nxxx` as needed, appended immediately after its parent callable)
      5. Branch (`Bxxxx`)
    - Grammar, where a preceding question mark indicates optional/as-needed:
      - Module level (not within a class): `C000<function_id><?nested_id><branch_id>`
      - Class level: `<class_id><?nested_class_id><method_id><?nested_id><branch_id>`
    - Full examples:
      - First branch of first module function: `C000F001B0001`.
      - First branch of first nested def inside first module function: `C000F001N001B0001`.
      - First branch of first method in first class: `C001M001B0001`.
      - First branch of first nested def inside first method of first nested class: `C001N001M001N001B0001`.
  - This ensures that:
    - all branch IDs will be unique per ledger.
    - IDs deterministically indicate the exact location in the code.
    - edits to one function/method do not force renumbering across the entire ledger.
  - The scheme must be applied consistently across the entire module ledger.
- Condition/pattern must match the code text as closely as possible.
- Outcome must be observable in a test:
  - return value
  - raised exception type and key message substring
  - yielded values
  - mutation of an output object
  - a call made to a mocked dependency

### 5) Unreachable branches

If a branch cannot be triggered without violating unit boundaries or requires an impossible state:

- `<branch_id>: <condition> -> UNREACHABLE (reason: ...)`

Do not write a test for unreachable branches.

### 6) Ledger completeness checklist

After the ledger, include a checklist confirming:
- all `if` / `elif` / `else` captured
- all `match` / `case` arms captured
- all `except` handlers captured
- all early `return`s / `raise`s / `yield`s captured
- all loop 0 vs ≥ 1 iterations captured
- all `break` / `continue` paths captured

---

## Ledger template

This section includes a template example ledger for reference. It lists section
headers that provide context for each section, fully namespaced branch IDs, and
generalized/templated conditions and outcomes.

```python
# ==============================================================================
# BRANCH LEDGER: <MODULE_NAME> (C000)
# ==============================================================================
#
# ------------------------------------------------------------------------------
# ## my_module_level_function(arg1, arg2)
#    (Module ID: C000, Function ID: F001)
# ------------------------------------------------------------------------------
# C000F001B0001: <condition / detail> -> <result>
# C000F001B0002: <condition / detail> -> <result>
# C000F001B0003: <condition / detail> -> <result>
# C000F001B0004: <condition / detail> -> <result>
# C000F001B0005: <condition / detail> -> <result>
# C000F001B0006: <condition / detail> -> <result>
# C000F001B0007: <condition / detail> -> <result>
# C000F001B0008: <condition / detail> -> <result>
#
# ------------------------------------------------------------------------------
# ## MyClass.first_instance_method(self, data)
#    (Class ID: C001, Method ID: M001)
# ------------------------------------------------------------------------------
# C001M001B0001: <condition / detail> -> <result>
# C001M001B0002: <condition / detail> -> <result>
# C001M001B0003: <condition / detail> -> <result>
# C001M001B0004: <condition / detail> -> <result>
# C001M001B0005: <condition / detail> -> <result>
# C001M001B0006: <condition / detail> -> <result>
#
# ------------------------------------------------------------------------------
# LEDGER COMPLETENESS CHECKLIST
#   [ ] all `if` / `elif` / `else` captured
#   [ ] all `match` / `case` arms captured
#   [ ] all `except` handlers captured
#   [ ] all early `return`s / `raise`s / `yield`s captured
#   [ ] all loop 0 vs >= 1 iterations captured
#   [ ] all `break` / `continue` paths captured
# ==============================================================================
```
