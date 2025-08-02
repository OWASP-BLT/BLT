import json
import logging
import os

import django

logger = logging.getLogger(__name__)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
django.setup()

from website.aibot.aibot_env import load_prompts
from website.aibot.clients import q_client
from website.aibot.models import PullRequest
from website.aibot.network import fetch_pr_diff, generate_embedding, generate_gemini_response, post_github_comment
from website.aibot.qdrant_utils import get_similar_merged_chunks
from website.aibot.utils import analyze_code_ruff_bandit, extract_json_block

PROMPTS = load_prompts()


from aibot import get_diff_query, process_diff

with open("webhook_pr_event.txt", "r", encoding="utf-8") as f:
    payload = f.read()

payload = json.loads(payload)

pr_instance = PullRequest(payload)

pr_diff = fetch_pr_diff(pr_instance.diff_url)

processed_diff, patch = process_diff(pr_diff)
diff_query = get_diff_query(processed_diff)
cleaned_json = extract_json_block(diff_query)
diff_query_json = json.loads(cleaned_json)

q = diff_query_json.get("query")
key_terms = diff_query_json.get("key_terms")
k = diff_query_json.get("k")

combined_query = q + key_terms
vector_query = generate_embedding(combined_query)
analysis_output = None
joined_snippets = None

if not vector_query:
    logger.warning("Embedding generation failed for query: %s", combined_query)
elif not pr_instance.raw_url_map:
    logger.warning("Missing raw URL map for PR instance: %s", pr_instance)
else:
    # source_collection, temp_collection = create_temp_pr_collection(pr_instance, patch)
    source_collection = "repo_embeddings"
    temp_collection = "temp_aibot-embedding_16"
    logger.info("Temporary collection created: %s", temp_collection)

    rename_mappings = {}
    for file in patch:
        rename_mappings[file.source_file] = file.target_file

    if source_collection and temp_collection:
        similar_chunks = get_similar_merged_chunks(
            q_client, source_collection, temp_collection, vector_query, k, rename_mappings
        )
        analysis_output = analyze_code_ruff_bandit(similar_chunks)
    else:
        logger.warning("Missing collection names: source=%s, temp=%s", source_collection, temp_collection)

    formatted_snippets = []
    for snippet in similar_chunks:
        file_path = snippet.get("file_path", "Unknown")
        chunk = snippet.get("chunk", "")
        start = snippet.get("start_line", "?")
        end = snippet.get("end_line", "?")

        formatted_snippet = f"File: {file_path}\n" f"Lines: {start}–{end}\n" f"```python\n{chunk}\n```"
        formatted_snippets.append(formatted_snippet)

    joined_snippets = "\n\n".join(formatted_snippets)

prompt = PROMPTS["PR_REVIEWER_PROMPT"]
placeholders = {
    "<INSERT_PR_TITLE>": pr_instance.title or "Not found",
    "<INSERT_PR_BODY>": pr_instance.body or "Not found",
    "<INSERT_PR_DIFF>": processed_diff or "Not found",
    "<INSERT_STATIC_ANALYSIS_OUTPUT>": analysis_output or "Not found",
    "<INSERT_RELEVANT_SNIPPETS>": joined_snippets or "Not found",
}

for key, value in placeholders.items():
    prompt = prompt.replace(key, str(value))

bot_response = generate_gemini_response(prompt)

post_github_comment(pr_instance.comments_url, bot_response)
