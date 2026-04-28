"""Tests for smplkit.management.client — all sync and async sub-clients."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from smplkit._errors import SmplNotFoundError, SmplValidationError
from smplkit.flags.types import Context
from smplkit.management._buffer import _ContextRegistrationBuffer
from smplkit.management.client import (
    AccountSettingsClient,
    AsyncAccountSettingsClient,
    AsyncContextsClient,
    AsyncContextTypesClient,
    AsyncEnvironmentsClient,
    AsyncManagementClient,
    ContextsClient,
    ContextTypesClient,
    EnvironmentsClient,
    ManagementClient,
    _build_bulk_register_body,
    _check_status,
    _ct_from_parsed,
    _ct_resource_from_dict,
    _ct_to_resource,
    _ctx_entity_from_dict,
    _ctx_entity_from_parsed,
    _env_from_parsed,
    _env_resource_from_dict,
    _env_to_resource,
    _is_unset,
    _split_context_id,
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_resp(status: int = 200, body: bytes = b"{}"):
    resp = MagicMock()
    resp.status_code = status
    resp.content = body
    resp.parsed = None
    return resp


def _ok_json_resp(data: dict, status: int = 200):
    resp = _ok_resp(status=status, body=json.dumps(data).encode())
    return resp


def _parsed_env_resp(id="env-1", name="production", color=None, classification="STANDARD"):
    attrs = MagicMock()
    attrs.name = name
    attrs.color = color
    attrs.classification = classification
    attrs.created_at = "2026-01-01T00:00:00Z"
    attrs.updated_at = None

    resource = MagicMock()
    resource.id = id
    resource.attributes = attrs

    parsed = MagicMock()
    parsed.data = resource
    return parsed


def _parsed_ct_resp(id="ct-1", name="user", attributes=None):
    attr_meta = MagicMock()
    attr_meta.additional_properties = attributes or {}

    attrs = MagicMock()
    attrs.name = name
    attrs.attributes = attr_meta
    attrs.created_at = "2026-01-01T00:00:00Z"
    attrs.updated_at = None
    attrs.id = id

    resource = MagicMock()
    resource.id = id
    resource.attributes = attrs

    parsed = MagicMock()
    parsed.data = resource
    return parsed


def _parsed_ctx_resp(composite_id="user:u-1", name=None, attributes=None):
    attrs = MagicMock()
    attrs.name = name
    attrs.attributes = attributes or {}
    attrs.created_at = "2026-01-01T00:00:00Z"
    attrs.updated_at = None

    resource = MagicMock()
    resource.id = composite_id
    resource.attributes = attrs

    parsed = MagicMock()
    parsed.data = resource
    return parsed


def _make_env_client():
    parent = MagicMock()
    app_http = MagicMock()
    return EnvironmentsClient(parent, app_http)


def _make_async_env_client():
    parent = MagicMock()
    app_http = MagicMock()
    return AsyncEnvironmentsClient(parent, app_http)


def _make_ct_client():
    parent = MagicMock()
    app_http = MagicMock()
    return ContextTypesClient(parent, app_http)


def _make_async_ct_client():
    parent = MagicMock()
    app_http = MagicMock()
    return AsyncContextTypesClient(parent, app_http)


def _make_contexts_client():
    parent = MagicMock()
    app_http = MagicMock()
    buf = _ContextRegistrationBuffer()
    return ContextsClient(parent, app_http, buf)


def _make_async_contexts_client():
    parent = MagicMock()
    app_http = MagicMock()
    buf = _ContextRegistrationBuffer()
    return AsyncContextsClient(parent, app_http, buf)


# ---------------------------------------------------------------------------
# Standalone helpers
# ---------------------------------------------------------------------------


class TestSplitContextId:
    def test_composite_form(self):
        t, k = _split_context_id("user:u-1", None)
        assert t == "user"
        assert k == "u-1"

    def test_two_arg_form(self):
        t, k = _split_context_id("user", "u-1")
        assert t == "user"
        assert k == "u-1"

    def test_composite_missing_colon_raises(self):
        with pytest.raises(ValueError, match="type:key"):
            _split_context_id("nocolon", None)

    def test_composite_with_colon_in_key(self):
        t, k = _split_context_id("user:u:1:extra", None)
        assert t == "user"
        assert k == "u:1:extra"


class TestIsUnset:
    def test_unset_type(self):
        from smplkit._generated.app.types import UNSET

        assert _is_unset(UNSET) is True

    def test_regular_value(self):
        assert _is_unset(None) is False
        assert _is_unset("hello") is False
        assert _is_unset(0) is False


class TestCheckStatus:
    def test_ok_does_not_raise(self):
        _check_status(200, b"")

    def test_404_raises_not_found(self):
        from smplkit._errors import SmplNotFoundError

        with pytest.raises(SmplNotFoundError):
            _check_status(404, b'{"errors":[{"status":"404","title":"Not Found"}]}')

    def test_500_raises(self):
        from smplkit._errors import SmplError

        with pytest.raises(SmplError):
            _check_status(500, b'{"errors":[{"status":"500","title":"Server Error"}]}')


class TestEnvToResource:
    def test_basic(self):
        env = Environment(name="production", color="#ff0000", classification=EnvironmentClassification.STANDARD)
        body = _env_to_resource(env)
        assert body.data.attributes.name == "production"
        assert body.data.attributes.color == "#ff0000"
        assert body.data.attributes.classification == "STANDARD"

    def test_ad_hoc_classification(self):
        env = Environment(name="preview", classification=EnvironmentClassification.AD_HOC)
        body = _env_to_resource(env)
        assert body.data.attributes.classification == "AD_HOC"


class TestEnvFromParsed:
    def test_sync(self):
        parsed = _parsed_env_resp()
        result = _env_from_parsed(parsed, sync_client=MagicMock(), async_client=None)
        assert isinstance(result, Environment)
        assert result.id == "env-1"
        assert result.name == "production"
        assert result.classification == EnvironmentClassification.STANDARD

    def test_async(self):
        parsed = _parsed_env_resp(classification="AD_HOC")
        result = _env_from_parsed(parsed, sync_client=None, async_client=MagicMock())
        assert isinstance(result, AsyncEnvironment)
        assert result.classification == EnvironmentClassification.AD_HOC


class TestEnvResourceFromDict:
    def test_sync(self):
        item = {
            "id": "env-1",
            "attributes": {
                "name": "production",
                "color": "#ff0000",
                "classification": "STANDARD",
                "created_at": "2026-01-01",
            },
        }
        result = _env_resource_from_dict(item, sync_client=MagicMock())
        assert isinstance(result, Environment)
        assert result.id == "env-1"
        assert result.color == "#ff0000"

    def test_async_ad_hoc(self):
        item = {
            "id": "env-2",
            "attributes": {"name": "preview", "classification": "AD_HOC"},
        }
        result = _env_resource_from_dict(item, async_client=MagicMock())
        assert isinstance(result, AsyncEnvironment)
        assert result.classification == EnvironmentClassification.AD_HOC

    def test_missing_attrs(self):
        result = _env_resource_from_dict({}, sync_client=MagicMock())
        assert result.id is None
        assert result.name == ""


class TestCtToResource:
    def test_basic(self):
        ct = ContextType(id="ct-1", name="user", attributes={"plan": {"type": "string"}})
        body = _ct_to_resource(ct)
        assert body.data.attributes.name == "user"
        assert body.data.attributes.id == "ct-1"

    def test_attributes_set(self):
        ct = ContextType(id="ct-1", name="user", attributes={"plan": {}})
        body = _ct_to_resource(ct)
        assert body.data.attributes.attributes.additional_properties == {"plan": {}}


class TestCtFromParsed:
    def test_sync(self):
        parsed = _parsed_ct_resp(attributes={"plan": {"type": "string"}})
        result = _ct_from_parsed(parsed, sync_client=MagicMock(), async_client=None)
        assert isinstance(result, ContextType)
        assert result.attributes == {"plan": {"type": "string"}}

    def test_async(self):
        parsed = _parsed_ct_resp()
        result = _ct_from_parsed(parsed, sync_client=None, async_client=MagicMock())
        assert isinstance(result, AsyncContextType)

    def test_null_attr_meta(self):
        parsed = _parsed_ct_resp()
        parsed.data.attributes.attributes = None
        result = _ct_from_parsed(parsed, sync_client=MagicMock(), async_client=None)
        assert result.attributes == {}

    def test_unset_attr_meta(self):
        from smplkit._generated.app.types import UNSET

        parsed = _parsed_ct_resp()
        parsed.data.attributes.attributes = UNSET
        result = _ct_from_parsed(parsed, sync_client=MagicMock(), async_client=None)
        assert result.attributes == {}


class TestCtResourceFromDict:
    def test_with_attributes(self):
        item = {
            "id": "ct-1",
            "attributes": {
                "name": "user",
                "attributes": {"plan": {"type": "string"}},
                "created_at": "2026-01-01",
            },
        }
        result = _ct_resource_from_dict(item, sync_client=MagicMock())
        assert isinstance(result, ContextType)
        assert result.attributes["plan"] == {"type": "string"}

    def test_async(self):
        item = {"id": "ct-2", "attributes": {"name": "account"}}
        result = _ct_resource_from_dict(item, async_client=MagicMock())
        assert isinstance(result, AsyncContextType)

    def test_non_dict_attribute_values(self):
        item = {
            "id": "ct-3",
            "attributes": {"name": "x", "attributes": {"plan": "not-a-dict"}},
        }
        result = _ct_resource_from_dict(item, sync_client=MagicMock())
        assert result.attributes["plan"] == {}


class TestCtxEntityFromParsed:
    def test_sync(self):
        parsed = _parsed_ctx_resp("user:u-1", name="Alice")
        result = _ctx_entity_from_parsed(parsed, sync=True)
        assert isinstance(result, ContextEntity)
        assert result.type == "user"
        assert result.key == "u-1"
        assert result.name == "Alice"

    def test_async(self):
        parsed = _parsed_ctx_resp("account:acme")
        result = _ctx_entity_from_parsed(parsed, sync=False)
        assert isinstance(result, AsyncContextEntity)
        assert result.type == "account"
        assert result.key == "acme"

    def test_no_colon_in_id(self):
        parsed = _parsed_ctx_resp("nocolon")
        result = _ctx_entity_from_parsed(parsed, sync=True)
        assert result.type == "nocolon"
        assert result.key == ""

    def test_dict_attributes(self):
        parsed = _parsed_ctx_resp("user:u-1")
        parsed.data.attributes.attributes = {"plan": "pro"}
        result = _ctx_entity_from_parsed(parsed, sync=True)
        assert result.attributes == {"plan": "pro"}

    def test_unset_attributes(self):
        from smplkit._generated.app.types import UNSET

        parsed = _parsed_ctx_resp("user:u-1")
        parsed.data.attributes.attributes = UNSET
        result = _ctx_entity_from_parsed(parsed, sync=True)
        assert result.attributes == {}

    def test_object_with_additional_properties(self):
        attr_obj = MagicMock()
        attr_obj.additional_properties = {"plan": "pro"}
        parsed = _parsed_ctx_resp("user:u-1")
        parsed.data.attributes.attributes = attr_obj
        result = _ctx_entity_from_parsed(parsed, sync=True)
        assert result.attributes == {"plan": "pro"}


class TestCtxEntityFromDict:
    def test_sync(self):
        item = {
            "id": "user:u-1",
            "attributes": {"name": "Alice", "attributes": {"plan": "pro"}},
        }
        result = _ctx_entity_from_dict(item)
        assert isinstance(result, ContextEntity)
        assert result.type == "user"
        assert result.key == "u-1"
        assert result.attributes == {"plan": "pro"}

    def test_async(self):
        item = {"id": "account:acme", "attributes": {}}
        result = _ctx_entity_from_dict(item, async_=True)
        assert isinstance(result, AsyncContextEntity)

    def test_no_colon(self):
        result = _ctx_entity_from_dict({"id": "nocolon", "attributes": {}})
        assert result.type == "nocolon"
        assert result.key == ""

    def test_non_dict_raw_attrs(self):
        item = {"id": "user:u-1", "attributes": {"attributes": "not-a-dict"}}
        result = _ctx_entity_from_dict(item)
        assert result.attributes == {}


class TestBuildBulkRegisterBody:
    def test_basic(self):
        items = [
            {"type": "user", "key": "u-1", "attributes": {"plan": "pro"}},
        ]
        body = _build_bulk_register_body(items)
        assert len(body.contexts) == 1
        assert body.contexts[0].type_ == "user"
        assert body.contexts[0].key == "u-1"
        assert body.contexts[0].attributes.additional_properties == {"plan": "pro"}

    def test_no_attributes(self):
        items = [{"type": "user", "key": "u-2"}]
        body = _build_bulk_register_body(items)
        assert body.contexts[0].attributes.additional_properties == {}


# ---------------------------------------------------------------------------
# EnvironmentsClient (sync)
# ---------------------------------------------------------------------------


class TestEnvironmentsClient:
    def test_new(self):
        client = _make_env_client()
        env = client.new("env-1", name="production", color="#ff0000")
        assert isinstance(env, Environment)
        assert env.id == "env-1"
        assert env.name == "production"
        assert env.color == "#ff0000"

    @patch("smplkit.management.client._gen_list_environments.sync_detailed")
    def test_list(self, mock_list):
        data = [
            {"id": "env-1", "attributes": {"name": "production", "classification": "STANDARD"}},
        ]
        mock_list.return_value = _ok_json_resp({"data": data})
        client = _make_env_client()
        result = client.list()
        assert len(result) == 1
        assert result[0].name == "production"

    @patch("smplkit.management.client._gen_get_environment.sync_detailed")
    def test_get(self, mock_get):
        parsed = _parsed_env_resp()
        mock_get.return_value = _ok_resp()
        mock_get.return_value.parsed = parsed
        client = _make_env_client()
        env = client.get("env-1")
        assert env.id == "env-1"

    @patch("smplkit.management.client._gen_get_environment.sync_detailed")
    def test_get_not_found(self, mock_get):
        mock_get.return_value = _ok_resp()
        mock_get.return_value.parsed = None
        client = _make_env_client()
        with pytest.raises(SmplNotFoundError):
            client.get("nonexistent")

    @patch("smplkit.management.client._gen_delete_environment.sync_detailed")
    def test_delete(self, mock_delete):
        mock_delete.return_value = _ok_resp(204, b"")
        client = _make_env_client()
        client.delete("env-1")
        mock_delete.assert_called_once()

    @patch("smplkit.management.client._gen_create_environment.sync_detailed")
    def test_create(self, mock_create):
        parsed = _parsed_env_resp()
        mock_create.return_value = _ok_resp(201)
        mock_create.return_value.parsed = parsed
        client = _make_env_client()
        env = Environment(name="production")
        result = client._create(env)
        assert result.id == "env-1"

    @patch("smplkit.management.client._gen_create_environment.sync_detailed")
    def test_create_null_parsed_raises(self, mock_create):
        mock_create.return_value = _ok_resp(201)
        mock_create.return_value.parsed = None
        client = _make_env_client()
        env = Environment(name="production")
        with pytest.raises(SmplValidationError):
            client._create(env)

    @patch("smplkit.management.client._gen_update_environment.sync_detailed")
    def test_update(self, mock_update):
        parsed = _parsed_env_resp()
        mock_update.return_value = _ok_resp()
        mock_update.return_value.parsed = parsed
        client = _make_env_client()
        env = Environment(client, id="env-1", name="production", created_at="2026-01-01")
        result = client._update(env)
        assert result.id == "env-1"

    def test_update_null_id_raises(self):
        client = _make_env_client()
        env = Environment(client, name="production", created_at="2026-01-01")
        env.id = None
        with pytest.raises(ValueError, match="no id"):
            client._update(env)

    @patch("smplkit.management.client._gen_update_environment.sync_detailed")
    def test_update_null_parsed_raises(self, mock_update):
        mock_update.return_value = _ok_resp()
        mock_update.return_value.parsed = None
        client = _make_env_client()
        env = Environment(client, id="env-1", name="production", created_at="2026-01-01")
        with pytest.raises(SmplValidationError):
            client._update(env)


# ---------------------------------------------------------------------------
# AsyncEnvironmentsClient
# ---------------------------------------------------------------------------


class TestAsyncEnvironmentsClient:
    def test_new(self):
        client = _make_async_env_client()
        env = client.new("env-1", name="staging")
        assert isinstance(env, AsyncEnvironment)

    @patch("smplkit.management.client._gen_list_environments.asyncio_detailed")
    def test_list(self, mock_list):
        data = [{"id": "env-1", "attributes": {"name": "staging", "classification": "AD_HOC"}}]
        mock_list.return_value = _ok_json_resp({"data": data})

        async def _run():
            mock_list.return_value = _ok_json_resp({"data": data})
            mock_coro = AsyncMock(return_value=_ok_json_resp({"data": data}))
            with patch("smplkit.management.client._gen_list_environments.asyncio_detailed", mock_coro):
                client = _make_async_env_client()
                result = await client.list()
                assert len(result) == 1
                assert result[0].classification == EnvironmentClassification.AD_HOC

        asyncio.run(_run())

    @patch("smplkit.management.client._gen_get_environment.asyncio_detailed")
    def test_get(self, mock_get):
        async def _run():
            parsed = _parsed_env_resp()
            resp = _ok_resp()
            resp.parsed = parsed
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_get_environment.asyncio_detailed", mock_coro):
                client = _make_async_env_client()
                env = await client.get("env-1")
                assert env.id == "env-1"
                assert isinstance(env, AsyncEnvironment)

        asyncio.run(_run())

    def test_get_not_found(self):
        async def _run():
            resp = _ok_resp()
            resp.parsed = None
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_get_environment.asyncio_detailed", mock_coro):
                client = _make_async_env_client()
                with pytest.raises(SmplNotFoundError):
                    await client.get("nope")

        asyncio.run(_run())

    def test_delete(self):
        async def _run():
            mock_coro = AsyncMock(return_value=_ok_resp(204, b""))
            with patch("smplkit.management.client._gen_delete_environment.asyncio_detailed", mock_coro):
                client = _make_async_env_client()
                await client.delete("env-1")

        asyncio.run(_run())

    def test_create(self):
        async def _run():
            parsed = _parsed_env_resp()
            resp = _ok_resp(201)
            resp.parsed = parsed
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_create_environment.asyncio_detailed", mock_coro):
                client = _make_async_env_client()
                env = AsyncEnvironment(name="production")
                result = await client._create(env)
                assert result.id == "env-1"

        asyncio.run(_run())

    def test_create_null_parsed_raises(self):
        async def _run():
            resp = _ok_resp(201)
            resp.parsed = None
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_create_environment.asyncio_detailed", mock_coro):
                client = _make_async_env_client()
                env = AsyncEnvironment(name="production")
                with pytest.raises(SmplValidationError):
                    await client._create(env)

        asyncio.run(_run())

    def test_update(self):
        async def _run():
            parsed = _parsed_env_resp()
            resp = _ok_resp()
            resp.parsed = parsed
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_update_environment.asyncio_detailed", mock_coro):
                client = _make_async_env_client()
                env = AsyncEnvironment(client, id="env-1", name="production", created_at="2026-01-01")
                result = await client._update(env)
                assert result.id == "env-1"

        asyncio.run(_run())

    def test_update_null_id_raises(self):
        async def _run():
            client = _make_async_env_client()
            env = AsyncEnvironment(client, name="production", created_at="2026-01-01")
            env.id = None
            with pytest.raises(ValueError, match="no id"):
                await client._update(env)

        asyncio.run(_run())

    def test_update_null_parsed_raises(self):
        async def _run():
            resp = _ok_resp()
            resp.parsed = None
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_update_environment.asyncio_detailed", mock_coro):
                client = _make_async_env_client()
                env = AsyncEnvironment(client, id="env-1", name="production", created_at="2026-01-01")
                with pytest.raises(SmplValidationError):
                    await client._update(env)

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# ContextTypesClient (sync)
# ---------------------------------------------------------------------------


class TestContextTypesClient:
    def test_new(self):
        client = _make_ct_client()
        ct = client.new("user", name="User", attributes={"plan": {}})
        assert isinstance(ct, ContextType)
        assert ct.id == "user"
        assert ct.name == "User"

    def test_new_default_name(self):
        client = _make_ct_client()
        ct = client.new("user")
        assert ct.name == "user"

    @patch("smplkit.management.client._gen_list_context_types.sync_detailed")
    def test_list(self, mock_list):
        data = [{"id": "ct-1", "attributes": {"name": "user", "attributes": {"plan": {"type": "str"}}}}]
        mock_list.return_value = _ok_json_resp({"data": data})
        client = _make_ct_client()
        result = client.list()
        assert len(result) == 1
        assert result[0].name == "user"
        assert result[0].attributes == {"plan": {"type": "str"}}

    @patch("smplkit.management.client._gen_get_context_type.sync_detailed")
    def test_get(self, mock_get):
        parsed = _parsed_ct_resp()
        resp = _ok_resp()
        resp.parsed = parsed
        mock_get.return_value = resp
        client = _make_ct_client()
        ct = client.get("ct-1")
        assert ct.id == "ct-1"

    @patch("smplkit.management.client._gen_get_context_type.sync_detailed")
    def test_get_not_found(self, mock_get):
        resp = _ok_resp()
        resp.parsed = None
        mock_get.return_value = resp
        client = _make_ct_client()
        with pytest.raises(SmplNotFoundError):
            client.get("nope")

    @patch("smplkit.management.client._gen_delete_context_type.sync_detailed")
    def test_delete(self, mock_delete):
        mock_delete.return_value = _ok_resp(204, b"")
        client = _make_ct_client()
        client.delete("ct-1")
        mock_delete.assert_called_once()

    @patch("smplkit.management.client._gen_create_context_type.sync_detailed")
    def test_create(self, mock_create):
        parsed = _parsed_ct_resp()
        resp = _ok_resp(201)
        resp.parsed = parsed
        mock_create.return_value = resp
        client = _make_ct_client()
        ct = ContextType(name="user")
        result = client._create(ct)
        assert result.id == "ct-1"

    @patch("smplkit.management.client._gen_create_context_type.sync_detailed")
    def test_create_null_parsed_raises(self, mock_create):
        resp = _ok_resp(201)
        resp.parsed = None
        mock_create.return_value = resp
        client = _make_ct_client()
        ct = ContextType(name="user")
        with pytest.raises(SmplValidationError):
            client._create(ct)

    @patch("smplkit.management.client._gen_update_context_type.sync_detailed")
    def test_update(self, mock_update):
        parsed = _parsed_ct_resp()
        resp = _ok_resp()
        resp.parsed = parsed
        mock_update.return_value = resp
        client = _make_ct_client()
        ct = ContextType(client, id="ct-1", name="user", created_at="2026-01-01")
        result = client._update(ct)
        assert result.id == "ct-1"

    def test_update_null_id_raises(self):
        client = _make_ct_client()
        ct = ContextType(client, name="user")
        ct.id = None
        with pytest.raises(ValueError, match="no id"):
            client._update(ct)

    @patch("smplkit.management.client._gen_update_context_type.sync_detailed")
    def test_update_null_parsed_raises(self, mock_update):
        resp = _ok_resp()
        resp.parsed = None
        mock_update.return_value = resp
        client = _make_ct_client()
        ct = ContextType(client, id="ct-1", name="user", created_at="2026-01-01")
        with pytest.raises(SmplValidationError):
            client._update(ct)


# ---------------------------------------------------------------------------
# AsyncContextTypesClient
# ---------------------------------------------------------------------------


class TestAsyncContextTypesClient:
    def test_new(self):
        client = _make_async_ct_client()
        ct = client.new("user", name="User")
        assert isinstance(ct, AsyncContextType)

    def test_list(self):
        async def _run():
            data = [{"id": "ct-1", "attributes": {"name": "user"}}]
            mock_coro = AsyncMock(return_value=_ok_json_resp({"data": data}))
            with patch("smplkit.management.client._gen_list_context_types.asyncio_detailed", mock_coro):
                client = _make_async_ct_client()
                result = await client.list()
                assert len(result) == 1

        asyncio.run(_run())

    def test_get(self):
        async def _run():
            parsed = _parsed_ct_resp()
            resp = _ok_resp()
            resp.parsed = parsed
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_get_context_type.asyncio_detailed", mock_coro):
                client = _make_async_ct_client()
                ct = await client.get("ct-1")
                assert isinstance(ct, AsyncContextType)

        asyncio.run(_run())

    def test_get_not_found(self):
        async def _run():
            resp = _ok_resp()
            resp.parsed = None
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_get_context_type.asyncio_detailed", mock_coro):
                client = _make_async_ct_client()
                with pytest.raises(SmplNotFoundError):
                    await client.get("nope")

        asyncio.run(_run())

    def test_delete(self):
        async def _run():
            mock_coro = AsyncMock(return_value=_ok_resp(204, b""))
            with patch("smplkit.management.client._gen_delete_context_type.asyncio_detailed", mock_coro):
                client = _make_async_ct_client()
                await client.delete("ct-1")

        asyncio.run(_run())

    def test_create(self):
        async def _run():
            parsed = _parsed_ct_resp()
            resp = _ok_resp(201)
            resp.parsed = parsed
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_create_context_type.asyncio_detailed", mock_coro):
                client = _make_async_ct_client()
                ct = AsyncContextType(name="user")
                result = await client._create(ct)
                assert result.id == "ct-1"

        asyncio.run(_run())

    def test_create_null_parsed_raises(self):
        async def _run():
            resp = _ok_resp(201)
            resp.parsed = None
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_create_context_type.asyncio_detailed", mock_coro):
                client = _make_async_ct_client()
                ct = AsyncContextType(name="user")
                with pytest.raises(SmplValidationError):
                    await client._create(ct)

        asyncio.run(_run())

    def test_update(self):
        async def _run():
            parsed = _parsed_ct_resp()
            resp = _ok_resp()
            resp.parsed = parsed
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_update_context_type.asyncio_detailed", mock_coro):
                client = _make_async_ct_client()
                ct = AsyncContextType(client, id="ct-1", name="user", created_at="2026-01-01")
                result = await client._update(ct)
                assert isinstance(result, AsyncContextType)

        asyncio.run(_run())

    def test_update_null_id_raises(self):
        async def _run():
            client = _make_async_ct_client()
            ct = AsyncContextType(client, name="user")
            ct.id = None
            with pytest.raises(ValueError, match="no id"):
                await client._update(ct)

        asyncio.run(_run())

    def test_update_null_parsed_raises(self):
        async def _run():
            resp = _ok_resp()
            resp.parsed = None
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_update_context_type.asyncio_detailed", mock_coro):
                client = _make_async_ct_client()
                ct = AsyncContextType(client, id="ct-1", name="user", created_at="2026-01-01")
                with pytest.raises(SmplValidationError):
                    await client._update(ct)

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# ContextsClient (sync)
# ---------------------------------------------------------------------------


class TestContextsClient:
    def test_register_queues_to_buffer(self):
        client = _make_contexts_client()
        client.register(Context("user", "u-1", plan="pro"))
        assert client._buffer.pending_count == 1

    def test_register_list(self):
        client = _make_contexts_client()
        client.register([Context("user", "u-1"), Context("account", "acme")])
        assert client._buffer.pending_count == 2

    @patch("smplkit.management.client._gen_bulk_register_contexts.sync_detailed")
    def test_register_with_flush(self, mock_bulk):
        mock_bulk.return_value = _ok_resp()
        client = _make_contexts_client()
        client.register(Context("user", "u-1"), flush=True)
        mock_bulk.assert_called_once()
        assert client._buffer.pending_count == 0

    @patch("smplkit.management.client._gen_bulk_register_contexts.sync_detailed")
    def test_flush_empty_does_nothing(self, mock_bulk):
        client = _make_contexts_client()
        client.flush()
        mock_bulk.assert_not_called()

    @patch("smplkit.management.client._gen_bulk_register_contexts.sync_detailed")
    def test_flush_sends_batch(self, mock_bulk):
        mock_bulk.return_value = _ok_resp()
        client = _make_contexts_client()
        client._buffer.observe([Context("user", "u-1", plan="pro")])
        client.flush()
        mock_bulk.assert_called_once()
        _, kwargs = mock_bulk.call_args
        assert kwargs["body"].contexts[0].type_ == "user"

    @patch("smplkit.management.client._gen_list_contexts.sync_detailed")
    def test_list(self, mock_list):
        data = [{"id": "user:u-1", "attributes": {"name": "Alice"}}]
        mock_list.return_value = _ok_json_resp({"data": data})
        client = _make_contexts_client()
        result = client.list("user")
        assert len(result) == 1
        assert result[0].type == "user"
        assert result[0].key == "u-1"

    @patch("smplkit.management.client._gen_get_context.sync_detailed")
    def test_get_composite_id(self, mock_get):
        parsed = _parsed_ctx_resp("user:u-1")
        resp = _ok_resp()
        resp.parsed = parsed
        mock_get.return_value = resp
        client = _make_contexts_client()
        entity = client.get("user:u-1")
        assert entity.type == "user"
        mock_get.assert_called_once_with("user:u-1", client=client._app_http)

    @patch("smplkit.management.client._gen_get_context.sync_detailed")
    def test_get_two_args(self, mock_get):
        parsed = _parsed_ctx_resp("user:u-1")
        resp = _ok_resp()
        resp.parsed = parsed
        mock_get.return_value = resp
        client = _make_contexts_client()
        entity = client.get("user", "u-1")
        assert entity.key == "u-1"

    @patch("smplkit.management.client._gen_get_context.sync_detailed")
    def test_get_not_found(self, mock_get):
        resp = _ok_resp()
        resp.parsed = None
        mock_get.return_value = resp
        client = _make_contexts_client()
        with pytest.raises(SmplNotFoundError):
            client.get("user:u-999")

    @patch("smplkit.management.client._gen_delete_context.sync_detailed")
    def test_delete_composite(self, mock_delete):
        mock_delete.return_value = _ok_resp(204, b"")
        client = _make_contexts_client()
        client.delete("user:u-1")
        mock_delete.assert_called_once_with("user:u-1", client=client._app_http)

    @patch("smplkit.management.client._gen_delete_context.sync_detailed")
    def test_delete_two_args(self, mock_delete):
        mock_delete.return_value = _ok_resp(204, b"")
        client = _make_contexts_client()
        client.delete("account", "acme")
        mock_delete.assert_called_once_with("account:acme", client=client._app_http)


# ---------------------------------------------------------------------------
# AsyncContextsClient
# ---------------------------------------------------------------------------


class TestAsyncContextsClient:
    def test_register_queues(self):
        async def _run():
            client = _make_async_contexts_client()
            await client.register(Context("user", "u-1"))
            assert client._buffer.pending_count == 1

        asyncio.run(_run())

    def test_register_list(self):
        async def _run():
            client = _make_async_contexts_client()
            await client.register([Context("user", "u-1"), Context("account", "acme")])
            assert client._buffer.pending_count == 2

        asyncio.run(_run())

    def test_register_with_flush(self):
        async def _run():
            mock_coro = AsyncMock(return_value=_ok_resp())
            with patch("smplkit.management.client._gen_bulk_register_contexts.asyncio_detailed", mock_coro):
                client = _make_async_contexts_client()
                await client.register(Context("user", "u-1"), flush=True)
                mock_coro.assert_called_once()

        asyncio.run(_run())

    def test_flush_empty_does_nothing(self):
        async def _run():
            mock_coro = AsyncMock(return_value=_ok_resp())
            with patch("smplkit.management.client._gen_bulk_register_contexts.asyncio_detailed", mock_coro):
                client = _make_async_contexts_client()
                await client.flush()
                mock_coro.assert_not_called()

        asyncio.run(_run())

    def test_flush_sends_batch(self):
        async def _run():
            mock_coro = AsyncMock(return_value=_ok_resp())
            with patch("smplkit.management.client._gen_bulk_register_contexts.asyncio_detailed", mock_coro):
                client = _make_async_contexts_client()
                client._buffer.observe([Context("user", "u-1")])
                await client.flush()
                mock_coro.assert_called_once()

        asyncio.run(_run())

    def test_list(self):
        async def _run():
            data = [{"id": "account:acme", "attributes": {}}]
            mock_coro = AsyncMock(return_value=_ok_json_resp({"data": data}))
            with patch("smplkit.management.client._gen_list_contexts.asyncio_detailed", mock_coro):
                client = _make_async_contexts_client()
                result = await client.list("account")
                assert isinstance(result[0], AsyncContextEntity)
                assert result[0].type == "account"

        asyncio.run(_run())

    def test_get_composite(self):
        async def _run():
            parsed = _parsed_ctx_resp("user:u-1")
            resp = _ok_resp()
            resp.parsed = parsed
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_get_context.asyncio_detailed", mock_coro):
                client = _make_async_contexts_client()
                entity = await client.get("user:u-1")
                assert isinstance(entity, AsyncContextEntity)
                assert entity.type == "user"

        asyncio.run(_run())

    def test_get_two_args(self):
        async def _run():
            parsed = _parsed_ctx_resp("user:u-1")
            resp = _ok_resp()
            resp.parsed = parsed
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_get_context.asyncio_detailed", mock_coro):
                client = _make_async_contexts_client()
                entity = await client.get("user", "u-1")
                assert entity.key == "u-1"

        asyncio.run(_run())

    def test_get_not_found(self):
        async def _run():
            resp = _ok_resp()
            resp.parsed = None
            mock_coro = AsyncMock(return_value=resp)
            with patch("smplkit.management.client._gen_get_context.asyncio_detailed", mock_coro):
                client = _make_async_contexts_client()
                with pytest.raises(SmplNotFoundError):
                    await client.get("user:nope")

        asyncio.run(_run())

    def test_delete_composite(self):
        async def _run():
            mock_coro = AsyncMock(return_value=_ok_resp(204, b""))
            with patch("smplkit.management.client._gen_delete_context.asyncio_detailed", mock_coro):
                client = _make_async_contexts_client()
                await client.delete("user:u-1")
                mock_coro.assert_called_once_with("user:u-1", client=client._app_http)

        asyncio.run(_run())

    def test_delete_two_args(self):
        async def _run():
            mock_coro = AsyncMock(return_value=_ok_resp(204, b""))
            with patch("smplkit.management.client._gen_delete_context.asyncio_detailed", mock_coro):
                client = _make_async_contexts_client()
                await client.delete("account", "acme")
                mock_coro.assert_called_once_with("account:acme", client=client._app_http)

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# AccountSettingsClient (sync)
# ---------------------------------------------------------------------------


class TestAccountSettingsClient:
    def _make_client(self):
        parent = MagicMock()
        return AccountSettingsClient(parent, "http://app:8000", "sk_test")

    def test_get(self):
        with patch("smplkit.management.client.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b'{"environment_order":["prod"]}'
            mock_resp.json.return_value = {"environment_order": ["prod"]}
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            client = self._make_client()
            settings = client.get()
            assert isinstance(settings, AccountSettings)
            assert settings.environment_order == ["prod"]

    def test_get_empty_response(self):
        with patch("smplkit.management.client.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"null"
            mock_resp.json.return_value = None
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            client = self._make_client()
            settings = client.get()
            assert settings._data == {}

    def test_save(self):
        with patch("smplkit.management.client.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b'{"environment_order":["prod","staging"]}'
            mock_resp.json.return_value = {"environment_order": ["prod", "staging"]}
            MockClient.return_value.__enter__.return_value.put.return_value = mock_resp
            client = self._make_client()
            result = client._save({"environment_order": ["prod", "staging"]})
            assert isinstance(result, AccountSettings)
            assert result.environment_order == ["prod", "staging"]

    def test_save_empty_response(self):
        with patch("smplkit.management.client.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"null"
            mock_resp.json.return_value = None
            MockClient.return_value.__enter__.return_value.put.return_value = mock_resp
            client = self._make_client()
            result = client._save({})
            assert result._data == {}


# ---------------------------------------------------------------------------
# AsyncAccountSettingsClient
# ---------------------------------------------------------------------------


class TestAsyncAccountSettingsClient:
    def _make_client(self):
        parent = MagicMock()
        return AsyncAccountSettingsClient(parent, "http://app:8000", "sk_test")

    def test_get(self):
        async def _run():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b'{"environment_order":["prod"]}'
            mock_resp.json.return_value = {"environment_order": ["prod"]}

            async_ctx = AsyncMock()
            async_ctx.__aenter__ = AsyncMock(return_value=async_ctx)
            async_ctx.__aexit__ = AsyncMock(return_value=False)
            async_ctx.get = AsyncMock(return_value=mock_resp)

            with patch("smplkit.management.client.httpx.AsyncClient", return_value=async_ctx):
                client = self._make_client()
                settings = await client.get()
                assert isinstance(settings, AsyncAccountSettings)
                assert settings.environment_order == ["prod"]

        asyncio.run(_run())

    def test_get_empty_response(self):
        async def _run():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"null"
            mock_resp.json.return_value = None

            async_ctx = AsyncMock()
            async_ctx.__aenter__ = AsyncMock(return_value=async_ctx)
            async_ctx.__aexit__ = AsyncMock(return_value=False)
            async_ctx.get = AsyncMock(return_value=mock_resp)

            with patch("smplkit.management.client.httpx.AsyncClient", return_value=async_ctx):
                client = self._make_client()
                settings = await client.get()
                assert settings._data == {}

        asyncio.run(_run())

    def test_save(self):
        async def _run():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b'{"environment_order":["prod","staging"]}'
            mock_resp.json.return_value = {"environment_order": ["prod", "staging"]}

            async_ctx = AsyncMock()
            async_ctx.__aenter__ = AsyncMock(return_value=async_ctx)
            async_ctx.__aexit__ = AsyncMock(return_value=False)
            async_ctx.put = AsyncMock(return_value=mock_resp)

            with patch("smplkit.management.client.httpx.AsyncClient", return_value=async_ctx):
                client = self._make_client()
                result = await client._save({"environment_order": ["prod", "staging"]})
                assert isinstance(result, AsyncAccountSettings)
                assert result.environment_order == ["prod", "staging"]

        asyncio.run(_run())

    def test_save_empty_response(self):
        async def _run():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"null"
            mock_resp.json.return_value = None

            async_ctx = AsyncMock()
            async_ctx.__aenter__ = AsyncMock(return_value=async_ctx)
            async_ctx.__aexit__ = AsyncMock(return_value=False)
            async_ctx.put = AsyncMock(return_value=mock_resp)

            with patch("smplkit.management.client.httpx.AsyncClient", return_value=async_ctx):
                client = self._make_client()
                result = await client._save({})
                assert result._data == {}

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# ManagementClient / AsyncManagementClient top-level
# ---------------------------------------------------------------------------


class TestManagementClient:
    def test_init_wires_sub_clients(self):
        with patch("smplkit.management.client._AppAuthClient"):
            parent = MagicMock()
            buf = _ContextRegistrationBuffer()
            mc = ManagementClient(parent, app_base_url="http://app:8000", api_key="sk_test", buffer=buf)
            assert isinstance(mc.environments, EnvironmentsClient)
            assert isinstance(mc.contexts, ContextsClient)
            assert isinstance(mc.context_types, ContextTypesClient)
            assert isinstance(mc.account_settings, AccountSettingsClient)
            assert mc.contexts._buffer is buf


class TestAsyncManagementClient:
    def test_init_wires_sub_clients(self):
        with patch("smplkit.management.client._AppAuthClient"):
            parent = MagicMock()
            buf = _ContextRegistrationBuffer()
            mc = AsyncManagementClient(parent, app_base_url="http://app:8000", api_key="sk_test", buffer=buf)
            assert isinstance(mc.environments, AsyncEnvironmentsClient)
            assert isinstance(mc.contexts, AsyncContextsClient)
            assert isinstance(mc.context_types, AsyncContextTypesClient)
            assert isinstance(mc.account_settings, AsyncAccountSettingsClient)
            assert mc.contexts._buffer is buf
