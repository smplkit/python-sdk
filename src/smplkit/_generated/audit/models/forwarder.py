from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, TYPE_CHECKING

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.forwarder_type import check_forwarder_type
from ..models.forwarder_type import ForwarderType
from dateutil.parser import isoparse
from typing import cast
import datetime

if TYPE_CHECKING:
    from ..models.forwarder_data import ForwarderData
    from ..models.forwarder_filter_type_0 import ForwarderFilterType0
    from ..models.forwarder_http import ForwarderHttp


T = TypeVar("T", bound="Forwarder")


@_attrs_define
class Forwarder:
    """Public-facing forwarder resource.

    Attribute set on POST /api/v1/forwarders:
        - name (required)
        - forwarder_type (required)
        - http (required)
        - enabled (optional, defaults true)
        - filter (optional, JSON Logic)
        - transform (optional, JSONata)

    The slug is server-derived from name on create; it is immutable on
    update because consumers (UI, observability) key off it.

        Attributes:
            name (str):
            forwarder_type (ForwarderType): Supported forwarder destination types.

                Carried as a typed enum so the OpenAPI spec emits an ``enum``
                constraint and the auto-generated SDK clients (in all 6 languages)
                surface a typed enum to customers rather than free-form strings.
                Subclassing ``str`` keeps JSON serialization byte-identical to the
                prior ``str`` field — no migration of stored ``forwarder.type``
                values needed.

                Values are SCREAMING_SNAKE_CASE per ADR-014. The Forwarder schema
                accepts any casing on input via _normalize_forwarder_type.

                Adding a new destination here requires a corresponding implementation
                in ``app.services.forwarding`` and a regeneration of the OpenAPI
                spec so the SDK clients pick up the new variant.
            http (ForwarderHttp): The destination HTTP request shape stored encrypted on a forwarder.

                ``success_status`` is a string: either a single status code (e.g.
                ``"200"``, ``"204"``) or a class (e.g. ``"2xx"``, ``"3xx"``). The
                string-only contract is intentional — a Pydantic ``int | str`` union
                confused several SDK code generators (Java in particular wrote the
                default ``"2xx"`` unquoted into a typed enum). String covers both
                shapes universally with a single wire type.
            enabled (bool | Unset):  Default: True.
            filter_ (ForwarderFilterType0 | None | Unset):
            transform (None | str | Unset):
            slug (None | str | Unset):
            created_at (datetime.datetime | None | Unset):
            updated_at (datetime.datetime | None | Unset):
            deleted_at (datetime.datetime | None | Unset):
            version (int | None | Unset):
            data (ForwarderData | Unset):
    """

    name: str
    forwarder_type: ForwarderType
    http: ForwarderHttp
    enabled: bool | Unset = True
    filter_: ForwarderFilterType0 | None | Unset = UNSET
    transform: None | str | Unset = UNSET
    slug: None | str | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    updated_at: datetime.datetime | None | Unset = UNSET
    deleted_at: datetime.datetime | None | Unset = UNSET
    version: int | None | Unset = UNSET
    data: ForwarderData | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.forwarder_filter_type_0 import ForwarderFilterType0

        name = self.name

        forwarder_type: str = self.forwarder_type

        http = self.http.to_dict()

        enabled = self.enabled

        filter_: dict[str, Any] | None | Unset
        if isinstance(self.filter_, Unset):
            filter_ = UNSET
        elif isinstance(self.filter_, ForwarderFilterType0):
            filter_ = self.filter_.to_dict()
        else:
            filter_ = self.filter_

        transform: None | str | Unset
        if isinstance(self.transform, Unset):
            transform = UNSET
        else:
            transform = self.transform

        slug: None | str | Unset
        if isinstance(self.slug, Unset):
            slug = UNSET
        else:
            slug = self.slug

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        elif isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        updated_at: None | str | Unset
        if isinstance(self.updated_at, Unset):
            updated_at = UNSET
        elif isinstance(self.updated_at, datetime.datetime):
            updated_at = self.updated_at.isoformat()
        else:
            updated_at = self.updated_at

        deleted_at: None | str | Unset
        if isinstance(self.deleted_at, Unset):
            deleted_at = UNSET
        elif isinstance(self.deleted_at, datetime.datetime):
            deleted_at = self.deleted_at.isoformat()
        else:
            deleted_at = self.deleted_at

        version: int | None | Unset
        if isinstance(self.version, Unset):
            version = UNSET
        else:
            version = self.version

        data: dict[str, Any] | Unset = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "forwarder_type": forwarder_type,
                "http": http,
            }
        )
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if filter_ is not UNSET:
            field_dict["filter"] = filter_
        if transform is not UNSET:
            field_dict["transform"] = transform
        if slug is not UNSET:
            field_dict["slug"] = slug
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at
        if deleted_at is not UNSET:
            field_dict["deleted_at"] = deleted_at
        if version is not UNSET:
            field_dict["version"] = version
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.forwarder_data import ForwarderData
        from ..models.forwarder_filter_type_0 import ForwarderFilterType0
        from ..models.forwarder_http import ForwarderHttp

        d = dict(src_dict)
        name = d.pop("name")

        forwarder_type = check_forwarder_type(d.pop("forwarder_type"))

        http = ForwarderHttp.from_dict(d.pop("http"))

        enabled = d.pop("enabled", UNSET)

        def _parse_filter_(data: object) -> ForwarderFilterType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                filter_type_0 = ForwarderFilterType0.from_dict(data)

                return filter_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(ForwarderFilterType0 | None | Unset, data)

        filter_ = _parse_filter_(d.pop("filter", UNSET))

        def _parse_transform(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        transform = _parse_transform(d.pop("transform", UNSET))

        def _parse_slug(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        slug = _parse_slug(d.pop("slug", UNSET))

        def _parse_created_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                created_at_type_0 = isoparse(data)

                return created_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_updated_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                updated_at_type_0 = isoparse(data)

                return updated_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        updated_at = _parse_updated_at(d.pop("updated_at", UNSET))

        def _parse_deleted_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                deleted_at_type_0 = isoparse(data)

                return deleted_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        deleted_at = _parse_deleted_at(d.pop("deleted_at", UNSET))

        def _parse_version(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        version = _parse_version(d.pop("version", UNSET))

        _data = d.pop("data", UNSET)
        data: ForwarderData | Unset
        if isinstance(_data, Unset):
            data = UNSET
        else:
            data = ForwarderData.from_dict(_data)

        forwarder = cls(
            name=name,
            forwarder_type=forwarder_type,
            http=http,
            enabled=enabled,
            filter_=filter_,
            transform=transform,
            slug=slug,
            created_at=created_at,
            updated_at=updated_at,
            deleted_at=deleted_at,
            version=version,
            data=data,
        )

        forwarder.additional_properties = d
        return forwarder

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
