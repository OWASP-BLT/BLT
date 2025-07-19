import json
import os
import subprocess
import tempfile
from typing import List, Optional

import django
import google.generativeai as genai
import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
django.setup()

from aibot import process_diff
from website.aibot.network import fetch_pr_files


def _run_command(command: List[str], input_data: Optional[str] = None) -> str:
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, input=input_data, check=False
        )
        return result.stdout
    except Exception as e:
        return f"Error running {command}: {str(e)}"


def _run_ruff_on_code(code: str) -> str:
    command = ["ruff", "check", "--select=ALL", "--output-format", "json"]
    return _run_command(command, input_data=code)


def _run_bandit_on_files(files: List[str]) -> str:
    if not files:
        return ""
    command = ["bandit", "-r", "--format", "json"] + files
    return _run_command(command)


def _run_bandit_on_code(code: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmpfile:
        tmpfile.write(code)
        tmpfile_path = tmpfile.name

    try:
        command = ["bandit", "--format", "json", tmpfile_path]
        return _run_command(command)
    finally:
        os.remove(tmpfile_path)


try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except AttributeError:
    print("GEMINI_API_KEY not found in Django settings. Please add it.")
    exit()


head_ref = "rinkitadhana:feature/new-file-structure"
URL = "https://patch-diff.githubusercontent.com/raw/OWASP-BLT/BLT/pull/4396.diff"
response = requests.get(URL, timeout=5)
diff = response.text

output_filename = "embedding_agent_response.txt"
processed_diff, patch = process_diff(diff)


files_url = "https://api.github.com/repos/OWASP-BLT/BLT/pulls/4396/files"

pr_files = fetch_pr_files(files_url)

if pr_files:
    pr_files_json = json.loads(pr_files)

if pr_files_json:
    raw_url_map = {}

    for file in pr_files_json:
        raw_url_map[file["filename"]] = file["raw_url"]

print(raw_url_map)

# diff_query = _generate_diff_query(processed_diff)
# cleaned_json = extract_json_block(diff_query)
# diff_query_json = json.loads(cleaned_json)
# print(diff_query_json)

# print("creating temp pr collection...")
# temp_collection = create_temp_pr_collection(head_ref, 4396, patch)
# print("collection creation complete")

# q = diff_query_json.get("query")
# key_terms = diff_query_json.get("key_terms")
# k = diff_query_json.get("k")

# combined_query = q + key_terms
# print(combined_query)

# files_to_be_analyzed_statically = [file.source_file for file in patch if file.is_modified_file or file.is_added_file]

# vector_query = generate_embedding(combined_query)
# source_collection = "repo_embeddings"

# rename_mappings = {}

# for file in patch:
#     rename_mappings[file.source_file] = file.target_file

# import json

# try:
#     main_points = qdrant_client.query_points(collection_name=source_collection, query=vector_query, limit=k)
#     temp_points = qdrant_client.query_points(collection_name=temp_collection, query=vector_query, limit=k)

#     relevant_chunks = {}

#     for point in main_points.points:
#         chunk_data = point.payload
#         key = chunk_data["file_path"]
#         relevant_chunks[key] = chunk_data

#     for point in temp_points.points:
#         chunk_data = point.payload
#         key = chunk_data["file_path"]

#         if key in relevant_chunks:
#             print(f"Found existing key: {key}. Overwriting with: ")
#             print(chunk_data["chunk"])
#             key = rename_mappings.get(key, key)

#         relevant_chunks[key] = chunk_data

#     chunks = list(relevant_chunks.values())

#     with open("merged_chunks.json", "w", encoding="utf-8") as f:
#         json.dump(chunks, f, indent=2, ensure_ascii=False)

# except Exception as e:
#     raise e
