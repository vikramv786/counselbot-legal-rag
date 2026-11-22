
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from counselbot_legal_rag.demo_users import get_demo_user
from counselbot_legal_rag.rag_pipeline import answer_legal_question


app = FastAPI(
    title="CounselBot Legal RAG",
    description="AI-powered legal assistant for Veridian Legal Hub",
    version="0.1.0",
)



class ChatRequest(BaseModel):
    """Request body for the local-demo chat endpoint."""

    username: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^\S+$",
    )

    question: str = Field(
        min_length=1,
        max_length=4000,
        pattern=r"(?s).*\S.*",
    )



class ChatResponse(BaseModel):
    """Response returned by the chat endpoint."""

    username: str
    answer: str


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "CounselBot Legal RAG",
    }


@app.get("/demo-users/{username}")
def read_demo_user(username: str):
    """Look up a demo user's server-defined permissions."""

    user = get_demo_user(username)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Demo user not found",
        )

    return {
        "username": username,
        "role": user["role"],
        "matters": user["matters"],
    }


@app.post("/demo/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Answer a question using a server-defined demo user's access."""

    user = get_demo_user(request.username)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Demo user not found",
        )

    answer = answer_legal_question(
        query=request.question,
        user=user,
    )

    return ChatResponse(
        username=request.username,
        answer=answer,
    )
