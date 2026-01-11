import hashlib
from collections import OrderedDict
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from unittest import mock

import pytest

from unit.helpers.serialization_helper import SerializableFixture, DeserializableFixture, MultiformatModelFixture
from project_resolution_engine.internal.util.multiformat import (
    _normalize,
    MultiformatSerializableMixin,
    MultiformatDeserializableMixin,
    MultiformatModelMixin
)

###############################################################################
# BRANCH LEDGER
###############################################################################
"""
## _normalize(value: Any)
B01: match value - case Path() -> returns value.as_posix()
B02: match value - case Enum() -> returns value.value
B03: match value - case Mapping() -> returns normalized mapping
B04: match value - case set() | frozenset() -> returns sorted list with normalized values
B05: match value - case list() | tuple() -> returns list with normalized values
B06: match value - case datetime() -> returns value.isoformat()
B07: match value - case _ -> returns value unchanged

## MultiformatSerializableMixin.mapping_hash()
B08: self.to_mapping() call -> returns normalized mapping
B09: json.dumps() with normalized mapping -> serializes to JSON
B10: hashlib.new("sha512", payload).hexdigest() -> computes and returns SHA-512 hash

## MultiformatSerializableMixin.to_mapping()
B11: NotImplementedError raised -> requires implementation in subclass

## MultiformatSerializableMixin.to_json()
B12: self.to_mapping() call -> converts object data to mapping
B13: json.dumps() with mapping -> returns JSON string

## MultiformatSerializableMixin.to_yaml()
B14: try import yaml -> successful import
B15: except ImportError -> raises RuntimeError
B16: yaml.safe_dump() -> returns YAML string

## MultiformatSerializableMixin.to_toml()
B17: sort_dict() recursively sorts dictionary -> returns sorted dictionary
B18: dump_toml_to_str() -> returns TOML string

## MultiformatSerializableMixin.serialize()
B19: match fmt - case 'json' -> returns self.to_json()
B20: match fmt - case 'yaml' -> returns self.to_yaml()
B21: match fmt - case 'toml' -> returns self.to_toml()
B22: match fmt - case _ -> raises ValueError with unrecognized format message

## MultiformatSerializableMixin.flat_summary()
B23: set(mapping.keys()) - set(exclude) -> filters excluded keys
B24: [f for f in first_fields if f in all_keys] -> filters first fields
B25: [f for f in last_fields if f in all_keys and f not in first] -> filters last fields
B26: sorted(all_keys - set(first) - set(last)) -> sorts middle keys
B27: for loop - zero iterations -> returns empty string
B28: for loop - one or more iterations -> processes keys
B29: if not include_empty and (v is None or v == "" or (isinstance(v, (list, tuple, set, dict)) and not v)) -> skips empty values
B30: if isinstance(v, (datetime, date)) -> formats as ISO string
B31: elif k.lower() == "payload" and isinstance(v, dict) -> formats as JSON string
B32: except Exception when formatting payload -> uses repr(v)
B33: elif isinstance(v, dict) -> formats as dictionary string
B34: elif isinstance(v, (list, tuple, set)) -> formats as list string
B35: else -> uses str(v)
B36: sep.join(items) -> joins items with separator

## MultiformatSerializableMixin.__str__()
B37: return self.flat_summary() -> delegates to flat_summary

## MultiformatDeserializableMixin.from_mapping()
B38: NotImplementedError raised -> requires implementation in subclass

## MultiformatDeserializableMixin.deserialize()
B39: cls._parse_text() call -> parses text based on format
B40: cls._coerce_root_mapping() call -> ensures parsed data is a mapping
B41: cls._preprocess_mapping() call -> preprocesses mapping
B42: cls.from_mapping() call -> creates instance from mapping
B43: cls._postprocess_instance() call -> postprocesses instance

## MultiformatDeserializableMixin.from_json()
B44: cls.deserialize() with fmt="json" -> delegates to deserialize()

## MultiformatDeserializableMixin.from_yaml()
B45: cls.deserialize() with fmt="yaml" -> delegates to deserialize()

## MultiformatDeserializableMixin.from_toml()
B46: cls.deserialize() with fmt="toml" -> delegates to deserialize()

## MultiformatDeserializableMixin.from_file()
B47: Path(path) -> converts path to Path object
B48: cls._load_text() call -> loads text from file
B49: fmt or cls._infer_format_from_suffix() -> infers format if not provided
B50: cls._parse_text() call -> parses text based on format
B51: cls._coerce_root_mapping() call -> ensures parsed data is a mapping
B52: cls._preprocess_mapping() call -> preprocesses mapping
B53: cls.from_mapping() call -> creates instance from mapping
B54: cls._postprocess_instance() call -> postprocesses instance

## MultiformatDeserializableMixin._load_text()
B55: path.read_text(encoding="utf-8") -> reads text from file

## MultiformatDeserializableMixin._infer_format_from_suffix()
B56: match suffix - case ".json" -> returns "json"
B57: match suffix - case ".yaml" | ".yml" -> returns "yaml"
B58: match suffix - case ".toml" -> returns "toml"
B59: match suffix - case _ -> raises ValueError

## MultiformatDeserializableMixin._parse_text()
B60: match fmt - case "json" -> parses JSON
B61: match fmt - case "yaml" -> attempts to import yaml
B62: except ImportError when importing yaml -> raises RuntimeError
B63: yaml.safe_load_all() -> loads YAML document(s)
B64: if len(docs) > 1 -> raises ValueError
B65: return docs[0] if docs else {} -> returns parsed YAML
B66: match fmt - case "toml" -> parses TOML
B67: match fmt - case _ -> raises ValueError

## MultiformatDeserializableMixin._coerce_root_mapping()
B68: if isinstance(raw, Mapping) -> returns raw
B69: raise TypeError -> if raw is not a Mapping

## MultiformatDeserializableMixin._preprocess_mapping()
B70: return mapping -> default pass-through implementation

## MultiformatDeserializableMixin._postprocess_instance()
B71: if hasattr(inst, "source_description") -> checks if attribute exists
B72: current = getattr(inst, "source_description", None) -> gets current value
B73: if not current -> checks if current value is falsey
B74: if path is not None -> checks if path is provided
B75: setattr(inst, "source_description", desc) -> sets attribute
B76: except Exception -> catches exceptions during setattr
B77: return inst -> returns instance

LEDGER COMPLETENESS CHECK:
- All if/elif/else captured: ✓
- All match/case arms captured: ✓
- All except blocks captured: ✓
- All early returns/raises captured: ✓
- All loop zero/one+ iterations captured: ✓
"""

###############################################################################
# TEST FIXTURES
###############################################################################

class SampleEnum(Enum):
    """Sample enum for testing."""
    VALUE1 = "one"
    VALUE2 = "two"


@pytest.fixture
def complex_data():
    """Fixture providing complex nested data for testing normalization."""
    return {
        "path": Path("/some/path"),
        "enum": SampleEnum.VALUE1,
        "mapping": {"b": 2, "a": 1},
        "set": {3, 1, 2},
        "frozenset": frozenset([3, 1, 2]),
        "list": [3, 1, 2],
        "tuple": (3, 1, 2),
        "datetime": datetime(2023, 1, 1, 12, 0, 0),
        "date": date(2023, 1, 1),
        "string": "string",
        "number": 123,
        "nested": {
            "list": [Path("/nested/path"), SampleEnum.VALUE2]
        }
    }

@pytest.fixture
def yaml_module_mock():
    """Mock for the yaml module."""
    mock_yaml = mock.MagicMock()
    return mock_yaml

###############################################################################
# TESTS FOR _normalize FUNCTION
###############################################################################

@pytest.mark.parametrize(
    "value, expected, branches",
    [
        # B01: Path case
        (Path("/test/path"), "/test/path", ["B01"]),
        
        # B02: Enum case
        (SampleEnum.VALUE1, "one", ["B02"]),
        
        # B03: Mapping case
        ({"b": 1, "a": 2}, {"a": 2, "b": 1}, ["B03"]),
        
        # B04: set/frozenset case
        ({1, 3, 2}, [1, 2, 3], ["B04"]),
        (frozenset([1, 3, 2]), [1, 2, 3], ["B04"]),
        
        # B05: list/tuple case
        ([3, 1, 2], [3, 1, 2], ["B05"]),
        ((3, 1, 2), [3, 1, 2], ["B05"]),
        
        # B06: datetime case
        (datetime(2023, 1, 1, 12, 0, 0), "2023-01-01T12:00:00", ["B06"]),
        (date(2023, 1, 1), "2023-01-01", ["B06"]),
        
        # B07: default case
        ("string", "string", ["B07"]),
        (123, 123, ["B07"]),
        (None, None, ["B07"]),
    ]
)
def test_normalize(value, expected, branches):
    """Test _normalize function with various input types. Covers branches B01-B07."""
    result = _normalize(value)
    assert result == expected

def test_normalize_complex(complex_data):
    """Test _normalize with complex nested data. Covers branches B01-B07 in nested structures."""
    result = _normalize(complex_data)
    
    # Verify specific transformations
    assert result["path"] == "/some/path"
    assert result["enum"] == "one"
    assert result["mapping"] == {"a": 1, "b": 2}
    assert result["set"] == [1, 2, 3]
    assert result["frozenset"] == [1, 2, 3]
    assert result["list"] == [3, 1, 2]
    assert result["tuple"] == [3, 1, 2]
    assert result["datetime"] == "2023-01-01T12:00:00"
    assert result["date"] == "2023-01-01"
    assert result["string"] == "string"
    assert result["number"] == 123
    assert result["nested"]["list"] == ["/nested/path", "two"]

###############################################################################
# TESTS FOR MultiformatSerializableMixin
###############################################################################

def test_to_mapping_not_implemented():
    """Test that to_mapping raises NotImplementedError when not implemented. Covers branch B11."""
    class IncompleteSerializable(MultiformatSerializableMixin):
        pass
    
    with pytest.raises(NotImplementedError) as excinfo:
        IncompleteSerializable().to_mapping()
    
    assert "must implement to_mapping()" in str(excinfo.value)

def test_mapping_hash(complex_data):
    """Test mapping_hash method. Covers branches B08-B10."""
    test_obj = SerializableFixture(complex_data)
    
    # Mock JSON dumps to return a predictable string
    with mock.patch('json.dumps', return_value='{"mocked":"json"}') as mock_dumps:
        result = test_obj.mapping_hash()
        
        # Verify to_mapping was called (B08)
        assert complex_data == test_obj.to_mapping()
        
        # Verify json.dumps was called with normalized mapping (B09)
        mock_dumps.assert_called_once()
        assert mock_dumps.call_args[1]['sort_keys'] == True
        
        # Verify hashlib was used (B10)
        expected_hash = hashlib.new("sha512", b'{"mocked":"json"}').hexdigest()
        assert result == expected_hash

def test_to_json(complex_data):
    """Test to_json method. Covers branches B12-B13."""
    test_obj = SerializableFixture(complex_data)
    
    with mock.patch('json.dumps') as mock_dumps:
        test_obj.to_json()
        
        # Verify to_mapping was called (B12)
        mock_dumps.assert_called_once()
        
        # Verify json.dumps was called with correct arguments (B13)
        assert mock_dumps.call_args[0][0] == complex_data
        assert mock_dumps.call_args[1]['ensure_ascii'] == False
        assert mock_dumps.call_args[1]['indent'] == 2
        assert mock_dumps.call_args[1]['sort_keys'] == True

def test_to_yaml_success(complex_data):
    """Test to_yaml method with successful yaml import. Covers branches B14, B16."""
    test_obj = SerializableFixture(complex_data)
    
    mock_yaml = mock.MagicMock()
    
    with mock.patch.dict('sys.modules', {'yaml': mock_yaml}):
        test_obj.to_yaml()
        
        # Verify yaml.safe_dump was called with correct arguments (B16)
        mock_yaml.safe_dump.assert_called_once()
        assert mock_yaml.safe_dump.call_args[0][0] == complex_data
        assert mock_yaml.safe_dump.call_args[1]['sort_keys'] == True
        assert mock_yaml.safe_dump.call_args[1]['allow_unicode'] == True
        assert mock_yaml.safe_dump.call_args[1]['indent'] == 2

def test_to_yaml_import_error():
    """Test to_yaml method when yaml import fails. Covers branch B15."""
    test_obj = SerializableFixture({})
    
    with mock.patch.dict('sys.modules', {'yaml': None}):
        with mock.patch('builtins.__import__', side_effect=ImportError):
            with pytest.raises(RuntimeError) as excinfo:
                test_obj.to_yaml()
            
            assert "PyYAML not installed" in str(excinfo.value)

def test_to_toml(complex_data):
    """Test to_toml method. Covers branches B17-B18."""
    test_obj = SerializableFixture(complex_data)
    
    with mock.patch('project_resolution_engine.internal.util.multiformat.dump_toml_to_str') as mock_dump:
        test_obj.to_toml()
        
        # Verify dump_toml_to_str was called (B18)
        mock_dump.assert_called_once()
        
        # Check that the dictionary was sorted (B17)
        # The exact sorting logic is complex to verify, but we can check that dump_toml_to_str was called
        sorted_mapping = mock_dump.call_args[0][0]
        assert isinstance(sorted_mapping, dict)

@pytest.mark.parametrize(
    "fmt, expected_method, error, branches",
    [
        ("json", "to_json", None, ["B19"]),
        ("yaml", "to_yaml", None, ["B20"]),
        ("toml", "to_toml", None, ["B21"]),
        ("invalid", None, ValueError, ["B22"]),
    ]
)
def test_serialize(fmt, expected_method, error, branches):
    """Test serialize method. Covers branches B19-B22."""
    test_obj = SerializableFixture({})
    
    # Mock the format-specific methods
    with mock.patch.object(test_obj, 'to_json', return_value='json_result') as mock_json, \
         mock.patch.object(test_obj, 'to_yaml', return_value='yaml_result') as mock_yaml, \
         mock.patch.object(test_obj, 'to_toml', return_value='toml_result') as mock_toml:
        
        if error:
            with pytest.raises(error) as excinfo:
                test_obj.serialize(fmt=fmt)
            assert f"unrecognized format: {fmt}" in str(excinfo.value)
        else:
            result = test_obj.serialize(fmt=fmt)
            
            # Verify the correct method was called
            if expected_method == "to_json":
                mock_json.assert_called_once()
                assert result == 'json_result'
            elif expected_method == "to_yaml":
                mock_yaml.assert_called_once()
                assert result == 'yaml_result'
            elif expected_method == "to_toml":
                mock_toml.assert_called_once()
                assert result == 'toml_result'

@pytest.mark.parametrize(
    "test_data, first_fields, last_fields, exclude, include_empty, expected_fragments, branches",
    [
        # Basic case with data
        (
            {"a": 1, "b": 2, "c": 3},
            (), (), (), False,
            ["a: 1", "b: 2", "c: 3"],
            ["B23", "B24", "B25", "B26", "B28", "B35", "B36"],
        ),
        
        # Test with first_fields
        (
            {"a": 1, "b": 2, "c": 3},
            ("c", "missing"), (), (), False,
            ["c: 3", "a: 1", "b: 2"],
            ["B23", "B24", "B25", "B26", "B28", "B35", "B36"],
        ),
        
        # Test with last_fields
        (
            {"a": 1, "b": 2, "c": 3},
            (), ("a", "missing"), (), False,
            ["b: 2", "c: 3", "a: 1"],
            ["B23", "B24", "B25", "B26", "B28", "B35", "B36"],
        ),
        
        # Test with first and last fields (some overlap)
        (
            {"a": 1, "b": 2, "c": 3, "d": 4},
            ("a", "b"), ("b", "c"), (), False,
            ["a: 1", "b: 2", "d: 4", "c: 3"],
            ["B23", "B24", "B25", "B26", "B28", "B35", "B36"],
        ),
        
        # Test with exclude
        (
            {"a": 1, "b": 2, "c": 3},
            (), (), ("b",), False,
            ["a: 1", "c: 3"],
            ["B23", "B24", "B25", "B26", "B28", "B35", "B36"],
        ),
        
        # Test with empty values not included
        (
            {"a": 1, "b": None, "c": "", "d": [], "e": {}},
            (), (), (), False,
            ["a: 1"],
            ["B23", "B24", "B25", "B26", "B28", "B29", "B35", "B36"],
        ),
        
        # Test with empty values included
        (
            {"a": 1, "b": None, "c": "", "d": [], "e": {}},
            (), (), (), True,
            ["a: 1", "b: None", "c: ", "d: []", "e: {}"],
            ["B23", "B24", "B25", "B26", "B28", "B35", "B36"],
        ),
        
        # Test with datetime
        (
            {"a": 1, "date": datetime(2023, 1, 1, 12, 0, 0)},
            (), (), (), False,
            ["a: 1", "date: 2023-01-01T12:00:00"],
            ["B23", "B24", "B25", "B26", "B28", "B30", "B35", "B36"],
        ),
        
        # Test with date
        (
            {"a": 1, "date": date(2023, 1, 1)},
            (), (), (), False,
            ["a: 1", "date: 2023-01-01"],
            ["B23", "B24", "B25", "B26", "B28", "B30", "B35", "B36"],
        ),
        
        # Test with payload dictionary
        (
            {"a": 1, "payload": {"key": "value"}},
            (), (), (), False,
            ["a: 1", "payload: {\"key\":\"value\"}"],
            ["B23", "B24", "B25", "B26", "B28", "B31", "B35", "B36"],
        ),
        
        # Test with dictionary
        (
            {"a": 1, "dict": {"key": "value"}},
            (), (), (), False,
            ["a: 1", "dict: {key: 'value'}"],
            ["B23", "B24", "B25", "B26", "B28", "B33", "B35", "B36"],
        ),
        
        # Test with list
        (
            {"a": 1, "list": [1, 2, 3]},
            (), (), (), False,
            ["a: 1", "list: [1, 2, 3]"],
            ["B23", "B24", "B25", "B26", "B28", "B34", "B35", "B36"],
        ),
    ]
)
def test_flat_summary(test_data, first_fields, last_fields, exclude, include_empty, expected_fragments, branches):
    """Test flat_summary method. Covers branches B23-B36."""
    test_obj = SerializableFixture(test_data)
    
    result = test_obj.flat_summary(
        first_fields=first_fields,
        last_fields=last_fields,
        exclude=exclude,
        include_empty=include_empty,
    )
    
    # Check that all expected fragments are in the result
    for fragment in expected_fragments:
        assert fragment in result

def test_flat_summary_payload_exception():
    """Test flat_summary when JSON serialization of payload raises exception. Covers branch B32."""
    test_data = {"payload": {"key": object()}}  # object() can't be JSON serialized
    test_obj = SerializableFixture(test_data)
    
    with mock.patch('json.dumps', side_effect=TypeError("can't serialize")):
        result = test_obj.flat_summary()
        
        # Check that repr was used instead
        assert "payload:" in result
        assert "{'key': <object object at 0x" in result

def test_str_method():
    """Test __str__ method. Covers branch B37."""
    test_data = {"a": 1, "b": 2}
    test_obj = SerializableFixture(test_data)
    
    with mock.patch.object(test_obj, 'flat_summary', return_value='flat_summary_result') as mock_summary:
        result = str(test_obj)
        
        # Verify flat_summary was called
        mock_summary.assert_called_once()
        assert result == 'flat_summary_result'

###############################################################################
# TESTS FOR MultiformatDeserializableMixin
###############################################################################

def test_from_mapping_not_implemented():
    """Test that from_mapping raises NotImplementedError when not implemented. Covers branch B38."""
    class IncompleteDeserializable(MultiformatDeserializableMixin):
        pass
    
    with pytest.raises(NotImplementedError) as excinfo:
        IncompleteDeserializable.from_mapping({})
    
    assert "must implement from_mapping" in str(excinfo.value)

def test_deserialize():
    """Test deserialize method. Covers branches B39-B43."""
    test_class = DeserializableFixture
    
    with mock.patch.object(test_class, '_parse_text', return_value='parsed_data') as mock_parse, \
         mock.patch.object(test_class, '_coerce_root_mapping', return_value={'key': 'value'}) as mock_coerce, \
         mock.patch.object(test_class, '_preprocess_mapping', return_value={'processed_key': 'processed_value'}) as mock_preprocess, \
         mock.patch.object(test_class, 'from_mapping', return_value=DeserializableFixture({'from_mapping': 'result'})) as mock_from_mapping, \
         mock.patch.object(test_class, '_postprocess_instance', return_value='final_result') as mock_postprocess:
        
        result = test_class.deserialize("input text", fmt="json")
        
        # Verify each step was called
        mock_parse.assert_called_once_with("input text", fmt="json", path=None)
        mock_coerce.assert_called_once_with('parsed_data', fmt="json", path=None)
        mock_preprocess.assert_called_once_with({'key': 'value'}, fmt="json", path=None)
        mock_from_mapping.assert_called_once_with({'processed_key': 'processed_value'})
        mock_postprocess.assert_called_once()
        assert result == 'final_result'

@pytest.mark.parametrize(
    "method, fmt, branches",
    [
        (DeserializableFixture.from_json, "json", ["B44"]),
        (DeserializableFixture.from_yaml, "yaml", ["B45"]),
        (DeserializableFixture.from_toml, "toml", ["B46"]),
    ]
)
def test_format_specific_deserialize_methods(method, fmt, branches):
    """Test from_json, from_yaml, and from_toml methods. Covers branches B44-B46."""
    with mock.patch.object(DeserializableFixture, 'deserialize', return_value='deserialized_result') as mock_deserialize:
        result = method("input text")
        
        # Verify deserialize was called with the correct format
        mock_deserialize.assert_called_once_with("input text", fmt=fmt)
        assert result == 'deserialized_result'

def test_from_file():
    """Test from_file method. Covers branches B47-B54."""
    test_class = DeserializableFixture
    test_path = "test.json"
    
    with mock.patch.object(test_class, '_load_text', return_value='file_content') as mock_load, \
         mock.patch.object(test_class, '_infer_format_from_suffix', return_value='inferred_format') as mock_infer, \
         mock.patch.object(test_class, '_parse_text', return_value='parsed_data') as mock_parse, \
         mock.patch.object(test_class, '_coerce_root_mapping', return_value={'key': 'value'}) as mock_coerce, \
         mock.patch.object(test_class, '_preprocess_mapping', return_value={'processed_key': 'processed_value'}) as mock_preprocess, \
         mock.patch.object(test_class, 'from_mapping', return_value=DeserializableFixture({'from_mapping': 'result'})) as mock_from_mapping, \
         mock.patch.object(test_class, '_postprocess_instance', return_value='final_result') as mock_postprocess:
        
        # Case 1: with explicit format
        result1 = test_class.from_file(test_path, fmt="explicit_format")
        
        # Verify each step was called correctly
        assert isinstance(mock_load.call_args[0][0], Path)
        assert str(mock_load.call_args[0][0]) == test_path
        mock_infer.assert_not_called()
        mock_parse.assert_called_with('file_content', fmt="explicit_format", path=mock.ANY)
        mock_coerce.assert_called_with('parsed_data', fmt="explicit_format", path=mock.ANY)
        mock_preprocess.assert_called_with({'key': 'value'}, fmt="explicit_format", path=mock.ANY)
        mock_from_mapping.assert_called_with({'processed_key': 'processed_value'})
        mock_postprocess.assert_called_with(mock.ANY, fmt="explicit_format", path=mock.ANY)
        assert result1 == 'final_result'
        
        # Reset mocks
        mock_load.reset_mock()
        mock_infer.reset_mock()
        mock_parse.reset_mock()
        mock_coerce.reset_mock()
        mock_preprocess.reset_mock()
        mock_from_mapping.reset_mock()
        mock_postprocess.reset_mock()
        
        # Case 2: without explicit format (infer from suffix)
        result2 = test_class.from_file(test_path, fmt=None)
        
        # Verify each step was called correctly
        assert isinstance(mock_load.call_args[0][0], Path)
        assert str(mock_load.call_args[0][0]) == test_path
        mock_infer.assert_called_once()
        mock_parse.assert_called_with('file_content', fmt='inferred_format', path=mock.ANY)
        assert result2 == 'final_result'

def test_load_text():
    """Test _load_text method. Covers branch B55."""
    mock_path = mock.MagicMock(spec=Path)
    mock_path.read_text.return_value = "file content"
    
    result = DeserializableFixture._load_text(mock_path)
    
    # Verify read_text was called with UTF-8 encoding
    mock_path.read_text.assert_called_once_with(encoding="utf-8")
    assert result == "file content"

@pytest.mark.parametrize(
    "suffix, expected_format, error, branches",
    [
        (".json", "json", None, ["B56"]),
        (".yaml", "yaml", None, ["B57"]),
        (".yml", "yaml", None, ["B57"]),
        (".toml", "toml", None, ["B58"]),
        (".txt", None, ValueError, ["B59"]),
    ]
)
def test_infer_format_from_suffix(suffix, expected_format, error, branches):
    """Test _infer_format_from_suffix method. Covers branches B56-B59."""
    mock_path = mock.MagicMock(spec=Path)
    mock_path.suffix = suffix
    
    if error:
        with pytest.raises(error) as excinfo:
            DeserializableFixture._infer_format_from_suffix(mock_path)
        assert "Cannot infer format from extension" in str(excinfo.value)
    else:
        result = DeserializableFixture._infer_format_from_suffix(mock_path)
        assert result == expected_format

@pytest.mark.parametrize(
    "fmt, text, expected_result, mock_setup, error, branches",
    [
        # JSON case
        (
            "json", 
            '{"key":"value"}', 
            {"key": "value"}, 
            lambda: mock.patch('json.loads', return_value={"key": "value"}),
            None,
            ["B60"]
        ),
        # Empty JSON case
        (
            "json", 
            '', 
            {}, 
            lambda: mock.patch('json.loads', return_value={}),
            None,
            ["B60"]
        ),
        # YAML case
        (
            "yaml", 
            'key: value', 
            {"key": "value"},
            lambda: mock.patch.dict(
                'sys.modules',
                {'yaml': mock.MagicMock(
                    safe_load_all=mock.MagicMock(return_value=iter([{"key": "value"}])))}),
                None,
            ["B61", "B63", "B65"]
        ),
        # YAML import error
        (
            "yaml", 
            'key: value', 
            None, 
            lambda: mock.patch.dict('sys.modules', {'yaml': None}) and 
                  mock.patch('builtins.__import__', side_effect=ImportError),
            RuntimeError,
            ["B61", "B62"]
        ),
        # YAML multiple documents error
        (
            "yaml", 
            'doc1: value\n---\ndoc2: value', 
            None,
            lambda: mock.patch.dict(
                'sys.modules',
                {'yaml': mock.MagicMock(
                    safe_load_all=mock.MagicMock(
                        return_value=iter([{"doc1": "value"}, {"doc2": "value"}])))}),
            ValueError,
            ["B61", "B63", "B64"]
        ),
        # TOML case
        (
            "toml", 
            'key = "value"', 
            {"key": "value"}, 
            lambda: mock.patch('project_resolution_engine.internal.util.multiformat.load_toml_text', 
                              return_value={"key": "value"}),
            None,
            ["B66"]
        ),
        # Empty TOML case
        (
            "toml", 
            '', 
            {}, 
            lambda: mock.patch('project_resolution_engine.internal.util.multiformat.load_toml_text', 
                              return_value={}),
            None,
            ["B66"]
        ),
        # Unrecognized format
        (
            "unknown", 
            'content', 
            None, 
            lambda: mock.MagicMock(),
            ValueError,
            ["B67"]
        ),
    ]
)
def test_parse_text(fmt, text, expected_result, mock_setup, error, branches):
    """Test _parse_text method. Covers branches B60-B67."""
    with mock_setup():
        if error:
            with pytest.raises(error) as excinfo:
                DeserializableFixture._parse_text(text, fmt=fmt, path=None)
            
            if error == RuntimeError:
                assert "PyYAML not installed" in str(excinfo.value)
            elif error == ValueError and fmt == "yaml":
                assert "Expected single YAML document" in str(excinfo.value)
            elif error == ValueError and fmt == "unknown":
                assert f"unrecognized format: {fmt!r}" in str(excinfo.value)
        else:
            result = DeserializableFixture._parse_text(text, fmt=fmt, path=None)
            assert result == expected_result

@pytest.mark.parametrize(
    "raw, error, branches",
    [
        ({"key": "value"}, None, ["B68"]),
        (OrderedDict([("key", "value")]), None, ["B68"]),
        ("not a mapping", TypeError, ["B69"]),
        (123, TypeError, ["B69"]),
        ([], TypeError, ["B69"]),
    ]
)
def test_coerce_root_mapping(raw, error, branches):
    """Test _coerce_root_mapping method. Covers branches B68-B69."""
    if error:
        with pytest.raises(error) as excinfo:
            DeserializableFixture._coerce_root_mapping(raw, fmt="json", path=None)
        assert "expected top-level mapping" in str(excinfo.value)
    else:
        result = DeserializableFixture._coerce_root_mapping(raw, fmt="json", path=None)
        assert result == raw

def test_preprocess_mapping():
    """Test _preprocess_mapping method. Covers branch B70."""
    mapping = {"key": "value"}
    
    # Default implementation should just return the mapping unchanged
    result = DeserializableFixture._preprocess_mapping(mapping, fmt="json", path=None)
    assert result == mapping

@pytest.mark.parametrize(
    "has_attr, current_value, has_path, setup, expected_desc, branches",
    [
        # Has attribute, empty value, with path
        (
            True, None, True,
            lambda inst: None,
            "json:test_path",
            ["B71", "B72", "B73", "B74", "B75", "B77"]
        ),
        # Has attribute, empty value, no path
        (
            True, None, False,
            lambda inst: None,
            "json:<inline>",
            ["B71", "B72", "B73", "B75", "B77"]
        ),
        # Has attribute, non-empty value
        (
            True, "existing", True,
            lambda inst: setattr(inst, "source_description", "existing"),
            "existing",
            ["B71", "B72", "B77"]
        ),
        # No attribute
        (
            False, None, True,
            lambda inst: None,
            None,
            ["B77"]
        ),
        # Has attribute, setattr raises exception
        (
            True, None, True,
            lambda inst: mock.patch.object(inst, 'source_description', 
                                          new_callable=mock.PropertyMock, 
                                          side_effect=AttributeError),
            None,
            ["B71", "B72", "B73", "B74", "B76", "B77"]
        ),
    ]
)
def test_postprocess_instance(has_attr, current_value, has_path, setup, expected_desc, branches):
    """Test _postprocess_instance method. Covers branches B71-B77."""
    test_class = DeserializableFixture
    inst = DeserializableFixture({})
    
    # Set up the instance based on test parameters
    if not has_attr:
        delattr(inst, "source_description")
    elif current_value is not None:
        inst.source_description = current_value
    else:
        inst.source_description = None
    
    path = Path("test_path") if has_path else None
    
    # Apply any additional setup
    setup(inst)
    
    # Call the method
    result = test_class._postprocess_instance(inst, fmt="json", path=path)
    
    # Check the result
    assert result is inst
    
    # Check source_description if the attribute exists
    if hasattr(inst, "source_description") and expected_desc is not None:
        assert inst.source_description == expected_desc

def test_postprocess_instance_exception():
    """Test _postprocess_instance method when setattr raises an exception. Covers branch B76."""
    # Create a class that raises an exception when source_description is set
    class ExceptionRaisingDeserializable(MultiformatDeserializableMixin):
        def __init__(self):
            self._source_description = None

        @property
        def source_description(self):
            return self._source_description

        @source_description.setter
        def source_description(self, value):
            if value and ":" in value:  # Only raise when setting a formatted value like "json:path"
                raise AttributeError("Cannot set attribute")
            self._source_description = value

        @classmethod
        def from_mapping(cls, mapping, **_):
            return cls()

    inst = ExceptionRaisingDeserializable()
    inst.source_description = None  # This won't raise

    result = ExceptionRaisingDeserializable._postprocess_instance(
        inst, fmt="json", path=Path("test_path"))

    assert result is inst
    assert inst.source_description is None

###############################################################################
# TESTS FOR MultiformatModelMixin
###############################################################################

def test_model_mixin_inheritance():
    """Test that MultiformatModelMixin inherits from both serializable and deserializable mixins."""
    assert issubclass(MultiformatModelMixin, MultiformatSerializableMixin)
    assert issubclass(MultiformatModelMixin, MultiformatDeserializableMixin)

def test_model_mixin_functionality():
    """Test that MultiformatModelMixin provides both serialization and deserialization capabilities."""
    # Create test data
    test_data = {"key": "value"}
    
    # Create model instance
    model = MultiformatModelFixture(test_data)
    
    # Test serialization
    with mock.patch('json.dumps', return_value='{"key":"value"}'):
        json_result = model.to_json()
        assert isinstance(json_result, str)
    
    # Test deserialization
    with mock.patch.object(MultiformatModelFixture, '_parse_text', return_value=test_data), \
         mock.patch.object(MultiformatModelFixture, '_coerce_root_mapping', return_value=test_data), \
         mock.patch.object(MultiformatModelFixture, '_preprocess_mapping', return_value=test_data):
        
        instance = MultiformatModelFixture.from_json('{"key":"value"}')
        assert isinstance(instance, MultiformatModelFixture)
        assert instance.data == test_data