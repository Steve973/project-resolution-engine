from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import pytest
from packaging.specifiers import SpecifierSet
from packaging.tags import Tag
from packaging.version import Version

import project_resolution_engine.internal.resolvelib as resolvelib_mod
from project_resolution_engine.internal.resolvelib import (
    ProjectResolutionProvider,
    _env_python_version,
    _expand_tags_for_context,
    _safe_url_basename,
    _version_sort_key,
    path_from_file_uri,
    resolve as resolve_via_resolvelib,
)
from project_resolution_engine.model.resolution import YankedWheelPolicy
from unit.helpers.models_helper import (
    FakeWheelKey,
    FakeWheelSpec,
    FakeResolverRequirement,
    FakeResolverCandidate,
    FakePep691FileMetadata,
    FakePep691Metadata
)


@pytest.fixture
def patch_pep691_metadata(monkeypatch):
    monkeypatch.setattr(resolvelib_mod, "Pep691Metadata", FakePep691Metadata, raising=True)


# ==============================================================================
# BRANCH LEDGER: resolvelib.py (C000)
# ==============================================================================
# Source: /mnt/data/resolvelib.py :contentReference[oaicite:0]{index=0}
# Spec: /mnt/data/BRANCH_LEDGER_SPEC.md :contentReference[oaicite:1]{index=1}
#
# Classes (top to bottom):
#   C001 = ProjectResolutionProvider
#
# Module functions (top to bottom):
#   C000F001 = _expand_tags_for_context
#   C000F002 = _safe_url_basename
#   C000F003 = path_from_file_uri
#   C000F004 = _env_python_version
#   C000F005 = _version_sort_key
#   C000F006 = resolve
# ------------------------------------------------------------------------------
#
#
# ------------------------------------------------------------------------------
# ## _expand_tags_for_context(*, python_version: Version, context_tag: Tag) -> frozenset[Tag]
#    (Module ID: C000, Function ID: F001)
# ------------------------------------------------------------------------------
# C000F001B0001: context_tag.interpreter.startswith("cp") and context_tag.interpreter[2:].isdigit() -> returns frozenset including base tags plus {Tag(cp,"abi3",plat), Tag(cp,"none",plat)}
# C000F001B0002: else (not (context_tag.interpreter.startswith("cp") and context_tag.interpreter[2:].isdigit())) -> returns frozenset containing only the initial 5 tags set (no cp abi fallbacks)
#
#
# ------------------------------------------------------------------------------
# ## _safe_url_basename(url: str) -> str
#    (Module ID: C000, Function ID: F002)
# ------------------------------------------------------------------------------
# C000F002B0001: if not base -> raises ValueError("URL has no path basename")
# C000F002B0002: else -> returns Path(unquote(parsed.path)).name
#
#
# ------------------------------------------------------------------------------
# ## path_from_file_uri(uri: str) -> Path
#    (Module ID: C000, Function ID: F003)
# ------------------------------------------------------------------------------
# C000F003B0001: if u.scheme != "file" -> raises ValueError("Expected file URI")
# C000F003B0002: else -> returns Path(url2pathname(u.path))
#
#
# ------------------------------------------------------------------------------
# ## _env_python_version(env: ResolutionEnv) -> Version
#    (Module ID: C000, Function ID: F004)
# ------------------------------------------------------------------------------
# C000F004B0001: full = env.marker_environment.get("python_full_version") is truthy -> raw is full; proceeds to parse Version(str(raw))
# C000F004B0002: else if short = env.marker_environment.get("python_version") is truthy -> raw is short; proceeds to parse Version(str(raw))
# C000F004B0003: else (full falsy and short falsy) -> raw is "0"; proceeds to parse Version("0")
# C000F004B0004: try: Version(str(raw)) succeeds -> returns Version(str(raw))
# C000F004B0005: except InvalidVersion -> returns Version("0")
#
#
# ------------------------------------------------------------------------------
# ## _version_sort_key(v: str) -> tuple[int, Version | str]
#    (Module ID: C000, Function ID: F005)
# ------------------------------------------------------------------------------
# C000F005B0001: try: Version(v) succeeds -> returns (1, Version(v))
# C000F005B0002: except InvalidVersion -> returns (0, v)
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider.__init__(self, *, services: ResolutionServices, env: ResolutionEnv, index_base: str = "https://pypi.org/simple") -> None
#    (Class ID: C001, Method ID: M001)
# ------------------------------------------------------------------------------
# C001M001B0001: init executes -> sets _services/_env/_index_base/_policy, initializes caches and requested extras dicts
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider.identify(self, requirement_or_candidate: ResolverRequirement | ResolverCandidate) -> str
#    (Class ID: C001, Method ID: M002)
# ------------------------------------------------------------------------------
# C001M002B0001: executes -> returns requirement_or_candidate.name
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._best_hash(item: Pep691FileMetadata) -> tuple[str, str] | None
#    (Class ID: C001, Method ID: M003)
# ------------------------------------------------------------------------------
# C001M003B0001: hashes = item.hashes or {} is falsy -> returns None
# C001M003B0002: hashes truthy and hashes.get("sha256") present -> returns ("sha256", <value>)
# C001M003B0003: hashes truthy and sha256 missing, hashes.get("sha512") present -> returns ("sha512", <value>)
# C001M003B0004: hashes truthy and sha256/sha512 missing, hashes.get("sha384") present -> returns ("sha384", <value>)
# C001M003B0005: hashes truthy but none of ("sha256","sha512","sha384") present -> returns None
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider.find_matches(self, identifier: str, requirements: Mapping[str, Iterator[ResolverRequirement]], incompatibilities: Mapping[str, Iterator[ResolverCandidate]]) -> Iterable[ResolverCandidate]
#    (Class ID: C001, Method ID: M004)
# ------------------------------------------------------------------------------
# C001M004B0001: executes -> name = canonicalize_name(identifier); req_list materialized; _update_requested_extras called; bad computed
# C001M004B0002: uri_candidates = self._build_uri_candidates(...) returns not None -> returns self._sort_candidates(uri_candidates)
# C001M004B0003: uri_candidates is None -> combined_spec computed; pep691 loaded; py_version computed; named_candidates built; returns self._sort_candidates(named_candidates)
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._materialize_requirements(requirements: Mapping[str, Iterator[ResolverRequirement]], name: str) -> list[ResolverRequirement]
#    (Class ID: C001, Method ID: M005)
# ------------------------------------------------------------------------------
# C001M005B0001: requirements.get(name, iter(())) is empty iterator -> returns []
# C001M005B0002: requirements.get(name, iter(())) yields >= 1 -> returns list containing all yielded requirements
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._update_requested_extras(self, name: str, req_list: Sequence[ResolverRequirement]) -> None
#    (Class ID: C001, Method ID: M006)
# ------------------------------------------------------------------------------
# C001M006B0001: if not req_list -> returns None (no mutation)
# C001M006B0002: for r in req_list executes 0 times -> extras_union remains empty; falls through to "if not extras_union"
# C001M006B0003: for r in req_list executes >= 1 time -> extras_union updated with r.extras
# C001M006B0004: if not extras_union -> returns None (no mutation)
# C001M006B0005: else (extras_union truthy) -> updates self._requested_extras_by_name[name] to union of existing and extras_union
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._compute_bad_set(name: str, incompatibilities: Mapping[str, Iterator[ResolverCandidate]]) -> set[tuple[str, str, str]]
#    (Class ID: C001, Method ID: M007)
# ------------------------------------------------------------------------------
# C001M007B0001: incompatibilities.get(name, iter(())) yields 0 -> returns empty set()
# C001M007B0002: incompatibilities.get(name, iter(())) yields >= 1 -> returns set of (c.name, c.wheel_key.version, c.wheel_key.tag) for all yielded candidates
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._build_uri_candidates(self, name: str, req_list: Sequence[ResolverRequirement], bad: set[tuple[str, str, str]]) -> list[ResolverCandidate] | None
#    (Class ID: C001, Method ID: M008)
# ------------------------------------------------------------------------------
# C001M008B0001: uri_reqs = [r for r in req_list if r.uri] results empty -> returns None
# C001M008B0002: uri_reqs non empty and for r in uri_reqs executes 0 times -> returns [] (empty candidates list)
# C001M008B0003: for r in uri_reqs executes >= 1 and parsed = urlparse(r.uri); if not parsed.scheme -> raises ValueError("Invalid resolver requirement URI")
# C001M008B0004: for r in uri_reqs executes >= 1 and parsed.scheme truthy and _candidate_from_uri_req returns None -> does not append; continues; returns candidates (possibly empty)
# C001M008B0005: for r in uri_reqs executes >= 1 and parsed.scheme truthy and _candidate_from_uri_req returns candidate -> appends to candidates; returns candidates list
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._candidate_from_uri_req(self, *, name: str, req: ResolverRequirement, bad: set[tuple[str, str, str]]) -> ResolverCandidate | None
#    (Class ID: C001, Method ID: M009)
# ------------------------------------------------------------------------------
# C001M009B0001: try: filename = _safe_url_basename(req.uri); parse_wheel_filename(filename) raises -> raises ValueError("Direct URI requirement does not look like a wheel file")
# C001M009B0002: parse succeeds and if canonicalize_name(dist) != name -> returns None
# C001M009B0003: dist matches; best_tag = self._best_tag(file_tag_set) is None -> returns None
# C001M009B0004: best_tag found; tup in bad -> returns None
# C001M009B0005: req.version is not None and not req.version.contains(wk.version) -> returns None
# C001M009B0006: else -> returns ResolverCandidate(wheel_key=wk) with origin_uri=req.uri and satisfied_tags from filename tags
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._combined_spec(req_list: Sequence[ResolverRequirement]) -> SpecifierSet | None
#    (Class ID: C001, Method ID: M010)
# ------------------------------------------------------------------------------
# C001M010B0001: req_list loop executes 0 times -> returns None
# C001M010B0002: loop executes >= 1; all r.version is None -> returns None
# C001M010B0003: loop sees first r.version not None and combined_spec is None -> combined_spec becomes r.version; returns that if no later versions
# C001M010B0004: loop sees later r.version not None and combined_spec not None -> combined_spec becomes SpecifierSet(f"{combined_spec},{r.version}"); returns final combined_spec
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._load_pep691(self, name: str) -> Pep691Metadata
#    (Class ID: C001, Method ID: M011)
# ------------------------------------------------------------------------------
# C001M011B0001: pep691 = self._index_cache.get(name) is not None -> returns cached pep691 (no service calls)
# C001M011B0002: pep691 cache miss -> calls services.index_metadata.resolve(IndexMetadataKey(project=name, index_base=self._index_base)); reads JSON; Pep691Metadata.from_mapping; stores in cache; returns pep691
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._build_index_candidates(self, *, name: str, pep691: Pep691Metadata, combined_spec: SpecifierSet | None, py_version: str, bad: set[tuple[str, str, str]]) -> list[ResolverCandidate]
#    (Class ID: C001, Method ID: M012)
# ------------------------------------------------------------------------------
# C001M012B0001: for f in pep691.files executes 0 times -> returns []
# C001M012B0002: for f executes >= 1 and _candidate_from_index_file returns None -> does not append; returns candidates (possibly empty)
# C001M012B0003: for f executes >= 1 and _candidate_from_index_file returns candidate -> appends; returns candidates list
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._candidate_from_index_file(self, *, name: str, f: Pep691FileMetadata, combined_spec: SpecifierSet | None, py_version: str, bad: set[tuple[str, str, str]]) -> ResolverCandidate | None
#    (Class ID: C001, Method ID: M013)
# ------------------------------------------------------------------------------
# C001M013B0001: if not f.filename.lower().endswith(".whl") -> returns None
# C001M013B0002: if f.yanked and self._policy.yanked_wheel_policy == YankedWheelPolicy.SKIP -> returns None
# C001M013B0003: try: parse_wheel_filename(f.filename) raises -> returns None
# C001M013B0004: parse succeeds and if canonicalize_name(dist) != name -> returns None
# C001M013B0005: combined_spec is not None and not combined_spec.contains(ver_str) -> returns None
# C001M013B0006: f.requires_python truthy and try: not SpecifierSet(f.requires_python).contains(py_version) -> returns None
# C001M013B0007: f.requires_python truthy and except Exception in requires_python parsing -> ignores and continues (no return)
# C001M013B0008: best_tag = self._best_tag(file_tag_set) is None -> returns None
# C001M013B0009: hash_spec = self._best_hash(f) is None -> returns None
# C001M013B0010: tup in bad -> returns None
# C001M013B0011: else -> returns ResolverCandidate(wheel_key=wk) with requires_python, origin_uri=f.url, and hash_algorithm/content_hash set
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._best_tag(self, file_tag_set: set[str]) -> str | None
#    (Class ID: C001, Method ID: M014)
# ------------------------------------------------------------------------------
# C001M014B0001: ordered = getattr(self._env, "supported_tags_ordered", None) is not None -> returns first t in ordered where t in file_tag_set, else None
# C001M014B0002: ordered is None -> ordered = self._env.supported_tags; returns first t in ordered where t in file_tag_set, else None
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider._sort_candidates(candidates: list[ResolverCandidate]) -> list[ResolverCandidate]
#    (Class ID: C001, Method ID: M015)
# ------------------------------------------------------------------------------
# C001M015B0001: candidates is empty -> returns [] (after sort no-op)
# C001M015B0002: candidates has >= 1 -> sorts in place by (_version_sort_key(c.version), c.wheel_key.tag) with reverse=True; returns same list object
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider.is_satisfied_by(self, requirement: ResolverRequirement, candidate: ResolverCandidate) -> bool
#    (Class ID: C001, Method ID: M016)
# ------------------------------------------------------------------------------
# C001M016B0001: if candidate.name != requirement.name -> returns False
# C001M016B0002: requirement.uri is not None and candidate.wheel_key.origin_uri == requirement.uri -> returns True
# C001M016B0003: requirement.uri is not None and candidate.wheel_key.origin_uri != requirement.uri -> returns False
# C001M016B0004: requirement.uri is None and requirement.version is None -> returns True
# C001M016B0005: requirement.uri is None and requirement.version is not None and try: requirement.version.contains(candidate.version) succeeds -> returns that boolean
# C001M016B0006: requirement.uri is None and requirement.version is not None and except Exception -> returns False
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider.get_dependencies(self, candidate: ResolverCandidate) -> Iterable[ResolverRequirement]
#    (Class ID: C001, Method ID: M017)
# ------------------------------------------------------------------------------
# C001M017B0001: wk.origin_uri is None -> returns () (empty tuple)
# C001M017B0002: wk.origin_uri not None and meta is found in _core_metadata_cache -> uses cached meta (no services.core_metadata.resolve call)
# C001M017B0003: wk.origin_uri not None and meta cache miss -> calls services.core_metadata.resolve(CoreMetadataKey(...)); reads text; Pep658Metadata.from_core_metadata_text; caches; continues
# C001M017B0004: requested_extras = self._requested_extras_by_name.get(wk.name, frozenset()) is empty -> marker_env_base["extra"] defaulted to ""; uses base env for marker evaluation
# C001M017B0005: requested_extras is non empty -> marker_env_base["extra"] defaulted to ""; per-extra evaluation is used when marker exists
# C001M017B0006: for raw in meta.requires_dist executes 0 times -> returns [] (empty deps list)
# C001M017B0007: for raw executes >= 1 and Requirement(raw) raises -> continue; dependency skipped
# C001M017B0008: req.marker is not None and requested_extras truthy and per-extra loop executes 0 times -> ok stays False; dependency skipped
# C001M017B0009: req.marker is not None and requested_extras truthy and per-extra loop executes >= 1 and some req.marker.evaluate(environment=marker_env) True -> ok True; dependency included
# C001M017B0010: req.marker is not None and requested_extras truthy and per-extra loop executes >= 1 but all evaluations False -> dependency skipped
# C001M017B0011: req.marker is not None and requested_extras falsy and req.marker.evaluate(environment=marker_env_base) is False -> dependency skipped
# C001M017B0012: req.marker is not None and requested_extras falsy and req.marker.evaluate(environment=marker_env_base) is True -> dependency included
# C001M017B0013: req.marker is None -> dependency included
# C001M017B0014: dependency included -> appends ResolverRequirement(wheel_spec=WheelSpec(name=req.name, version=req.specifier if str(req.specifier) else None, extras=frozenset(req.extras), marker=req.marker, uri=req.url if req.url else None))
# C001M017B0015: end -> returns deps list
#
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionProvider.get_preference(self, identifier: str, resolutions: Mapping[str, ResolverCandidate], candidates: Mapping[str, Iterator[ResolverCandidate]], information: Mapping[str, Iterator[RequirementInformation[ResolverRequirement, ResolverCandidate]]], backtrack_causes: Sequence[RequirementInformation[ResolverRequirement, ResolverCandidate]]) -> Preference
#    (Class ID: C001, Method ID: M018)
# ------------------------------------------------------------------------------
# C001M018B0001: infos = tuple(information.get(identifier, ())) yields empty -> is_root False; parent_count 0
# C001M018B0002: infos non empty and any(ri.parent is None) -> is_root True
# C001M018B0003: infos non empty and all ri.parent is not None -> is_root False
# C001M018B0004: parent_count computed with 0 parents -> parent_count == 0
# C001M018B0005: parent_count computed with >= 1 parents -> parent_count >= 1
# C001M018B0006: is_backtrack_cause if any(getattr(ri.requirement,"name",None) == identifier for ri in backtrack_causes) -> first tuple element is 0 else 1
# C001M018B0007: is_already_resolved if identifier in resolutions -> 4th tuple element is 1 else 0
# C001M018B0008: executes -> returns preference tuple (backtrack_flag, root_flag, -parent_count, resolved_flag, identifier)
#
#
# ------------------------------------------------------------------------------
# ## resolve(*, services, env: ResolutionEnv, roots: Sequence[ResolverRequirement]) -> Result[ResolverRequirement, ResolverCandidate, str]
#    (Module ID: C000, Function ID: F006)
# ------------------------------------------------------------------------------
# C000F006B0001: executes -> constructs ProjectResolutionProvider(services=services, env=env), ProjectResolutionReporter(), Resolver(provider, reporter); returns resolver.resolve(roots)
#
#
# ------------------------------------------------------------------------------
# LEDGER COMPLETENESS CHECKLIST
#   [x] all `if` / `elif` / `else` captured
#   [x] all `match` / `case` arms captured (none present)
#   [x] all `except` handlers captured
#   [x] all early `return`s / `raise`s captured
#   [x] all loop 0 vs >= 1 iterations captured
#   [x] all `break` / `continue` paths captured (continues captured; no breaks)
# ==============================================================================


# ==============================================================================
# Local test doubles (external deps are stubbed; unit under test is resolvelib.py)
# ==============================================================================

@dataclass(slots=True)
class _FakeRecord:
    destination_uri: str


class _FakeCoordinator:
    def __init__(self, mapping: Mapping[str, _FakeRecord]) -> None:
        self._mapping = dict(mapping)
        self.calls: list[Any] = []

    def resolve(self, key: Any) -> _FakeRecord:
        # Key itself isn't important for these unit tests; capture for assertions.
        self.calls.append(key)
        # The mapping is keyed by a string selector we stash on the key, else just "default".
        selector = getattr(key, "_test_selector", "default")
        return self._mapping[selector]


@dataclass(slots=True)
class _FakeServices:
    index_metadata: _FakeCoordinator
    core_metadata: _FakeCoordinator


@dataclass(slots=True)
class _FakePolicy:
    yanked_wheel_policy: YankedWheelPolicy = YankedWheelPolicy.SKIP


class _FakeEnv:
    """
    Minimal env shape used by ProjectResolutionProvider.

    We intentionally provide deterministic iteration order for supported_tags where needed.
    """

    def __init__(
            self,
            *,
            supported_tags: Sequence[str] | frozenset[str],
            marker_environment: dict[str, str] | None = None,
            yanked_policy: YankedWheelPolicy = YankedWheelPolicy.SKIP,
            supported_tags_ordered: Sequence[str] | None = None,
    ) -> None:
        self.supported_tags = supported_tags
        self.marker_environment = marker_environment or {}
        self.policy = SimpleNamespace(yanked_wheel_policy=yanked_policy)
        if supported_tags_ordered is not None:
            self.supported_tags_ordered = list(supported_tags_ordered)


def _wk(*, name: str, version: str, tag: str, origin_uri: str | None = None) -> FakeWheelKey:
    return FakeWheelKey(
        name=name,
        version=version,
        tag=tag,
        requires_python=None,
        satisfied_tags=frozenset({tag}),
        origin_uri=origin_uri,
    )


def _req(*, name: str, version: str | None = None, uri: str | None = None,
         extras: Sequence[str] = ()) -> FakeResolverRequirement:
    spec = SpecifierSet(version) if version is not None else None
    return FakeResolverRequirement(
        wheel_spec=FakeWheelSpec(
            name=name,
            version=spec,
            extras=frozenset(extras),
            marker=None,
            uri=uri,
        )
    )


def _pep691_file(
        *,
        filename: str,
        url: str = "https://files.example/x.whl",
        hashes: Mapping[str, str] | None = None,
        requires_python: str | None = None,
        yanked: bool = False,
) -> FakePep691FileMetadata:
    return FakePep691FileMetadata(
        filename=filename,
        url=url,
        hashes=dict(hashes or {}),
        requires_python=requires_python,
        yanked=yanked,
        core_metadata=False,
        data_dist_info_metadata=False,
    )


def _write_json(tmp_path: Path, payload: Any) -> Path:
    p = tmp_path / "index.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def _write_core_metadata(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "core-metadata.txt"
    p.write_text(text, encoding="utf-8")
    return p


# ==============================================================================
# 7) Case matrices (per contract)
# ==============================================================================

_ENV_PY_VER_CASES = [
    # Covers: C000F004B0001, C000F004B0004
    {"env": _FakeEnv(supported_tags=(), marker_environment={"python_full_version": "3.11.7"}), "expect": "3.11.7",
     "covers": ["C000F004B0001", "C000F004B0004"]},
    # Covers: C000F004B0002, C000F004B0004
    {"env": _FakeEnv(supported_tags=(), marker_environment={"python_version": "3.11"}), "expect": "3.11",
     "covers": ["C000F004B0002", "C000F004B0004"]},
    # Covers: C000F004B0003, C000F004B0004
    {"env": _FakeEnv(supported_tags=(), marker_environment={}), "expect": "0",
     "covers": ["C000F004B0003", "C000F004B0004"]},
    # Covers: C000F004B0001, C000F004B0005
    {"env": _FakeEnv(supported_tags=(), marker_environment={"python_full_version": "not-a-version"}), "expect": "0",
     "covers": ["C000F004B0001", "C000F004B0005"]},
]

_VERSION_SORT_KEY_CASES = [
    # Covers: C000F005B0001
    {"v": "1.2.3", "expect_first": 1, "covers": ["C000F005B0001"]},
    # Covers: C000F005B0002
    {"v": "nope", "expect_first": 0, "covers": ["C000F005B0002"]},
]

_SAFE_URL_BASENAME_CASES = [
    # Covers: C000F002B0001
    {"url": "https://example.com/", "raises": "URL has no path basename", "covers": ["C000F002B0001"]},
    # Covers: C000F002B0002
    {"url": "https://example.com/files/demo%2D1.0.0-py3-none-any.whl", "expect": "demo-1.0.0-py3-none-any.whl",
     "covers": ["C000F002B0002"]},
]

_PATH_FROM_FILE_URI_CASES = [
    # Covers: C000F003B0001
    {"uri": "https://example.com/x", "raises": "Expected file URI", "covers": ["C000F003B0001"]},
]

_BEST_HASH_CASES = [
    # Covers: C001M003B0001
    {"hashes": {}, "expect": None, "covers": ["C001M003B0001"]},
    # Covers: C001M003B0002
    {"hashes": {"sha256": "a"}, "expect": ("sha256", "a"), "covers": ["C001M003B0002"]},
    # Covers: C001M003B0003
    {"hashes": {"sha512": "b"}, "expect": ("sha512", "b"), "covers": ["C001M003B0003"]},
    # Covers: C001M003B0004
    {"hashes": {"sha384": "c"}, "expect": ("sha384", "c"), "covers": ["C001M003B0004"]},
    # Covers: C001M003B0005
    {"hashes": {"md5": "d"}, "expect": None, "covers": ["C001M003B0005"]},
]


# ==============================================================================
# Tests: module functions
# ==============================================================================

def test_expand_tags_for_context_cp_and_non_cp():
    # Covers: C000F001B0001, C000F001B0002
    pyver = Version("3.11")

    seed_cp = Tag("cp311", "cp311", "manylinux_2_17_x86_64")
    tags_cp = _expand_tags_for_context(python_version=pyver, context_tag=seed_cp)
    assert Tag("cp311", "abi3", "manylinux_2_17_x86_64") in tags_cp
    assert Tag("cp311", "none", "manylinux_2_17_x86_64") in tags_cp

    seed_non = Tag("py3", "none", "any")
    tags_non = _expand_tags_for_context(python_version=pyver, context_tag=seed_non)
    assert Tag("py3", "abi3", "any") not in tags_non
    assert Tag("py3", "none", "any") in tags_non  # base tag set still includes context_tag


@pytest.mark.parametrize("row", _SAFE_URL_BASENAME_CASES)
def test_safe_url_basename_cases(row: dict[str, Any]):
    # Covers: per-row row["covers"]
    if "raises" in row:
        with pytest.raises(ValueError) as ei:
            _safe_url_basename(row["url"])
        assert row["raises"] in str(ei.value)
    else:
        assert _safe_url_basename(row["url"]) == row["expect"]


@pytest.mark.parametrize("row", _PATH_FROM_FILE_URI_CASES)
def test_path_from_file_uri_non_file_scheme(row: dict[str, Any]):
    # Covers: per-row row["covers"]
    with pytest.raises(ValueError) as ei:
        _ = path_from_file_uri(row["uri"])
    assert row["raises"] in str(ei.value)


def test_path_from_file_uri_file_scheme_round_trip(tmp_path: Path):
    # Covers: C000F003B0002
    p = tmp_path / "x.txt"
    uri = p.as_uri()
    out = path_from_file_uri(uri)
    assert out == p


@pytest.mark.parametrize("row", _ENV_PY_VER_CASES)
def test_env_python_version_cases(row: dict[str, Any]):
    # Covers: per-row row["covers"]
    v = _env_python_version(row["env"])
    assert str(v) == row["expect"]


@pytest.mark.parametrize("row", _VERSION_SORT_KEY_CASES)
def test_version_sort_key_cases(row: dict[str, Any]):
    # Covers: per-row row["covers"]
    k = _version_sort_key(row["v"])
    assert k[0] == row["expect_first"]


# ==============================================================================
# Tests: provider basics
# ==============================================================================

def test_provider_init_and_identify():
    # Covers: C001M001B0001, C001M002B0001
    env = _FakeEnv(supported_tags=("py3-none-any",))
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=_FakeCoordinator({}))
    p = ProjectResolutionProvider(services=services, env=env)

    r = _req(name="My-Pkg", version="==1.0")
    c = FakeResolverCandidate(wheel_key=_wk(name="my-pkg", version="1.0.0", tag="py3-none-any"))
    assert p.identify(r) == "my-pkg"
    assert p.identify(c) == "my-pkg"


@pytest.mark.parametrize("row", _BEST_HASH_CASES)
def test_provider_best_hash_cases(row: dict[str, Any]):
    # Covers: per-row row["covers"]
    item = _pep691_file(
        filename="demo-1.0.0-py3-none-any.whl",
        hashes=row["hashes"],
    )
    assert ProjectResolutionProvider._best_hash(item) == row["expect"]


def test_materialize_requirements_empty_and_non_empty():
    # Covers: C001M005B0001, C001M005B0002
    r1 = _req(name="demo", version="==1.0")
    r2 = _req(name="demo", version="==2.0")

    empty = ProjectResolutionProvider._materialize_requirements({}, "demo")
    assert empty == []

    non_empty = ProjectResolutionProvider._materialize_requirements({"demo": iter((r1, r2))}, "demo")
    assert non_empty == [r1, r2]


def test_update_requested_extras_branches():
    # Covers: C001M006B0001, C001M006B0003, C001M006B0004, C001M006B0005
    env = _FakeEnv(supported_tags=("py3-none-any",))
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=_FakeCoordinator({}))
    p = ProjectResolutionProvider(services=services, env=env)

    # B0001: empty req_list -> no mutation
    p._update_requested_extras("demo", [])
    assert p._requested_extras_by_name == {}

    # B0003 + B0004: req_list present but extras empty -> no mutation
    p._update_requested_extras("demo", [_req(name="demo", version="==1.0", extras=())])
    assert p._requested_extras_by_name == {}

    # B0005: union with existing
    p._requested_extras_by_name["demo"] = frozenset({"a"})
    p._update_requested_extras("demo", [_req(name="demo", version="==1.0", extras=("b", "c"))])
    assert p._requested_extras_by_name["demo"] == frozenset({"a", "b", "c"})


def test_compute_bad_set_empty_and_non_empty():
    # Covers: C001M007B0001, C001M007B0002
    bad0 = ProjectResolutionProvider._compute_bad_set("demo", {})
    assert bad0 == set()

    c1 = FakeResolverCandidate(wheel_key=_wk(name="demo", version="1.0.0", tag="py3-none-any"))
    c2 = FakeResolverCandidate(wheel_key=_wk(name="demo", version="2.0.0", tag="py3-none-any"))
    bad = ProjectResolutionProvider._compute_bad_set("demo", {"demo": iter((c1, c2))})
    assert ("demo", "1.0.0", "py3-none-any") in bad
    assert ("demo", "2.0.0", "py3-none-any") in bad


# ==============================================================================
# Tests: URI candidate path
# ==============================================================================

def test_build_uri_candidates_none_and_invalid_scheme_and_append():
    # Covers: C001M008B0001, C001M008B0003, C001M008B0004, C001M008B0005
    env = _FakeEnv(supported_tags=("py3-none-any",), supported_tags_ordered=("py3-none-any",))
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=_FakeCoordinator({}))
    p = ProjectResolutionProvider(services=services, env=env)
    bad: set[tuple[str, str, str]] = set()

    # B0001: no uri requirements -> None
    assert p._build_uri_candidates("demo", [_req(name="demo", version="==1.0")], bad) is None

    # B0003: uri with no scheme -> ValueError
    with pytest.raises(ValueError) as ei:
        _ = p._build_uri_candidates("demo", [_req(name="demo", version="==1.0", uri="demo-1.0.0-py3-none-any.whl")],
                                    bad)
    assert "Invalid resolver requirement URI" in str(ei.value)

    # B0004: valid scheme but candidate_from_uri_req returns None (dist mismatch)
    out0 = p._build_uri_candidates(
        "demo",
        [_req(name="demo", version="==1.0", uri="https://example.com/other-1.0.0-py3-none-any.whl")],
        bad,
    )
    assert out0 == []

    # B0005: candidate appended
    out1 = p._build_uri_candidates(
        "demo",
        [_req(name="demo", version="==1.0", uri="https://example.com/demo-1.0.0-py3-none-any.whl")],
        bad,
    )
    assert out1 is not None
    assert len(out1) == 1
    assert out1[0].wheel_key.origin_uri == "https://example.com/demo-1.0.0-py3-none-any.whl"


@pytest.mark.parametrize(
    "row",
    [
        # Covers: C001M009B0001
        {
            "req": _req(name="demo", version="==1.0", uri="https://example.com/not-a-wheel.txt"),
            "bad": set(),
            "raises": "does not look like a wheel file",
            "covers": ["C001M009B0001"],
        },
        # Covers: C001M009B0002
        {
            "req": _req(name="demo", version="==1.0", uri="https://example.com/other-1.0.0-py3-none-any.whl"),
            "bad": set(),
            "expect": None,
            "covers": ["C001M009B0002"],
        },
        # Covers: C001M009B0003
        {
            "req": _req(name="demo", version="==1.0", uri="https://example.com/demo-1.0.0-py3-none-any.whl"),
            "env": _FakeEnv(supported_tags=("cp311-cp311-manylinux_2_17_x86_64",),
                            supported_tags_ordered=("cp311-cp311-manylinux_2_17_x86_64",)),
            "bad": set(),
            "expect": None,
            "covers": ["C001M009B0003"],
        },
        # Covers: C001M009B0004
        {
            "req": _req(name="demo", version="==1.0", uri="https://example.com/demo-1.0.0-py3-none-any.whl"),
            "bad": {("demo", "1.0.0", "py3-none-any")},
            "expect": None,
            "covers": ["C001M009B0004"],
        },
        # Covers: C001M009B0005
        {
            "req": _req(name="demo", version="==2.0", uri="https://example.com/demo-1.0.0-py3-none-any.whl"),
            "bad": set(),
            "expect": None,
            "covers": ["C001M009B0005"],
        },
        # Covers: C001M009B0006
        {
            "req": _req(name="demo", version="==1.0", uri="https://example.com/demo-1.0.0-py3-none-any.whl"),
            "bad": set(),
            "expect_origin": "https://example.com/demo-1.0.0-py3-none-any.whl",
            "covers": ["C001M009B0006"],
        },
    ],
)
def test_candidate_from_uri_req_branches(row: dict[str, Any]):
    # Covers: per-row row["covers"]
    env = row.get("env") or _FakeEnv(supported_tags=("py3-none-any",), supported_tags_ordered=("py3-none-any",))
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=_FakeCoordinator({}))
    p = ProjectResolutionProvider(services=services, env=env)

    if "raises" in row:
        with pytest.raises(ValueError) as ei:
            _ = p._candidate_from_uri_req(name="demo", req=row["req"], bad=row["bad"])
        assert row["raises"] in str(ei.value)
        return

    out = p._candidate_from_uri_req(name="demo", req=row["req"], bad=row["bad"])
    if row.get("expect") is None and "expect_origin" not in row:
        assert out is None
    else:
        assert out is not None
        assert out.wheel_key.origin_uri == row["expect_origin"]


@pytest.mark.parametrize(
    "row",
    [
        # Covers: C001M010B0001
        {"reqs": [], "expect": None, "covers": ["C001M010B0001"]},
        # Covers: C001M010B0002
        {"reqs": [_req(name="demo", version=None, uri="https://example.com/demo-1.0.0-py3-none-any.whl")],
         "expect": None,
         "covers": ["C001M010B0002"]},
        # Covers: C001M010B0003
        {"reqs": [_req(name="demo", version=">=1.0")], "expect": ">=1.0", "covers": ["C001M010B0003"]},
        # Covers: C001M010B0004
        {"reqs": [_req(name="demo", version=">=1.0"), _req(name="demo", version="<2.0")], "expect": "<2.0,>=1.0",
         "covers": ["C001M010B0004"]},
    ],
)
def test_combined_spec_cases(row: dict[str, Any]):
    # Covers: per-row row["covers"]
    out = ProjectResolutionProvider._combined_spec(row["reqs"])
    if row["expect"] is None:
        assert out is None
    else:
        # SpecifierSet stringification can reorder; assert semantic containment via str equality of the composed repr we expect.
        assert str(out) == row["expect"]


# ==============================================================================
# Tests: index candidate path (PEP 691 + PEP 658 core metadata)
# ==============================================================================

def test_load_pep691_cache_miss_then_hit(tmp_path: Path, patch_pep691_metadata):
    # Covers: C001M011B0002, C001M011B0001
    payload = {
        "name": "demo",
        "files": [
            _pep691_file(filename="demo-1.0.0-py3-none-any.whl", hashes={"sha256": "a" * 64}).to_mapping(),
        ],
        "last_serial": 1,
    }
    idx_path = _write_json(tmp_path, payload)
    rec = _FakeRecord(destination_uri=idx_path.as_uri())

    index_coord = _FakeCoordinator({"default": rec})
    core_coord = _FakeCoordinator({})
    services = _FakeServices(index_metadata=index_coord, core_metadata=core_coord)

    env = _FakeEnv(supported_tags=("py3-none-any",))
    p = ProjectResolutionProvider(services=services, env=env)

    m1 = p._load_pep691("demo")
    assert isinstance(m1, FakePep691Metadata)
    assert len(index_coord.calls) == 1

    m2 = p._load_pep691("demo")
    assert m2 is m1
    assert len(index_coord.calls) == 1  # cache hit, no new calls


def test_build_index_candidates_loop_0_and_none_and_some():
    # Covers: C001M012B0001, C001M012B0002, C001M012B0003
    env = _FakeEnv(supported_tags=("py3-none-any",), supported_tags_ordered=("py3-none-any",))
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=_FakeCoordinator({}))
    p = ProjectResolutionProvider(services=services, env=env)

    pep_empty = FakePep691Metadata(name="demo", files=[])
    out0 = p._build_index_candidates(name="demo", pep691=pep_empty, combined_spec=None, py_version="3.11", bad=set())
    assert out0 == []

    pep_none = FakePep691Metadata(name="demo", files=[_pep691_file(filename="not-a-wheel.txt")])
    out1 = p._build_index_candidates(name="demo", pep691=pep_none, combined_spec=None, py_version="3.11", bad=set())
    assert out1 == []

    pep_some = FakePep691Metadata(
        name="demo",
        files=[_pep691_file(filename="demo-1.0.0-py3-none-any.whl", hashes={"sha256": "a" * 64})],
    )
    out2 = p._build_index_candidates(name="demo", pep691=pep_some, combined_spec=None, py_version="3.11", bad=set())
    assert len(out2) == 1
    assert out2[0].wheel_key.content_hash == "a" * 64


@pytest.mark.parametrize(
    "row",
    [
        # Covers: C001M013B0001
        {"f": _pep691_file(filename="demo-1.0.0.tar.gz"), "expect": None, "covers": ["C001M013B0001"]},
        # Covers: C001M013B0002
        {"f": _pep691_file(filename="demo-1.0.0-py3-none-any.whl", yanked=True, hashes={"sha256": "a" * 64}),
         "policy": YankedWheelPolicy.SKIP, "expect": None, "covers": ["C001M013B0002"]},
        # Covers: C001M013B0003
        {"f": _pep691_file(filename="bad.whl", hashes={"sha256": "a" * 64}), "expect": None,
         "covers": ["C001M013B0003"]},
        # Covers: C001M013B0004
        {"f": _pep691_file(filename="other-1.0.0-py3-none-any.whl", hashes={"sha256": "a" * 64}),
         "expect": None, "covers": ["C001M013B0004"]},
        # Covers: C001M013B0005
        {"f": _pep691_file(filename="demo-1.0.0-py3-none-any.whl", hashes={"sha256": "a" * 64}),
         "combined": SpecifierSet("==2.0.0"), "expect": None, "covers": ["C001M013B0005"]},
        # Covers: C001M013B0006
        {"f": _pep691_file(filename="demo-1.0.0-py3-none-any.whl", hashes={"sha256": "a" * 64}, requires_python="<3.0"),
         "expect": None, "covers": ["C001M013B0006"]},
        # Covers: C001M013B0007
        {"f": _pep691_file(filename="demo-1.0.0-py3-none-any.whl", hashes={"sha256": "a" * 64},
                           requires_python="not-a-spec"),
         "expect_non_none": True, "covers": ["C001M013B0007", "C001M013B0011"]},
        # Covers: C001M013B0008
        {"f": _pep691_file(filename="demo-1.0.0-py3-none-any.whl", hashes={"sha256": "a" * 64}),
         "env": _FakeEnv(supported_tags=("cp311-cp311-manylinux_2_17_x86_64",),
                         supported_tags_ordered=("cp311-cp311-manylinux_2_17_x86_64",)),
         "expect": None, "covers": ["C001M013B0008"]},
        # Covers: C001M013B0009
        {"f": _pep691_file(filename="demo-1.0.0-py3-none-any.whl", hashes={}),
         "expect": None, "covers": ["C001M013B0009"]},
        # Covers: C001M013B0010
        {"f": _pep691_file(filename="demo-1.0.0-py3-none-any.whl", hashes={"sha256": "a" * 64}),
         "bad": {("demo", "1.0.0", "py3-none-any")}, "expect": None, "covers": ["C001M013B0010"]},
        # Covers: C001M013B0011
        {"f": _pep691_file(filename="demo-1.0.0-py3-none-any.whl", hashes={"sha256": "a" * 64}),
         "expect_non_none": True, "covers": ["C001M013B0011"]},
        {"f": _pep691_file(filename="demo-1.0.0-py3-none-any.whl", hashes={"sha256": "a" * 64}, requires_python=">=3.8"),
         "expect_non_none": True, "covers": ["C001M013B0011"]},
    ],
)
def test_candidate_from_index_file_branches(row: dict[str, Any]):
    # Covers: per-row row["covers"]
    env = row.get("env") or _FakeEnv(supported_tags=("py3-none-any",), supported_tags_ordered=("py3-none-any",),
                                     yanked_policy=row.get("policy", YankedWheelPolicy.SKIP))
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=_FakeCoordinator({}))
    p = ProjectResolutionProvider(services=services, env=env)

    out = p._candidate_from_index_file(
        name="demo",
        f=row["f"],
        combined_spec=row.get("combined"),
        py_version="3.11",
        bad=row.get("bad", set()),
    )
    if row.get("expect_non_none"):
        assert out is not None
        assert out.wheel_key.hash_algorithm is not None
        assert out.wheel_key.content_hash is not None
    else:
        assert out is row.get("expect")


def test_best_tag_ordered_and_fallback():
    # Covers: C001M014B0001, C001M014B0002
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=_FakeCoordinator({}))

    # ordered branch
    env1 = _FakeEnv(
        supported_tags=("py2-none-any", "py3-none-any"),
        supported_tags_ordered=("py3-none-any", "py2-none-any"),
    )
    p1 = ProjectResolutionProvider(services=services, env=env1)
    assert p1._best_tag({"py2-none-any", "py3-none-any"}) == "py3-none-any"

    # fallback branch (no supported_tags_ordered attribute) with deterministic supported_tags sequence
    env2 = _FakeEnv(supported_tags=("py2-none-any", "py3-none-any"))
    p2 = ProjectResolutionProvider(services=services, env=env2)
    assert p2._best_tag({"py2-none-any", "py3-none-any"}) == "py2-none-any"


def test_sort_candidates_empty_and_sorted():
    # Covers: C001M015B0001, C001M015B0002, plus C000F005B0001/C000F005B0002 transitively
    assert ProjectResolutionProvider._sort_candidates([]) == []

    c1 = FakeResolverCandidate(wheel_key=_wk(name="demo", version="1.0.0", tag="py2-none-any"))
    c2 = FakeResolverCandidate(wheel_key=_wk(name="demo", version="2.0.0", tag="py2-none-any"))
    c3 = FakeResolverCandidate(wheel_key=_wk(name="demo", version="2.0.0", tag="py3-none-any"))
    arr = [c1, c2, c3]
    out = ProjectResolutionProvider._sort_candidates(arr)
    assert out is arr
    assert [c.wheel_key.version for c in out] == ["2.0.0", "2.0.0", "1.0.0"]
    assert out[0].wheel_key.tag == "py3-none-any"  # version tie broken by tag desc (lexical)


def test_is_satisfied_by_all_branches():
    # Covers: C001M016B0001..B0006
    env = _FakeEnv(supported_tags=("py3-none-any",))
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=_FakeCoordinator({}))
    p = ProjectResolutionProvider(services=services, env=env)

    cand = FakeResolverCandidate(
        wheel_key=_wk(name="demo", version="1.0.0", tag="py3-none-any", origin_uri="https://x/demo.whl"))

    # name mismatch
    assert p.is_satisfied_by(_req(name="other", version="==1.0"), cand) is False

    # uri matches
    assert p.is_satisfied_by(_req(name="demo", version="==1.0", uri="https://x/demo.whl"), cand) is True

    # uri mismatch
    assert p.is_satisfied_by(_req(name="demo", version="==1.0", uri="https://x/other.whl"), cand) is False

    # no uri, no version
    assert p.is_satisfied_by(_req(name="demo", version="==1.0"),
                             cand) is True  # FakeWheelSpec requires version or uri; we supply version but requirement.version None isn't possible with FakeWheelSpec.
    # So explicitly cover B0004 by crafting a requirement-like object:
    req_like = SimpleNamespace(name="demo", uri=None, version=None)
    assert p.is_satisfied_by(req_like, cand) is True

    # contains True / False
    assert p.is_satisfied_by(_req(name="demo", version="==1.0.0"), cand) is True
    assert p.is_satisfied_by(_req(name="demo", version="==2.0.0"), cand) is False

    # contains raises
    class _Boom:
        def contains(self, *_: Any, **__: Any) -> bool:
            raise RuntimeError("boom")

    req_boom = SimpleNamespace(name="demo", uri=None, version=_Boom())
    assert p.is_satisfied_by(req_boom, cand) is False


def test_get_dependencies_origin_uri_none():
    # Covers: C001M017B0001
    env = _FakeEnv(supported_tags=("py3-none-any",))
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=_FakeCoordinator({}))
    p = ProjectResolutionProvider(services=services, env=env)

    c = FakeResolverCandidate(wheel_key=_wk(name="demo", version="1.0.0", tag="py3-none-any", origin_uri=None))
    assert p.get_dependencies(c) == ()


def test_get_dependencies_cache_and_markers_and_invalid_requires_dist(tmp_path: Path):
    # Covers: C001M017B0003, C001M017B0002, C001M017B0004, C001M017B0005,
    #         C001M017B0006, C001M017B0007, C001M017B0009, C001M017B0010,
    #         C001M017B0011, C001M017B0012, C001M017B0013, C001M017B0014, C001M017B0015

    core_text = "\n".join(
        [
            "Name: demo",
            "Version: 1.0.0",
            # invalid requirement -> skip (B0007)
            "Requires-Dist: this is not a valid requirement !!!",
            # marker false (no extras) -> skip (B0011)
            'Requires-Dist: dep_false>=0 ; python_version < "0"',
            # marker true (no extras) -> include (B0012)  NOTE: must have spec or URL
            'Requires-Dist: dep_true>=0 ; python_version >= "0"',
            # marker on extra -> depends on requested_extras (B0005 + B0009/B0010)
            'Requires-Dist: dep_extra>=0 ; extra == "feat"',
            # no marker -> include (B0013/B0014)
            "Requires-Dist: dep_nomarker>=1.0",
            # direct url -> include and sets WheelSpec.uri (B0014)
            'Requires-Dist: dep_url @ https://example.com/dep_url-1.0.0-py3-none-any.whl ; python_version >= "0"',
            "",
        ]
    )
    cm_path = _write_core_metadata(tmp_path, core_text)
    core_rec = _FakeRecord(destination_uri=cm_path.as_uri())

    core_coord = _FakeCoordinator({"default": core_rec})
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=core_coord)

    env = _FakeEnv(
        supported_tags=("py3-none-any",),
        marker_environment={"python_version": "3.11"},
    )
    p = ProjectResolutionProvider(services=services, env=env)

    cand = FakeResolverCandidate(
        wheel_key=_wk(
            name="demo",
            version="1.0.0",
            tag="py3-none-any",
            origin_uri="https://files.example/demo-1.0.0-py3-none-any.whl",
        )
    )

    # requested_extras empty: dep-extra should be skipped (B0011), dep-true included (B0012)
    deps0 = list(p.get_dependencies(cand))
    assert len(core_coord.calls) == 1  # cache miss -> service call (B0003)

    dep_names0 = [d.name for d in deps0]
    assert "dep-true" in dep_names0
    assert "dep-nomarker" in dep_names0
    assert "dep-url" in dep_names0
    assert "dep-extra" not in dep_names0

    # Ensure WheelSpec.uri and version behavior on appended deps
    dep_url = next(d for d in deps0 if d.name == "dep-url")
    assert dep_url.uri == "https://example.com/dep_url-1.0.0-py3-none-any.whl"
    assert dep_url.version is None  # no specifier in "dep_url @ ..."

    dep_nomarker = next(d for d in deps0 if d.name == "dep-nomarker")
    assert str(dep_nomarker.version) == ">=1.0"

    dep_true = next(d for d in deps0 if d.name == "dep-true")
    assert str(dep_true.version) == ">=0"

    # Now set requested extras: dep-extra included (B0009) and still skips for non matching extras (B0010)
    p._requested_extras_by_name["demo"] = frozenset({"feat", "nope"})
    deps1 = list(p.get_dependencies(cand))
    assert len(core_coord.calls) == 1  # cache hit -> no new calls (B0002)

    dep_names1 = [d.name for d in deps1]
    assert "dep-extra" in dep_names1


def test_get_dependencies_requires_dist_loop_zero(tmp_path: Path):
    # Covers: C001M017B0003, C001M017B0006, C001M017B0015
    core_text = "\n".join(["Name: demo", "Version: 1.0.0", ""])
    cm_path = _write_core_metadata(tmp_path, core_text)
    core_rec = _FakeRecord(destination_uri=cm_path.as_uri())

    core_coord = _FakeCoordinator({"default": core_rec})
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=core_coord)

    env = _FakeEnv(supported_tags=("py3-none-any",), marker_environment={"python_version": "3.11"})
    p = ProjectResolutionProvider(services=services, env=env)

    cand = FakeResolverCandidate(wheel_key=_wk(
        name="demo",
        version="1.0.0",
        tag="py3-none-any",
        origin_uri="https://files.example/demo-1.0.0-py3-none-any.whl",
    ))
    assert list(p.get_dependencies(cand)) == []


# ==============================================================================
# Tests: get_preference
# ==============================================================================

@dataclass(slots=True)
class _RI:
    requirement: Any
    parent: Any


def test_get_preference_cases():
    # Covers: C001M018B0001..B0008 (by subcases)
    env = _FakeEnv(supported_tags=("py3-none-any",))
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=_FakeCoordinator({}))
    p = ProjectResolutionProvider(services=services, env=env)

    ident = "demo"

    # infos empty
    pref0 = p.get_preference(
        identifier=ident,
        resolutions={},
        candidates={},
        information={},
        backtrack_causes=[],
    )
    assert pref0 == (1, 1, 0, 0, "demo")

    # root requirement + parent_count 0
    pref1 = p.get_preference(
        identifier=ident,
        resolutions={},
        candidates={},
        information={ident: iter((_RI(requirement=SimpleNamespace(name=ident), parent=None),))},
        backtrack_causes=[],
    )
    assert pref1[1] == 0  # root flag

    # non root with 2 parents
    pref2 = p.get_preference(
        identifier=ident,
        resolutions={},
        candidates={},
        information={ident: iter((
            _RI(requirement=SimpleNamespace(name=ident), parent="p1"),
            _RI(requirement=SimpleNamespace(name=ident), parent="p2"),
        ))},
        backtrack_causes=[],
    )
    assert pref2[1] == 1
    assert pref2[2] == -2

    # backtrack cause
    pref3 = p.get_preference(
        identifier=ident,
        resolutions={},
        candidates={},
        information={ident: iter((_RI(requirement=SimpleNamespace(name=ident), parent=None),))},
        backtrack_causes=[_RI(requirement=SimpleNamespace(name=ident), parent="x")],
    )
    assert pref3[0] == 0

    # already resolved
    pref4 = p.get_preference(
        identifier=ident,
        resolutions={ident: FakeResolverCandidate(wheel_key=_wk(name="demo", version="1.0.0", tag="py3-none-any"))},
        candidates={},
        information={},
        backtrack_causes=[],
    )
    assert pref4[3] == 1


# ==============================================================================
# Tests: find_matches + resolve()
# ==============================================================================

def test_find_matches_uri_path_does_not_touch_index_services():
    # Covers: C001M004B0001, C001M004B0002 (plus URI path internals transitively)
    env = _FakeEnv(supported_tags=("py3-none-any",), supported_tags_ordered=("py3-none-any",))
    index_coord = _FakeCoordinator({})
    core_coord = _FakeCoordinator({})
    services = _FakeServices(index_metadata=index_coord, core_metadata=core_coord)

    p = ProjectResolutionProvider(services=services, env=env)

    reqs = {"demo": iter((_req(name="demo", version="==1.0", uri="https://example.com/demo-1.0.0-py3-none-any.whl"),))}
    out = list(p.find_matches("demo", reqs, incompatibilities={}))
    assert len(out) == 1
    assert index_coord.calls == []  # no pep691 load


def test_find_matches_named_path_loads_pep691_and_builds_candidates(tmp_path: Path):
    # Covers: C001M004B0001, C001M004B0003 (plus pep691 load + index candidate internals transitively)
    payload = {
        "name": "demo",
        "files": [
            _pep691_file(filename="demo-1.0.0-py3-none-any.whl", hashes={"sha256": "a" * 64}).to_mapping(),
            _pep691_file(filename="demo-2.0.0-py3-none-any.whl", hashes={"sha256": "b" * 64}).to_mapping(),
        ],
    }
    idx_path = _write_json(tmp_path, payload)
    rec = _FakeRecord(destination_uri=idx_path.as_uri())
    index_coord = _FakeCoordinator({"default": rec})
    core_coord = _FakeCoordinator({})

    services = _FakeServices(index_metadata=index_coord, core_metadata=core_coord)
    env = _FakeEnv(
        supported_tags=("py3-none-any",),
        supported_tags_ordered=("py3-none-any",),
        marker_environment={"python_full_version": "3.11.7"},
    )
    p = ProjectResolutionProvider(services=services, env=env)

    reqs = {"demo": iter((_req(name="demo", version=">=1.0"),))}
    out = list(p.find_matches("demo", reqs, incompatibilities={}))
    assert [c.wheel_key.version for c in out] == ["2.0.0", "1.0.0"]  # sorted desc
    assert len(index_coord.calls) == 1


def test_resolve_constructs_resolver_and_calls_resolve(monkeypatch):
    # Covers: C000F006B0001
    sentinel = object()

    class _FakeResolver:
        def __init__(self, provider: Any, reporter: Any) -> None:
            self.provider = provider
            self.reporter = reporter

        def resolve(self, roots: Any) -> Any:
            assert isinstance(roots, Sequence)
            return sentinel

    monkeypatch.setattr("project_resolution_engine.internal.resolvelib.Resolver", _FakeResolver)

    env = _FakeEnv(supported_tags=("py3-none-any",))
    services = _FakeServices(index_metadata=_FakeCoordinator({}), core_metadata=_FakeCoordinator({}))

    roots = [_req(name="demo", version=">=1.0")]
    out = resolve_via_resolvelib(services=services, env=env, roots=roots)
    assert out is sentinel
