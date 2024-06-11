from pathlib import Path

import openai
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
from openai import OpenAI

load_dotenv(find_dotenv(), override=True)


def is_api_key_valid(api_key):
    client = OpenAI(api_key=api_key)
    try:
        response = client.completions.create(
            prompt="Hello", model="gpt-3.5-turbo-instruct", max_tokens=1
        )
        return True
    except openai.APIConnectionError as e:
        print("Failed to connect to OpenAI API: {e}")
        return False
    except openai.RateLimitError as e:
        print("OpenAI API rate limit exceeded: {e}")
        return False
    except openai.APIError as e:
        print("OpenAI API error: {e}")
        return False


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


def embed_documents_and_save(embed_docs, db_dir="", db_name="faiss_index"):
    db_path = Path(db_dir)
    if not db_path.exists():
        db_path.mkdir(parents=True, exist_ok=True)

    db_file_path = db_path / db_name

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    if db_file_path.exists():
        db = FAISS.load_local(db_file_path, embeddings, allow_dangerous_deserialization=True)
        db.add_documents(embed_docs)
    else:
        db = FAISS.from_documents(embed_docs, embeddings)

    db.save_local(db_file_path)
    return db


def load_vector_store(db_path):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    db_path = Path(db_path)

    db = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
    return db


def conversation_chain(vector_store):
    prompt = ChatPromptTemplate.from_messages(
        (
            "human",
            (
                "You are an assistant specifically designed for answering questions about "
                "the OWASP Bug Logging Tool (BLT) application. Use the following pieces of "
                "retrieved context to answer the question. If the user's question is not "
                "related to the BLT application or if the context does not provide enough "
                "information to answer the question, respond with 'Please ask a query related "
                "to the BLT Application.' Ensure your response is concise and does not exceed "
                "three sentences.\nQuestion: {question}\nContext: {context}\nAnswer:"
            ),
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
