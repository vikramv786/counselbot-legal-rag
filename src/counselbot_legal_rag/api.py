
"""Authenticated FastAPI endpoints for CounselBot Legal RAG."""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from counselbot_legal_rag.auth import (
    authenticate_demo_user,
    create_access_token,
    verify_access_token,
)
from counselbot_legal_rag.demo_users import get_demo_user
from counselbot_legal_rag.rag_pipeline import answer_legal_question
from counselbot_legal_rag.retrieval import ROLE_COLLECTIONS


app = FastAPI(
    title="CounselBot Legal RAG",
    description="AI-powered legal assistant for Veridian Legal Hub",
    version="0.1.0",
)


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.get("/health")
def health_check():
    """Return the API's health status."""
    return {
        "status": "ok",
        "service": "CounselBot Legal RAG",
    }


# ---------------------------------------------------------
# Login and JWT authentication
# ---------------------------------------------------------

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """Authenticate a demo user and issue a signed JWT."""

    if not authenticate_demo_user(
        request.username,
        request.password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token = create_access_token(request.username)

    return LoginResponse(access_token=token)


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict:
    """Resolve trusted permissions from a valid Bearer token."""

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    username = verify_access_token(credentials.credentials)

    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user = get_demo_user(username)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return {
        "username": username,
        "role": user["role"],
        "matters": user["matters"],
    }


# ---------------------------------------------------------
# Authenticated user information
# ---------------------------------------------------------

@app.get("/me")
def read_current_user(
    user: dict = Depends(get_current_user),
):
    """Return only the authenticated user's permissions."""

    return {
        "username": user["username"],
        "role": user["role"],
        "matters": user["matters"],
        "collections": ROLE_COLLECTIONS[user["role"]],
    }


# ---------------------------------------------------------
# Authenticated collection access
# ---------------------------------------------------------

@app.get("/collections/{role}")
def read_role_collections(
    role: str,
    user: dict = Depends(get_current_user),
):
    """Return collections only for the authenticated user's role."""

    if role not in ROLE_COLLECTIONS:
        raise HTTPException(
            status_code=404,
            detail="Unknown role",
        )

    if role != user["role"]:
        raise HTTPException(
            status_code=403,
            detail="Role access denied",
        )

    return {
        "role": role,
        "collections": ROLE_COLLECTIONS[role],
    }


# ---------------------------------------------------------
# Authenticated chat
# ---------------------------------------------------------

class SecureChatRequest(BaseModel):
    """Accept only a question; permissions come from the JWT."""

    model_config = {"extra": "forbid"}

    question: str = Field(
        min_length=1,
        max_length=4000,
        pattern=r"(?s).*\S.*",
    )


@app.post("/chat")
def authenticated_chat(
    request: SecureChatRequest,
    user: dict = Depends(get_current_user),
):
    """Answer using the authenticated user's server-defined permissions."""

    result = answer_legal_question(
        query=request.question,
        user={
            "role": user["role"],
            "matters": user["matters"],
        },
        return_metadata=True,
    )

    return {
        **result,
        "role": user["role"],
    }
