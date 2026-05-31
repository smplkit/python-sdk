from typing import Literal

InvitationResourceType = Literal["invitation"]

INVITATION_RESOURCE_TYPE_VALUES: set[InvitationResourceType] = {
    "invitation",
}


def check_invitation_resource_type(value: str) -> InvitationResourceType:
    if value in INVITATION_RESOURCE_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {INVITATION_RESOURCE_TYPE_VALUES!r}")
