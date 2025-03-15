# commenting temporary
# import os
# from pathlib import Path

# from website.bot import embed_documents_and_save, is_api_key_valid, load_document, split_document
from website.management.base import LoggedBaseCommand


class Command(LoggedBaseCommand):
    help = "Update the FAISS database with new documents"

    def handle(self, *args, **kwargs):
        return None
        # check_api = is_api_key_valid(os.getenv("OPENAI_API_KEY"))
        # if not check_api:
        #     self.stdout.write(self.style.ERROR(check_api))
        #     return None


#         # Calculate the base directory
#         base_dir = Path(__file__).resolve().parents[3]

#         # Set the paths to the website directory, documents, and faiss_index directories
#         website_dir = base_dir / "website"
#         documents_dir = website_dir / "documents"
#         processed_files_path = website_dir / "processed_files.txt"

#         # Check if the documents directory exists
#         if not documents_dir.exists():
#             self.stdout.write(self.style.ERROR(f"Documents directory does not exist: {documents_dir}"))
#             return None

#         # Load the list of already processed files
#         if processed_files_path.exists():
#             with processed_files_path.open("r") as f:
#                 processed_files = set(f.read().splitlines())
#         else:
#             processed_files = set()

#         # Load documents and filter out already processed files
#         document_files = [f for f in documents_dir.iterdir() if f.is_file()]
#         new_documents = [f for f in document_files if f.name not in processed_files]

#         if not new_documents:
#             self.stdout.write(self.style.WARNING("No new documents to process"))
#             return None

#         all_split_docs = []
#         for doc_file in new_documents:
#             document = load_document(doc_file)
#             split_docs = split_document(1000, 100, document)
#             all_split_docs.extend(split_docs)

#         # Embed the new documents
#         # embed_documents_and_save(all_split_docs, db_dir=str(faiss_index_dir))
#         embed_documents_and_save(all_split_docs)

#         # Update the list of processed files
#         with processed_files_path.open("a") as f:
#             for doc_file in new_documents:
#                 f.write(f"{doc_file.name}\n")

#         self.stdout.write(self.style.SUCCESS("Documents embedded and saved successfully"))
