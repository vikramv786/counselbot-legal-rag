
"""JWT token creation and verification for CounselBot."""

import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv

load_dotenv()


def get_jwt_secret() -> str:
    """Read the JWT signing secret from the environment."""

    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY is missing from the environment."
        )

    return secret


def create_access_token(username: str) -> str:
    """Create a signed token for an authenticated user."""

    now = datetime.now(timezone.utc)

    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(hours=8),
    }

    return jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm="HS256",
    )


def verify_access_token(token: str) -> str | None:
    """Return the authenticated username, or None for invalid tokens."""

    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )

        username = payload.get("sub")

        if not isinstance(username, str) or not username:
            return None

        return username

    except jwt.InvalidTokenError:
        return None


def authenticate_demo_user(
    username: str,
    password: str,
) -> bool:
    """Verify credentials for a fictional demo account."""

    import hmac

    from counselbot_legal_rag.demo_users import get_demo_user

    expected_password = os.getenv("DEMO_PASSWORD", "demo@123")

    user = get_demo_user(username)

    return (
        user is not None
        and hmac.compare_digest(password, expected_password)
    )
