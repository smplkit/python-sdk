"""Tests for the shared _helpers module."""

from smplkit._helpers import key_to_display_name


def test_hyphenated_key():
    assert key_to_display_name("checkout-v2") == "Checkout V2"


def test_underscored_key():
    assert key_to_display_name("user_service") == "User Service"


def test_mixed_separators():
    assert key_to_display_name("my-app_config") == "My App Config"


def test_single_word():
    assert key_to_display_name("logging") == "Logging"


def test_already_title_case():
    assert key_to_display_name("Already-Good") == "Already Good"
