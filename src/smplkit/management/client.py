"""Smpl management-plane sub-clients.

Provides ``client.management.{environments, contexts, context_types,
account_settings}`` for app-service-owned resources.
"""

from __future__ import annotations

import datetime as _datetime
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, overload

from smplkit._errors import SmplNotFoundError, SmplValidationError, _raise_for_status
from smplkit._generated.app.api.context_types import (
    create_context_type as _gen_create_context_type,
    delete_context_type as _gen_delete_context_type,
    get_context_type as _gen_get_context_type,
    list_context_types as _gen_list_context_types,
    update_context_type as _gen_update_context_type,
)
from smplkit._generated.app.api.contexts import (
    bulk_register_contexts as _gen_bulk_register_contexts,
    delete_context as _gen_delete_context,
    get_context as _gen_get_context,
    list_contexts as _gen_list_contexts,
)
from smplkit._generated.app.api.environments import (
    create_environment as _gen_create_environment,
    delete_environment as _gen_delete_environment,
    get_environment as _gen_get_environment,
    list_environments as _gen_list_environments,
    update_environment as _gen_update_environment,
)
from smplkit._generated.app.api.metrics import (
    bulk_ingest_metrics as _gen_bulk_ingest_metrics,
)
from smplkit._generated.app.client import AuthenticatedClient as _AppAuthClient
from smplkit._generated.app.types import UNSET, Unset
from smplkit._generated.app.models import (
    ContextBulkItem as _GenContextBulkItem,
    ContextBulkItemAttributes as _GenContextBulkItemAttributes,
    ContextBulkRegister as _GenContextBulkRegister,
    ContextType as _GenContextType,
    ContextTypeAttributes as _GenContextTypeAttributes,
    ContextTypeResource as _GenContextTypeResource,
    ContextTypeResponse as _GenContextTypeResponse,
    Environment as _GenEnvironment,
    EnvironmentResource as _GenEnvironmentResource,
    EnvironmentResponse as _GenEnvironmentResponse,
    MetricAttributes as _GenMetricAttributes,
    MetricBulkRequest as _GenMetricBulkRequest,
    MetricResource as _GenMetricResource,
)
from smplkit._generated.app.models.metric_attributes_dimensions import (
    MetricAttributesDimensions as _GenMetricAttributesDimensions,
)
from smplkit.management.models import (
    AccountSettings,
    AsyncAccountSettings,
    AsyncContextEntity,
    AsyncContextType,
    AsyncEnvironment,
    ContextEntity,
    ContextType,
    Environment,
)
from smplkit.management.types import EnvironmentClassification

if TYPE_CHECKING:  # pragma: no cover
    from smplkit.client import AsyncSmplClient, SmplClient
    from smplkit.flags.types import Context
    from smplkit.management._buffer import _ContextRegistrationBuffer


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _split_context_id(id_or_type: str, key: str | None) -> tuple[str, str]:
    """Resolve the two-arg or composite-id form to ``(type, key)``."""
    if key is None:
        if ":" not in id_or_type:
            raise ValueError(
                f"context id must be 'type:key' (got {id_or_type!r}); alternatively pass type and key as separate args"
            )
        ctx_type, _, ctx_key = id_or_type.partition(":")
        return ctx_type, ctx_key
    return id_or_type, key


def _env_to_resource(env: Environment | AsyncEnvironment) -> _GenEnvironmentResponse:
    attrs = _GenEnvironment(
        name=env.name,
        color=env.color,
        classification=env.classification.value,
    )
    resource = _GenEnvironmentResource(
        type_="environment",
        attributes=attrs,
        id=env.id,
    )
    return _GenEnvironmentResponse(data=resource)


def _env_from_parsed(
    parsed: Any, sync_client: EnvironmentsClient | None, async_client: AsyncEnvironmentsClient | None
) -> Any:
    """Build an Environment / AsyncEnvironment from a parsed EnvironmentResponse."""
    data = parsed.data
    attrs = data.attributes
    classification_value = getattr(attrs, "classification", None) or "STANDARD"
    if classification_value == "AD_HOC":
        classification = EnvironmentClassification.AD_HOC
    else:
        classification = EnvironmentClassification.STANDARD
    if async_client is not None:
        return AsyncEnvironment(
            async_client,
            id=data.id,
            name=attrs.name,
            color=getattr(attrs, "color", None),
            classification=classification,
            created_at=getattr(attrs, "created_at", None) or None,
            updated_at=getattr(attrs, "updated_at", None) or None,
        )
    return Environment(
        sync_client,
        id=data.id,
        name=attrs.name,
        color=getattr(attrs, "color", None),
        classification=classification,
        created_at=getattr(attrs, "created_at", None) or None,
        updated_at=getattr(attrs, "updated_at", None) or None,
    )


def _ct_to_resource(ct: ContextType | AsyncContextType) -> _GenContextTypeResponse:
    attr_meta = _GenContextTypeAttributes()
    attr_meta.additional_properties = dict(ct.attributes)
    attrs = _GenContextType(name=ct.name, attributes=attr_meta)
    resource = _GenContextTypeResource(
        type_="context_type",
        attributes=attrs,
        id=ct.id,
    )
    return _GenContextTypeResponse(data=resource)


def _ct_from_parsed(
    parsed: Any, sync_client: ContextTypesClient | None, async_client: AsyncContextTypesClient | None
) -> Any:
    data = parsed.data
    attrs = data.attributes
    raw_attr_meta = getattr(attrs, "attributes", None)
    if raw_attr_meta is None or _is_unset(raw_attr_meta):
        attributes: dict[str, dict[str, Any]] = {}
    else:
        # Generated ContextTypeAttributes wraps a dict on additional_properties.
        attributes = dict(getattr(raw_attr_meta, "additional_properties", {}))
    if async_client is not None:
        return AsyncContextType(
            async_client,
            id=data.id,
            name=attrs.name,
            attributes=attributes,
            created_at=getattr(attrs, "created_at", None) or None,
            updated_at=getattr(attrs, "updated_at", None) or None,
        )
    return ContextType(
        sync_client,
        id=data.id,
        name=attrs.name,
        attributes=attributes,
        created_at=getattr(attrs, "created_at", None) or None,
        updated_at=getattr(attrs, "updated_at", None) or None,
    )


def _ctx_entity_from_parsed(parsed: Any, sync: bool) -> Any:
    """Build a ContextEntity / AsyncContextEntity from a parsed ContextResponse.

    The on-the-wire id is the composite ``"type:key"``. We split it
    back into the two fields the model exposes (mirrored back as a
    composite via the ``id`` property).
    """
    data = parsed.data
    composite_id = data.id or ""
    if ":" in composite_id:
        ctx_type, _, ctx_key = composite_id.partition(":")
    else:
        ctx_type, ctx_key = composite_id, ""

    attrs = data.attributes
    attr_obj = getattr(attrs, "attributes", None)
    if attr_obj is None or _is_unset(attr_obj):
        attr_dict: dict[str, Any] = {}
    elif isinstance(attr_obj, dict):
        attr_dict = dict(attr_obj)
    else:
        attr_dict = dict(getattr(attr_obj, "additional_properties", {}))

    if sync:
        return ContextEntity(
            type=ctx_type,
            key=ctx_key,
            name=getattr(attrs, "name", None) or None,
            attributes=attr_dict,
            created_at=getattr(attrs, "created_at", None) or None,
            updated_at=getattr(attrs, "updated_at", None) or None,
        )
    return AsyncContextEntity(
        type=ctx_type,
        key=ctx_key,
        name=getattr(attrs, "name", None) or None,
        attributes=attr_dict,
        created_at=getattr(attrs, "created_at", None) or None,
        updated_at=getattr(attrs, "updated_at", None) or None,
    )


def _is_unset(value: Any) -> bool:
    return type(value).__name__ == "Unset"


def _check_status(status_code: int, content: bytes) -> None:
    _raise_for_status(int(status_code), content)


# ---------------------------------------------------------------------------
# Environments
# ---------------------------------------------------------------------------


class EnvironmentsClient:
    """Sync environment CRUD."""

    def __init__(self, parent: SmplClient, app_http: _AppAuthClient) -> None:
        self._parent = parent
        self._app_http = app_http

    def new(
        self,
        id: str,
        *,
        name: str,
        color: str | None = None,
        classification: EnvironmentClassification = EnvironmentClassification.STANDARD,
    ) -> Environment:
        """Return an unsaved :class:`Environment`. Call ``.save()`` to persist."""
        return Environment(
            self,
            id=id,
            name=name,
            color=color,
            classification=classification,
        )

    def list(self) -> list[Environment]:
        resp = _gen_list_environments.sync_detailed(client=self._app_http)
        _check_status(int(resp.status_code), resp.content)
        body = json.loads(resp.content)
        return [_env_resource_from_dict(item, sync_client=self) for item in body.get("data", [])]

    def get(self, id: str) -> Environment:
        resp = _gen_get_environment.sync_detailed(id, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplNotFoundError(f"Environment with id {id!r} not found", status_code=404)
        return _env_from_parsed(resp.parsed, sync_client=self, async_client=None)

    def delete(self, id: str) -> None:
        resp = _gen_delete_environment.sync_detailed(id, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)

    def _create(self, env: Environment) -> Environment:
        body = _env_to_resource(env)
        resp = _gen_create_environment.sync_detailed(client=self._app_http, body=body)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplValidationError(
                f"HTTP {int(resp.status_code)}: unexpected response",
                status_code=int(resp.status_code),
            )
        return _env_from_parsed(resp.parsed, sync_client=self, async_client=None)

    def _update(self, env: Environment) -> Environment:
        body = _env_to_resource(env)
        if env.id is None:
            raise ValueError("cannot update an Environment with no id")
        resp = _gen_update_environment.sync_detailed(env.id, client=self._app_http, body=body)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplValidationError(
                f"HTTP {int(resp.status_code)}: unexpected response",
                status_code=int(resp.status_code),
            )
        return _env_from_parsed(resp.parsed, sync_client=self, async_client=None)


class AsyncEnvironmentsClient:
    """Async environment CRUD."""

    def __init__(self, parent: AsyncSmplClient, app_http: _AppAuthClient) -> None:
        self._parent = parent
        self._app_http = app_http

    def new(
        self,
        id: str,
        *,
        name: str,
        color: str | None = None,
        classification: EnvironmentClassification = EnvironmentClassification.STANDARD,
    ) -> AsyncEnvironment:
        return AsyncEnvironment(
            self,
            id=id,
            name=name,
            color=color,
            classification=classification,
        )

    async def list(self) -> list[AsyncEnvironment]:
        resp = await _gen_list_environments.asyncio_detailed(client=self._app_http)
        _check_status(int(resp.status_code), resp.content)
        body = json.loads(resp.content)
        return [_env_resource_from_dict(item, async_client=self) for item in body.get("data", [])]

    async def get(self, id: str) -> AsyncEnvironment:
        resp = await _gen_get_environment.asyncio_detailed(id, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplNotFoundError(f"Environment with id {id!r} not found", status_code=404)
        return _env_from_parsed(resp.parsed, sync_client=None, async_client=self)

    async def delete(self, id: str) -> None:
        resp = await _gen_delete_environment.asyncio_detailed(id, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)

    async def _create(self, env: AsyncEnvironment) -> AsyncEnvironment:
        body = _env_to_resource(env)
        resp = await _gen_create_environment.asyncio_detailed(client=self._app_http, body=body)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplValidationError(
                f"HTTP {int(resp.status_code)}: unexpected response",
                status_code=int(resp.status_code),
            )
        return _env_from_parsed(resp.parsed, sync_client=None, async_client=self)

    async def _update(self, env: AsyncEnvironment) -> AsyncEnvironment:
        body = _env_to_resource(env)
        if env.id is None:
            raise ValueError("cannot update an AsyncEnvironment with no id")
        resp = await _gen_update_environment.asyncio_detailed(env.id, client=self._app_http, body=body)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplValidationError(
                f"HTTP {int(resp.status_code)}: unexpected response",
                status_code=int(resp.status_code),
            )
        return _env_from_parsed(resp.parsed, sync_client=None, async_client=self)


def _env_resource_from_dict(
    item: dict[str, Any],
    *,
    sync_client: EnvironmentsClient | None = None,
    async_client: AsyncEnvironmentsClient | None = None,
) -> Any:
    """Build an Environment from a raw JSON resource dict.

    Used by list() — each entry is a ``{"id", "type", "attributes"}``
    dict, not a pre-parsed model.
    """
    attrs = item.get("attributes") or {}
    classification = (
        EnvironmentClassification.AD_HOC
        if attrs.get("classification") == "AD_HOC"
        else EnvironmentClassification.STANDARD
    )
    if async_client is not None:
        return AsyncEnvironment(
            async_client,
            id=item.get("id"),
            name=attrs.get("name", ""),
            color=attrs.get("color"),
            classification=classification,
            created_at=attrs.get("created_at"),
            updated_at=attrs.get("updated_at"),
        )
    return Environment(
        sync_client,
        id=item.get("id"),
        name=attrs.get("name", ""),
        color=attrs.get("color"),
        classification=classification,
        created_at=attrs.get("created_at"),
        updated_at=attrs.get("updated_at"),
    )


# ---------------------------------------------------------------------------
# Context Types
# ---------------------------------------------------------------------------


class ContextTypesClient:
    """Sync context-type CRUD."""

    def __init__(self, parent: SmplClient, app_http: _AppAuthClient) -> None:
        self._parent = parent
        self._app_http = app_http

    def new(
        self,
        id: str,
        *,
        name: str | None = None,
        attributes: dict[str, dict[str, Any]] | None = None,
    ) -> ContextType:
        return ContextType(
            self,
            id=id,
            name=name or id,
            attributes=attributes or {},
        )

    def list(self) -> list[ContextType]:
        resp = _gen_list_context_types.sync_detailed(client=self._app_http)
        _check_status(int(resp.status_code), resp.content)
        body = json.loads(resp.content)
        return [_ct_resource_from_dict(item, sync_client=self) for item in body.get("data", [])]

    def get(self, id: str) -> ContextType:
        resp = _gen_get_context_type.sync_detailed(id, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplNotFoundError(f"ContextType with id {id!r} not found", status_code=404)
        return _ct_from_parsed(resp.parsed, sync_client=self, async_client=None)

    def delete(self, id: str) -> None:
        resp = _gen_delete_context_type.sync_detailed(id, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)

    def _create(self, ct: ContextType) -> ContextType:
        body = _ct_to_resource(ct)
        resp = _gen_create_context_type.sync_detailed(client=self._app_http, body=body)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplValidationError(
                f"HTTP {int(resp.status_code)}: unexpected response",
                status_code=int(resp.status_code),
            )
        return _ct_from_parsed(resp.parsed, sync_client=self, async_client=None)

    def _update(self, ct: ContextType) -> ContextType:
        body = _ct_to_resource(ct)
        if ct.id is None:
            raise ValueError("cannot update a ContextType with no id")
        resp = _gen_update_context_type.sync_detailed(ct.id, client=self._app_http, body=body)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplValidationError(
                f"HTTP {int(resp.status_code)}: unexpected response",
                status_code=int(resp.status_code),
            )
        return _ct_from_parsed(resp.parsed, sync_client=self, async_client=None)


class AsyncContextTypesClient:
    def __init__(self, parent: AsyncSmplClient, app_http: _AppAuthClient) -> None:
        self._parent = parent
        self._app_http = app_http

    def new(
        self,
        id: str,
        *,
        name: str | None = None,
        attributes: dict[str, dict[str, Any]] | None = None,
    ) -> AsyncContextType:
        return AsyncContextType(
            self,
            id=id,
            name=name or id,
            attributes=attributes or {},
        )

    async def list(self) -> list[AsyncContextType]:
        resp = await _gen_list_context_types.asyncio_detailed(client=self._app_http)
        _check_status(int(resp.status_code), resp.content)
        body = json.loads(resp.content)
        return [_ct_resource_from_dict(item, async_client=self) for item in body.get("data", [])]

    async def get(self, id: str) -> AsyncContextType:
        resp = await _gen_get_context_type.asyncio_detailed(id, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplNotFoundError(f"ContextType with id {id!r} not found", status_code=404)
        return _ct_from_parsed(resp.parsed, sync_client=None, async_client=self)

    async def delete(self, id: str) -> None:
        resp = await _gen_delete_context_type.asyncio_detailed(id, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)

    async def _create(self, ct: AsyncContextType) -> AsyncContextType:
        body = _ct_to_resource(ct)
        resp = await _gen_create_context_type.asyncio_detailed(client=self._app_http, body=body)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplValidationError(
                f"HTTP {int(resp.status_code)}: unexpected response",
                status_code=int(resp.status_code),
            )
        return _ct_from_parsed(resp.parsed, sync_client=None, async_client=self)

    async def _update(self, ct: AsyncContextType) -> AsyncContextType:
        body = _ct_to_resource(ct)
        if ct.id is None:
            raise ValueError("cannot update an AsyncContextType with no id")
        resp = await _gen_update_context_type.asyncio_detailed(ct.id, client=self._app_http, body=body)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplValidationError(
                f"HTTP {int(resp.status_code)}: unexpected response",
                status_code=int(resp.status_code),
            )
        return _ct_from_parsed(resp.parsed, sync_client=None, async_client=self)


def _ct_resource_from_dict(
    item: dict[str, Any],
    *,
    sync_client: ContextTypesClient | None = None,
    async_client: AsyncContextTypesClient | None = None,
) -> Any:
    attrs = item.get("attributes") or {}
    raw_attr_meta = attrs.get("attributes")
    if isinstance(raw_attr_meta, dict):
        attribute_metadata: dict[str, dict[str, Any]] = {
            k: dict(v) if isinstance(v, dict) else {} for k, v in raw_attr_meta.items()
        }
    else:
        attribute_metadata = {}
    if async_client is not None:
        return AsyncContextType(
            async_client,
            id=item.get("id"),
            name=attrs.get("name", ""),
            attributes=attribute_metadata,
            created_at=attrs.get("created_at"),
            updated_at=attrs.get("updated_at"),
        )
    return ContextType(
        sync_client,
        id=item.get("id"),
        name=attrs.get("name", ""),
        attributes=attribute_metadata,
        created_at=attrs.get("created_at"),
        updated_at=attrs.get("updated_at"),
    )


# ---------------------------------------------------------------------------
# Contexts
# ---------------------------------------------------------------------------


def _build_bulk_register_body(items: list[dict[str, Any]]) -> _GenContextBulkRegister:
    bulk: list[_GenContextBulkItem] = []
    for item in items:
        attrs = _GenContextBulkItemAttributes()
        attrs.additional_properties = dict(item.get("attributes") or {})
        bulk.append(
            _GenContextBulkItem(
                type_=item["type"],
                key=item["key"],
                attributes=attrs,
            )
        )
    return _GenContextBulkRegister(contexts=bulk)


class ContextsClient:
    """Sync context registration + read/delete."""

    def __init__(
        self,
        parent: SmplClient,
        app_http: _AppAuthClient,
        buffer: _ContextRegistrationBuffer,
    ) -> None:
        self._parent = parent
        self._app_http = app_http
        self._buffer = buffer

    def register(self, items: Context | list[Context], *, flush: bool = False) -> None:
        """Buffer contexts for registration; optionally flush immediately.

        When ``flush=False`` (default) contexts are queued for the
        SDK's background flush — right for high-frequency observation
        from a live request handler. When ``flush=True`` the call
        awaits the round-trip — right for IaC scripts.
        """
        batch = items if isinstance(items, list) else [items]
        self._buffer.observe(batch)
        if flush:
            self.flush()

    def flush(self) -> None:
        """Send any pending observations to the server."""
        batch = self._buffer.drain()
        if not batch:
            return
        body = _build_bulk_register_body(batch)
        resp = _gen_bulk_register_contexts.sync_detailed(client=self._app_http, body=body)
        _check_status(int(resp.status_code), resp.content)

    def list(self, type: str) -> list[ContextEntity]:
        """List all contexts of a given type."""
        resp = _gen_list_contexts.sync_detailed(
            client=self._app_http,
            filtercontext_type=type,
        )
        _check_status(int(resp.status_code), resp.content)
        body = json.loads(resp.content)
        return [_ctx_entity_from_dict(item) for item in body.get("data", [])]

    @overload
    def get(self, id: str) -> ContextEntity: ...
    @overload
    def get(self, type: str, key: str) -> ContextEntity: ...
    def get(self, id_or_type: str, key: str | None = None) -> ContextEntity:
        ctx_type, ctx_key = _split_context_id(id_or_type, key)
        composite = f"{ctx_type}:{ctx_key}"
        resp = _gen_get_context.sync_detailed(composite, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplNotFoundError(
                f"Context with id {composite!r} not found",
                status_code=404,
            )
        return _ctx_entity_from_parsed(resp.parsed, sync=True)

    @overload
    def delete(self, id: str) -> None: ...
    @overload
    def delete(self, type: str, key: str) -> None: ...
    def delete(self, id_or_type: str, key: str | None = None) -> None:
        ctx_type, ctx_key = _split_context_id(id_or_type, key)
        composite = f"{ctx_type}:{ctx_key}"
        resp = _gen_delete_context.sync_detailed(composite, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)


class AsyncContextsClient:
    def __init__(
        self,
        parent: AsyncSmplClient,
        app_http: _AppAuthClient,
        buffer: _ContextRegistrationBuffer,
    ) -> None:
        self._parent = parent
        self._app_http = app_http
        self._buffer = buffer

    async def register(self, items: Context | list[Context], *, flush: bool = False) -> None:
        batch = items if isinstance(items, list) else [items]
        self._buffer.observe(batch)
        if flush:
            await self.flush()

    async def flush(self) -> None:
        batch = self._buffer.drain()
        if not batch:
            return
        body = _build_bulk_register_body(batch)
        resp = await _gen_bulk_register_contexts.asyncio_detailed(client=self._app_http, body=body)
        _check_status(int(resp.status_code), resp.content)

    async def list(self, type: str) -> list[AsyncContextEntity]:
        resp = await _gen_list_contexts.asyncio_detailed(
            client=self._app_http,
            filtercontext_type=type,
        )
        _check_status(int(resp.status_code), resp.content)
        body = json.loads(resp.content)
        return [_ctx_entity_from_dict(item, async_=True) for item in body.get("data", [])]

    @overload
    async def get(self, id: str) -> AsyncContextEntity: ...
    @overload
    async def get(self, type: str, key: str) -> AsyncContextEntity: ...
    async def get(self, id_or_type: str, key: str | None = None) -> AsyncContextEntity:
        ctx_type, ctx_key = _split_context_id(id_or_type, key)
        composite = f"{ctx_type}:{ctx_key}"
        resp = await _gen_get_context.asyncio_detailed(composite, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)
        if resp.parsed is None:
            raise SmplNotFoundError(
                f"Context with id {composite!r} not found",
                status_code=404,
            )
        return _ctx_entity_from_parsed(resp.parsed, sync=False)

    @overload
    async def delete(self, id: str) -> None: ...
    @overload
    async def delete(self, type: str, key: str) -> None: ...
    async def delete(self, id_or_type: str, key: str | None = None) -> None:
        ctx_type, ctx_key = _split_context_id(id_or_type, key)
        composite = f"{ctx_type}:{ctx_key}"
        resp = await _gen_delete_context.asyncio_detailed(composite, client=self._app_http)
        _check_status(int(resp.status_code), resp.content)


def _ctx_entity_from_dict(item: dict[str, Any], *, async_: bool = False) -> Any:
    composite_id = item.get("id") or ""
    if ":" in composite_id:
        ctx_type, _, ctx_key = composite_id.partition(":")
    else:
        ctx_type, ctx_key = composite_id, ""
    attrs = item.get("attributes") or {}
    raw_attrs = attrs.get("attributes") or {}
    cls = AsyncContextEntity if async_ else ContextEntity
    return cls(
        type=ctx_type,
        key=ctx_key,
        name=attrs.get("name") or None,
        attributes=dict(raw_attrs) if isinstance(raw_attrs, dict) else {},
        created_at=attrs.get("created_at"),
        updated_at=attrs.get("updated_at"),
    )


# ---------------------------------------------------------------------------
# Account Settings
# ---------------------------------------------------------------------------


import httpx  # noqa: E402  (kept here so the management module is self-contained)


class AccountSettingsClient:
    """Sync account-settings get/save.

    The endpoint isn't JSON:API — body is a raw JSON object — so we
    use httpx directly rather than going through a generated client.
    """

    def __init__(self, parent: SmplClient, app_base_url: str, api_key: str) -> None:
        self._parent = parent
        self._base_url = app_base_url
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def get(self) -> AccountSettings:
        with httpx.Client(base_url=self._base_url, headers=self._headers, timeout=30.0) as h:
            resp = h.get("/api/v1/accounts/current/settings")
        _check_status(resp.status_code, resp.content)
        return AccountSettings(self, data=resp.json() or {})

    def _save(self, data: dict[str, Any]) -> AccountSettings:
        with httpx.Client(base_url=self._base_url, headers=self._headers, timeout=30.0) as h:
            resp = h.put("/api/v1/accounts/current/settings", json=data)
        _check_status(resp.status_code, resp.content)
        return AccountSettings(self, data=resp.json() or {})


class AsyncAccountSettingsClient:
    def __init__(self, parent: AsyncSmplClient, app_base_url: str, api_key: str) -> None:
        self._parent = parent
        self._base_url = app_base_url
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def get(self) -> AsyncAccountSettings:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=30.0) as h:
            resp = await h.get("/api/v1/accounts/current/settings")
        _check_status(resp.status_code, resp.content)
        return AsyncAccountSettings(self, data=resp.json() or {})

    async def _save(self, data: dict[str, Any]) -> AsyncAccountSettings:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=30.0) as h:
            resp = await h.put("/api/v1/accounts/current/settings", json=data)
        _check_status(resp.status_code, resp.content)
        return AsyncAccountSettings(self, data=resp.json() or {})


# ---------------------------------------------------------------------------
# Metrics (bulk ingest of pre-aggregated points)
# ---------------------------------------------------------------------------


@dataclass
class MetricItem:
    """A single pre-aggregated metric point for bulk ingest.

    Mirrors the ``MetricBulkRequest`` body shape with sensible defaults.
    Used by :meth:`MetricsClient.bulk_ingest` and its async counterpart.
    """

    name: str
    value: float | int
    recorded_at: _datetime.datetime
    period_seconds: int = 60
    unit: str | None = None
    dimensions: dict[str, str] | None = None


def _to_metric_resource(item: MetricItem) -> _GenMetricResource:
    dims: _GenMetricAttributesDimensions | Unset
    if item.dimensions:
        dims = _GenMetricAttributesDimensions()
        for k, v in item.dimensions.items():
            dims[k] = v
    else:
        dims = UNSET
    attrs = _GenMetricAttributes(
        name=item.name,
        value=item.value,
        period_seconds=item.period_seconds,
        recorded_at=item.recorded_at,
        unit=item.unit if item.unit is not None else UNSET,
        dimensions=dims,
    )
    return _GenMetricResource(type_="metric", attributes=attrs)


class MetricsClient:
    """Sync ``client.management.metrics`` — bulk-ingest pre-aggregated points."""

    def __init__(self, parent: SmplClient, app_http: _AppAuthClient) -> None:
        self._parent = parent
        self._app_http = app_http

    def bulk_ingest(self, items: list[MetricItem]) -> None:
        """POST a batch of pre-aggregated metric points to ``/metrics/bulk``.

        Returns when the server has accepted the batch (HTTP 202). The
        endpoint is fire-and-forget — there is no per-item response.
        """
        if not items:
            return
        body = _GenMetricBulkRequest(data=[_to_metric_resource(i) for i in items])
        resp = _gen_bulk_ingest_metrics.sync_detailed(client=self._app_http, body=body)
        _raise_for_status(int(resp.status_code), resp.content)


class AsyncMetricsClient:
    """Async ``client.management.metrics``."""

    def __init__(self, parent: AsyncSmplClient, app_http: _AppAuthClient) -> None:
        self._parent = parent
        self._app_http = app_http

    async def bulk_ingest(self, items: list[MetricItem]) -> None:
        if not items:
            return
        body = _GenMetricBulkRequest(data=[_to_metric_resource(i) for i in items])
        resp = await _gen_bulk_ingest_metrics.asyncio_detailed(client=self._app_http, body=body)
        _raise_for_status(int(resp.status_code), resp.content)


# ---------------------------------------------------------------------------
# Top-level ManagementClient
# ---------------------------------------------------------------------------


class ManagementClient:
    """Sync ``client.management`` namespace."""

    environments: EnvironmentsClient
    contexts: ContextsClient
    context_types: ContextTypesClient
    account_settings: AccountSettingsClient
    metrics: MetricsClient

    def __init__(
        self,
        parent: SmplClient,
        *,
        app_base_url: str,
        api_key: str,
        buffer: _ContextRegistrationBuffer,
    ) -> None:
        self._parent = parent
        app_http = _AppAuthClient(base_url=app_base_url, token=api_key)
        self.environments = EnvironmentsClient(parent, app_http)
        self.contexts = ContextsClient(parent, app_http, buffer)
        self.context_types = ContextTypesClient(parent, app_http)
        self.account_settings = AccountSettingsClient(parent, app_base_url, api_key)
        self.metrics = MetricsClient(parent, app_http)


class AsyncManagementClient:
    environments: AsyncEnvironmentsClient
    contexts: AsyncContextsClient
    context_types: AsyncContextTypesClient
    account_settings: AsyncAccountSettingsClient
    metrics: AsyncMetricsClient

    def __init__(
        self,
        parent: AsyncSmplClient,
        *,
        app_base_url: str,
        api_key: str,
        buffer: _ContextRegistrationBuffer,
    ) -> None:
        self._parent = parent
        app_http = _AppAuthClient(base_url=app_base_url, token=api_key)
        self.environments = AsyncEnvironmentsClient(parent, app_http)
        self.contexts = AsyncContextsClient(parent, app_http, buffer)
        self.context_types = AsyncContextTypesClient(parent, app_http)
        self.account_settings = AsyncAccountSettingsClient(parent, app_base_url, api_key)
        self.metrics = AsyncMetricsClient(parent, app_http)
