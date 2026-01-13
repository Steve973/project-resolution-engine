from typing import Any

import pytest

from project_resolution_engine.internal.resolvelib_types import ResolverRequirement, ResolverCandidate
from project_resolution_engine.model.graph import ResolvedNode, ResolvedGraph
from project_resolution_engine.model.keys import IndexMetadataKey, CoreMetadataKey, WheelKey
from project_resolution_engine.model.pep import Pep658Metadata, Pep691FileMetadata, Pep691Metadata
from project_resolution_engine.model.resolution import WheelSpec, ResolutionPolicy, ResolutionEnv, ResolutionParams, \
    ResolutionResult
from project_resolution_engine.repository import ArtifactRecord
from unit.helpers.helper_validation import MirrorValidatableFake
from unit.helpers.models_helper import FakeWheelKey, FakeWheelSpec, FakeIndexMetadataKey, FakeCoreMetadataKey, \
    FakeResolvedNode, FakeResolvedGraph, FakePep658Metadata, FakePep691FileMetadata, FakePep691Metadata, \
    FakeResolutionPolicy, FakeResolutionEnv, FakeResolutionParams, FakeResolutionResult, FakeResolverRequirement, \
    FakeResolverCandidate, FakeArtifactRecord

"""
This module tests that the models helpers contracts (fakes for various model
classes) do not become outdated as the models change. If tests are failing, it
will be helpful to know, specifically, if it is caused by a model change and
the helper becoming outdated.
"""

MIRROR_PAIRS = [
    (WheelKey, FakeWheelKey),
    (WheelSpec, FakeWheelSpec),
    (IndexMetadataKey, FakeIndexMetadataKey),
    (CoreMetadataKey, FakeCoreMetadataKey),
    (ResolvedNode, FakeResolvedNode),
    (ResolvedGraph, FakeResolvedGraph),
    (Pep658Metadata, FakePep658Metadata),
    (Pep691FileMetadata, FakePep691FileMetadata),
    (Pep691Metadata, FakePep691Metadata),
    (ResolutionPolicy, FakeResolutionPolicy),
    (ResolutionEnv, FakeResolutionEnv),
    (ResolutionParams, FakeResolutionParams),
    (ResolutionResult, FakeResolutionResult),
    (ResolverRequirement, FakeResolverRequirement),
    (ResolverCandidate, FakeResolverCandidate),
    (ArtifactRecord, FakeArtifactRecord),
]


@pytest.mark.parametrize(
    "real_cls,fake_cls",
    MIRROR_PAIRS,
    ids=[r.__name__ for r, _ in MIRROR_PAIRS]
)
def test_fake_mirrors_model(real_cls: type[Any], fake_cls: type[MirrorValidatableFake]) -> None:
    report = fake_cls.validate_mirror(real_cls)
    assert report.ok, report.pretty()
