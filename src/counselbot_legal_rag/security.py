
def can_access_document(user: dict, document: dict) -> bool:
    """Check both role permissions and matter assignments."""

    role_allowed = user["role"] in document["access_roles"]

    matter_id = document["matter_id"]
    user_matters = user["matters"]

    matter_allowed = (
        matter_id == "NONE"
        or "*" in user_matters
        or matter_id in user_matters
    )

    return role_allowed and matter_allowed
