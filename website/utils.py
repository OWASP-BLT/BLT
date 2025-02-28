import ast
import difflib
import hashlib
import os
import re
import time
from collections import deque
from urllib.parse import urlparse, urlsplit, urlunparse

import markdown
import numpy as np
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "sk-proj-1234567890"))
import requests
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import HttpRequest, HttpResponseBadRequest
from django.shortcuts import redirect
from openai import OpenAI

from .models import PRAnalysisReport

GITHUB_API_TOKEN = os.getenv("GITHUB_TOKEN")

import logging

import urllib3
from django.conf import settings
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WHITELISTED_IMAGE_TYPES = {
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
}


def get_client_ip(request):
    """Extract the client's IP address from the request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def get_email_from_domain(domain_name):
    new_urls = deque(["http://" + domain_name])
    processed_urls = set()
    emails = set()
    emails_out = set()
    t_end = time.time() + 20

    while len(new_urls) and time.time() < t_end:
        url = new_urls.popleft()
        processed_urls.add(url)
        parts = urlsplit(url)
        base_url = "{0.scheme}://{0.netloc}".format(parts)
        path = url[: url.rfind("/") + 1] if "/" in parts.path else url
        try:
            response = requests.get(url)
        except:
            continue
        new_emails = set(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", response.text, re.I))
        if new_emails:
            emails.update(new_emails)
            break
        soup = BeautifulSoup(response.text)
        for anchor in soup.find_all("a"):
            link = anchor.attrs["href"] if "href" in anchor.attrs else ""
            if link.startswith("/"):
                link = base_url + link
            elif not link.startswith("http"):
                link = path + link
            if link not in new_urls and link not in processed_urls and link.find(domain_name) > 0:
                new_urls.append(link)

    for email in emails:
        if email.find(domain_name) > 0:
            emails_out.add(email)
    try:
        return list(emails_out)[0]
    except:
        return False


import numpy as np
from PIL import Image


def image_validator(img):
    try:
        filesize = img.file.size
    except:
        filesize = img.size

    extension = img.name.split(".")[-1]
    content_type = img.content_type
    megabyte_limit = 3.0
    if not extension or extension.lower() not in WHITELISTED_IMAGE_TYPES.keys():
        error = "Invalid image types"
        return error
    elif filesize > megabyte_limit * 1024 * 1024:
        error = "Max file size is %sMB" % str(megabyte_limit)
        return error
    elif content_type not in WHITELISTED_IMAGE_TYPES.values():
        error = "Invalid image content-type"
        return error

    # Images must not be single color.
    img_array = np.array(Image.open(img))
    if img_array.std() < 10:
        error = "Image appears to be a single color"
        return error

    else:
        return True


def is_valid_https_url(url):
    validate = URLValidator(schemes=["https"])
    try:
        validate(url)
        return True
    except ValidationError:
        return False


def rebuild_safe_url(url):
    parsed_url = urlparse(url)
    return urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", "", ""))


def get_github_issue_title(github_issue_url):
    """Helper function to fetch the title of a GitHub issue."""
    try:
        repo_path = "/".join(github_issue_url.split("/")[3:5])
        issue_number = github_issue_url.split("/")[-1]
        github_api_url = f"https://api.github.com/repos/{repo_path}/issues/{issue_number}"
        response = requests.get(github_api_url)
        if response.status_code == 200:
            issue_data = response.json()
            return issue_data.get("title", "No Title")
        return f"Issue #{issue_number}"
    except Exception:
        return "No Title"


def is_safe_url(url, allowed_hosts, allowed_paths=None):
    if not is_valid_https_url(url):
        return False

    parsed_url = urlparse(url)

    if parsed_url.netloc not in allowed_hosts:
        return False

    if allowed_paths and parsed_url.path not in allowed_paths:
        return False

    return True


def safe_redirect_allowed(url, allowed_hosts, allowed_paths=None):
    if is_safe_url(url, allowed_hosts, allowed_paths):
        safe_url = rebuild_safe_url(url)
        return redirect(safe_url)
    else:
        return HttpResponseBadRequest("Invalid redirection URL.")


def safe_redirect_request(request: HttpRequest):
    http_referer = request.META.get("HTTP_REFERER")
    if http_referer:
        referer_url = urlparse(http_referer)
        if referer_url.netloc == request.get_host():
            safe_url = urlunparse((referer_url.scheme, referer_url.netloc, referer_url.path, "", "", ""))
            return redirect(safe_url)
    fallback_url = f"{request.scheme}://{request.get_host()}/"
    return redirect(fallback_url)


def admin_required(user):
    return user.is_superuser


def format_timedelta(td):
    """
    Helper function to format timedelta objects into 'Xh Ym Zs' format.
    """
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


def fetch_github_data(owner, repo, endpoint, number):
    """
    Fetch data from GitHub API for a given repository endpoint.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/{endpoint}/{number}"
    headers = {
        "Authorization": f"Bearer {GITHUB_API_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return {"error": f"Failed to fetch data: {response.status_code}"}


def analyze_pr_content(pr_data, roadmap_data):
    """
    Use OpenAI API to analyze PR content against roadmap priorities.
    """
    prompt = f"""
    Compare the following pull request details with the roadmap priorities and provide:
    1. A priority alignment score (1-10) with reasoning.
    2. Key recommendations for improvement.
    3. Assess the quality of the pull request based on its description, structure, and potential impact.

    ### PR Data:
    {pr_data}

    ### Roadmap Data:
    {roadmap_data}
    """
    response = client.chat.completions.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0.7
    )
    return response.choices[0].message.content


def save_analysis_report(pr_link, issue_link, analysis):
    """
    Save the analysis report into the database.
    """
    priority_score = analysis.get("priority_score", 0)
    revision_score = analysis.get("revision_score", 0)
    recommendations = analysis.get("recommendations", "")

    PRAnalysisReport.objects.create(
        pr_link=pr_link,
        issue_link=issue_link,
        priority_alignment_score=priority_score,
        revision_score=revision_score,
        recommendations=recommendations,
    )


def generate_embedding(text, retries=2, backoff_factor=2):
    """
    Generate embedding for a function's full text using OpenAI's embeddings API.
    :param function_text: The full text of the function.
    :return: The embedding vector for the function text.
    """
    for attempt in range(retries):
        try:
            response = openai.embeddings.create(model="text-embedding-ada-002", input=text, encoding_format="float")
            # response = {
            # "object": "list",
            # "data": [
            #     {
            #     "object": "embedding",
            #     "embedding": [
            #         0.0023064255,
            #         -0.009327292,
            #         -0.0028842222,
            #     ],
            #     "index": 0
            #     }
            #     ],
            #     "model": "text-embedding-ada-002",
            #     "usage": {
            #         "prompt_tokens": 8,
            #         "total_tokens": 8
            #     }
            # }
            # Extract the embedding from the response
            embedding = response.data[0].embedding
            return np.array(embedding)

        except openai.RateLimitError as e:
            # If rate-limiting error occurs, wait and retry
            print(f"Rate-limiting error encountered: {e}. Retrying in {2 ** attempt} seconds.")
            time.sleep(2**attempt)  # Exponential backoff

        except Exception as e:
            # For other errors, print the error and return None
            print(f"An error occurred: {e}")
            return None

    print(f"Failed to complete request after {retries} attempts.")
    return None


def cosine_similarity(embedding1, embedding2):
    """
    Compute the cosine similarity between two embeddings.
    :param embedding1: The first embedding vector.
    :param embedding2: The second embedding vector.
    :return: The cosine similarity score between the two embeddings.
    """
    similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

    similarity_score = similarity * 100  # Scale similarity to 0-100
    return round(similarity_score, 2)


def extract_function_signatures_and_content(repo_path):
    """
    Extract function signatures (name, parameters) and full text from Python files.
    :param repo_path: Path to the repository
    :return: List of function metadata (signature + full text)
    """
    functions = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    try:
                        file_content = f.read()
                        tree = ast.parse(file_content, filename=file)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                signature = {
                                    "name": node.name,
                                    "args": [arg.arg for arg in node.args.args],
                                    "defaults": [ast.dump(default) for default in node.args.defaults],
                                }
                                # Extract function body as full text
                                function_text = ast.get_source_segment(file_content, node)
                                function_data = {
                                    "signature": signature,
                                    "full_text": function_text,  # Full text of the function
                                }
                                functions.append(function_data)
                    except Exception as e:
                        print(f"Error parsing {file_path}: {e}")
    return functions


def extract_django_models(repo_path):
    """
    Extract Django model names and fields from the given repository.
    :param repo_path: Path to the repository
    :return: List of models with their fields
    """
    models = []

    # Walk through the repository directory
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):  # Only process Python files
                file_path = os.path.join(root, file)

                # Open the file and read its contents
                with open(file_path, "r") as f:
                    lines = f.readlines()
                    model_name = None
                    fields = []

                    for line in lines:
                        line = line.strip()
                        # Look for class definition that inherits from models.Model
                        if line.startswith("class ") and "models.Model" in line:
                            if model_name:  # Save the previous model if exists
                                models.append({"name": model_name, "fields": fields})
                            model_name = line.split("(")[0].replace("class ", "").strip()
                            fields = []  # Reset fields when a new model starts

                        else:
                            # Match field definitions like: name = models.CharField(max_length=...)
                            match = re.match(r"^\s*(\w+)\s*=\s*models\.(\w+)", line)
                            if match:
                                field_name = match.group(1)
                                field_type = match.group(2)
                                fields.append({"field_name": field_name, "field_type": field_type})

                            # Match other field types like ForeignKey, ManyToManyField, etc.
                            match_complex = re.match(
                                r"^\s*(\w+)\s*=\s*models\.(ForeignKey|ManyToManyField|OneToOneField)\((.*)\)",
                                line,
                            )
                            if match_complex:
                                field_name = match_complex.group(1)
                                field_type = match_complex.group(2)
                                field_params = match_complex.group(3).strip()
                                fields.append(
                                    {
                                        "field_name": field_name,
                                        "field_type": field_type,
                                        "parameters": field_params,
                                    }
                                )

                    # Add the last model if the file ends without another class
                    if model_name:
                        models.append({"name": model_name, "fields": fields})

    return models


def compare_model_fields(model1, model2):
    """
    Compare the names and fields of two Django models using difflib.
    Compares model names, field names, and field types to calculate similarity scores.

    :param model1: First model's details (e.g., {'name': 'User', 'fields': [...]})
    :param model2: Second model's details (e.g., {'name': 'Account', 'fields': [...]})
    :return: Dictionary containing name and field similarity details
    """
    # Compare model names
    model_name_similarity = difflib.SequenceMatcher(None, model1["name"], model2["name"]).ratio() * 100

    # Initialize field comparison details
    field_comparison_details = []

    # Get fields from both models
    fields1 = model1.get("fields", [])
    fields2 = model2.get("fields", [])

    for field1 in fields1:
        for field2 in fields2:
            # Compare field names
            field_name_similarity = (
                difflib.SequenceMatcher(None, field1["field_name"], field2["field_name"]).ratio() * 100
            )

            # Compare field types
            field_type_similarity = (
                difflib.SequenceMatcher(None, field1["field_type"], field2["field_type"]).ratio() * 100
            )

            # Average similarity between the field name and type
            overall_similarity = (field_name_similarity + field_type_similarity) / 2

            # Append details for each field comparison
            if overall_similarity > 50:
                field_comparison_details.append(
                    {
                        "field1_name": field1["field_name"],
                        "field1_type": field1["field_type"],
                        "field2_name": field2["field_name"],
                        "field2_type": field2["field_type"],
                        "field_name_similarity": round(field_name_similarity, 2),
                        "field_type_similarity": round(field_type_similarity, 2),
                        "overall_similarity": round(overall_similarity, 2),
                    }
                )

    # Calculate overall similarity across all fields
    if field_comparison_details:
        total_similarity = sum([entry["overall_similarity"] for entry in field_comparison_details])
        overall_field_similarity = total_similarity / len(field_comparison_details)
    else:
        overall_field_similarity = 0.0

    return {
        "model_name_similarity": round(model_name_similarity, 2),
        "field_comparison_details": field_comparison_details,
        "overall_field_similarity": round(overall_field_similarity, 2),
    }


def git_url_to_zip_url(git_url, branch="master"):
    if git_url.endswith(".git"):
        base_url = git_url[:-4]
        zip_url = f"{base_url}/archive/refs/heads/{branch}.zip"
        return zip_url
    else:
        raise ValueError("Invalid .git URL provided")


def markdown_to_text(markdown_content):
    """Convert Markdown to plain text."""
    html_content = markdown.markdown(markdown_content)
    text_content = BeautifulSoup(html_content, "html.parser").get_text()
    return text_content


def ai_summary(text):
    """Generate an AI-driven summary using OpenAI's GPT"""
    try:
        prompt = f"Generate a brief summary of the following text, focusing on key aspects such as purpose, features, technologies used, and current status. Consider the following readme content: {text}"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=0.5,
        )

        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        return f"Error generating summary: {str(e)}"


def gravatar_url(email, size=80):
    """Generate Gravatar URL for a given email."""
    email = email.lower().encode("utf-8")
    gravatar_hash = hashlib.md5(email).hexdigest()
    return f"https://www.gravatar.com/avatar/{gravatar_hash}?s={size}&d=mp"


def check_security_txt(domain_url):
    """
    Check if a domain has security.txt file
    Returns: (bool, str) - (has_security, error_message)
    """
    security_txt_paths = ["/.well-known/security.txt", "/security.txt"]

    for path in security_txt_paths:
        try:
            url = f"https://{domain_url.rstrip('/')}{path}"
            response = requests.get(
                url, timeout=10, verify=not settings.DEBUG, headers={"User-Agent": "BLT Security Scanner/1.0"}
            )
            if response.status_code == 200:
                logger.info(f"Found security.txt at {url}")
                return True, None
        except RequestException as e:
            logger.warning(f"Error checking security.txt for {domain_url}: {str(e)}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error checking security.txt for {domain_url}: {str(e)}")
            return False, str(e)

    return False, None
