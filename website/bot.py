import os
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
    name, extension = os.path.splitext(file_path)
    if extension == ".pdf":
        loader = PyPDFLoader(file_path)
    elif extension == ".docx":
        loader = Docx2txtLoader(file_path)
    elif extension == ".txt":
        loader = TextLoader(file_path)
    elif extension == ".md":
        loader = UnstructuredMarkdownLoader(file_path)
    else:
        raise ValueError("Unsupported file format: " + extension)
    data = loader.load()
    return data


def load_directory(dir_path):
    loader = DirectoryLoader(dir_path)
    data = loader.load()
    return data


def split_document(chunk_size, chunk_overlap, document):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    docs = text_splitter.split_documents(document)
    return docs


def embed_documents_and_save(embedDocs, db_dir="", db_name="faiss_index"):
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    db_path = os.path.join(db_dir, db_name)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    if os.path.exists(db_path):
        db = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
        db.add_documents(embedDocs)
    else:
        db = FAISS.from_documents(embedDocs, embeddings)

    db.save_local(db_path)
    return db


def load_vector_store(db_path):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"FAISS index directory does not exist: {db_path}")
    db = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
    return db


def conversation_chain(vector_store):
    prompt = ChatPromptTemplate.from_messages(
        (
            "human",
            "You are an assistant specifically designed for answering questions about the OWASP Bug Logging Tool (BLT) application. Use the following pieces of retrieved context to answer the question. If the user's question is not related to the BLT application or if the context does not provide enough information to answer the question, respond with 'Please ask a query related to the BLT Application.' Ensure your response is concise and does not exceed three sentences.\nQuestion: {question}\nContext: {context}\nAnswer:",
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
