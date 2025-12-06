import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from website.bot import embed_documents_and_save, load_document, split_document
from website.management.base import LoggedBaseCommand


class Command(LoggedBaseCommand):
    help = "Update the FAISS database with new documents using OpenAI embeddings."

    def handle(self, *args, **kwargs):
        # Load environment variables
        load_dotenv(find_dotenv(), override=True)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.strip():
            self.stdout.write(self.style.ERROR("OPENAI_API_KEY not found. Please set it in your .env file."))
            return None

        # Calculate the base directory
        base_dir = Path(__file__).resolve().parents[3]

        # Set the paths to the website directory, documents, and faiss_index directories
        website_dir = base_dir / "website"
        documents_dir = website_dir / "documents"
        processed_files_path = website_dir / "processed_files.txt"

        # Check if the documents directory exists
        if not documents_dir.exists():
            self.stdout.write(self.style.ERROR(f"Documents directory does not exist: {documents_dir}"))
            return None

        # Load the list of already processed files
        processed_files = set()
        if processed_files_path.exists():
            with processed_files_path.open("r") as f:
                processed_files = set(f.read().splitlines())

        # Load documents and filter out already processed files
        document_files = [f for f in documents_dir.iterdir() if f.is_file()]
        new_documents = [f for f in document_files if f.name not in processed_files]

        if not new_documents:
            self.stdout.write(self.style.WARNING("No new documents to process."))
            return None

        all_split_docs = []
        for doc_file in new_documents:
            try:
                document = load_document(doc_file)
                split_docs = split_document(1000, 100, document)
                all_split_docs.extend(split_docs)
                self.stdout.write(self.style.SUCCESS(f"Processed: {doc_file.name}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to process {doc_file.name}: {e}"))

        try:
            # Embed the new documents
            # embed_documents_and_save(all_split_docs, db_dir=str(faiss_index_dir))
            embed_documents_and_save(all_split_docs)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f" Error during embedding: {e}"))
            return None

        # Update the list of processed files
        with processed_files_path.open("a") as f:
            for doc_file in new_documents:
                f.write(f"{doc_file.name}\n")

        self.stdout.write(self.style.SUCCESS("Documents embedded and saved successfully."))
