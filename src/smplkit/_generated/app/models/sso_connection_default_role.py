from typing import Literal

SSOConnectionDefaultRole = Literal["ADMIN", "MEMBER", "OWNER", "VIEWER"]

SSO_CONNECTION_DEFAULT_ROLE_VALUES: set[SSOConnectionDefaultRole] = {
    "ADMIN",
    "MEMBER",
    "OWNER",
    "VIEWER",
}


def check_sso_connection_default_role(value: str) -> SSOConnectionDefaultRole:
    if value in SSO_CONNECTION_DEFAULT_ROLE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SSO_CONNECTION_DEFAULT_ROLE_VALUES!r}")
