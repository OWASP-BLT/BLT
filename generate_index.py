import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()


def generate_index():
    # Files to index
    docs_to_index = []

    # 1. Load README.md
    if os.path.exists("README.md"):
        loader = TextLoader("README.md", encoding="utf-8")
        docs_to_index.extend(loader.load())

    # 2. Load documents from docs/ directory
    if os.path.isdir("docs"):
        loader = DirectoryLoader("docs", glob="**/*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
        docs_to_index.extend(loader.load())

    if not docs_to_index:
        return

    # 3. Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len,
    )
    chunks = text_splitter.split_documents(docs_to_index)

    # 4. Create and save FAISS index
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.from_documents(chunks, embeddings)

    db_folder = Path("faiss_index")
    db.save_local(db_folder)


if __name__ == "__main__":
    generate_index()
