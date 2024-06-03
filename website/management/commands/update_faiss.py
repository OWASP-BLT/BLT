
import os
from django.core.management.base import BaseCommand
from website.bot import load_document, split_document, embed_documents_and_save

class Command(BaseCommand):
    help = 'Update the FAISS database with new documents'

    def handle(self, *args, **kwargs):
        # Calculate the base directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # Set the paths to the website directory, documents, and faiss_index directories
        website_dir = os.path.join(base_dir, 'website')
        documents_dir = os.path.join(website_dir, 'documents')
        faiss_index_dir = os.path.join(website_dir, '')
        processed_files_path = os.path.join(website_dir, 'processed_files.txt')

        # Check if the documents directory exists
        if not os.path.exists(documents_dir):
            self.stdout.write(self.style.ERROR(f'Documents directory does not exist: {documents_dir}'))
            return

        # Load the list of already processed files
        if os.path.exists(processed_files_path):
            with open(processed_files_path, 'r') as f:
                processed_files = set(f.read().splitlines())
        else:
            processed_files = set()

        # Load documents and filter out already processed files
        document_files = [f for f in os.listdir(documents_dir) if os.path.isfile(os.path.join(documents_dir, f))]
        new_documents = [f for f in document_files if f not in processed_files]

        if not new_documents:
            self.stdout.write(self.style.WARNING('No new documents to process'))
            return

        all_split_docs = []
        for doc_file in new_documents:
            doc_path = os.path.join(documents_dir, doc_file)
            document = load_document(doc_path)
            split_docs = split_document(1000, 200, document)
            all_split_docs.extend(split_docs)

        # Embed the new documents
        embed_documents_and_save(all_split_docs, db_dir=faiss_index_dir)
        
        # Update the list of processed files
        with open(processed_files_path, 'a') as f:
            for filename in new_documents:
                f.write(f'{filename}\n')
        
        self.stdout.write(self.style.SUCCESS("Documents embedded and saved successfully"))