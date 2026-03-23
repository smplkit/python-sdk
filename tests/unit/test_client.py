"""Basic tests for SDK client initialization."""

from smplkit import SmplkitClient


def test_client_init_with_api_key():
    client = SmplkitClient(api_key="sk_api_test")
    assert client._api_key == "sk_api_test"


def test_client_init_with_sdk_key():
    client = SmplkitClient(sdk_key="sk_sdk_test")
    assert client._sdk_key == "sk_sdk_test"


def test_client_default_import():
    """Verify the public import path works."""
    from smplkit import SmplkitClient as Client

    assert Client is not None


def test_client_init_with_base_url():
    client = SmplkitClient(api_key="sk_api_test", base_url="https://api.example.com")
    assert client._base_url == "https://api.example.com"


def test_client_init_defaults():
    client = SmplkitClient()
    assert client._api_key is None
    assert client._sdk_key is None
    assert client._base_url is None
