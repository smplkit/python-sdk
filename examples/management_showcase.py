"""
Smpl SDK Showcase — Management API
====================================

Demonstrates ``client.management.*`` — the management plane for
app-service-owned resources that aren't tied to a specific
microservice: environments, contexts, context types, and per-account
settings.

Just as ``client.config.management``, ``client.flags.management``,
and ``client.logging.management`` cover the per-microservice
management surfaces, ``client.management`` is the catch-all for the
app/control-plane.

For runtime experiences (resolving configs, evaluating flags,
controlling log levels) see the per-service runtime showcases.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key
    - The smplkit app service running and reachable

Usage::

    python examples/management_showcase.py
"""

import asyncio

from smplkit import AsyncSmplClient, Context, EnvironmentClassification


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}\n")


def step(description: str) -> None:
    print(f"  → {description}")


async def main() -> None:

    # ======================================================================
    # 1. SDK INITIALIZATION
    # ======================================================================
    section("1. SDK Initialization")

    async with AsyncSmplClient(
        environment="production",
        service="management-showcase",
    ) as client:
        step("AsyncSmplClient initialized")

        # Best-effort cleanup of leftovers from previous runs.
        for env_id in ("preview_acme",):
            try:
                await client.management.environments.delete(env_id)
            except Exception:
                pass
        for ct_id in ("user", "account", "device"):
            try:
                await client.management.context_types.delete(ct_id)
            except Exception:
                pass

        # ==================================================================
        # 2. ENVIRONMENTS — client.management.environments
        # ==================================================================
        # Active record: new() / save() / get(id) / list() / delete(id).
        # Built-ins (production/staging/development) ship STANDARD;
        # add AD_HOC for transient targets like preview branches.
        # ==================================================================

        section("2a. List built-in environments")

        for e in await client.management.environments.list():
            step(f"id={e.id!r} name={e.name!r} classification={e.classification.value!r}")

        section("2b. Create an AD_HOC environment")

        preview = client.management.environments.new(
            "preview_acme",
            name="Preview Acme branch",
            color="#8b5cf6",
            classification=EnvironmentClassification.AD_HOC,
        )
        await preview.save()
        step(f"Created: id={preview.id!r}")

        section("2c. Update an environment in place")

        prod = await client.management.environments.get("production")
        prod.color = "#ef4444"
        await prod.save()
        step(f"Updated: id={prod.id!r} color={prod.color!r}")

        # ==================================================================
        # 3. CONTEXT TYPES — client.management.context_types
        # ==================================================================
        # Targeting-rule entity schemas. Registering a Context against
        # an unknown type lazily creates one with default metadata;
        # use this namespace when you want polished display names and
        # an explicit known-attribute schema.
        #
        # Mutate attributes via add_attribute / remove_attribute /
        # update_attribute — never by reassigning the dict — so the
        # diff against the server stays clean.
        # ==================================================================

        section("3a. Create context types")

        user_ct = client.management.context_types.new("user", name="User")
        user_ct.add_attribute("plan")
        user_ct.add_attribute("region")
        user_ct.add_attribute("beta_tester")
        user_ct.add_attribute("signup_date")
        user_ct.add_attribute("account_age_days")
        await user_ct.save()
        step(f"user: attributes={list(user_ct.attributes)}")

        account_ct = client.management.context_types.new("account", name="Account")
        for attr in ("tier", "industry", "region", "employee_count", "annual_revenue"):
            account_ct.add_attribute(attr)
        await account_ct.save()

        device_ct = client.management.context_types.new("device", name="Device")
        for attr in ("os", "version", "type"):
            device_ct.add_attribute(attr)
        await device_ct.save()
        step("account, device created")

        section("3b. List + mutate an existing context type")

        for t in await client.management.context_types.list():
            step(f"id={t.id!r} name={t.name!r}")

        existing = await client.management.context_types.get("user")
        existing.add_attribute("lifetime_value")
        existing.remove_attribute("account_age_days")
        await existing.save()
        step(f"user attributes now: {list(existing.attributes)}")

        # ==================================================================
        # 4. CONTEXTS — client.management.contexts
        # ==================================================================
        # Write side: register(items, flush=False). Flush=False (default)
        # buffers for background flush — right for high-frequency runtime
        # observation. flush=True awaits the round-trip — right for IaC
        # scripts that need confirmation.
        #
        # Read side: list(type), get(id), delete(id). ``id`` is the
        # colon-delimited "{type}:{key}" form; a (type, key) overload is
        # accepted everywhere ``id`` appears for ergonomics.
        # ==================================================================

        section("4a. Register contexts (immediate flush)")

        await client.management.contexts.register(
            [
                Context("user", "usr_a1b2c3", {"plan": "free", "region": "us"}),
                Context("user", "usr_d4e5f6", {"plan": "enterprise", "region": "eu"}),
                Context("account", "acct_acme_inc", {"tier": "enterprise", "industry": "retail"}),
            ],
            flush=True,
        )
        step("3 contexts registered + flushed")

        section("4b. List contexts of a single type")

        for c in await client.management.contexts.list("user"):
            step(f"  type={c.type!r} key={c.key!r} attributes={c.attributes}")

        section("4c. Get + delete by composite id (or by (type, key))")

        one = await client.management.contexts.get("user:usr_a1b2c3")
        step(f"got: {one.type}:{one.key}")

        same = await client.management.contexts.get("user", "usr_a1b2c3")
        step(f"got via (type, key): {same.type}:{same.key}")

        await client.management.contexts.delete("user:usr_a1b2c3")
        step("deleted user:usr_a1b2c3")

        # ==================================================================
        # 5. ACCOUNT SETTINGS — client.management.account_settings
        # ==================================================================
        # Wire format is opaque JSON; the SDK exposes a typed
        # AccountSettings model with active record semantics.
        # Documented keys (e.g. environment_order) are typed
        # properties; unknown keys are preserved through .raw.
        # ==================================================================

        section("5a. Read settings")

        settings = await client.management.account_settings.get()
        step(f"environment_order={settings.environment_order}")
        step(f"raw={settings.raw}")

        section("5b. Mutate + save (active record)")

        settings.environment_order = ["production", "staging", "development"]
        await settings.save()
        step(f"saved: environment_order={settings.environment_order}")

        # ==================================================================
        # 6. CLEANUP
        # ==================================================================
        section("6. Cleanup")

        for c in await client.management.contexts.list("user"):
            await client.management.contexts.delete(c.type, c.key)
        for c in await client.management.contexts.list("account"):
            await client.management.contexts.delete(c.type, c.key)

        for ct_id in ("user", "account", "device"):
            try:
                await client.management.context_types.delete(ct_id)
            except Exception:
                pass

        try:
            await client.management.environments.delete("preview_acme")
        except Exception:
            pass

        section("Showcase complete")


if __name__ == "__main__":
    asyncio.run(main())
