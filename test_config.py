"""Tests for the TOML config loader (config/env.toml)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402


def _write(tmp_path, text):
    p = tmp_path / "env.toml"
    p.write_text(text)
    return str(p)


def test_load_config_missing_returns_empty(tmp_path):
    assert config.load_config(str(tmp_path / "absent.toml")) == {}


def test_config_scopes_reads_list(tmp_path):
    path = _write(tmp_path, '[google]\nscopes = ["https://a", "https://b"]\n')
    assert config.config_scopes(path) == ["https://a", "https://b"]


def test_config_scopes_empty_when_absent(tmp_path):
    path = _write(tmp_path, "[google]\n")
    assert config.config_scopes(path) == []


def test_config_secret_file(tmp_path):
    path = _write(tmp_path, '[google]\nsecret_file = "client_secret.json"\n')
    assert config.config_secret_file(path) == "client_secret.json"


def test_config_secret_file_none_when_absent(tmp_path):
    path = _write(tmp_path, "[google]\n")
    assert config.config_secret_file(path) is None


def test_config_token_file(tmp_path):
    path = _write(tmp_path, '[google]\ntoken_file = "token.json"\n')
    assert config.config_token_file(path) == "token.json"


def test_config_token_file_none_when_absent(tmp_path):
    path = _write(tmp_path, "[google]\n")
    assert config.config_token_file(path) is None


def test_bundled_default_toml_is_complete():
    # The shipped config/default.toml carries the canonical defaults.
    assert len(config.config_scopes()) > 0
    assert config.config_secret_file() == "client_secret.json"
    assert config.config_token_file() == "token.json"
