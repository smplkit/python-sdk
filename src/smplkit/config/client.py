"""ConfigClient and AsyncConfigClient — management-plane operations for configs."""

from __future__ import annotations


import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from uuid import UUID

from smplkit._errors import (
    SmplConflictError,
    SmplConnectionError,
    SmplNotFoundError,
    SmplTimeoutError,
    SmplValidationError,
)
from smplkit._generated.config.api.configs import (
    create_config,
    delete_config,
    get_config,
    list_configs,
    update_config,
)
from smplkit._generated.config.models.config import Config as GenConfig
from smplkit._generated.config.models.config_environments_type_0 import (
    ConfigEnvironmentsType0,
)
from smplkit._generated.config.models.config_values_type_0 import ConfigValuesType0
from smplkit._generated.config.models.resource_config import ResourceConfig
from smplkit._generated.config.models.response_config import ResponseConfig
from smplkit.config.models import AsyncConfig, Config

if TYPE_CHECKING:
    from smplkit.client import AsyncSmplClient, SmplClient

logger = logging.getLogger("smplkit")


def _make_values(values: dict[str, Any] | None) -> ConfigValuesType0 | None:
    """Convert a plain dict to the generated ConfigValuesType0 model."""
    if values is None:
        return None
    obj = ConfigValuesType0()
    obj.additional_properties = dict(values)
    return obj


def _make_environments(
    environments: dict[str, Any] | None,
) -> ConfigEnvironmentsType0 | None:
    """Convert a plain dict to the generated ConfigEnvironmentsType0 model."""
    if environments is None:
        return None
    obj = ConfigEnvironmentsType0()
    obj.additional_properties = dict(environments)
    return obj


def _extract_values(values: Any) -> dict[str, Any]:
    """Extract a plain dict from a generated values object."""
    if values is None or isinstance(values, type(None)):
        return {}
    if isinstance(values, ConfigValuesType0):
        return dict(values.additional_properties)
    if isinstance(values, dict):
        return dict(values)
    return {}


def _extract_environments(environments: Any) -> dict[str, Any]:
    """Extract a plain dict from a generated environments object."""
    if environments is None or isinstance(environments, type(None)):
        return {}
    if isinstance(environments, ConfigEnvironmentsType0):
        return dict(environments.additional_properties)
    if isinstance(environments, dict):
        return dict(environments)
    return {}


def _extract_datetime(value: Any) -> Any:
    """Pass through datetime objects, return None for Unset/None."""
    if value is None:
        return None
    # Check for Unset sentinel
    type_name = type(value).__name__
    if type_name == "Unset":
        return None
    return value


def _unset_to_none(value: Any) -> Any:
    """Convert Unset sentinels to None."""
    type_name = type(value).__name__
    if type_name == "Unset":
        return None
    return value


def _check_response_status(status_code: HTTPStatus, content: bytes) -> None:
    """Map HTTP error status codes to SDK exceptions.

    Args:
        status_code: The HTTP status code from the response.
        content: The raw response body for error messages.

    Raises:
        SmplNotFoundError: On 404.
        SmplConflictError: On 409.
        SmplValidationError: On 422.
    """
    code = int(status_code)
    if code == 404:
        raise SmplNotFoundError(content.decode("utf-8", errors="replace"))
    if code == 409:
        raise SmplConflictError(content.decode("utf-8", errors="replace"))
    if code == 422:
        raise SmplValidationError(content.decode("utf-8", errors="replace"))


def _build_request_body(
    *,
    name: str,
    key: str | None = None,
    description: str | None = None,
    parent: str | None = None,
    values: dict[str, Any] | None = None,
    environments: dict[str, Any] | None = None,
) -> ResponseConfig:
    """Build a JSON:API request body for create/update operations."""
    attrs = GenConfig(
        name=name,
        key=key,
        description=description,
        parent=parent,
        values=_make_values(values),
        environments=_make_environments(environments),
    )
    resource = ResourceConfig(attributes=attrs, type_="config")
    return ResponseConfig(data=resource)


class ConfigClient:
    """Synchronous management-plane client for Smpl Config.

    Provides CRUD operations on config resources.  Obtained via
    ``SmplClient(...).config``.

    All methods communicate with the server synchronously and raise
    structured exceptions on failure.

    Raises:
        SmplConnectionError: If a network request fails.
        SmplTimeoutError: If an operation exceeds its timeout.
    """

    def __init__(self, parent: SmplClient) -> None:
        self._parent = parent

    def get(self, *, key: str | None = None, id: str | None = None) -> Config:
        """Fetch a single config by key or UUID.

        Exactly one of *key* or *id* must be provided.

        Args:
            key: The human-readable config key (e.g. ``"user_service"``).
            id: The config UUID.

        Returns:
            The matching :class:`Config`.

        Raises:
            ValueError: If neither or both of *key* and *id* are provided.
            SmplNotFoundError: If no matching config exists.
        """
        if (key is None) == (id is None):
            raise ValueError("Exactly one of 'key' or 'id' must be provided.")

        try:
            if id is not None:
                return self._get_by_id(id)
            return self._get_by_key(key)  # type: ignore[arg-type]
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise

    def _get_by_id(self, config_id: str) -> Config:
        """Fetch a config by UUID."""
        response = get_config.sync_detailed(
            UUID(config_id),
            client=self._parent._http_client,
        )
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Config {config_id} not found")
        return self._to_model(response.parsed)

    def _get_by_key(self, key: str) -> Config:
        """Fetch a config by key using the list endpoint with a filter."""
        response = list_configs.sync_detailed(
            client=self._parent._http_client,
            filterkey=key,
        )
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            raise SmplNotFoundError(f"Config with key '{key}' not found")
        items = response.parsed.data
        if not items:
            raise SmplNotFoundError(f"Config with key '{key}' not found")
        return self._resource_to_model(items[0])

    def create(
        self,
        *,
        name: str,
        key: str | None = None,
        description: str | None = None,
        parent: str | None = None,
        values: dict[str, Any] | None = None,
    ) -> Config:
        """Create a new config.

        Args:
            name: Display name for the config.
            key: Human-readable key. Auto-generated if omitted.
            description: Optional description.
            parent: Parent config UUID. Defaults to the account's common
                config if omitted.
            values: Initial base values.

        Returns:
            The created :class:`Config`.

        Raises:
            SmplValidationError: If the server rejects the request.
        """
        body = _build_request_body(
            name=name,
            key=key,
            description=description,
            parent=parent,
            values=values,
        )
        try:
            response = create_config.sync_detailed(
                client=self._parent._http_client,
                body=body,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to create config")
        return self._to_model(response.parsed)

    def list(self) -> list[Config]:
        """List all configs for the account.

        Returns:
            A list of :class:`Config` objects.
        """
        try:
            response = list_configs.sync_detailed(
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._resource_to_model(r) for r in response.parsed.data]

    def delete(self, config_id: str) -> None:
        """Delete a config by UUID.

        Args:
            config_id: The UUID of the config to delete.

        Raises:
            SmplNotFoundError: If the config does not exist.
            SmplConflictError: If the config has children.
        """
        try:
            response = delete_config.sync_detailed(
                UUID(config_id),
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    def _update_config(
        self,
        *,
        config_id: str,
        name: str,
        key: str | None = None,
        description: str | None = None,
        parent: str | None = None,
        values: dict[str, Any] | None = None,
        environments: dict[str, Any] | None = None,
    ) -> Config:
        """Internal: PUT a full config update and return the updated model."""
        body = _build_request_body(
            name=name,
            key=key,
            description=description,
            parent=parent,
            values=values,
            environments=environments,
        )
        try:
            response = update_config.sync_detailed(
                UUID(config_id),
                client=self._parent._http_client,
                body=body,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to update config")
        return self._to_model(response.parsed)

    def _to_model(self, parsed: Any) -> Config:
        """Convert a ConfigResponse (single resource) to a Config model."""
        return self._resource_to_model(parsed.data)

    def _resource_to_model(self, resource: Any) -> Config:
        """Convert a ConfigResource to a Config model."""
        attrs = resource.attributes
        return Config(
            self,
            id=_unset_to_none(resource.id) or "",
            key=_unset_to_none(attrs.key) or "",
            name=attrs.name,
            description=_unset_to_none(attrs.description),
            parent=_unset_to_none(attrs.parent),
            values=_extract_values(attrs.values),
            environments=_extract_environments(attrs.environments),
            created_at=_extract_datetime(attrs.created_at),
            updated_at=_extract_datetime(attrs.updated_at),
        )


class AsyncConfigClient:
    """Asynchronous management-plane client for Smpl Config.

    Provides CRUD operations on config resources.  Obtained via
    ``AsyncSmplClient(...).config``.

    All methods communicate with the server asynchronously and raise
    structured exceptions on failure.

    Raises:
        SmplConnectionError: If a network request fails.
        SmplTimeoutError: If an operation exceeds its timeout.
    """

    def __init__(self, parent: AsyncSmplClient) -> None:
        self._parent = parent

    async def get(
        self, *, key: str | None = None, id: str | None = None
    ) -> AsyncConfig:
        """Fetch a single config by key or UUID.

        Exactly one of *key* or *id* must be provided.

        Args:
            key: The human-readable config key (e.g. ``"user_service"``).
            id: The config UUID.

        Returns:
            The matching :class:`AsyncConfig`.

        Raises:
            ValueError: If neither or both of *key* and *id* are provided.
            SmplNotFoundError: If no matching config exists.
        """
        if (key is None) == (id is None):
            raise ValueError("Exactly one of 'key' or 'id' must be provided.")

        try:
            if id is not None:
                return await self._get_by_id(id)
            return await self._get_by_key(key)  # type: ignore[arg-type]
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise

    async def _get_by_id(self, config_id: str) -> AsyncConfig:
        """Fetch a config by UUID."""
        response = await get_config.asyncio_detailed(
            UUID(config_id),
            client=self._parent._http_client,
        )
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplNotFoundError(f"Config {config_id} not found")
        return self._to_model(response.parsed)

    async def _get_by_key(self, key: str) -> AsyncConfig:
        """Fetch a config by key using the list endpoint with a filter."""
        response = await list_configs.asyncio_detailed(
            client=self._parent._http_client,
            filterkey=key,
        )
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            raise SmplNotFoundError(f"Config with key '{key}' not found")
        items = response.parsed.data
        if not items:
            raise SmplNotFoundError(f"Config with key '{key}' not found")
        return self._resource_to_model(items[0])

    async def create(
        self,
        *,
        name: str,
        key: str | None = None,
        description: str | None = None,
        parent: str | None = None,
        values: dict[str, Any] | None = None,
    ) -> AsyncConfig:
        """Create a new config.

        Args:
            name: Display name for the config.
            key: Human-readable key. Auto-generated if omitted.
            description: Optional description.
            parent: Parent config UUID. Defaults to the account's common
                config if omitted.
            values: Initial base values.

        Returns:
            The created :class:`AsyncConfig`.

        Raises:
            SmplValidationError: If the server rejects the request.
        """
        body = _build_request_body(
            name=name,
            key=key,
            description=description,
            parent=parent,
            values=values,
        )
        try:
            response = await create_config.asyncio_detailed(
                client=self._parent._http_client,
                body=body,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to create config")
        return self._to_model(response.parsed)

    async def list(self) -> list[AsyncConfig]:
        """List all configs for the account.

        Returns:
            A list of :class:`AsyncConfig` objects.
        """
        try:
            response = await list_configs.asyncio_detailed(
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None or not hasattr(response.parsed, "data"):
            return []
        return [self._resource_to_model(r) for r in response.parsed.data]

    async def delete(self, config_id: str) -> None:
        """Delete a config by UUID.

        Args:
            config_id: The UUID of the config to delete.

        Raises:
            SmplNotFoundError: If the config does not exist.
            SmplConflictError: If the config has children.
        """
        try:
            response = await delete_config.asyncio_detailed(
                UUID(config_id),
                client=self._parent._http_client,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)

    async def _update_config(
        self,
        *,
        config_id: str,
        name: str,
        key: str | None = None,
        description: str | None = None,
        parent: str | None = None,
        values: dict[str, Any] | None = None,
        environments: dict[str, Any] | None = None,
    ) -> AsyncConfig:
        """Internal: PUT a full config update and return the updated model."""
        body = _build_request_body(
            name=name,
            key=key,
            description=description,
            parent=parent,
            values=values,
            environments=environments,
        )
        try:
            response = await update_config.asyncio_detailed(
                UUID(config_id),
                client=self._parent._http_client,
                body=body,
            )
        except Exception as exc:
            _maybe_reraise_network_error(exc)
            raise
        _check_response_status(response.status_code, response.content)
        if response.parsed is None:
            raise SmplValidationError("Failed to update config")
        return self._to_model(response.parsed)

    def _to_model(self, parsed: Any) -> AsyncConfig:
        """Convert a ConfigResponse (single resource) to an AsyncConfig model."""
        return self._resource_to_model(parsed.data)

    def _resource_to_model(self, resource: Any) -> AsyncConfig:
        """Convert a ConfigResource to an AsyncConfig model."""
        attrs = resource.attributes
        return AsyncConfig(
            self,
            id=_unset_to_none(resource.id) or "",
            key=_unset_to_none(attrs.key) or "",
            name=attrs.name,
            description=_unset_to_none(attrs.description),
            parent=_unset_to_none(attrs.parent),
            values=_extract_values(attrs.values),
            environments=_extract_environments(attrs.environments),
            created_at=_extract_datetime(attrs.created_at),
            updated_at=_extract_datetime(attrs.updated_at),
        )


def _maybe_reraise_network_error(exc: Exception) -> None:
    """Re-raise httpx exceptions as SDK exceptions if applicable."""
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        raise SmplTimeoutError(str(exc)) from exc
    if isinstance(exc, httpx.HTTPError):
        raise SmplConnectionError(str(exc)) from exc
    if isinstance(exc, (SmplNotFoundError, SmplConflictError, SmplValidationError)):
        raise exc
