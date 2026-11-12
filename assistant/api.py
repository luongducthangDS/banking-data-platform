"""uvicorn assistant.api:app --port 8003"""
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from assistant.llm import Gemini
from assistant.text2sql import ask

app = FastAPI(title="Banking AI Analytics Assistant")


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@lru_cache
def llm() -> Gemini:
    return Gemini()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask_endpoint(q: Question):
    try:
        res = ask(q.question, llm())
    except RuntimeError as e:  # LLM unavailable (no key / quota)
        raise HTTPException(503, str(e))
    if res["status"] == "blocked":
        raise HTTPException(400, res["answer"])
    return res
