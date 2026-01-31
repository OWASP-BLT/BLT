import logging
import os
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from dotenv import find_dotenv, load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

# Safe imports for AI dependencies to prevent startup crashes if missing
try:
    import openai
    from langchain.chains import ConversationalRetrievalChain
    from langchain.memory import ConversationSummaryMemory
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import DirectoryLoader, Docx2txtLoader, PyPDFLoader, TextLoader
    from langchain_community.vectorstores import FAISS
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from openai import OpenAI

    AI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AI dependencies not found: {e}. AI features will be disabled.")
    AI_AVAILABLE = False


def log_chat(message):
    """Log chat-related events."""
    logger.info(f"CHAT: {message}")


def is_api_key_valid(api_key):
    if not AI_AVAILABLE:
        return False

    client = OpenAI(api_key=api_key)
    try:
        client.models.list()
        return True
    except openai.APIConnectionError as e:
        log_chat(f"Failed to connect to OpenAI API: {e}")
    except openai.RateLimitError as e:
        log_chat(f"OpenAI API rate limit exceeded: {e}")
    except openai.APIError as e:
        log_chat(f"OpenAI API error: {e}")
    except Exception as e:
        log_chat(f"Unexpected error validating API key: {e}")
    return False


def load_document(file_path):
    if not AI_AVAILABLE:
        raise ImportError("AI dependencies are missing")

    loaders = {
        ".pdf": PyPDFLoader,
        ".docx": Docx2txtLoader,
        ".txt": TextLoader,
        ".md": TextLoader,
    }

    file_path = Path(file_path)
    extension = file_path.suffix
    Loader = loaders.get(extension)

    if Loader is None:
        log_chat(f"Unsupported file format: {extension}")
        raise ValueError(f"Unsupported file format: {extension}")

    log_chat(f"Loading document from {file_path}")
    return Loader(file_path).load()


def load_directory(dir_path):
    if not AI_AVAILABLE:
        raise ImportError("AI dependencies are missing")
    log_chat(f"Loading directory from {dir_path}")
    return DirectoryLoader(dir_path).load()


def split_document(chunk_size, chunk_overlap, document):
    if not AI_AVAILABLE:
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    log_chat(f"Splitting document into chunks of size {chunk_size} with overlap {chunk_overlap}")
    return text_splitter.split_documents(document)


def get_temp_db_path(db_folder_path):
    temp_dir = tempfile.TemporaryDirectory()
    db_folder_str = str(db_folder_path)
    temp_db_path = Path(temp_dir.name) / db_folder_path
    temp_db_path.mkdir(parents=True, exist_ok=True)
    log_chat(f"Created temporary directory at {temp_db_path}")
    return temp_dir, db_folder_str, temp_db_path


def embed_documents_and_save(embed_docs):
    if not AI_AVAILABLE:
        log_chat("AI unavailable, skipping embedding.")
        return None

    db_folder_path = Path("faiss_index")

    # Ensure API Key is set
    if not os.getenv("OPENAI_API_KEY"):
        log_chat("OPENAI_API_KEY environment variable not set.")
        return None

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    temp_dir, db_folder_str, temp_db_path = get_temp_db_path(db_folder_path)

    try:
        # Check if the folder exists in the storage system and download files
        # Check if the folder exists in the storage system and download files
        if default_storage.exists(db_folder_str):
            dirs, files = default_storage.listdir(db_folder_str)
            if files:
                log_chat(f"Downloading FAISS index from storage: {db_folder_str}")
                for file_name in files:
                    with default_storage.open(db_folder_path / file_name, "rb") as f:
                        content = f.read()
                    with open(temp_db_path / file_name, "wb") as temp_file:
                        temp_file.write(content)
                    log_chat(f"Downloaded file {file_name} to {temp_db_path}")

                # Load the FAISS index from the temp directory
                # Security: allow_dangerous_deserialization is set to False to prevent RCE.
                # If you have legacy trusted indexes, you might need to rebuild them.
                db = FAISS.load_local(temp_db_path, embeddings, allow_dangerous_deserialization=False)
                log_chat(f"Loaded FAISS index from {temp_db_path}")
                # Add new documents to the index
                db.add_documents(embed_docs)
                log_chat("Added new documents to the FAISS index")
            else:
                log_chat("No files found in storage directory; creating new index")
                db = FAISS.from_documents(embed_docs, embeddings)
        else:
            log_chat("No existing FAISS index found; creating new index")
            # Create a new FAISS index if it doesn't exist
            db = FAISS.from_documents(embed_docs, embeddings)

        # Save the updated FAISS index back to the temp directory
        db.save_local(temp_db_path)
        log_chat(f"Saved FAISS index to {temp_db_path}")

        # Clean up the storage directory before uploading the new files
        if default_storage.exists(db_folder_str):
            log_chat(f"Cleaning up storage directory: {db_folder_str}")
            dirs, files = default_storage.listdir(db_folder_str)
            for file_name in files:
                default_storage.delete(db_folder_path / file_name)
                log_chat(f"Deleted file {file_name} from storage")

        # Upload the updated files back to Django's storage
        for file in temp_db_path.rglob("*"):
            if file.is_file():
                with open(file, "rb") as f:
                    content = f.read()
                default_storage.save(str(db_folder_path / file.relative_to(temp_db_path)), ContentFile(content))
                log_chat(f"Uploaded file {file.name} to storage")
    except Exception as e:
        log_chat(f"Error during FAISS index embedding and saving: {e}")
        raise
    finally:
        temp_dir.cleanup()

    return db


def load_vector_store():
    if not AI_AVAILABLE:
        return None

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    db_folder_path = Path("faiss_index/")

    temp_dir, db_folder_str, temp_db_path = get_temp_db_path(db_folder_path)

    # Check if the folder exists in the storage system
    check_db_folder_str = str(db_folder_path / "index.faiss")
    # Note: default_storage.exists expects a string path
    if not default_storage.exists(check_db_folder_str):
        temp_dir.cleanup()
        # ChatBotLog logic removed as it depends on a model not imported
        log_chat(f"FAISS index not found at {check_db_folder_str}")
        return None

    try:
        # Download all files from the storage folder to the temp directory
        dirs, files = default_storage.listdir(db_folder_str)
        for file_name in files:
            with default_storage.open(db_folder_path / file_name, "rb") as f:
                content = f.read()
            with open(temp_db_path / file_name, "wb") as temp_file:
                temp_file.write(content)

        # Load the FAISS index from the temp directory
        db = FAISS.load_local(temp_db_path, embeddings, allow_dangerous_deserialization=False)
    except Exception as e:
        log_chat(f"Error loading vector store: {e}")
        return None
    finally:
        temp_dir.cleanup()

    return db


def conversation_chain(vector_store):
    if not AI_AVAILABLE:
        return None, None

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
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": retrieval_search_results})
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
    log_chat("Created conversational retrieval chain")
    return crc, memory
