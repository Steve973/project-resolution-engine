from project_resolution_engine.internal.util.multiformat import (
    MultiformatSerializableMixin,
    MultiformatDeserializableMixin,
    MultiformatModelMixin,
)


class SerializableFixture(MultiformatSerializableMixin):
    """Test class implementing MultiformatSerializableMixin."""

    def __init__(self, data):
        self.data = data

    def to_mapping(self):
        return self.data


class DeserializableFixture(MultiformatDeserializableMixin):
    """Test class implementing MultiformatDeserializableMixin."""

    def __init__(self, data):
        self.data = data
        self.source_description = None

    @classmethod
    def from_mapping(cls, mapping, **_):
        return cls(mapping)


class MultiformatModelFixture(MultiformatModelMixin):
    """Test class implementing MultiformatModelMixin."""

    def __init__(self, data):
        self.data = data
        self.source_description = None

    def to_mapping(self):
        return self.data

    @classmethod
    def from_mapping(cls, mapping, **_):
        return cls(mapping)
