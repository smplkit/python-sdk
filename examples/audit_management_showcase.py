"""
Demonstrates the smplkit management SDK for Smpl Audit.

Prerequisites:
    - ``pip install smplkit-sdk``
    - A valid smplkit API key, provided via one of:
        - ``SMPLKIT_API_KEY`` environment variable
        - ``~/.smplkit`` configuration file (see SDK docs)

Usage::

    python examples/audit_management_showcase.py
"""

import uuid

from smplkit import SmplManagementClient
from smplkit.audit import ForwarderHttp, ForwarderType, HttpHeader


# JSON Logic filter — only forward ``invoice.*`` actions.
# Events that don't match are recorded as ``filtered_out`` deliveries.
# See https://jsonlogic.com for the full operator reference.
INVOICE_FILTER = {"in": ["invoice.", {"var": "action"}]}

# JSONata template — reshape the event payload before POSTing to the
# destination. This example flattens the event into a compact SIEM-style
# record. See https://jsonata.org for the full language reference.
SIEM_TRANSFORM = """
{
    "event": action,
    "subject": resource_type & ":" & resource_id,
    "ts": occurred_at,
    "actor": actor_label
}
"""


def main() -> None:

    # create the client (use AsyncSmplManagementClient for asynchronous use)
    with SmplManagementClient() as manage:
        forwarder_name = f"showcase-{uuid.uuid4().hex[:6]}"

        # create a forwarder
        forwarder = manage.audit.forwarders.create(
            name=forwarder_name,
            forwarder_type=ForwarderType.HTTP,
            http=ForwarderHttp(
                method="POST",
                url="https://httpbin.org/post",
                headers=[HttpHeader(name="X-Showcase", value="ok")],
                success_status="2xx",
            ),
            filter=INVOICE_FILTER,
            transform=SIEM_TRANSFORM,
        )
        assert forwarder.name == forwarder_name
        assert forwarder.enabled is True
        assert forwarder.filter == INVOICE_FILTER
        assert forwarder.transform == SIEM_TRANSFORM
        print(f"Created forwarder: {forwarder.slug}")

        # fetch a forwarder
        fetched = manage.audit.forwarders.get(forwarder.id)
        assert fetched.id == forwarder.id
        assert fetched.name == forwarder_name
        assert fetched.filter == INVOICE_FILTER
        assert fetched.transform == SIEM_TRANSFORM
        print(f"Fetched forwarder: {fetched.name}")

        # list forwarders
        listed = manage.audit.forwarders.list()
        assert forwarder.id in {f.id for f in listed.forwarders}
        print(f"Account has {len(listed.forwarders)} forwarder(s)")

        # update a forwarder
        renamed = f"{forwarder.name}-renamed"
        updated = manage.audit.forwarders.update(
            forwarder.id,
            name=renamed,
            forwarder_type=forwarder.forwarder_type,
            http=ForwarderHttp(
                method="POST",
                url="https://httpbin.org/post",
                headers=[HttpHeader(name="X-Showcase", value="ok")],
                success_status="2xx",
            ),
            enabled=False,
            filter=INVOICE_FILTER,
            transform=SIEM_TRANSFORM,
        )
        assert updated.name == renamed
        assert updated.enabled is False
        print(f"Updated forwarder: {updated.name} (enabled={updated.enabled})")

        # delete a forwarder
        manage.audit.forwarders.delete(forwarder.id)
        remaining = manage.audit.forwarders.list()
        assert forwarder.id not in {f.id for f in remaining.forwarders}
        print(f"Deleted forwarder: {forwarder.slug}")

        print("Done!")


if __name__ == "__main__":
    main()
