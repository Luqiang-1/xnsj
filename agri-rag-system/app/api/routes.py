from fastapi import APIRouter
from pydantic import BaseModel
from app.llm.ollama_client import ask_ollama

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

@router.get("/")
def home():
    return {
        "message": "农业知识库问答系统启动成功"
    }

@router.post("/chat")
def chat(req: ChatRequest):

    question = req.question

    answer = ask_ollama(question)

    return {
        "question": question,
        "answer": answer
    }