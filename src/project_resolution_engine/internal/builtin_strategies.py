from __future__ import annotations

import hashlib
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from typing import Final
from urllib.parse import unquote
from urllib.parse import urlparse

import requests

from project_resolution_engine.repository import ArtifactRecord, ArtifactSource
from project_resolution_engine.model.keys import IndexMetadataKey, CoreMetadataKey, WheelKey
from project_resolution_engine.strategies import (
    StrategyNotApplicable, WheelFileStrategy, CoreMetadataStrategy, IndexMetadataStrategy,
)

_INVALID_SEGMENT_CHARS: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_segment(value: str) -> str:
    """
    Make a filesystem-safe path segment.
    """
    value = value.strip()
    if not value:
        return "_"
    value = _INVALID_SEGMENT_CHARS.sub("_", value)
    return value[:160]  # keep segments sane


def _short_hash(value: str) -> str:
    """
    Stable short hash for building unique filenames without leaking huge URLs into paths.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _url_basename(url: str) -> str | None:
    """
    Best-effort extraction of a filename-like basename from a URL.
    """
    try:
        parsed = urlparse(url)
        if not parsed.path:
            return None
        base = Path(unquote(parsed.path)).name
        return base or None
    except Exception:
        return None


# -------------------------
# helpers
# -------------------------

def _require_file_destination(destination_uri: str) -> Path:
    """
    Built-in strategies are intentionally file-only.

    If a user wants s3://, gs://, etc., they provide their own strategy implementation.
    """
    parsed = urlparse(destination_uri)
    if parsed.scheme != "file":
        raise ValueError(f"Built-in strategies require file:// destination URIs, got: {destination_uri!r}")
    return Path(parsed.path)


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _simple_project_json_url(index_base: str, project: str) -> str:
    base = index_base.rstrip("/") + "/"
    proj = project.strip("/")
    return f"{base}{proj}/"


def _write_canonical_json(path: Path, payload: Any) -> None:
    # Deterministic output for stable hashes.
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _pep658_metadata_url(file_url: str) -> str:
    # PEP 658 sidecar is served at "<file_url>.metadata".
    return f"{file_url}.metadata"


def _find_dist_info_metadata_path(zf: zipfile.ZipFile) -> str:
    """
    Find a member path that looks like "<something>.dist-info/METADATA".
    """
    candidates = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
    if not candidates:
        raise FileNotFoundError("Wheel does not contain any *.dist-info/METADATA entry")
    # Deterministic pick.
    candidates.sort()
    return candidates[0]


# -------------------------
# strategies
# -------------------------

@dataclass(frozen=True)
class Pep691IndexMetadataHttpStrategy(IndexMetadataStrategy):
    name: str = "pep691_http"
    precedence: int = 50
    timeout_s: float = 30.0
    user_agent: str = "project-resolution-engine/0"

    def resolve(self, *, key: IndexMetadataKey, destination_uri: str) -> ArtifactRecord | None:
        if not isinstance(key, IndexMetadataKey):
            raise StrategyNotApplicable()

        dest_path = _require_file_destination(destination_uri)
        _ensure_parent_dir(dest_path)

        url = _simple_project_json_url(key.index_base, key.project)
        headers = {
            "Accept": "application/vnd.pypi.simple.v1+json",
            "User-Agent": self.user_agent,
        }

        resp = requests.get(url, headers=headers, timeout=self.timeout_s)
        resp.raise_for_status()

        payload: Any = resp.json()
        _write_canonical_json(dest_path, payload)

        size = dest_path.stat().st_size
        sha256 = _sha256_file(dest_path)

        return ArtifactRecord(
            key=key,
            destination_uri=dest_path.as_uri(),
            origin_uri=url,
            source=self.source,
            content_sha256=sha256,
            size=size,
            content_hashes={"sha256": sha256})


@dataclass(frozen=True)
class HttpWheelFileStrategy(WheelFileStrategy):
    name: str = "wheel_http"
    precedence: int = 50
    timeout_s: float = 120.0
    user_agent: str = "project-resolution-engine/0"
    chunk_bytes: int = 1024 * 1024

    def resolve(self, *, key: WheelKey, destination_uri: str) -> ArtifactRecord | None:
        if not isinstance(key, WheelKey):
            raise StrategyNotApplicable()

        dest_path = _require_file_destination(destination_uri)
        _ensure_parent_dir(dest_path)

        headers = {"User-Agent": self.user_agent}

        if key.origin_uri is None:
            raise ValueError("WheelKey must have origin_uri set")

        with requests.get(key.origin_uri, headers=headers, timeout=self.timeout_s, stream=True) as resp:
            resp.raise_for_status()
            with dest_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=self.chunk_bytes):
                    if chunk:
                        f.write(chunk)

        size = dest_path.stat().st_size
        sha256 = _sha256_file(dest_path)

        return ArtifactRecord(
            key=key,
            destination_uri=dest_path.as_uri(),
            origin_uri=key.origin_uri,
            source=self.source,
            content_sha256=sha256,
            size=size,
            content_hashes={"sha256": sha256})


@dataclass(frozen=True)
class Pep658CoreMetadataHttpStrategy(CoreMetadataStrategy):
    """
    Download core metadata via PEP 658 sidecar (<file_url>.metadata).
    """
    name: str = "pep658_http"
    precedence: int = 50
    timeout_s: float = 30.0
    user_agent: str = "project-resolution-engine/0"

    def resolve(self, *, key: CoreMetadataKey, destination_uri: str) -> ArtifactRecord | None:
        if not isinstance(key, CoreMetadataKey):
            raise StrategyNotApplicable()

        dest_path = _require_file_destination(destination_uri)
        _ensure_parent_dir(dest_path)

        url = _pep658_metadata_url(key.file_url)
        headers = {"User-Agent": self.user_agent}

        resp = requests.get(url, headers=headers, timeout=self.timeout_s)
        if resp.status_code == 404:
            # Explicitly not applicable: let fallback strategies run.
            raise StrategyNotApplicable()

        resp.raise_for_status()
        dest_path.write_bytes(resp.content)

        size = dest_path.stat().st_size
        sha256 = _sha256_file(dest_path)

        return ArtifactRecord(
            key=key,
            destination_uri=dest_path.as_uri(),
            origin_uri=url,
            source=self.source,
            content_sha256=sha256,
            size=size,
            content_hashes={"sha256": sha256})


@dataclass(frozen=True)
class WheelExtractedCoreMetadataStrategy(CoreMetadataStrategy):
    """
    Fallback: download the wheel (using an injected WheelFileStrategy) and extract
    *.dist-info/METADATA into destination_uri.
    """
    name: str = "wheel_extracted_metadata"
    precedence: int = 90
    source: ArtifactSource = ArtifactSource.WHEEL_EXTRACTED
    wheel_strategy: WheelFileStrategy = field(kw_only=True)

    def resolve(self, *, key: CoreMetadataKey, destination_uri: str) -> ArtifactRecord | None:
        if not isinstance(key, CoreMetadataKey):
            raise StrategyNotApplicable()

        dest_path = _require_file_destination(destination_uri)
        _ensure_parent_dir(dest_path)

        wheel_key = WheelKey(
            name=key.name,
            version=key.version,
            tag=key.tag,
            origin_uri=key.file_url)

        with tempfile.TemporaryDirectory(prefix="pre-wheel-extract-") as td:
            wheel_path = Path(td) / "artifact.whl"
            wheel_uri = wheel_path.as_uri()

            # Acquire wheel (no repository access here).
            self.wheel_strategy.resolve(key=wheel_key, destination_uri=wheel_uri)

            with zipfile.ZipFile(wheel_path, "r") as zf:
                meta_member = _find_dist_info_metadata_path(zf)
                metadata_bytes = zf.read(meta_member)

            dest_path.write_bytes(metadata_bytes)

        size = dest_path.stat().st_size
        sha256 = _sha256_file(dest_path)

        return ArtifactRecord(
            key=key,
            destination_uri=dest_path.as_uri(),
            origin_uri=key.file_url,
            source=self.source,
            content_sha256=sha256,
            size=size,
            content_hashes={"sha256": sha256})


@dataclass(frozen=True)
class DirectUriWheelFileStrategy(WheelFileStrategy):
    name: str = "uri_wheel_file"
    precedence: int = 40  # higher priority than HTTP
    chunk_bytes: int = 1024 * 1024
    source: ArtifactSource = ArtifactSource.URI_WHEEL

    def resolve(self, *, key: WheelKey, destination_uri: str) -> ArtifactRecord | None:
        if not isinstance(key, WheelKey):
            raise StrategyNotApplicable()
        if key.origin_uri is None:
            raise ValueError("WheelKey must have origin_uri set")

        src_parsed = urlparse(key.origin_uri)
        if src_parsed.scheme not in ("file", ""):
            raise StrategyNotApplicable()

        dest_path = _require_file_destination(destination_uri)
        _ensure_parent_dir(dest_path)

        # src path
        src_path = Path(src_parsed.path) if src_parsed.scheme == "file" else Path(key.origin_uri)
        if not src_path.exists():
            raise FileNotFoundError(str(src_path))

        # copy
        with src_path.open("rb") as r, dest_path.open("wb") as w:
            for chunk in iter(lambda: r.read(self.chunk_bytes), b""):
                w.write(chunk)

        size = dest_path.stat().st_size
        sha256 = _sha256_file(dest_path)

        return ArtifactRecord(
            key=key,
            destination_uri=dest_path.as_uri(),
            origin_uri=key.origin_uri,
            source=self.source,
            content_sha256=sha256,
            size=size,
            content_hashes={"sha256": sha256})


@dataclass(frozen=True)
class DirectUriCoreMetadataStrategy(CoreMetadataStrategy):
    """
    Resolve core metadata for a wheel whose CoreMetadataKey.file_url is a local path
    or file:// URI by extracting *.dist-info/METADATA directly from the wheel.
    """
    name: str = "direct_uri_core_metadata"
    precedence: int = 40
    source: ArtifactSource = ArtifactSource.URI_WHEEL

    def resolve(self, *, key: CoreMetadataKey, destination_uri: str) -> ArtifactRecord | None:
        if not isinstance(key, CoreMetadataKey):
            raise StrategyNotApplicable()

        parsed = urlparse(key.file_url)
        if parsed.scheme not in ("", "file"):
            raise StrategyNotApplicable()

        wheel_path = Path(unquote(parsed.path)) if parsed.scheme == "file" else Path(key.file_url)
        if not wheel_path.exists():
            raise FileNotFoundError(str(wheel_path))
        if not wheel_path.is_file():
            raise ValueError(f"Core metadata file_url is not a file: {wheel_path}")

        dest_path = _require_file_destination(destination_uri)
        _ensure_parent_dir(dest_path)

        with zipfile.ZipFile(wheel_path) as zf:
            member = _find_dist_info_metadata_path(zf)
            metadata_bytes = zf.read(member)
            dest_path.write_bytes(metadata_bytes)

        size = dest_path.stat().st_size
        sha256 = _sha256_file(dest_path)

        return ArtifactRecord(
            key=key,
            destination_uri=dest_path.as_uri(),
            origin_uri=key.file_url,
            source=self.source,
            content_sha256=sha256,
            size=size,
            content_hashes={"sha256": sha256})
