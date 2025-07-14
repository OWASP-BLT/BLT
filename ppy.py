import json
import os
import subprocess
from typing import List, Optional

import django
import google.generativeai as genai
import requests
from django.conf import settings

from clients import qdrant_client
from parse_utils import extract_json_block, generate_embedding
from website.views.aibot import _generate_diff_query, _process_diff, create_temp_pr_collection


def _run_command(command: List[str], input_data: Optional[str] = None) -> str:
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, input=input_data, check=False
        )
        return result.stdout
    except Exception as e:
        return f"Error running {command}: {str(e)}"


def _run_ruff(code: str) -> str:
    command = ["ruff", "check", "--select=ALL", "--output-format", "json", "-"]
    return _run_command(command, input_data=code)


def _run_bandit_on_files(files: List[str]) -> str:
    if not files:
        return ""
    command = ["bandit", "-r", "--format", "json"] + files
    return _run_command(command)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
django.setup()

try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
except AttributeError:
    print("GEMINI_API_KEY not found in Django settings. Please add it.")
    exit()


head_ref = "feature/new-file-structure"
URL = "https://patch-diff.githubusercontent.com/raw/OWASP-BLT/BLT/pull/4396.diff"
response = requests.get(URL, timeout=5)
diff = response.text

output_filename = "embedding_agent_response.txt"
processed_diff, patch = _process_diff(diff)


diff_query = _generate_diff_query(processed_diff)
cleaned_json = extract_json_block(diff_query)
diff_query_json = json.loads(cleaned_json)
print(diff_query_json)

print("creating temp pr collection...")
temp_collection = create_temp_pr_collection(head_ref, 4396, patch)
print("collection creation complete")

q = diff_query_json.get("query")
key_terms = diff_query_json.get("key_terms")
k = diff_query_json.get("k")

combined_query = q + key_terms
print(combined_query)

files_to_be_analyzed_statically = [file.source_file for file in patch if file.is_modified_file or file.is_added_file]

vector_query = generate_embedding(combined_query)

try:
    search_result = qdrant_client.search(collection_name=temp_collection, query_vector=vector_query, limit=k)

    for point in search_result:
        payload = point.payload
        file_path = payload.get("file_path", "Unknown file")
        if file_path in files_to_be_analyzed_statically:
            if file_path.endswith(".py"):
                ruff_output = _run_ruff([file_path])
                bandit_output = _run_bandit_on_files([file_path])

    output_file = "search_results.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        for idx, point in enumerate(search_result, start=1):
            file_path = point.payload.get("file_path", "Unknown file")
            start_line = point.payload.get("start_line", "?")
            end_line = point.payload.get("end_line", "?")
            chunk = point.payload.get("chunk", "").strip()
            score = point.score

            block = (
                f"--- Match {idx} ---\n"
                f"File: {file_path}\n"
                f"Similarity Score: {score:.4f}\n"
                f"Chunk:\n"
                f"{chunk}\n"
                f"{'-' * 80}\n\n"
            )

            print(block)
            f.write(block)
            if file_path.endswith(".py"):
                ruff_output = _run_ruff_on_files([file_path])
                bandit_output = _run_bandit_on_files([file_path])

                f.write("Ruff Output:\n")
                f.write(ruff_output + "\n\n")
                f.write("Bandit Output:\n")
                f.write(bandit_output + "\n\n")

            elif file_path.endswith(".html"):
                djlint_output = _run_djlint_on_files([file_path])

                f.write("djLint Output:\n")
                f.write(djlint_output + "\n\n")

    print(f"Search results saved to '{output_file}'")

except Exception as e:
    print(f"Error during search or writing results: {e}")


try:
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(str(diff_query_json))
    print(f"Successfully saved processed diff to {output_filename}")
except IOError as e:
    print(f"Error saving file {output_filename}: {e}")
