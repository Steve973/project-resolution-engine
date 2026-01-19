from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import cast
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.tags import Tag
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version
from resolvelib import AbstractProvider, Resolver
from resolvelib.resolvers import Result
from resolvelib.structs import RequirementInformation

from project_resolution_engine.internal.resolvelib_types import (
    ResolverRequirement,
    ResolverCandidate,
    ProjectResolutionReporter,
    Preference,
)
from project_resolution_engine.model.keys import (
    IndexMetadataKey,
    CoreMetadataKey,
    WheelKey,
)
from project_resolution_engine.model.pep import (
    Pep691Metadata,
    Pep658Metadata,
    Pep691FileMetadata,
)
from project_resolution_engine.model.resolution import (
    ResolutionEnv,
    WheelSpec,
    YankedWheelPolicy,
)
from project_resolution_engine.services import ResolutionServices


def _expand_tags_for_context(
    *, python_version: Version, context_tag: Tag
) -> frozenset[Tag]:
    major = python_version.major
    minor = python_version.minor
    plat = context_tag.platform

    py_maj = f"py{major}"
    py_maj_min = f"py{major}{minor}"

    # universal pure-Python
    tags = {
        Tag(py_maj, "none", "any"),
        Tag(py_maj_min, "none", "any"),
        Tag(py_maj, "none", plat),
        Tag(py_maj_min, "none", plat),
        context_tag,
    }

    # CPython-ish ABI fallbacks when the seed is cpXY-...
    if (
        context_tag.interpreter.startswith("cp")
        and context_tag.interpreter[2:].isdigit()
    ):
        cp = context_tag.interpreter  # e.g. "cp311"
        tags |= {
            Tag(cp, "abi3", plat),
            Tag(cp, "none", plat),
        }

    return frozenset(tags)


def _safe_url_basename(url: str) -> str:
    parsed = urlparse(url)
    base = Path(unquote(parsed.path)).name
    if not base:
        raise ValueError(f"URL has no path basename: {url!r}")
    return base


def path_from_file_uri(uri: str) -> Path:
    u = urlparse(uri)
    if u.scheme != "file":
        raise ValueError(f"Expected file URI, got: {uri!r}")
    return Path(url2pathname(u.path))


def _env_python_version(env: ResolutionEnv) -> Version:
    # Prefer the full version if present (e.g., 3.11.7); else python_version (e.g., 3.11).
    full = env.marker_environment.get("python_full_version")
    short = env.marker_environment.get("python_version")
    raw = full or short or "0"
    try:
        return Version(str(raw))
    except InvalidVersion:
        return Version("0")


def _version_sort_key(v: str) -> tuple[int, Version | str]:
    # Higher is better. We'll sort by this key *descending*.
    try:
        return 1, Version(v)
    except InvalidVersion:
        return 0, v


class ProjectResolutionProvider(
    AbstractProvider[ResolverRequirement, ResolverCandidate, str]
):
    """A minimal resolvelib Provider for project_resolution_engine."""

    def __init__(
        self,
        *,
        services: ResolutionServices,
        env: ResolutionEnv,
        index_base: str = "https://pypi.org/simple",
    ) -> None:
        self._services = services
        self._env = env
        self._index_base = index_base
        self._policy = env.policy
        self._index_cache: dict[str, Pep691Metadata] = {}
        self._core_metadata_cache: dict[tuple[str, str, str, str], Pep658Metadata] = {}
        self._requested_extras_by_name: dict[str, frozenset[str]] = {}

    def identify(
        self, requirement_or_candidate: ResolverRequirement | ResolverCandidate
    ) -> str:
        return requirement_or_candidate.name

    @staticmethod
    def _best_hash(item: Pep691FileMetadata) -> tuple[str, str] | None:
        # Prefer sha256 but tolerate other strong hashes if present.
        hashes = item.hashes or {}
        if hashes:
            for alg in ("sha256", "sha512", "sha384"):
                h = hashes.get(alg)
                if h:
                    return alg, h
        return None

    def find_matches(
        self,
        identifier: str,
        requirements: Mapping[str, Iterator[ResolverRequirement]],
        incompatibilities: Mapping[str, Iterator[ResolverCandidate]],
    ) -> Iterable[ResolverCandidate]:
        name = canonicalize_name(identifier)

        req_list = self._materialize_requirements(requirements, name)
        self._update_requested_extras(name, req_list)

        bad = self._compute_bad_set(name, incompatibilities)

        uri_candidates = self._build_uri_candidates(name, req_list, bad)
        if uri_candidates is not None:
            return self._sort_candidates(uri_candidates)

        combined_spec = self._combined_spec(req_list)

        pep691 = self._load_pep691(name)
        py_version = _env_python_version(self._env)

        named_candidates = self._build_index_candidates(
            name=name,
            pep691=pep691,
            combined_spec=combined_spec,
            py_version=str(py_version),
            bad=bad,
        )

        return self._sort_candidates(named_candidates)

    @staticmethod
    def _materialize_requirements(
        requirements: Mapping[str, Iterator[ResolverRequirement]], name: str
    ) -> list[ResolverRequirement]:
        return list(requirements.get(name, iter(())))

    def _update_requested_extras(
        self, name: str, req_list: Sequence[ResolverRequirement]
    ) -> None:
        if not req_list:
            return

        extras_union: set[str] = set()
        for r in req_list:
            extras_union.update(r.extras)

        if not extras_union:
            return

        existing = self._requested_extras_by_name.get(name, frozenset())
        self._requested_extras_by_name[name] = frozenset(set(existing) | extras_union)

    @staticmethod
    def _compute_bad_set(
        name: str, incompatibilities: Mapping[str, Iterator[ResolverCandidate]]
    ) -> set[tuple[str, str, str]]:
        return {
            (c.name, c.wheel_key.version, c.wheel_key.tag)
            for c in incompatibilities.get(name, iter(()))
        }

    def _build_uri_candidates(
        self,
        name: str,
        req_list: Sequence[ResolverRequirement],
        bad: set[tuple[str, str, str]],
    ) -> list[ResolverCandidate] | None:
        uri_reqs = [r for r in req_list if r.uri]
        if not uri_reqs:
            return None

        candidates: list[ResolverCandidate] = []
        for r in uri_reqs:
            parsed = urlparse(r.uri)
            if not parsed.scheme:
                raise ValueError(f"Invalid resolver requirement URI: {r.uri!r}")
            c = self._candidate_from_uri_req(name=name, req=r, bad=bad)
            if c is not None:
                candidates.append(c)

        return candidates

    def _candidate_from_uri_req(
        self, *, name: str, req: ResolverRequirement, bad: set[tuple[str, str, str]]
    ) -> ResolverCandidate | None:
        assert req.uri is not None

        try:
            filename = _safe_url_basename(req.uri)
            dist, ver, _build, tags = parse_wheel_filename(filename)
        except Exception:
            raise ValueError(
                f"Direct URI requirement does not look like a wheel file for {name!r}: {req.uri!r}"
            )

        if canonicalize_name(dist) != name:
            return None

        file_tag_set = {str(t) for t in tags}
        best_tag = self._best_tag(file_tag_set)
        if best_tag is None:
            return None

        wk = WheelKey(
            name=name,
            version=str(ver),
            tag=best_tag,
            requires_python=None,
            satisfied_tags=frozenset(file_tag_set),
            origin_uri=req.uri,
        )

        tup = (wk.name, wk.version, wk.tag)
        if tup in bad:
            return None

        if req.version is not None and not req.version.contains(wk.version):
            return None

        return ResolverCandidate(wheel_key=wk)

    @staticmethod
    def _combined_spec(req_list: Sequence[ResolverRequirement]) -> SpecifierSet | None:
        combined_spec: SpecifierSet | None = None
        for r in req_list:
            if r.version is None:
                continue
            combined_spec = (
                r.version
                if combined_spec is None
                else SpecifierSet(f"{combined_spec},{r.version}")
            )
        return combined_spec

    def _load_pep691(self, name: str) -> Pep691Metadata:
        pep691 = self._index_cache.get(name)
        if pep691 is not None:
            return pep691

        idx_key = IndexMetadataKey(project=name, index_base=self._index_base)
        idx_record = self._services.index_metadata.resolve(idx_key)
        idx_path = path_from_file_uri(idx_record.destination_uri)

        payload = json.loads(idx_path.read_text(encoding="utf-8"))
        pep691 = Pep691Metadata.from_mapping(payload)
        self._index_cache[name] = pep691
        return pep691

    def _build_index_candidates(
        self,
        *,
        name: str,
        pep691: Pep691Metadata,
        combined_spec: SpecifierSet | None,
        py_version: str,
        bad: set[tuple[str, str, str]],
    ) -> list[ResolverCandidate]:
        candidates: list[ResolverCandidate] = []
        for f in pep691.files:
            c = self._candidate_from_index_file(
                name=name,
                f=f,
                combined_spec=combined_spec,
                py_version=py_version,
                bad=bad,
            )
            if c is not None:
                candidates.append(c)
        return candidates

    def _candidate_from_index_file(
        self,
        *,
        name: str,
        f: Pep691FileMetadata,
        combined_spec: SpecifierSet | None,
        py_version: str,
        bad: set[tuple[str, str, str]],
    ) -> ResolverCandidate | None:
        if not f.filename.lower().endswith(".whl"):
            return None

        if f.yanked and self._policy.yanked_wheel_policy == YankedWheelPolicy.SKIP:
            return None

        try:
            dist, ver, _build, tags = parse_wheel_filename(f.filename)
        except Exception:
            return None

        if canonicalize_name(dist) != name:
            return None

        ver_str = str(ver)

        if combined_spec is not None and not combined_spec.contains(ver_str):
            return None

        if f.requires_python:
            try:
                if not SpecifierSet(f.requires_python).contains(py_version):
                    return None
            except Exception:
                pass

        file_tag_set = {str(t) for t in tags}
        best_tag = self._best_tag(file_tag_set)
        if best_tag is None:
            return None

        hash_spec = self._best_hash(f)
        if hash_spec is None:
            return None
        alg, h = hash_spec

        wk = WheelKey(
            name=name,
            version=ver_str,
            tag=best_tag,
            requires_python=f.requires_python,
            satisfied_tags=frozenset(file_tag_set),
            origin_uri=f.url,
            content_hash=h,
            hash_algorithm=alg,
        )

        tup = (wk.name, wk.version, wk.tag)
        if tup in bad:
            return None

        return ResolverCandidate(wheel_key=wk)

    def _best_tag(self, file_tag_set: set[str]) -> str | None:
        """
        Return the preferred satisfied tag for this file according to the env's ordering.

        This assumes the env exposes an ordered collection. If it does not, this will still
         work, but selection will be arbitrary.
        """
        ordered = getattr(self._env, "supported_tags_ordered", None)
        if ordered is None:
            ordered = self._env.supported_tags  # fallback, possibly unordered
        return next((t for t in ordered if t in file_tag_set), None)

    @staticmethod
    def _sort_candidates(
        candidates: list[ResolverCandidate],
    ) -> list[ResolverCandidate]:
        """
        Current behavior: version desc, then tag desc (lexical), stable enough for now.

        When supported tags become ordered, and you want "most general wins", replace the
        secondary key with a tag rank derived from env.supported_tags_ordered.
        """
        candidates.sort(
            key=lambda c: (_version_sort_key(c.version), c.wheel_key.tag), reverse=True
        )
        return candidates

    def is_satisfied_by(
        self, requirement: ResolverRequirement, candidate: ResolverCandidate
    ) -> bool:
        if candidate.name != requirement.name:
            return False

        if requirement.uri is not None:
            return candidate.wheel_key.origin_uri == requirement.uri

        if requirement.version is None:
            return True

        try:
            return requirement.version.contains(candidate.version)
        except Exception:
            return False

    def get_dependencies(
        self, candidate: ResolverCandidate
    ) -> Iterable[ResolverRequirement]:
        wk = candidate.wheel_key
        if wk.origin_uri is None:
            return ()

        cache_key = (wk.name, wk.version, wk.tag, wk.origin_uri)
        meta = self._core_metadata_cache.get(cache_key)
        if meta is None:
            cm_key = CoreMetadataKey(
                name=wk.name, version=wk.version, tag=wk.tag, file_url=wk.origin_uri
            )
            cm_record = self._services.core_metadata.resolve(cm_key)
            cm_path = path_from_file_uri(cm_record.destination_uri)
            text = cm_path.read_text(encoding="utf-8", errors="replace")
            meta = Pep658Metadata.from_core_metadata_text(text)
            self._core_metadata_cache[cache_key] = meta

        requested_extras = self._requested_extras_by_name.get(wk.name, frozenset())
        marker_env_base = cast(
            dict[str, str], cast(object, self._env.marker_environment)
        )
        marker_env_base.setdefault("extra", "")

        deps: list[ResolverRequirement] = []
        for raw in meta.requires_dist:
            try:
                req = Requirement(raw)
            except Exception:
                continue

            if req.marker is not None:
                if requested_extras:
                    ok = False
                    for extra in requested_extras:
                        marker_env = dict(marker_env_base)
                        marker_env["extra"] = extra
                        if req.marker.evaluate(environment=marker_env):
                            ok = True
                            break
                    if not ok:
                        continue
                else:
                    if not req.marker.evaluate(environment=marker_env_base):
                        continue

            deps.append(
                ResolverRequirement(
                    wheel_spec=WheelSpec(
                        name=req.name,
                        version=req.specifier if str(req.specifier) else None,
                        extras=frozenset(req.extras),
                        marker=req.marker,
                        uri=req.url if req.url else None,
                    )
                )
            )

        return deps

    def get_preference(
        self,
        identifier: str,
        resolutions: Mapping[str, ResolverCandidate],
        candidates: Mapping[str, Iterator[ResolverCandidate]],
        information: Mapping[
            str,
            Iterator[RequirementInformation[ResolverRequirement, ResolverCandidate]],
        ],
        backtrack_causes: Sequence[
            RequirementInformation[ResolverRequirement, ResolverCandidate]
        ],
    ) -> Preference:
        """
        Decide which identifier resolvelib should try to resolve next.

        This does NOT directly rank wheel/file candidates. Candidate ranking should be handled
        in find_matches() by yielding candidates in the preferred order.
        """

        # Safe to materialize: 'information[identifier]' is passed as an iterator for this call.
        # We avoid touching 'candidates[identifier]' because consuming that iterator would be bad.
        infos = tuple(information.get(identifier, ()))

        # Root requirements (those with parent=None) generally deserve attention early because
        # they are user intent, not incidental transitive deps.
        is_root = any(ri.parent is None for ri in infos)

        # How many distinct parents are imposing constraints on this identifier?
        # More parents => more constrained => usually resolve earlier to reduce backtracking.
        parent_count = sum(1 for ri in infos if ri.parent is not None)

        # Prefer resolving things implicated in backtracking earlier to converge faster.
        # backtrack_causes holds RequirementInformation entries; match by identifier.
        is_backtrack_cause = any(
            getattr(ri.requirement, "name", None) == identifier
            for ri in backtrack_causes
        )

        # If already pinned (should be rare in get_preference calls), deprioritize.
        is_already_resolved = identifier in resolutions

        # Return a tuple: smaller sorts first.
        #
        # Order of importance:
        #  1) backtrack causes first (0)
        #  2) root requirements first (0)
        #  3) higher parent_count first (so use negative)
        #  4) unresolved before resolved
        #  5) stable tie-breaker by identifier
        return (
            0 if is_backtrack_cause else 1,
            0 if is_root else 1,
            -parent_count,
            1 if is_already_resolved else 0,
            identifier,
        )


def resolve(
    *, services, env: ResolutionEnv, roots: Sequence[ResolverRequirement]
) -> Result[ResolverRequirement, ResolverCandidate, str]:
    provider = ProjectResolutionProvider(services=services, env=env)
    reporter = ProjectResolutionReporter()
    resolver: Resolver[ResolverRequirement, ResolverCandidate, str] = Resolver(
        provider, reporter
    )
    return resolver.resolve(roots)
