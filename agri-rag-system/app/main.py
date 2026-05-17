from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="农业知识库问答系统",
    version="1.0.0"
)

app.include_router(router)