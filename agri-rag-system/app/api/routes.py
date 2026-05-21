import shutil

from fastapi import APIRouter, File, UploadFile

from app.config import KNOWLEDGE_DIR
from app.llm.ollama_client import ask_ollama
from app.models.chat_model import ChatRequest
from app.rag.qa_chain import search_knowledge

router = APIRouter()


@router.get("/")
def home():
    return {"message": "农业知识库问答系统启动成功"}


@router.post("/chat")
def chat(request: ChatRequest):
    question = request.question
    knowledge = search_knowledge(question)

    prompt = f"""
你是一名农业专家。
请基于下面知识库内容回答问题。

【知识库】
{knowledge}

【用户问题】
{question}

请给出准确、专业、简洁的回答。
"""

    answer = ask_ollama(prompt)

    return {
        "question": question,
        "knowledge": knowledge,
        "answer": answer,
    }


@router.get("/health")
def health():
    return {
        "status": "ok",
        "message": "Agri RAG System Running",
    }


@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    save_path = KNOWLEDGE_DIR / file.filename

    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message": "文件上传成功",
        "filename": file.filename,
    }
