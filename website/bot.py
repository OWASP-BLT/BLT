from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationSummaryMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    DirectoryLoader,
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv(find_dotenv(), override=True)


def load_document(file_path):
    loaders = {
        ".pdf": PyPDFLoader,
        ".docx": Docx2txtLoader,
        ".txt": TextLoader,
        ".md": UnstructuredMarkdownLoader,
    }

    file_path = Path(file_path)
    extension = file_path.suffix
    Loader = loaders.get(extension)

    if Loader is None:
        raise ValueError(f"Unsupported file format: {extension}")

    return Loader(file_path).load()


def load_directory(dir_path):
    return DirectoryLoader(dir_path).load()


def split_document(chunk_size, chunk_overlap, document):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return text_splitter.split_documents(document)


def embed_documents_and_save(embedDocs, db_dir="", db_name="faiss_index"):
    db_path = Path(db_dir)
    if not db_path.exists():
        db_path.mkdir(parents=True, exist_ok=True)

    db_file_path = db_path / db_name

    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        if db_file_path.exists():
            db = FAISS.load_local(db_file_path, embeddings, allow_dangerous_deserialization=True)
            db.add_documents(embedDocs)
        else:
            db = FAISS.from_documents(embedDocs, embeddings)

        db.save_local(db_file_path)
        return db
    except Exception as e:
        return "Bot is down due to API issues."


def load_vector_store(db_path):
    try:
        print("Loading vector store...")
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        db_path = Path(db_path)

        if not db_path.exists():
            raise FileNotFoundError(f"FAISS index directory does not exist: {db_path}")

        db = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
        return db
    except Exception as e:
        return "Bot is down due to API issues."


def conversation_chain(vector_store):
    prompt = ChatPromptTemplate.from_messages(
        (
            "human",
            "You are an OWASP BLT assistant. Use the given context to answer the question.If the question isn't related to BLT or lacks enough context, reply with 'Please ask a query related to the BLT Application.' Keep responses concise, max three sentences.\nQuestion: {question}\nContext: {context}\nAnswer:",
        )
    )
    llm = ChatOpenAI(model_name="gpt-3.5-turbo-0125", temperature=0.5)
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})
    memory = ConversationSummaryMemory(
        llm=llm, return_messages=True, memory_key="chat_history", max_token_limit=1000
    )

    crc = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        chain_type="stuff",
        combine_docs_chain_kwargs={"prompt": prompt},
    )
    return crc, memory
