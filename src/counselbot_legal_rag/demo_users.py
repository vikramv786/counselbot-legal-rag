
"""Server-side demo-user registry for CounselBot.

Contains fictional user roles and matter assignments.
Authentication will be handled separately.
"""

DEMO_USERS = {
    "gc.sharma": {
        "role": "general_counsel",
        "matters": ["*"],
    },
    "adv.rao": {
        "role": "corporate_counsel",
        "matters": ["MTR-017"],
    },
    "adv.nair": {
        "role": "corporate_counsel",
        "matters": ["MTR-031"],
    },
    "adv.khan": {
        "role": "litigation_counsel",
        "matters": ["MTR-031", "MTR-044"],
    },
    "adv.iyer": {
        "role": "litigation_counsel",
        "matters": ["MTR-044"],
    },
    "comp.deshpande": {
        "role": "compliance_officer",
        "matters": ["MTR-023"],
    },
    "comp.bose": {
        "role": "compliance_officer",
        "matters": [],
    },
    "para.sneha": {
        "role": "paralegal",
        "matters": ["MTR-017"],
    },
}


def get_demo_user(username: str) -> dict | None:
    """Return server-defined permissions for a demo user."""

    user = DEMO_USERS.get(username)

    if user is None:
        return None

    return {
        "role": user["role"],
        "matters": list(user["matters"]),
    }
