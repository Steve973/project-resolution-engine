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
from packaging.utils import canonicalize_name, parse_wheel_filename, NormalizedName
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
    """
    Generates an expanded set of tags based on the provided Python version and context tag.

    This function creates a set of platform and interpreter-specific tags
    that are derived from a base context tag. The expanded tags ensure compatibility
    with various Python interpreters, versions, and platforms while considering
    universal pure-Python tags and CPython ABI fallbacks.

    Arguments:
        python_version (Version): The version of the Python interpreter in use.
        context_tag (Tag): The base context-specific tag to expand.

    Returns:
        frozenset[Tag]: A set of expanded tags derived from the provided
        context tag and Python version.
    """
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
    """
    Extracts the basename from a URL path, ensuring it is safe for use.

    This function parses the given URL to extract its path component, then retrieves
    the basename of the path after decoding it. If the URL does not contain a valid
    path basename, a ValueError is raised.

    Parameters:
        url (str): The URL from which the path basename will be extracted.

    Returns:
        str: The decoded basename of the URL path.

    Raises:
        ValueError: If the URL has no valid path basename.
    """
    parsed = urlparse(url)
    base = Path(unquote(parsed.path)).name
    if not base:
        raise ValueError(f"URL has no path basename: {url!r}")
    return base


def path_from_file_uri(uri: str) -> Path:
    """
    Converts a file URI to a filesystem path.

    This function takes a file URI and converts it into a Path object representing
    the corresponding filesystem path. If the provided URI does not have a "file"
    scheme, a ValueError is raised.

    Parameters:
    uri: str
        A file URI to convert.

    Returns:
    Path
        A Path object corresponding to the filesystem location represented by the
        given file URI.

    Raises:
    ValueError
        If the provided URI does not have a "file" scheme.
    """
    u = urlparse(uri)
    if u.scheme != "file":
        raise ValueError(f"Expected file URI, got: {uri!r}")
    return Path(url2pathname(u.path))


def _env_python_version(env: ResolutionEnv) -> Version:
    """
    Derives and returns the Python version from the provided `ResolutionEnv`.

    This function attempts to extract the Python version from the `marker_environment`
    attribute present in the `ResolutionEnv` instance. It gives precedence to the
    full Python version (e.g., `3.11.7`) if available; otherwise, it falls back to
    the short Python version (e.g., `3.11`). If neither is provided, a default version
    of "0" is used. In case the obtained value is not a valid version, a fallback
    Version object with "0" is returned.

    Parameters:
        env (ResolutionEnv): The resolution environment from which the Python version
        will be resolved. It must have a `marker_environment` attribute to extract
        version-related information.

    Returns:
        Version: A `Version` instance corresponding to the derived Python version.
        If no valid version can be determined, a default version "0" is returned.

    Raises:
        None.
    """
    # Prefer the full version if present (e.g., 3.11.7); else python_version (e.g., 3.11).
    full = env.marker_environment.get("python_full_version")
    short = env.marker_environment.get("python_version")
    raw = full or short or "0"
    try:
        return Version(str(raw))
    except InvalidVersion:
        return Version("0")


def _version_sort_key(v: str) -> tuple[int, Version | str]:
    """
    Generates a sorting key for version strings.

    This function attempts to parse the given version string into a Version object.
    If the string is a valid version, it returns a tuple with a priority of 1 and
    the Version object. If the string is not a valid version, it returns a tuple
    with a priority of 0 and the original string.

    Returns:
        tuple[int, Version | str]: A tuple containing a priority value and either
        a Version object or the original string.

    Parameters:
        v (str): The version string to be parsed.

    Raises:
        InvalidVersion: Raised internally if the version string cannot be parsed
        as a valid version, resulting in a fallback tuple.
    """
    try:
        return 1, Version(v)
    except InvalidVersion:
        return 0, v


class ProjectResolutionProvider(
    AbstractProvider[ResolverRequirement, ResolverCandidate, str]
):
    """
    Provides dependency resolution capabilities for identifying and resolving package candidates.

    The `ProjectResolutionProvider` class implements methods to facilitate dependency
    management for a given environment and resolution services. It identifies packages,
    resolves requirements to concrete candidates, handles extras, and ensures compatibility
    with given constraints and indices. The class leverages caching and indexing techniques
    to improve the efficiency of resolution processes.

    Attributes:
        services (ResolutionServices): The resolution services used for managing the
            dependency resolution process.
        env (ResolutionEnv): The environment configuration used for dependency resolution.
        index_base (str): The base URL for the package index utilized during resolution.
    """

    def __init__(
        self,
        *,
        services: ResolutionServices,
        env: ResolutionEnv,
        index_base: str = "https://pypi.org/simple",
    ) -> None:
        """
        Initializes the class with the provided resolution services, environment, and optional
        index base URL.

        Attributes:
            services (ResolutionServices): The resolution services used for managing the
                resolution process.
            env (ResolutionEnv): The environment configuration for dependency resolution.
            index_base (str): The base URL for the index used during dependency resolution.
        """
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
        """
        Identifies the name associated with the given requirement or candidate.

        This method takes either a `ResolverRequirement` or `ResolverCandidate` object
        and returns the name associated with the input. The input can be either a
        requirement object or a candidate object, and the method extracts its name
        accordingly.

        Args:
            requirement_or_candidate: This parameter accepts either a
            `ResolverRequirement` object which represents a requirement to resolve,
            or a `ResolverCandidate` object which represents a potential resolution.

        Returns:
            The name associated with the given requirement or candidate as a string.

        """
        return requirement_or_candidate.name

    @staticmethod
    def _best_hash(item: Pep691FileMetadata) -> tuple[str, str] | None:
        """
        Determine the best hash and its corresponding value for a given item.

        This method identifies and returns a tuple containing the algorithm and
        the hash value for the most preferred hash type available in the provided
        item's metadata. It prioritizes `sha256` but will consider other strong
        hashes such as `sha512` or `sha384` if `sha256` is unavailable. If no
        suitable hash is found, the method returns None.

        Args:
            item (Pep691FileMetadata): The metadata object containing hash
                                      values for different algorithms.

        Returns:
            tuple[str, str] | None: A tuple containing the algorithm name and the
                                    corresponding hash value, or None if no
                                    suitable hash is present.
        """
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
        """
        Finds and returns a sorted list of candidates that satisfy the provided requirements
        and are not present in the given incompatibilities.

        Arguments:
            identifier: A string representing the unique identifier for the package or
                dependency to be resolved.
            requirements: A mapping where keys are package identifiers, and values are
                iterators of ResolverRequirement objects, representing requirements that
                affect the resolution process.
            incompatibilities: A mapping where keys are package identifiers, and values are
                iterators of ResolverCandidate objects that are considered incompatible
                during resolution.

        Returns:
            An iterable of ResolverCandidate objects that fulfill the specified requirements
            and are compatible based on the provided incompatibilities.
        """
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
        """
        Static method to retrieve and materialize requirements for a given key.

        The method retrieves an iterator of `ResolverRequirement` objects mapped to
        the specified key and converts them into a list. If the key does not exist,
        it returns an empty list.

        Parameters:
        requirements (Mapping[str, Iterator[ResolverRequirement]]): A mapping of
            requirement names to their corresponding iterators.
        name (str): The key for which the associated requirements are to be retrieved.

        Returns:
        list[ResolverRequirement]: A list of `ResolverRequirement` objects
            associated with the specified key. Returns an empty list if the key is
            not present in the mapping.
        """
        return list(requirements.get(name, iter(())))

    def _update_requested_extras(
        self, name: str, req_list: Sequence[ResolverRequirement]
    ) -> None:
        """
        Updates the requested extras for a given name based on a list of resolver requirements.

        This method processes a sequence of resolver requirements and extracts their
        associated extras. If any extras are found, they are merged with the existing
        extras stored for the given name. If the resolver requirement list is empty or
        does not contain any extras, the method exits without making any changes.

        Args:
            name (str): The key or identifier for which the extras are being updated.
            req_list (Sequence[ResolverRequirement]): A sequence of resolver requirements
                containing extras to be added.

        Returns:
            None
        """
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
        """
        Computes a set of incompatible candidate details for a specific package name.

        Returns a set containing tuples of candidate name, version, and tag for all
        incompatible candidates associated with the specified package name.

        Parameters:
        name (str): The name of the package for which to compute the incompatible
            candidates.
        incompatibilities (Mapping[str, Iterator[ResolverCandidate]]): A mapping of
            package names to iterables of ResolverCandidate objects representing
            incompatibilities.

        Returns:
        set[tuple[str, str, str]]: A set of tuples, where each tuple consists of
            the candidate name, version, and tag for an incompatible candidate. If
            no incompatibilities are found for the specified name, returns an
            empty set.
        """
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
        """
        Constructs a list of potential resolver candidates based on URI-based requirements.

        This method filters the provided list of requirements to include only those with a
        URI specified. It then validates and processes each URI-based requirement to generate
        corresponding candidates. If no URI-based requirements are present, the method
        returns None.

        Parameters:
        name: The name associated with the resolver candidate.
        req_list: A sequence of resolver requirements, potentially containing URI-based entries.
        bad: A set of previously invalidated candidates, identified by name, version, and source.

        Returns:
        A list of generated resolver candidates based on URI-based requirements, or None
        if no such requirements are present.

        Raises:
        ValueError: If any URI-based requirement contains an invalid URI format.
        """
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
        """
        Processes a direct URI requirement to generate a resolver candidate if the
        requirement matches the expected specifications.

        Args:
            name: A string representing the canonicalized name of the package.
            req: An object representing the resolver requirement, containing information
                such as the URI and version constraints.
            bad: A set of tuples containing (name, version, tag) values marking
                invalid or previously rejected candidates.

        Returns:
            A ResolverCandidate object if the URI requirement is valid and meets
            the criteria; otherwise, None.
        """
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
        """
        Combines version specifiers from a sequence of requirements into a single SpecifierSet.

        This method iterates over a sequence of requirements, extracting the version specifier
        from each. It combines them into a single SpecifierSet while ignoring requirements
        without a version specifier.

        Returns None if no version specifiers are found.

        Args:
            req_list (Sequence[ResolverRequirement]): A sequence of objects representing
                requirements, each potentially containing a version specifier.

        Returns:
            SpecifierSet | None: A combined SpecifierSet representing all version
                constraints, or None if no version constraints are provided.
        """
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
        """
        Loads metadata information for a given project name conforming to PEP 691
        standards, using index caching to optimize repeated access and resolving the
        index metadata for relevant data.

        Args:
            name (str): The name of the project for which the metadata is being loaded.

        Returns:
            Pep691Metadata: The metadata information for the specified project name.
        """
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
        """
        Builds a list of resolver candidates from the given index data.

        This function processes index files provided through the `pep691` metadata,
        filters them based on the specified conditions, and returns a list of candidates
        that can be used by the resolver. If a file does not match the criteria, it will
        not be included in the resulting list.

        Parameters:
        name (str): The name of the package for which candidates are being generated.
        pep691 (Pep691Metadata): An object containing metadata and file information
            related to the package's index.
        combined_spec (SpecifierSet | None): A collection of version specifiers used
            to filter files based on their compatibility. If None, no filtering is applied.
        py_version (str): The Python version string to evaluate the compatibility of
            candidates.
        bad (set[tuple[str, str, str]]): A set of tuples representing combinations of
            package versions and Python versions that should be excluded.

        Returns:
        list[ResolverCandidate]: A list of resolver candidates created from the index
            data that meet the specified conditions.
        """
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

    @staticmethod
    def _matches_tag(
        f: Pep691FileMetadata,
        name: str,
        combined_spec: SpecifierSet | None,
        py_version: str,
        dist: NormalizedName,
        ver: Version,
    ) -> bool:
        """
        Determines if the given distribution and version match the specified criteria.

        This static method performs various checks to determine if a distribution name,
        version, and other metadata match a provided specification. The comparison also
        ensures compatibility with a specified Python version if required.

        Args:
            f: An instance of Pep691FileMetadata containing metadata about a file.
            name: The normalized distribution name to match against.
            combined_spec: An optional SpecifierSet that represents additional constraints
                           on the version to be matched.
            py_version: A string representing the target Python version for compatibility checks.
            dist: The normalized name of the distribution being evaluated.
            ver: The version of the distribution being evaluated.

        Returns:
            A boolean value indicating whether all criteria are satisfied and the provided
            information matches the defined specifications.
        """
        if canonicalize_name(dist) != name:
            return False

        if combined_spec is not None and not combined_spec.contains(str(ver)):
            return False

        if f.requires_python:
            try:
                if not SpecifierSet(f.requires_python).contains(py_version):
                    return False
            except Exception:
                pass

        return True

    def _is_non_yanked_wheel_file(self, f: Pep691FileMetadata) -> bool:
        """
        Determines if the provided wheel file meets the criteria for being considered
        non-yanked under the current policy.

        Parameters:
        f (Pep691FileMetadata): The metadata object representing the wheel file.

        Returns:
        bool: True if the file is a wheel, not marked as yanked, and the current
        yanked wheel policy specifies skipping yanked wheels. Otherwise, False.
        """
        return (
            f.filename.lower().endswith(".whl")
            and not f.yanked
            and self._policy.yanked_wheel_policy == YankedWheelPolicy.SKIP
        )

    def _validate_and_parse_wheel(
        self,
        *,
        f: Pep691FileMetadata,
        name: str,
        combined_spec: SpecifierSet | None,
        py_version: str,
    ) -> tuple[str, str, frozenset[str], tuple[str, str]] | None:
        """
        Validates and parses a wheel file to ensure it meets the specified requirements
        such as name, version specifiers, supported Python version, and compatible tags.
        If all criteria are met, returns pertinent metadata about the wheel. Otherwise,
        returns None.

        Arguments:
            f (Pep691FileMetadata): Metadata for the file to be validated and parsed.
            name (str): The expected canonical name of the distribution.
            combined_spec (SpecifierSet | None): SpecifierSet for version compatibility
                or None if version constraints are not specified.
            py_version (str): The targeted Python version to validate against the
                `requires_python` metadata.

        Returns:
            tuple[str, str, frozenset[str], tuple[str, str]] | None: A tuple containing
                the wheel version, best matching tag, frozen set of applicable tags,
                and best hash spec if validation is successful. Returns None otherwise.
        """
        if not self._is_non_yanked_wheel_file(f):
            return None

        try:
            dist, ver, _build, tags = parse_wheel_filename(f.filename)
        except Exception:
            return None

        if not self._matches_tag(f, name, combined_spec, py_version, dist, ver):
            return None

        file_tag_set = {str(t) for t in tags}
        best_tag = self._best_tag(file_tag_set)
        hash_spec = self._best_hash(f)

        if best_tag is None or hash_spec is None:
            return None

        return str(ver), best_tag, frozenset(file_tag_set), hash_spec

    def _candidate_from_index_file(
        self,
        *,
        name: str,
        f: Pep691FileMetadata,
        combined_spec: SpecifierSet | None,
        py_version: str,
        bad: set[tuple[str, str, str]],
    ) -> ResolverCandidate | None:
        """
        Generates a resolver candidate from metadata in the provided index file.

        This method processes metadata associated with a wheel file to create an instance
        of a resolver candidate. The validation and parsing of the wheel occur with checks
        on compatibility, Python version constraints, and hash integrity. If the
        metadata does not meet the required conditions or represents a "bad" candidate,
        the function returns None.

        Parameters:
        name : str
            The name of the package associated with the wheel.
        f : Pep691FileMetadata
            Metadata object containing wheel information such as version, tags, URL, and
            other relevant attributes.
        combined_spec : SpecifierSet | None
            A set of version specifiers used to validate the candidate version against
            required constraints. If None, version checks are skipped.
        py_version : str
            The version of Python used to determine compatibility with the wheel.
        bad : set[tuple[str, str, str]]
            A collection of tuples identifying "bad" candidates by their name, version,
            and tags. These candidates are excluded from resolution.

        Returns:
        ResolverCandidate | None
            An instance of ResolverCandidate if the wheel metadata validates
            successfully and is not listed in the "bad" candidates. If validation
            fails or the candidate is deemed bad, None is returned.
        """
        result = self._validate_and_parse_wheel(
            f=f, name=name, combined_spec=combined_spec, py_version=py_version
        )
        if result is None:
            return None

        ver_str, best_tag, file_tag_set, hash_spec = result
        alg, h = hash_spec

        wk = WheelKey(
            name=name,
            version=ver_str,
            tag=best_tag,
            requires_python=f.requires_python,
            satisfied_tags=file_tag_set,
            origin_uri=f.url,
            content_hash=h,
            hash_algorithm=alg,
        )

        if (wk.name, wk.version, wk.tag) in bad:
            return None

        return ResolverCandidate(wheel_key=wk)

    def _best_tag(self, file_tag_set: set[str]) -> str | None:
        """
        Determines the best matching tag from a provided set of tags based on a predefined
        order of preference.

        Parameters:
        file_tag_set : set[str]
            A set of tags to be evaluated against the preferred order.

        Returns:
        str or None
            The highest-priority tag from the provided set, as determined by the order of
            preference. Returns None if no tags from the provided set match the preferred
            order.

        Raises:
            None
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
        Sorts a list of ResolverCandidate objects based on version and wheel tag.

        This method reorders a given list of ResolverCandidate objects by applying a
        sorting function. The primary sort key is derived from the version of the
        ResolverCandidate. The secondary sort key is the wheel tag of the candidate.
        The sorting is performed in descending order.

        Parameters:
        candidates: list[ResolverCandidate]
            A list of ResolverCandidate objects to be sorted.

        Returns:
        list[ResolverCandidate]
            The sorted list of ResolverCandidate objects.
        """
        candidates.sort(
            key=lambda c: (_version_sort_key(c.version), c.wheel_key.tag), reverse=True
        )
        return candidates

    def is_satisfied_by(
        self, requirement: ResolverRequirement, candidate: ResolverCandidate
    ) -> bool:
        """
        Determines if a candidate satisfies a given requirement based on specific conditions.

        This function evaluates whether the provided candidate meets the specified
        requirement by comparing their attributes such as name, URI, and version.
        It performs thorough comparisons to ensure that the candidate aligns with
        the expected requirements.

        Args:
            requirement (ResolverRequirement): The requirement used as the basis for
                comparison. Contains attributes such as `name`, `uri`, and `version`.
            candidate (ResolverCandidate): The candidate being validated against the
                requirement. Includes relevant information such as `name`,
                `wheel_key.origin_uri`, and `version`.

        Returns:
            bool: True if the candidate satisfies the requirement based on matching
            criteria; otherwise, False.

        Raises:
            Exception: Raised if an error occurs during the version comparison.
        """
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

    @staticmethod
    def _parse_requirement(raw: str) -> Requirement | None:
        """
        Parses a raw requirement string into a Requirement object, handling
        exceptions that may arise during the parsing process.

        This method attempts to create a `Requirement` object using the given
        raw string. If the string cannot be parsed due to an error, the method
        returns `None`.

        Args:
            raw: Represents the raw string of the requirement to parse.

        Returns:
            A `Requirement` object if parsing is successful, or `None` if parsing
            fails due to an exception.
        """
        try:
            return Requirement(raw)
        except Exception:
            return None

    @staticmethod
    def _requirement_applies_to_extras(
        req: Requirement,
        requested_extras: frozenset[str],
        marker_env_base: dict[str, str],
    ) -> bool:
        """
        Determines if a given requirement applies based on the specified extras and marker environment.

        This utility checks whether the marker associated with the given requirement evaluates
        to `True` under the provided marker environment, taking into account any specified extras.

        Parameters:
        req: Requirement
            The requirement to be checked. This defines the conditions specified
            for applying the requirement.
        requested_extras: frozenset[str]
            The set of requested extras (optional parameters/features of a package),
            represented as a frozen set of strings.
        marker_env_base: dict[str, str]
            The base marker environment, given as a dictionary where keys and
            values represent environment markers and their corresponding values.

        Returns:
        bool
            True if the requirement applies for any of the requested extras (or without extras),
            otherwise False.
        """
        if req.marker is None:
            return True

        if not requested_extras:
            return req.marker.evaluate(environment=marker_env_base)

        # Check if marker evaluates true for any requested extra
        for extra in requested_extras:
            marker_env = dict(marker_env_base)
            marker_env["extra"] = extra
            if req.marker.evaluate(environment=marker_env):
                return True
        return False

    @staticmethod
    def _requirement_to_resolver_requirement(req: Requirement) -> ResolverRequirement:
        """
        Converts a Requirement object to a ResolverRequirement object.

        This method takes in a Requirement object and maps its attributes to
        create a new ResolverRequirement object. It handles optional values such
        as specifier, URL, and extras, setting them appropriately in the resulting
        ResolverRequirement object.

        Args:
            req (Requirement): The Requirement object to be converted into a
            ResolverRequirement.

        Returns:
            ResolverRequirement: A newly created ResolverRequirement object
            containing the mapped attributes from the input Requirement.
        """
        return ResolverRequirement(
            wheel_spec=WheelSpec(
                name=req.name,
                version=req.specifier if str(req.specifier) else None,
                extras=frozenset(req.extras),
                marker=req.marker,
                uri=req.url if req.url else None,
            )
        )

    def get_dependencies(
        self, candidate: ResolverCandidate
    ) -> Iterable[ResolverRequirement]:
        """
        Retrieves a list of dependencies for a given candidate.

        This method resolves dependencies by analyzing the metadata associated with
        the provided candidate. It uses caching to optimize performance and ensures
        that only applicable dependencies based on extras and marker environment are
        returned.

        Args:
            candidate (ResolverCandidate):
                The candidate whose dependencies need to be resolved.

        Returns:
            Iterable[ResolverRequirement]:
                An iterable of resolved dependencies for the candidate. If the
                candidate lacks origin URI, an empty iterable is returned.
        """
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
            req = self._parse_requirement(raw)
            if req is None:
                continue

            if not self._requirement_applies_to_extras(
                req, requested_extras, marker_env_base
            ):
                continue

            deps.append(self._requirement_to_resolver_requirement(req))

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
        Determine the resolution priority for a given identifier during dependency resolution.

        This function calculates a preference score for resolving a specific identifier by
        considering various factors such as whether it is a root requirement, how many parents
        impose constraints, whether it is implicated in backtracking, and if it is already resolved.
        Lower scores represent higher resolution priority.

        Args:
            identifier: The identifier whose resolution priority is being determined.
            resolutions: A mapping of currently resolved identifiers to their resolved
                candidates.
            candidates: A mapping of identifiers to iterators providing possible resolution
                candidates.
            information: A mapping of identifiers to iterators providing information about
                requirements associated with the identifier.
            backtrack_causes: A sequence containing requirement information objects representing
                the causes of backtracking in the resolution process.

        Returns:
            A tuple representing the priority of resolving the given identifier, where smaller
            values indicate a higher priority for resolution.
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
    """
    Resolve a sequence of requirements into resolved candidates using the given services
    and environment.

    This function defines a provider and a reporter for project resolution, which are
    passed to an instance of a resolver. The resolver processes the input requirements
    and resolves them into corresponding candidates alongside a resolution result.

    Arguments:
        services: A collection of services used for the resolution process.
        env: The resolution environment providing configuration and context for the
             resolution process.
        roots: A sequence of requirements that need to be resolved into candidates.

    Returns:
        A `Result` object containing resolved requirements, candidates, and
        associated resolution metadata (represented as strings).
    """
    provider = ProjectResolutionProvider(services=services, env=env)
    reporter = ProjectResolutionReporter()
    resolver: Resolver[ResolverRequirement, ResolverCandidate, str] = Resolver(
        provider, reporter
    )
    return resolver.resolve(roots)
