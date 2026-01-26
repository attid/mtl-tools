# tests/other/stellar/test_address_utils.py
import pytest
from other.stellar.address_utils import (
    find_stellar_public_key,
    find_stellar_federation_address,
    shorten_address,
)


def test_find_stellar_public_key():
    text = "Send to GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V please"
    result = find_stellar_public_key(text)
    assert result == "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"


def test_find_stellar_public_key_not_found():
    text = "No key here"
    result = find_stellar_public_key(text)
    assert result is None


def test_find_stellar_public_key_in_middle():
    text = "prefix GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI suffix"
    result = find_stellar_public_key(text)
    assert result == "GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI"


def test_find_federation_address():
    text = "Send to user*stellar.org"
    result = find_stellar_federation_address(text)
    assert result == "user*stellar.org"


def test_find_federation_address_with_subdomain():
    text = "Address is test*lobstr.co"
    result = find_stellar_federation_address(text)
    assert result == "test*lobstr.co"


def test_find_federation_address_not_found():
    text = "No federation here"
    result = find_stellar_federation_address(text)
    assert result is None


def test_shorten_address():
    address = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"
    result = shorten_address(address)
    assert result == "GACK..UK7V"


def test_shorten_address_short_input():
    address = "SHORT"
    result = shorten_address(address)
    assert result == "SHORT"


def test_shorten_address_empty():
    result = shorten_address("")
    assert result == ""
