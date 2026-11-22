
"""Trusted demo-user registry for local development.

These identities are for testing only, not production authentication.
"""

DEMO_USERS = {
    "adv.rao": {
        "role": "corporate_counsel",
        "matters": ["MTR-017"],
    },
    "gc.sharma": {
        "role": "general_counsel",
        "matters": ["*"],
    },
}


def get_demo_user(username: str) -> dict | None:
    """Look up a demo user's server-defined permissions."""

    user = DEMO_USERS.get(username)

    if user is None:
        return None

    return {
        "role": user["role"],
        "matters": list(user["matters"]),
    }
