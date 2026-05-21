from langchain_community.document_loaders import DirectoryLoader, TextLoader

from app.config import KNOWLEDGE_DIR


def load_documents():
    loader = DirectoryLoader(
        str(KNOWLEDGE_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )

    return loader.load()
