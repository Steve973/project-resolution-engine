from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from project_resolution_engine.internal.builtin_strategies import (
    _short_hash,
    _safe_segment,
    _url_basename,
)
from project_resolution_engine.model.keys import (
    BaseArtifactKey,
    IndexMetadataKey,
    CoreMetadataKey,
    WheelKey,
)
from project_resolution_engine.repository import ArtifactRepository, ArtifactRecord


@dataclass(slots=True)
class EphemeralArtifactRepository(ArtifactRepository):
    """
    Ephemeral artifact repository.

    Properties:
    - Run-scoped: uses a TemporaryDirectory and an in-memory index.
    - Storage: file:// destination URIs under an ephemeral root dir.
    - Uniqueness: controlled solely by the provided BaseArtifactKey equality/hash.
    - No persistence: index is not saved and the directory is cleaned up on close().

    Notes:
    - This repository does not validate content hashes; acquisition strategies can populate
      ArtifactRecord.content_sha256 / content_hashes if desired.
    """

    _tmp: tempfile.TemporaryDirectory[str]
    _root: Path
    _index: dict[BaseArtifactKey, ArtifactRecord]

    def __init__(self, *, prefix: str = "project-resolution-engine-ephemeral-") -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix=prefix)
        self._root = Path(self._tmp.name).resolve()
        self._index = {}

    # -------------------------
    # lifecycle
    # -------------------------

    @property
    def root_path(self) -> Path:
        return self._root

    @property
    def root_uri(self) -> str:
        return self._root.as_uri()

    def close(self) -> None:
        """
        Clean up the ephemeral workspace and clear the in-memory index.
        """
        self._index.clear()
        self._tmp.cleanup()

    def __enter__(self) -> EphemeralArtifactRepository:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # -------------------------
    # repository API
    # -------------------------

    def get(self, key: BaseArtifactKey) -> ArtifactRecord | None:
        """
        Return an ArtifactRecord if present. If the record exists but the underlying file
        is missing (e.g., a user deleted it), we drop it from the index and return None.
        """
        record = self._index.get(key)
        if record is None:
            return None

        # Only enforce existence for file:// destinations we generated.
        dest = record.destination_uri
        if dest.startswith("file://"):
            try:
                path = Path(dest.removeprefix("file://"))
                if not path.exists():
                    self._index.pop(key, None)
                    return None
            except Exception:
                # If parsing fails, just return the record; it's still an in-memory truth.
                return record

        return record

    def put(self, record: ArtifactRecord) -> None:
        self._index[record.key] = record

    def delete(self, key: BaseArtifactKey) -> None:
        record = self._index.pop(key, None)
        if record is None:
            return

        # Best-effort delete the underlying file if it's in our ephemeral root.
        dest = record.destination_uri
        if not dest.startswith("file://"):
            return

        try:
            path = Path(dest.removeprefix("file://")).resolve()
            if self._is_under_root(path) and path.exists():
                path.unlink()
        except Exception:
            # Intentionally swallow. Ephemeral repo should never fail hard on cleanup.
            return

    def allocate_destination_uri(self, key: BaseArtifactKey) -> str:
        """
        Allocate a file:// destination URI for the given key.

        This repository chooses deterministic paths for a given key to make debugging
        easier and to support "miss then allocate" flows cleanly.
        """
        path = self._allocate_path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.as_uri()

    # -------------------------
    # internals
    # -------------------------

    def _is_under_root(self, path: Path) -> bool:
        try:
            path.relative_to(self._root)
            return True
        except Exception:
            return False

    def _allocate_path_for_key(self, key: BaseArtifactKey) -> Path:
        match key:
            case IndexMetadataKey() as k:
                base_hash = _short_hash(k.index_base)
                project = _safe_segment(k.project)
                # Keep the index base partitioned to avoid collisions if the client uses multiple indexes.
                return self._root / "index_metadata" / base_hash / f"{project}.json"

            case CoreMetadataKey() as k:
                name = _safe_segment(k.name)
                version = _safe_segment(k.version)
                tag = _safe_segment(k.tag)
                url_hash = _short_hash(k.file_url)
                # Store as .metadata for clarity.
                return (
                    self._root
                    / "core_metadata"
                    / name
                    / version
                    / tag
                    / f"{url_hash}.metadata"
                )

            case WheelKey() as k:
                name = _safe_segment(k.name)
                version = _safe_segment(k.version)
                tag = _safe_segment(k.tag)
                if k.origin_uri is None:
                    raise ValueError("WheelKey must have an origin_uri")
                url_hash = _short_hash(k.origin_uri)

                # Prefer the basename from the URL if it looks sane, else use hash.
                base = _url_basename(k.origin_uri)
                if base is not None and base.endswith(".whl"):
                    filename = f"{url_hash}-{_safe_segment(base)}"
                else:
                    filename = f"{url_hash}.whl"

                return self._root / "wheels" / name / version / tag / filename

            case _:
                raise TypeError(f"Unsupported artifact key type: {type(key).__name__}")
