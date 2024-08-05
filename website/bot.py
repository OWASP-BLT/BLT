import tempfile
from pathlib import Path

import openai
from django.core.files.storage import default_storage
from dotenv import find_dotenv, load_dotenv
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationSummaryMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
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
        client.completions.create(prompt="Hello", model="gpt-3.5-turbo-instruct", max_tokens=1)
        return True
    except openai.APIConnectionError as e:
        print(f"Failed to connect to OpenAI API: {e}")
    except openai.RateLimitError as e:
        print(f"OpenAI API rate limit exceeded: {e}")
    except openai.APIError as e:
        print(f"OpenAI API error: {e}")
    return False


def load_document(file_path):
    loaders = {
        ".pdf": PyPDFLoader,
        ".docx": Docx2txtLoader,
        ".txt": TextLoader,
        ".md": UnstructuredMarkdownLoader,
    }

    extension = Path(file_path).suffix
    Loader = loaders.get(extension)

    if Loader is None:
        raise ValueError(f"Unsupported file format: {extension}")

    with default_storage.open(file_path) as f:
        return Loader(f).load()


def load_directory(dir_path):
    files = default_storage.listdir(dir_path)[1]
    documents = []
    for file_name in files:
        file_path = Path(dir_path) / file_name
        documents.extend(load_document(file_path))
    return documents


def split_document(chunk_size, chunk_overlap, document):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return text_splitter.split_documents(document)


def embed_documents_and_save(embed_docs):
    db_folder_path = "faiss_index"

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    with tempfile.TemporaryDirectory() as tmpdir:
        index_faiss_path = Path(tmpdir) / "index.faiss"
        index_pkl_path = Path(tmpdir) / "index.pkl"

        # Download index.faiss and index.pkl to local temporary directory
        with default_storage.open(f"{db_folder_path}/index.faiss", "rb") as fsrc, open(
            index_faiss_path, "wb"
        ) as fdst:
            fdst.write(fsrc.read())

        with default_storage.open(f"{db_folder_path}/index.pkl", "rb") as fsrc, open(
            index_pkl_path, "wb"
        ) as fdst:
            fdst.write(fsrc.read())

        # Ensure that the paths exist and are files
        assert index_faiss_path.is_file(), f"{index_faiss_path} is not a valid file."
        assert index_pkl_path.is_file(), f"{index_pkl_path} is not a valid file."

        # Load the FAISS index from the local temporary directory
        db = FAISS.load_local(
            str(index_faiss_path),
            str(index_pkl_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )

        # Add new documents to the index
        db.add_documents(embed_docs)

        # Save the updated FAISS index back to the cloud storage
        db.save_local(str(tmpdir))

        # Upload the updated files back to Google Cloud Storage
        with open(index_faiss_path, "rb") as fsrc:
            default_storage.save(f"{db_folder_path}/index.faiss", fsrc)

        with open(index_pkl_path, "rb") as fsrc:
            default_storage.save(f"{db_folder_path}/index.pkl", fsrc)

    return db


def load_vector_store():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    db_folder_path = "faiss_index"

    with tempfile.TemporaryDirectory() as tmpdir:
        index_faiss_path = Path(tmpdir) / "index.faiss"
        index_pkl_path = Path(tmpdir) / "index.pkl"

        # Download index.faiss and index.pkl to local temporary directory
        with default_storage.open(f"{db_folder_path}/index.faiss", "rb") as fsrc, open(
            index_faiss_path, "wb"
        ) as fdst:
            fdst.write(fsrc.read())

        with default_storage.open(f"{db_folder_path}/index.pkl", "rb") as fsrc, open(
            index_pkl_path, "wb"
        ) as fdst:
            fdst.write(fsrc.read())

        # Ensure that the paths exist and are files
        assert index_faiss_path.is_file(), f"{index_faiss_path} is not a valid file."
        assert index_pkl_path.is_file(), f"{index_pkl_path} is not a valid file."

        # Load the FAISS index from the local temporary directory
        db = FAISS.load_local(
            str(index_faiss_path),
            str(index_pkl_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )

    return db


def conversation_chain(vector_store):
    retrieval_search_results = 5
    summary_max_memory_token_limit = 1500
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
    retriever = vector_store.as_retriever(
        search_type="similarity", search_kwargs={"k": retrieval_search_results}
    )
    memory = ConversationSummaryMemory(
        llm=llm,
        return_messages=True,
        memory_key="chat_history",
        max_token_limit=summary_max_memory_token_limit,
    )

    crc = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        chain_type="stuff",
        combine_docs_chain_kwargs={"prompt": prompt},
    )
    return crc, memory
