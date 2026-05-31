from typing import Literal

SSOConnectionProtocol = Literal["oidc", "saml"]

SSO_CONNECTION_PROTOCOL_VALUES: set[SSOConnectionProtocol] = {
    "oidc",
    "saml",
}


def check_sso_connection_protocol(value: str) -> SSOConnectionProtocol:
    if value in SSO_CONNECTION_PROTOCOL_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SSO_CONNECTION_PROTOCOL_VALUES!r}")
