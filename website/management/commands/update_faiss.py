import os

from django.conf import settings

from website.management.base import LoggedBaseCommand

# Safe import attempt from bot
try:
    from website.bot import embed_documents_and_save, load_document, split_document, AI_AVAILABLE
except ImportError:
    AI_AVAILABLE = False


class Command(LoggedBaseCommand):
    help = "Update the FAISS database with new documents"

    def handle(self, *args, **kwargs):
        if not AI_AVAILABLE:
            self.stdout.write(self.style.ERROR("AI dependencies missing. Cannot Run Update."))
            return None

        # Check API Key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("OPENAI_API_KEY not found in environment."))
            return None

        # Optional: Validate API Key (can be slow, maybe skip for CLI speed)
        # check_api = is_api_key_valid(api_key)
        # if not check_api:
        #     self.stdout.write(self.style.ERROR("Invalid OpenAI API Key."))
        #     return None

        # Calculate the base directory
        base_dir = settings.BASE_DIR

        # Set the paths to the website directory, documents, and faiss_index directories
        # Assuming layout: /gsoc_BLT/website/
        website_dir = base_dir / "website"
        documents_dir = website_dir / "documents"
        processed_files_path = website_dir / "processed_files.txt"

        # Check if the documents directory exists
        if not documents_dir.exists():
            self.stdout.write(self.style.ERROR(f"Documents directory does not exist: {documents_dir}"))
            # Create it for user convenience
            try:
                documents_dir.mkdir(parents=True, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f"Created empty documents directory: {documents_dir}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to create directory: {e}"))
            return None

        # Load the list of already processed files
        if processed_files_path.exists():
            with processed_files_path.open("r") as f:
                processed_files = set(f.read().splitlines())
        else:
            processed_files = set()

        # Load documents and filter out already processed files
        document_files = [f for f in documents_dir.iterdir() if f.is_file()]
        new_documents = [f for f in document_files if f.name not in processed_files]

        if not new_documents:
            self.stdout.write(self.style.WARNING("No new documents to process"))
            return None

        all_split_docs = []
        successfully_processed = []
        for doc_file in new_documents:
            try:
                document = load_document(doc_file)
                split_docs = split_document(1000, 100, document)
                all_split_docs.extend(split_docs)
                successfully_processed.append(doc_file)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to process {doc_file.name}: {e}"))

        # Embed the new documents
        if all_split_docs:
            embed_documents_and_save(all_split_docs)

            # Update the list of processed files only after successful embedding
            with processed_files_path.open("a") as f:
                for doc_file in successfully_processed:
                    f.write(f"{doc_file.name}\n")

            self.stdout.write(self.style.SUCCESS(f"Successfully embedded {len(new_documents)} documents."))
        else:
            self.stdout.write(self.style.WARNING("No valid content found in new documents."))
