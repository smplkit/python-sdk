"""Active-record models for ``client.management.*`` resources."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

from smplkit.management.types import EnvironmentClassification

if TYPE_CHECKING:  # pragma: no cover
    from smplkit.management.client import (
        AsyncAccountSettingsClient,
        AsyncContextTypesClient,
        AsyncEnvironmentsClient,
        AccountSettingsClient,
        ContextTypesClient,
        EnvironmentsClient,
    )


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


class _EnvironmentBase:
    """Shared state for Environment / AsyncEnvironment."""

    id: str | None
    name: str
    color: str | None
    classification: EnvironmentClassification
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None

    def __init__(
        self,
        *,
        id: str | None = None,
        name: str,
        color: str | None = None,
        classification: EnvironmentClassification = EnvironmentClassification.STANDARD,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.color = color
        self.classification = classification
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"Environment(id={self.id!r}, name={self.name!r}, classification={self.classification.value!r})"

    def _apply(self, other: _EnvironmentBase) -> None:
        self.id = other.id
        self.name = other.name
        self.color = other.color
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
        color: str | None = None,
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


class AsyncEnvironment(_EnvironmentBase):
    """Environment resource (async). Mutate fields, then ``await save()``."""

    def __init__(
        self,
        client: AsyncEnvironmentsClient | None = None,
        *,
        id: str | None = None,
        name: str,
        color: str | None = None,
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


# ---------------------------------------------------------------------------
# ContextEntity (read/delete model — write side is via register())
# ---------------------------------------------------------------------------


class _ContextEntityBase:
    """A single context instance as returned by the management API.

    The runtime ``client.management.contexts.register([...])`` call
    accepts the lighter :class:`smplkit.flags.types.Context` builder
    type; this model is what comes back from ``list``/``get``.
    """

    type: str
    key: str
    name: str | None
    attributes: dict[str, Any]
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None

    def __init__(
        self,
        *,
        type: str,
        key: str,
        name: str | None = None,
        attributes: dict[str, Any] | None = None,
        created_at: datetime.datetime | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        self.type = type
        self.key = key
        self.name = name
        self.attributes = dict(attributes) if attributes else {}
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def id(self) -> str:
        """Composite ``"{type}:{key}"`` identifier."""
        return f"{self.type}:{self.key}"

    def __repr__(self) -> str:
        return f"ContextEntity(type={self.type!r}, key={self.key!r})"


class ContextEntity(_ContextEntityBase):
    pass


class AsyncContextEntity(_ContextEntityBase):
    pass


# ---------------------------------------------------------------------------
# AccountSettings
# ---------------------------------------------------------------------------


class _AccountSettingsBase:
    """Active-record account-settings model.

    The wire format is opaque JSON. Documented keys are exposed as
    typed properties; unknown keys live in :attr:`raw`. ``save()``
    writes the full settings object back.
    """

    _data: dict[str, Any]

    def __init__(self, *, data: dict[str, Any] | None = None) -> None:
        self._data = dict(data) if data else {}

    @property
    def raw(self) -> dict[str, Any]:
        """The full settings dict. Mutations are persisted on save()."""
        return self._data

    @raw.setter
    def raw(self, value: dict[str, Any]) -> None:
        self._data = dict(value)

    @property
    def environment_order(self) -> list[str]:
        """Canonical ordering of STANDARD environments. Empty list if unset."""
        return list(self._data.get("environment_order") or [])

    @environment_order.setter
    def environment_order(self, value: list[str]) -> None:
        self._data["environment_order"] = list(value)

    def __repr__(self) -> str:
        return f"AccountSettings({self._data!r})"

    def _apply(self, other: _AccountSettingsBase) -> None:
        self._data = dict(other._data)


class AccountSettings(_AccountSettingsBase):
    def __init__(
        self,
        client: AccountSettingsClient | None = None,
        *,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(data=data)
        self._client = client

    def save(self) -> None:
        if self._client is None:
            raise RuntimeError("AccountSettings was constructed without a client; cannot save")
        other = self._client._save(self._data)
        self._apply(other)


class AsyncAccountSettings(_AccountSettingsBase):
    def __init__(
        self,
        client: AsyncAccountSettingsClient | None = None,
        *,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(data=data)
        self._client = client

    async def save(self) -> None:
        if self._client is None:
            raise RuntimeError("AsyncAccountSettings was constructed without a client; cannot save")
        other = await self._client._save(self._data)
        self._apply(other)
