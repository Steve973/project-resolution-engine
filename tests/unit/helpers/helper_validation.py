from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, fields as dc_fields, is_dataclass
from typing import ClassVar, cast, Any


@dataclass(frozen=True, slots=True)
class MirrorReport:
    missing_in_fake: tuple[str, ...]
    extra_in_fake: tuple[str, ...]
    ignored: tuple[str, ...]
    aliases: tuple[tuple[str, str], ...]  # (real, fake)

    @property
    def ok(self) -> bool:
        return not self.missing_in_fake and not self.extra_in_fake

    def pretty(self) -> str:
        return (
            "MirrorReport(\n"
            f"  ok={self.ok},\n"
            f"  missing_in_fake={list(self.missing_in_fake)},\n"
            f"  extra_in_fake={list(self.extra_in_fake)},\n"
            f"  ignored={list(self.ignored)},\n"
            f"  aliases={dict(self.aliases)},\n"
            ")"
        )


class MirrorValidatableFake(ABC):
    """
    Inherit this in a fake. Tests will call `validate_mirror(RealClass)`.

    This compares:
      - dataclass field names
      - @property names
    """

    MIRROR_IGNORE: ClassVar[frozenset[str]] = frozenset()
    MIRROR_ALLOW_EXTRA: ClassVar[frozenset[str]] = frozenset()
    MIRROR_ALIASES: ClassVar[dict[str, str]] = {}  # real_name -> fake_name
    MIRROR_INCLUDE_PRIVATE: ClassVar[bool] = True

    @classmethod
    def validate_mirror(cls, real_cls: type) -> MirrorReport:
        fake = cls._surface_names(cls)
        real = cls._surface_names(real_cls)

        aliases = dict(cls.MIRROR_ALIASES or {})
        real_mapped = {aliases.get(n, n) for n in real}

        ignore = set(cls.MIRROR_IGNORE or frozenset())
        allow_extra = set(cls.MIRROR_ALLOW_EXTRA or frozenset())

        missing = sorted((real_mapped - fake) - ignore)
        extra = sorted((fake - real_mapped) - allow_extra)

        return MirrorReport(
            missing_in_fake=tuple(missing),
            extra_in_fake=tuple(extra),
            ignored=tuple(sorted(ignore)),
            aliases=tuple(sorted(aliases.items())),
        )

    @classmethod
    def _surface_names(cls, target: type) -> set[str]:
        names: set[str] = set()

        if is_dataclass(target):
            names.update(f.name for f in dc_fields(cast(Any, target)))

        for base in target.__mro__:
            for n, v in base.__dict__.items():
                if isinstance(v, property):
                    names.add(n)

        if not cls.MIRROR_INCLUDE_PRIVATE:
            names = {n for n in names if not n.startswith("_")}

        return names
