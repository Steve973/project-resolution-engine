from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, Collection, Protocol

from packaging.markers import Marker
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from resolvelib import BaseReporter
from resolvelib.resolvers import Criterion
from resolvelib.structs import State, RequirementInformation
from typing_extensions import Self

from project_resolution_engine.internal.util.multiformat import MultiformatModelMixin
from project_resolution_engine.model.keys import WheelKey
from project_resolution_engine.model.resolution import WheelSpec


class Preference(Protocol):
    def __lt__(self, __other: Any) -> bool: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolverRequirement(MultiformatModelMixin):
    wheel_spec: WheelSpec

    @property
    def name(self) -> str:
        return canonicalize_name(self.wheel_spec.name)

    @property
    def version(self) -> SpecifierSet | None:
        return self.wheel_spec.version

    @property
    def extras(self) -> frozenset[str]:
        return self.wheel_spec.extras

    @property
    def marker(self) -> Marker | None:
        return self.wheel_spec.marker

    @property
    def uri(self) -> str | None:
        return self.wheel_spec.uri

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {"wheel_spec": self.wheel_spec.to_mapping()}

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Self:
        return cls(wheel_spec=WheelSpec.from_mapping(mapping["wheel_spec"]))


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolverCandidate(MultiformatModelMixin):
    wheel_key: WheelKey

    @property
    def name(self) -> str:
        return self.wheel_key.name

    @property
    def version(self) -> str:
        return self.wheel_key.version

    @property
    def tag(self) -> str:
        return self.wheel_key.tag

    @property
    def requires_python(self) -> str | None:
        return self.wheel_key.requires_python

    @property
    def satisfied_tags(self) -> frozenset[str]:
        return self.wheel_key.satisfied_tags

    @property
    def dependency_ids(self) -> frozenset[str] | None:
        return self.wheel_key.dependency_ids

    @property
    def origin_uri(self) -> str | None:
        return self.wheel_key.origin_uri

    @property
    def marker(self) -> str | None:
        return self.wheel_key.marker

    @property
    def extras(self) -> frozenset[str] | None:
        return self.wheel_key.extras

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {"wheel_key": self.wheel_key.to_mapping()}

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Self:
        return cls(wheel_key=WheelKey.from_mapping(mapping["wheel_key"]))


class ProjectResolutionReporter(BaseReporter[ResolverRequirement, ResolverCandidate, str]):
    def starting(self) -> None:
        logging.log(logging.INFO, "Starting resolution...")

    def starting_round(self, index: int) -> None:
        logging.log(logging.DEBUG, f"Starting round {index}")

    def ending_round(self, index: int, state: State[ResolverRequirement, ResolverCandidate, str]) -> None:
        logging.log(logging.DEBUG, f"Ending round {index}")

    def ending(self, state) -> None:
        logging.log(logging.INFO, "Resolution complete.")

    def adding_requirement(self, requirement, parent) -> None:
        logging.log(logging.DEBUG, f"Adding requirement: {requirement}")

    def pinning(self, candidate) -> None:
        logging.log(logging.DEBUG, f"Pinning candidate: {candidate}")

    def rejecting_candidate(
            self,
            criterion: Criterion[ResolverRequirement, ResolverCandidate],
            candidate: ResolverCandidate) -> None:
        logging.log(logging.DEBUG, f"Rejecting candidate: {candidate} (criterion={criterion})")

    def resolving_conflicts(
            self,
            causes: Collection[RequirementInformation[ResolverRequirement, ResolverCandidate]]) -> None:
        logging.log(logging.DEBUG, f"Resolving conflicts: {causes}")
