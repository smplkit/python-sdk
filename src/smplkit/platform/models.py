"""Active-record models for ``client.platform.*`` resources."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

from smplkit.platform.types import Color, EnvironmentClassification


def _coerce_color(value: Color | str | None) -> Color | None:
    """Accept Color, hex string, or None; reject anything else."""
    if value is None or isinstance(value, Color):
        return value
    if isinstance(value, str):
        return Color(value)
    raise TypeError(f"color must be a Color, hex string, or None; got {value.__class__.__name__}: {value!r}")


if TYPE_CHECKING:  # pragma: no cover
    from smplkit.platform._client import (
        AsyncContextTypesClient,
        AsyncEnvironmentsClient,
        AsyncServicesClient,
        ContextTypesClient,
        EnvironmentsClient,
        ServicesClient,
    )


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


class _EnvironmentBase:
    """Shared state for Environment / AsyncEnvironment."""

    id: str | None
    name: str
    classification: EnvironmentClassification
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None

    def __init__(
        self,
        *,
        id: str | None = None,
        name: str,
        color: Color | str | None = None,
        classification: EnvironmentClassification = EnvironmentClassification.STANDARD,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self._color: Color | None = _coerce_color(color)
        self.classification = classification
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def color(self) -> Color | None:
        return self._color

    @color.setter
    def color(self, value: Color | str | None) -> None:
        self._color = _coerce_color(value)

    def __repr__(self) -> str:
        return f"Environment(id={self.id!r}, name={self.name!r}, classification={self.classification.value!r})"

    def _apply(self, other: _EnvironmentBase) -> None:
        self.id = other.id
        self.name = other.name
        self._color = other._color
        self.classification = other.classification
        self.created_at = other.created_at
        self.updated_at = other.updated_at


class Environment(_EnvironmentBase):
    """Environment resource (sync). Mutate fields, then call :meth:`save`."""

    def __init__(
        self,
        client: EnvironmentsClient | None = None,
        *,
        id: str | None = None,
        name: str,
        color: Color | str | None = None,
        classification: EnvironmentClassification = EnvironmentClassification.STANDARD,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            color=color,
            classification=classification,
            created_at=created_at,
            updated_at=updated_at,
        )
        self._client = client

    def save(self) -> None:
        """Create or update this environment on the server."""
        if self._client is None:
            raise RuntimeError("Environment was constructed without a client; cannot save")
        if self.created_at is None:
            other = self._client._create(self)
        else:
            other = self._client._update(self)
        self._apply(other)

    def delete(self) -> None:
        """Delete this environment from the server."""
        if self._client is None or self.id is None:
            raise RuntimeError("Environment was constructed without a client or id; cannot delete")
        self._client.delete(self.id)


class AsyncEnvironment(_EnvironmentBase):
    """Environment resource (async). Mutate fields, then ``await save()``."""

    def __init__(
        self,
        client: AsyncEnvironmentsClient | None = None,
        *,
        id: str | None = None,
        name: str,
        color: Color | str | None = None,
        classification: EnvironmentClassification = EnvironmentClassification.STANDARD,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            color=color,
            classification=classification,
            created_at=created_at,
            updated_at=updated_at,
        )
        self._client = client

    async def save(self) -> None:
        if self._client is None:
            raise RuntimeError("AsyncEnvironment was constructed without a client; cannot save")
        if self.created_at is None:
            other = await self._client._create(self)
        else:
            other = await self._client._update(self)
        self._apply(other)

    async def delete(self) -> None:
        """Delete this environment from the server."""
        if self._client is None or self.id is None:
            raise RuntimeError("AsyncEnvironment was constructed without a client or id; cannot delete")
        await self._client.delete(self.id)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class _ServiceBase:
    """Shared state for Service / AsyncService."""

    id: str | None
    name: str
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None

    def __init__(
        self,
        *,
        id: str | None = None,
        name: str,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"Service(id={self.id!r}, name={self.name!r})"

    def _apply(self, other: _ServiceBase) -> None:
        self.id = other.id
        self.name = other.name
        self.created_at = other.created_at
        self.updated_at = other.updated_at


class Service(_ServiceBase):
    """Service resource (sync). Mutate fields, then call :meth:`save`."""

    def __init__(
        self,
        client: ServicesClient | None = None,
        *,
        id: str | None = None,
        name: str,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            created_at=created_at,
            updated_at=updated_at,
        )
        self._client = client

    def save(self) -> None:
        """Create or update this service on the server."""
        if self._client is None:
            raise RuntimeError("Service was constructed without a client; cannot save")
        if self.created_at is None:
            other = self._client._create(self)
        else:
            other = self._client._update(self)
        self._apply(other)

    def delete(self) -> None:
        """Delete this service from the server."""
        if self._client is None or self.id is None:
            raise RuntimeError("Service was constructed without a client or id; cannot delete")
        self._client.delete(self.id)


class AsyncService(_ServiceBase):
    """Service resource (async). Mutate fields, then ``await save()``."""

    def __init__(
        self,
        client: AsyncServicesClient | None = None,
        *,
        id: str | None = None,
        name: str,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            created_at=created_at,
            updated_at=updated_at,
        )
        self._client = client

    async def save(self) -> None:
        if self._client is None:
            raise RuntimeError("AsyncService was constructed without a client; cannot save")
        if self.created_at is None:
            other = await self._client._create(self)
        else:
            other = await self._client._update(self)
        self._apply(other)

    async def delete(self) -> None:
        """Delete this service from the server."""
        if self._client is None or self.id is None:
            raise RuntimeError("AsyncService was constructed without a client or id; cannot delete")
        await self._client.delete(self.id)


# ---------------------------------------------------------------------------
# ContextType
# ---------------------------------------------------------------------------


class _ContextTypeBase:
    """Shared state for ContextType / AsyncContextType."""

    id: str | None
    name: str
    attributes: dict[str, dict[str, Any]]
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None

    def __init__(
        self,
        *,
        id: str | None = None,
        name: str,
        attributes: dict[str, dict[str, Any]] | None = None,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.attributes = dict(attributes) if attributes else {}
        self.created_at = created_at
        self.updated_at = updated_at

    def add_attribute(self, name: str, **metadata: Any) -> None:
        """Add a known-attribute slot. Local; call :meth:`save` to persist."""
        self.attributes[name] = dict(metadata)

    def remove_attribute(self, name: str) -> None:
        """Remove a known-attribute slot. Local; call :meth:`save` to persist."""
        self.attributes.pop(name, None)

    def update_attribute(self, name: str, **metadata: Any) -> None:
        """Replace a known-attribute slot's metadata. Local; call :meth:`save`."""
        self.attributes[name] = dict(metadata)

    def __repr__(self) -> str:
        return f"ContextType(id={self.id!r}, name={self.name!r})"

    def _apply(self, other: _ContextTypeBase) -> None:
        self.id = other.id
        self.name = other.name
        self.attributes = dict(other.attributes)
        self.created_at = other.created_at
        self.updated_at = other.updated_at


class ContextType(_ContextTypeBase):
    def __init__(
        self,
        client: ContextTypesClient | None = None,
        *,
        id: str | None = None,
        name: str,
        attributes: dict[str, dict[str, Any]] | None = None,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            attributes=attributes,
            created_at=created_at,
            updated_at=updated_at,
        )
        self._client = client

    def save(self) -> None:
        if self._client is None:
            raise RuntimeError("ContextType was constructed without a client; cannot save")
        if self.created_at is None:
            other = self._client._create(self)
        else:
            other = self._client._update(self)
        self._apply(other)

    def delete(self) -> None:
        """Delete this context type from the server."""
        if self._client is None or self.id is None:
            raise RuntimeError("ContextType was constructed without a client or id; cannot delete")
        self._client.delete(self.id)


class AsyncContextType(_ContextTypeBase):
    def __init__(
        self,
        client: AsyncContextTypesClient | None = None,
        *,
        id: str | None = None,
        name: str,
        attributes: dict[str, dict[str, Any]] | None = None,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            attributes=attributes,
            created_at=created_at,
            updated_at=updated_at,
        )
        self._client = client

    async def save(self) -> None:
        if self._client is None:
            raise RuntimeError("AsyncContextType was constructed without a client; cannot save")
        if self.created_at is None:
            other = await self._client._create(self)
        else:
            other = await self._client._update(self)
        self._apply(other)

    async def delete(self) -> None:
        """Delete this context type from the server."""
        if self._client is None or self.id is None:
            raise RuntimeError("AsyncContextType was constructed without a client or id; cannot delete")
        await self._client.delete(self.id)
