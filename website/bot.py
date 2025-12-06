import logging
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.utils.html import escape
from dotenv import find_dotenv, load_dotenv
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# Load environment variables
load_dotenv(find_dotenv(), override=True)

BASE_DIR = Path(settings.BASE_DIR)
logger = logging.getLogger(__name__)


def log_chat(message_type, message):
    """Unified logging for chatbot events."""
    logger.info(f"[{message_type.upper()}] {message}")


def load_document(file_path):
    """Load document using the appropriate loader based on file extension."""
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
        raise ValueError(f"Unsupported file format: {extension}")

    log_chat("info", f"Loading document: {file_path}")
    return Loader(file_path).load()


def split_document(chunk_size, chunk_overlap, document):
    """Split document text into smaller chunks for embedding."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    log_chat("info", f"Splitting document into chunks of size {chunk_size} (overlap {chunk_overlap})")
    return text_splitter.split_documents(document)


def embed_documents_and_save(embed_docs):
    """Embed and save documents to FAISS index using OpenAI embeddings."""
    db_folder_path = BASE_DIR / "faiss_index"
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    try:
        if db_folder_path.exists() and any(db_folder_path.iterdir()):
            log_chat("info", f"Updating existing FAISS index at {db_folder_path}")

            # Security note:
            # allow_dangerous_deserialization is required for FAISS load
            # since FAISS uses pickle-based serialization.
            # Index files are stored securely and not user-uploaded.
            db = FAISS.load_local(db_folder_path, embeddings, allow_dangerous_deserialization=True)
            db.add_documents(embed_docs)
        else:
            log_chat("info", "Creating new FAISS index...")
            db = FAISS.from_documents(embed_docs, embeddings)

        db.save_local(db_folder_path)
        log_chat("info", f"FAISS index saved at {db_folder_path}")

    except Exception as e:
        log_chat("error", f"Error during FAISS update: {e}")
        raise

    return db


def load_vector_store():
    """Load existing FAISS index from disk."""
    try:
        db_folder_path = Path(BASE_DIR) / "faiss_index"
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        if not db_folder_path.exists() or not (db_folder_path / "index.faiss").exists():
            log_chat("warning", "No FAISS index found.")
            return None

        # Security note: required for FAISS load (safe in trusted environment)
        db = FAISS.load_local(db_folder_path, embeddings, allow_dangerous_deserialization=True)
        log_chat("info", "FAISS index loaded successfully.")
        return db

    except Exception as e:
        log_chat("error", f"Error loading FAISS index: {e}")
        return None


def conversation_chain(vector_store):
    """Create a retrieval-based conversation chain using OpenAI."""
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)

    prompt = ChatPromptTemplate.from_template(
        """You are an assistant specifically designed for answering questions about the OWASP Bug Logging Tool (BLT) application.
        Use the following retrieved context to answer the user's question.
        If the user's question is not related to the BLT application or if the context does not provide enough information,
        respond with: "Please ask a query related to the BLT Application."
        Ensure your response is concise and does not exceed three sentences.

        Context: {context}
        Question: {input}
        Answer:"""
    )

    document_chain = create_stuff_documents_chain(llm, prompt)
    retrieval_chain = create_retrieval_chain(retriever, document_chain)

    log_chat("info", "OpenAI retrieval chain created.")
    return retrieval_chain


@api_view(["POST"])
@permission_classes([AllowAny])
def chatbot_conversation(request):
    """Main chatbot endpoint that handles user messages."""
    user_message = request.data.get("message", "").strip()

    if not user_message:
        return Response({"message": "Please type something."}, status=status.HTTP_400_BAD_REQUEST)
        
    safe_message = user_message
    vector_store = load_vector_store()

    if vector_store:
        try:
            cached_answer = cache.get(safe_message)
            if cached_answer:
                log_chat("info", "Cache hit for message")
                return Response({"message": cached_answer}, status=status.HTTP_200_OK)
            chain = conversation_chain(vector_store)
            result = chain.invoke({"input": safe_message})
            answer = result.get("answer") or result.get("output") or "Sorry, I couldn't find an answer."

            cache.set(safe_message, answer, timeout=3600)

            log_chat("input", safe_message)
            log_chat("output", answer)
            return Response({"message": answer}, status=status.HTTP_200_OK)

        except Exception as e:
            log_chat("error", str(e))
            return Response(
                {"message": "An error occurred while processing your request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return Response(
        {"message": "Something went wrong. Please try again later."},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
