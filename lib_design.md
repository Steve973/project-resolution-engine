# Project Resolution Engine design (pip-shaped, strategy-driven)

## Primary Goal
Create a standalone Python library that exposes a stable, reusable API for
dependency resolution and graph output, without pip internal types and without
client entanglement.

It should feel like: “pip never gave you an API for resolution, so here it is.”

## Requirements
* No install, uninstall, build, or wheel preparation lifecycle (pip does those).
* No opinionated on disk cache in core (clients can add that as an optional
  extension).
* The library is like a framework that uses provider strategies, both built-in
  and discoverable via entry points.

## Constraints and principles
* Keep the public API small and stable.
* Keep resolvelib as an internal implementation detail.
* The strategy system uses config-driven construction, entry point discovery,
  precedence ordering.
* Built-in caching is in-memory-only by default.
* Observability must exist without importing client logging or audit models.

---

## What we take from pip (shape, not implementation)
pip’s resolvelib integration is cleanly separated into:
* Resolver orchestrator that wires everything together and calls resolvelib.
* Provider implementation that satisfies resolvelib’s API and delegates to
  requirement and candidate objects.
* Factory as the stateless service layer that creates Candidate and Requirement
  objects and provides shared services.

pip’s implementation is tightly coupled to installation concerns
 - InstallRequirement
 - WheelCache
 - RequirementPreparer
 - etc.
We do not reuse that code, but we mirror the same decomposition to keep the
system understandable and extensible.

---

## What we keep from your approach (core differentiators)
* Strategy-based artifact acquisition and fallback:
  * PEP 691 project index metadata
  * PEP 658 sidecar core metadata
  * fallback: select wheel, fetch wheel, extract dist info METADATA
* WheelKey identity and late set metadata (actual_tag, satisfied_tags,
  origin_uri), so caching keys stay stable across runs.
* Deterministic candidate selection via tag policy that prefers most
  universal acceptable wheels.
* The result is an engine-owned graph model, not pip or resolvelib internals.

---

## Proposed architecture

### Public API modules
* `project_resolution_engine/engine.py`
  * `resolve(root_requirements, env, strategies, cache, trace) ->
    ResolutionResult`
  * Optional: `resolve_many(contexts) -> list[ResolutionResult]` later

* `project_resolution_engine/env.py`
  * `default_marker_environment() -> Mapping[str, str]`
  * `default_tags() -> Sequence[packaging.tags.Tag]`
  * Types: `ResolutionEnvironment` for marker env plus tags

* `project_resolution_engine/models.py`
  * `WheelKey` and WheelKeyMetadata
  * `ResolvedNode`, `ResolvedEdge`, `ResolvedGraph`
  * `ResolutionResult` and error models

* `project_resolution_engine/providers.py` (name can stay providers, but it
  exposes your real bases)
  * `ArtifactResolutionStrategy[TConfig]`
  * `BaseMetadataResolutionStrategy[TMetaCfg]`
  * `BaseWheelResolutionStrategy[TWheelCfg]`
  * Strategy config base types and the mapping round trip hooks

Public means: third party strategy authors can import these and implement
strategies without importing internal modules.

### Internal modules (allowed to change)
* `_internal/resolver_adapter.py`
  * The typed boundary around resolvelib calls and DirectedGraph API differences
    (your typed choke point concept)
  * Never exported publicly

* `_internal/factory.py`
  * Engine equivalent of pip’s Factory, but metadata first:
    * Candidate creation from index listings
    * Core metadata retrieval for a candidate
    * Requirement parsing from METADATA or sidecar content
  * Stateless services object held by provider and candidate objects, mirroring
    pip’s pattern.

* `_internal/provider.py`
  * resolvelib provider implementation
  * Identifies requirements and candidates, orders preferences, and calls
    find_matches
  * We take pip’s idea that identify and preference are provider
    responsibilities, but our preference includes your tag policy ranking rather
    than pip’s install focused heuristics.

* `_internal/requirements.py` and `_internal/candidates.py`
  * Engine-owned Requirement and Candidate classes that meet the internal API
    the provider expects
  * No pip InstallRequirement

* `_internal/trace.py`
  * Trace events similar to pip’s Reporter separation, but minimal and library
    safe.

* `_internal/strategy_loader.py`
  * Entry point discovery, registry, ordering

* `_internal/tag_policy.py`
  * Candidate ranking and tag preference

* `_internal/cache/` (core is in memory only)
  * In memory caches for:
    * project index JSON (PEP 691)
    * core metadata bytes (PEP 658 and fallback extracted METADATA)
    * optionally: resolved result cache for repeated roots in long-lived
      processes
  * Optional disk persistence lives in a separate extra or sibling package, not
    core.

---

## Strategy contracts
We keep the existing contract model:

### Metadata strategies
* `BaseMetadataResolutionStrategy`
  * `resolve(dest_dir, uri or wheel_key) -> ArtifactResolutionResult`
  * `fetch_metadata(...) -> bytes` or equivalent

Concrete built-ins:
* PEP 691 project metadata strategy
* PEP 658 sidecar core metadata strategy
* Wheel inspection fallback strategy (depends on wheel resolver)

### Wheel strategies
* `BaseWheelResolutionStrategy`
  * `resolve(dest_dir, uri or wheel_key) -> ArtifactResolutionResult`
  * `fetch_wheel(...) -> bytes` or equivalent

Concrete built in:
* HTTP wheel download strategy

### Coordinator resolvers
The resolvers are not “providers”; they are coordinators that:
* Choose which strategy to run
* Apply precedence ordering
* Apply cache lookup and store
* Implement fallback logic

These remain engine internal unless you want them explicitly part of the public
extension surface.

---

## Resolution workflow (single environment context)
1. Build `ResolutionEnvironment`:
   * tags: supported tags for the target environment
   * marker env mapping: keys used for marker evaluation (python_version,
     sys_platform, platform_machine, etc.)

2. Root requirements:
   * From user input (name pins, or name and version derived from root wheels)

3. Provider find_matches:
   * Query index strategy to list candidate files for a project (PEP 691)
   * Filter candidates by compatible tags
   * Rank candidates by tag policy preference (prefer most universal acceptable
     wheel)
   * Choose the best candidate per version, then let resolvelib choose a version
     according to constraints

4. Candidate dependencies:
   * Attempt core metadata fetch via PEP 658 sidecar
   * If unavailable or invalid, fallback:
     * choose candidate wheel URI that was already selected
     * use wheel resolver strategy to fetch wheel
     * extract dist info METADATA bytes
   * Parse Requires Dist, evaluate markers using marker env mapping
   * Return dependencies as Requirement objects

5. Run resolvelib and translate result to engine owned graph model.
pip’s Resolver does installation set construction after resolution, which we do
not do.

---

## Preference and narrowing policies
We adopt pip’s idea that the provider is responsible for preference ordering and
narrowing selection.

Our preference inputs differ:
* pip prioritizes direct, pinned, upper bound, user ordering, etc.
* we prioritize:
  * deterministic, most universal acceptable wheel for a version
  * stable tiebreaks by filename and origin
  * optional: user specified constraints ordering only if explicitly requested
    (keep default predictable)

Optional future improvement inspired by pip:
* narrow selection for “fast fail” checks like Requires Python. pip does this
  with a special identifier and checks it first.
We can implement a similar internal pseudo requirement to fail early on
incompatible python constraints, but without pip’s installation machinery.

---

## Caching policy
Core library ships in memory caches only:
* cache project index JSON per project and index base URL
* cache core metadata bytes per file URL and hash if available
* optionally cache parsed requirements for a METADATA payload

Disk persistence is an optional extension:
* separate package or extra, provided/used by a client
* implements the same cache interface but persists entries and indexes on disk

Rationale:
* library default should not write to disk
* PyChub can opt into persistence for build plan reuse

---

## Trace and reporting
Mirror pip’s reporter concept but minimal:
* `trace(event_name: str, payload: Mapping[str, Any]) -> None`

Emit events from:
* strategy selection and fallback
* cache hit, miss
* metadata fetch success, failure
* resolvelib rounds and outcome

This gives debuggability without importing PyChub audit models.

---

## Migration mapping from current PyChub derived modules
Goal is a mechanical move first, then refine.

Phase 1: port as is, fix imports
* Move strategy base classes:
  * artifact_resolution_strategy.py
  * metadata_strategy.py
  * wheel_strategy.py
* Move coordinator resolvers:
  * artifact_resolution.py
* Replace PyChub types:
  * WheelKey, cache models, toml utils, multiformat mixin

Phase 2: refit into pip-shaped internals
* Extract internal Factory responsibilities from existing resolver logic:
  * “how to get candidates”
  * “how to get metadata for a candidate”
  * “how to parse requirements”
* Make Provider the only resolvelib boundary

Phase 3: optional extension packages
* cachefs extra
* builder provider future work

---

## Open decisions (explicit)
1. Public or internal status of coordinator resolvers
   * Default: internal
   * If you want people to swap fallback chains, make them public and stable

2. Marker environment typing
   * Ensure env module returns Mapping[str, str] for packaging marker
     evaluation, not an Environment object.
   * Keep a separate type for installed distributions environment if ever
     needed.

3. Entry point group names
   * Choose stable group strings under this package and never change them once
     released.

---

## References (raw pip resolvelib files)
Use these only as architectural comparison, not as reusable code.
* https://raw.githubusercontent.com/pypa/pip/refs/heads/main/src/pip/_internal/resolution/resolvelib/base.py
* https://raw.githubusercontent.com/pypa/pip/refs/heads/main/src/pip/_internal/resolution/resolvelib/candidates.py
* https://raw.githubusercontent.com/pypa/pip/refs/heads/main/src/pip/_internal/resolution/resolvelib/factory.py
* https://raw.githubusercontent.com/pypa/pip/refs/heads/main/src/pip/_internal/resolution/resolvelib/found_candidates.py
* https://raw.githubusercontent.com/pypa/pip/refs/heads/main/src/pip/_internal/resolution/resolvelib/provider.py
* https://raw.githubusercontent.com/pypa/pip/refs/heads/main/src/pip/_internal/resolution/resolvelib/reporter.py
* https://raw.githubusercontent.com/pypa/pip/refs/heads/main/src/pip/_internal/resolution/resolvelib/requirements.py
* https://raw.githubusercontent.com/pypa/pip/refs/heads/main/src/pip/_internal/resolution/resolvelib/resolver.py
