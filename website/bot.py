import tempfile
from pathlib import Path

import openai
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
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
        client.completions.create(prompt="Hello", model="gpt-3.5-turbo-instruct", max_tokens=1)
        return True
    except openai.APIConnectionError as e:
        print(f"Failed to connect to OpenAI API: {e}")
        return False
    except openai.RateLimitError as e:
        print(f"OpenAI API rate limit exceeded: {e}")
        return False
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


def get_temp_db_path(db_folder_path):
    temp_dir = tempfile.TemporaryDirectory()
    db_folder_str = str(db_folder_path)
    temp_db_path = Path(temp_dir.name) / db_folder_path
    temp_db_path.mkdir(parents=True, exist_ok=True)
    return temp_dir, db_folder_str, temp_db_path


def embed_documents_and_save(embed_docs):
    db_folder_path = Path("faiss_index")

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # Temporary directory for local operations
    temp_dir, db_folder_str, temp_db_path = get_temp_db_path(db_folder_path)

    # Check if the folder exists in the storage system and download files
    if default_storage.exists(db_folder_str) and default_storage.listdir(db_folder_str):
        # Download all files from the storage folder to the temp directory
        for file_name in default_storage.listdir(db_folder_str)[1]:
            with default_storage.open(db_folder_path / file_name, "rb") as f:
                content = f.read()
            with open(temp_db_path / file_name, "wb") as temp_file:
                temp_file.write(content)

        # Load the FAISS index from the temp directory
        db = FAISS.load_local(temp_db_path, embeddings, allow_dangerous_deserialization=True)
        # Add new documents to the index
        db.add_documents(embed_docs)
    else:
        # Create a new FAISS index if it doesn't exist
        db = FAISS.from_documents(embed_docs, embeddings)

    # Save the updated FAISS index back to the temp directory
    db.save_local(temp_db_path)

    # Clean up the storage directory before uploading the new files
    if default_storage.exists(db_folder_str):
        for file_name in default_storage.listdir(db_folder_str)[1]:
            default_storage.delete(db_folder_path / file_name)

    # Upload the updated files back to Django's storage
    for file in temp_db_path.rglob("*"):
        if file.is_file():
            with open(file, "rb") as f:
                content = f.read()
            default_storage.save(
                str(db_folder_path / file.relative_to(temp_db_path)), ContentFile(content)
            )
    temp_dir.cleanup()

    return db


def load_vector_store():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    db_folder_path = Path("faiss_index")

    temp_dir, db_folder_str, temp_db_path = get_temp_db_path(db_folder_path)

    # check the file exists in the storage system and download files if not exist return None
    if not default_storage.exists(db_folder_str) or not default_storage.listdir(db_folder_str)[1]:
        temp_dir.cleanup()
        return None
    # Download all files from the storage folder to the temp directory
    for file_name in default_storage.listdir(db_folder_str)[1]:
        with default_storage.open(db_folder_path / file_name, "rb") as f:
            content = f.read()
        with open(temp_db_path / file_name, "wb") as temp_file:
            temp_file.write(content)

    # Load the FAISS index from the temp directory
    db = FAISS.load_local(temp_db_path, embeddings, allow_dangerous_deserialization=True)
    temp_dir.cleanup()

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
