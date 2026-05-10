"""
Demonstrates the smplkit MANAGEMENT SDK for Smpl Audit.

The management client owns every audit-service operation that isn't
fire-and-forget event recording: querying the audit log, listing the
distinct ``resource_type`` and ``action`` values seen for the account
(used to populate the Activity tab filter dropdowns), CRUD on SIEM
forwarders plus the delivery log, the ``test_forwarder`` proxy used by
the console's preview button, and the destructive account-wide
``wipe`` action.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)
    - Pro tier required for the forwarders portion. The showcase
      gracefully skips forwarders on a 402 (free / standard tier) so it
      remains runnable in any environment.
    - ``SHOWCASE_RUN_WIPE=yes`` in the environment to actually run the
      wipe action at the end. Wipe is account-wide and irreversible —
      the showcase only demonstrates the syntax by default.

Usage::

    python examples/audit_management_showcase.py
    SHOWCASE_RUN_WIPE=yes python examples/audit_management_showcase.py
"""

import os
import uuid

from smplkit import SmplClient
from smplkit._generated.audit.errors import UnexpectedStatus
from smplkit.audit import ForwarderHttp, ForwarderType, HttpHeader


def main() -> None:
    # SmplClient exposes a ``manage`` attribute that resolves to the same
    # SmplManagementClient an admin tool would construct directly. Pick
    # whichever entry point is more convenient for the calling code.
    with SmplClient(
        environment="production", service="showcase-service"
    ) as client:
        mgmt = client.manage

        # --------------------------------------------------------------
        # Seed the side tables: the management surface reads from them,
        # but they're maintained by the runtime client's events.record.
        # Use ``flush=True`` so the side tables reflect the new tuples
        # before we query.
        # --------------------------------------------------------------
        invoice_id = f"inv-{uuid.uuid4().hex[:8]}"
        client.audit.events.record(
            action="invoice.created",
            resource_type="invoice",
            resource_id=invoice_id,
            data={"snapshot": {"total_cents": 4900}},
            flush=True,
        )
        client.audit.events.record(
            action="invoice.paid",
            resource_type="invoice",
            resource_id=invoice_id,
            data={"snapshot": {"status": "paid"}},
            flush=True,
        )

        # --------------------------------------------------------------
        # Read the audit log — events.list / events.get under management.
        # --------------------------------------------------------------
        page = mgmt.audit.events.list(
            resource_type="invoice", resource_id=invoice_id, page_size=10
        )
        print(f"Found {len(page.events)} events for {invoice_id}:")
        for event in page.events:
            print(f"  {event.action}  id={event.id}  actor={event.actor_type}")

        first = mgmt.audit.events.get(page.events[0].id)
        print(f"Round-tripped: {first.action} at {first.occurred_at}")

        # --------------------------------------------------------------
        # Distinct-value listings — back the Activity tab dropdowns.
        # ``id`` on each row IS the slug (ADR-014 "key as id"); the
        # echoed attribute (``resource_type`` / ``action``) is provided
        # for ergonomic access without parsing the id.
        # --------------------------------------------------------------
        rt_page = mgmt.audit.resource_types.list(page_size=10)
        print(f"Distinct resource_types ({len(rt_page)}):")
        for rt in rt_page:
            print(f"  {rt.id}  first_seen={rt.created_at.date()}")

        # Without a filter, an action recorded under multiple
        # resource_types appears once — the API collapses it server-side.
        action_page = mgmt.audit.actions.list(page_size=10)
        print(f"Distinct actions ({len(action_page)}):")
        for a in action_page:
            print(f"  {a.id}")

        # With ``filter_resource_type``, narrows to actions seen with
        # that specific resource type — the cascading-filter behavior.
        invoice_actions = mgmt.audit.actions.list(
            filter_resource_type="invoice"
        )
        print(f"Actions for resource_type=invoice ({len(invoice_actions)}):")
        for a in invoice_actions:
            print(f"  {a.id}")

        # --------------------------------------------------------------
        # Forwarders (Pro tier — gracefully skip on 402).
        # ``ForwarderType`` is a string-valued Enum: members type-check
        # like normal enum values AND compare equal to the underlying
        # string (``ForwarderType.HTTP == "http"``), so passing literal
        # strings still works for callers who prefer that style.
        # --------------------------------------------------------------
        print(
            "Supported forwarder types: "
            + ", ".join(t.value for t in ForwarderType)
        )

        try:
            fwd = mgmt.audit.forwarders.create(
                name=f"showcase-{uuid.uuid4().hex[:6]}",
                forwarder_type=ForwarderType.HTTP,
                http=ForwarderHttp(
                    method="POST",
                    url="https://httpbin.org/post",
                    headers=[HttpHeader(name="X-Showcase", value="ok")],
                    success_status="2xx",
                ),
            )
        except UnexpectedStatus as exc:
            if exc.status_code == 402:
                print("Skipping forwarder showcase — account is not Pro tier")
                _maybe_run_wipe(mgmt)
                print("Done!")
                return
            raise

        print(f"Created forwarder: {fwd.slug}")
        try:
            # Test the destination via the proxy. The console uses this
            # to power the "try it out" button without browser CORS
            # blocking the request.
            test = mgmt.audit.functions.test_forwarder.actions.execute(
                url="https://httpbin.org/post",
                body='{"hello":"world"}',
                success_status="2xx",
                timeout_ms=5000,
            )
            print(
                f"test_forwarder: succeeded={test.succeeded} status={test.response_status}"
            )

            # ``do_not_forward=True`` records the event normally but
            # suppresses the SIEM fan-out. The skip is recorded in the
            # delivery log so it's still visible to operators.
            client.audit.events.record(
                action="invoice.created",
                resource_type="invoice",
                resource_id=f"{invoice_id}-skipped",
                do_not_forward=True,
                flush=True,
            )

            listed = mgmt.audit.forwarders.list(page_size=5)
            print(f"Account has {len(listed.forwarders)} active forwarders")
        finally:
            mgmt.audit.forwarders.delete(fwd.id)
            print(f"Deleted forwarder: {fwd.slug}")

        _maybe_run_wipe(mgmt)
        print("Done!")


def _maybe_run_wipe(mgmt) -> None:
    """Wipe is destructive and irreversible — gated on an explicit env var.

    Customers wiring the same call into their own integrations should
    pair it with explicit consent in the calling UI (a confirmation
    dialog, an admin-only CLI flag, etc.).
    """
    if os.environ.get("SHOWCASE_RUN_WIPE") != "yes":
        print(
            "Skipping wipe — set SHOWCASE_RUN_WIPE=yes to actually "
            "delete this account's audit data"
        )
        return
    wipe = mgmt.audit.functions.wipe.actions.execute()
    print(
        f"Wiped {wipe.total_rows_deleted} rows "
        f"(events={wipe.audit_event}, "
        f"resource_types={wipe.resource_type}, "
        f"actions={wipe.action})"
    )


if __name__ == "__main__":
    main()
