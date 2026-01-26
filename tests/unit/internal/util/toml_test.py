import builtins
import io

import pytest
import tomli
import tomli_w

import project_resolution_engine.internal.util.toml as toml_mod

# --------------------------------------------------------------------------
# C000F001: load_toml_file
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content, expected",
    [
        (b"a = 1\n", {"a": 1}),  # C000F001B0001
    ],
)
def test_load_toml_file_success(tmp_path, content, expected):
    file_path = tmp_path / "test.toml"
    file_path.write_bytes(content)
    result = toml_mod.load_toml_file(file_path)
    assert result == expected


@pytest.mark.parametrize(
    "exception_type",
    [
        FileNotFoundError,  # C000F001B0002
        PermissionError,  # C000F001B0003
    ],
)
def test_load_toml_file_open_exceptions(monkeypatch, exception_type):
    def fake_open(path, mode="rb"):
        raise exception_type("mocked")

    monkeypatch.setattr(builtins, "open", fake_open)
    with pytest.raises(exception_type):
        toml_mod.load_toml_file("dummy.toml")


def test_load_toml_file_decode_error(monkeypatch):
    # C000F001B0004
    def fake_open(path, mode="rb"):
        return io.BytesIO(b"bad = ]")

    def fake_load(f):
        raise tomli.TOMLDecodeError("bad", "bad", 0)

    monkeypatch.setattr(tomli, "load", fake_load)
    monkeypatch.setattr(builtins, "open", fake_open)
    with pytest.raises(tomli.TOMLDecodeError):
        toml_mod.load_toml_file("bad.toml")


# --------------------------------------------------------------------------
# C000F002: load_toml_text
# --------------------------------------------------------------------------


def test_load_toml_text_success():
    # C000F002B0001
    text = "a = 1"
    result = toml_mod.load_toml_text(text)
    assert result == {"a": 1}


def test_load_toml_text_decode_error(monkeypatch):
    # C000F002B0002
    def fake_loads(text):
        raise tomli.TOMLDecodeError("bad", "bad", 0)

    monkeypatch.setattr(tomli, "loads", fake_loads)
    with pytest.raises(tomli.TOMLDecodeError):
        toml_mod.load_toml_text("bad text")


# --------------------------------------------------------------------------
# C000F003: dump_toml_to_str
# --------------------------------------------------------------------------


def test_dump_toml_to_str(monkeypatch):
    # C000F003B0001
    captured = {}

    def fake_dumps(data, indent=2):
        captured["data"] = data
        captured["indent"] = indent
        return "key = 1\n"

    monkeypatch.setattr(tomli_w, "dumps", fake_dumps)
    result = toml_mod.dump_toml_to_str({"key": 1}, indent=4)
    assert result == "key = 1\n"
    assert captured == {"data": {"key": 1}, "indent": 4}


# --------------------------------------------------------------------------
# C000F004: dump_toml_to_file
# --------------------------------------------------------------------------


def test_dump_toml_to_file(tmp_path, monkeypatch):
    # C000F004B0001
    content = "key = 1\n"
    monkeypatch.setattr(toml_mod, "dump_toml_to_str", lambda d: content)

    target_path = tmp_path / "out.toml"
    toml_mod.dump_toml_to_file({"key": 1}, target_path)

    written = target_path.read_text(encoding="utf-8")
    assert written == content
