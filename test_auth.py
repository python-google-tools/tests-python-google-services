"""Tests for the closure-based auth providers.

Google network/file I/O is fully mocked — no live calls, no credentials needed.
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

# Make the library importable when tests run from inside the submodule.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth import auth  # noqa: E402


# --------------------------------------------------------------------------- #
# get_scopes
# --------------------------------------------------------------------------- #
def test_get_scopes_explicit_arg_wins():
    assert auth.get_scopes(["a", "b"]) == ["a", "b"]


def test_get_scopes_from_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_SCOPES", "https://x , https://y")
    assert auth.get_scopes() == ["https://x", "https://y"]


def test_get_scopes_falls_back_to_defaults(monkeypatch):
    monkeypatch.delenv("GOOGLE_SCOPES", raising=False)
    assert auth.get_scopes() == auth.DEFAULT_SCOPES


# --------------------------------------------------------------------------- #
# service_account_provider — returns a closure, defers all I/O
# --------------------------------------------------------------------------- #
def test_service_account_provider_returns_callable_without_io(tmp_path):
    # Building the provider must NOT touch the filesystem or validate anything.
    provider = auth.service_account_provider(key_file=str(tmp_path / "nope.json"))
    assert callable(provider)


def test_service_account_provider_raises_on_missing_file(tmp_path):
    provider = auth.service_account_provider(
        key_file=str(tmp_path / "missing.json"), scopes=["s"]
    )
    with pytest.raises(ValueError, match="key file"):
        provider()


def test_get_scopes_empty_list_falls_back_to_defaults():
    # An empty/falsy scopes arg is treated as "not provided" → defaults.
    assert auth.get_scopes([]) == auth.DEFAULT_SCOPES


def test_service_account_provider_builds_credentials(tmp_path):
    key = tmp_path / "key.json"
    key.write_text("{}")
    sentinel = object()
    fake_sa = mock.Mock()
    fake_sa.Credentials.from_service_account_file.return_value = sentinel
    with mock.patch.dict(
        "sys.modules", {"google.oauth2.service_account": fake_sa}
    ), mock.patch("google.oauth2.service_account", fake_sa, create=True):
        provider = auth.service_account_provider(key_file=str(key), scopes=["s"])
        creds = provider()
    assert creds is sentinel
    fake_sa.Credentials.from_service_account_file.assert_called_once_with(
        str(key), scopes=["s"]
    )


# --------------------------------------------------------------------------- #
# client_factory — closure caches the client
# --------------------------------------------------------------------------- #
def test_client_factory_lazy_and_cached():
    calls = {"provider": 0, "authorize": 0}

    def provider():
        calls["provider"] += 1
        return "CREDS"

    fake_gspread = mock.Mock()
    fake_gspread.authorize.side_effect = lambda c: calls.__setitem__(
        "authorize", calls["authorize"] + 1
    ) or mock.Mock()

    get_client = auth.client_factory(provider)
    # Nothing happens until the closure is called.
    assert calls["provider"] == 0

    with mock.patch.dict("sys.modules", {"gspread": fake_gspread}):
        c1 = get_client()
        c2 = get_client()

    assert c1 is c2  # cached
    assert calls["provider"] == 1  # provider only invoked once
    assert calls["authorize"] == 1  # client built once


def test_client_factory_verify_calls_connectivity_once():
    client = mock.Mock()
    fake_gspread = mock.Mock()
    fake_gspread.authorize.return_value = client

    with mock.patch.dict("sys.modules", {"gspread": fake_gspread}):
        get_client = auth.client_factory(lambda: "CREDS", verify=True)
        get_client()
        get_client()

    client.list_spreadsheet_files.assert_called_once()
