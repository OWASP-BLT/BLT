import ast
import difflib
import hashlib
import logging
import os
import re
import socket
import time
from collections import deque
from ipaddress import ip_address
from urllib.parse import quote, urlparse, urlsplit, urlunparse

import markdown
import numpy as np
import requests
import tweepy
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, URLValidator
from django.db import models
from django.http import HttpRequest, HttpResponseBadRequest
from django.shortcuts import redirect
from openai import OpenAI
from PIL import Image

from website.models import DailyStats

from .models import PRAnalysisReport

# Only initialize OpenAI client if API key is available and valid
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key and openai_api_key.startswith("sk-"):
    client = OpenAI(api_key=openai_api_key)
else:
    client = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


GITHUB_API_TOKEN = settings.GITHUB_TOKEN


WHITELISTED_IMAGE_TYPES = {
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
}


def validate_file_type(request, file_field_name, allowed_extensions, allowed_mime_types=None, max_size=None):
    file = request.FILES.get(file_field_name)
    if not file:
        return True, None  # File is optional; skip validation if not provided

    extension_validator = FileExtensionValidator(allowed_extensions=allowed_extensions)
    try:
        extension_validator(file)
    except ValidationError:
        return False, f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"

    if allowed_mime_types and file.content_type not in allowed_mime_types:
        return False, f"Invalid MIME type. Allowed: {', '.join(allowed_mime_types)}"

    if max_size and file.size > max_size:
        return False, f"File size exceeds the maximum limit of {max_size} bytes."

    return True, None


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
        except Exception:
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
    except Exception:
        return False


def image_validator(img):
    try:
        filesize = img.file.size
    except Exception:
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

    # Images must not be single color
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


def is_dns_safe(hostname):
    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False  # Unable to resolve hostname; treat as unsafe.
    for result in resolved:
        ip_str = result[4][0]
        try:
            ip = ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                return False
        except ValueError:
            continue
    return True


def rebuild_safe_url(url):
    parsed_url = urlparse(url)

    if parsed_url.scheme not in ("http", "https"):
        return None

    netloc = parsed_url.netloc.split("@")[-1]

    hostname = urlparse(f"http://{netloc}").hostname
    if not hostname:
        return None

    try:
        ip = ip_address(hostname)
        if ip.is_private or ip.is_loopback:
            return None
    except ValueError:
        if not is_dns_safe(hostname):
            return None

    path = parsed_url.path
    path = path.replace("\r", "").replace("\n", "")
    path = path.replace("/..", "").replace("/", "/")

    # Collapse multiple slashes into a single slash
    path = re.sub(r"/{2,}", "/", path)
    if path in ("", "."):
        path = "/"
    # Ensure the path starts with a slash
    elif not path.startswith("/"):
        path = "/" + path
    encoded_path = quote(path, safe="/")

    safe_url = urlunparse((parsed_url.scheme, netloc, encoded_path, "", "", ""))

    return safe_url


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
            response = client.embeddings.create(model="text-embedding-ada-002", input=text, encoding_format="float")
            # Extract the embedding from the response
            embedding = response.data[0].embedding
            return np.array(embedding)

        except Exception as e:
            # If rate-limiting error occurs, wait and retry
            print(f"Error encountered: {e}. Retrying in {2 ** attempt} seconds.")
            time.sleep(2**attempt)  # Exponential backoff

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


def fetch_github_user_data(username):
    """Fetches relevant GitHub user data for recommendations."""
    base_url = "https://api.github.com/users/"
    repos_url = f"{base_url}{username}/repos"
    starred_url = f"{base_url}{username}/starred"
    events_url = f"{base_url}{username}/events"

    headers = {
        "Authorization": f"token {GITHUB_API_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    user_data = {}
    try:
        # Fetch user profile
        logging.info(f"Fetching user profile: {username}")
        user_response = requests.get(f"{base_url}{username}", headers=headers)
        if user_response.status_code == 200:
            user_info = user_response.json()
            user_data["profile"] = {
                "username": user_info.get("login"),
                "name": user_info.get("name"),
                "bio": user_info.get("bio"),
                "location": user_info.get("location"),
                "followers": user_info.get("followers"),
                "following": user_info.get("following"),
                "avatar_url": user_info.get("avatar_url"),
                "blog": user_info.get("blog"),
                "company": user_info.get("company"),
                "twitter": user_info.get("twitter_username"),
                "public_repos": user_info.get("public_repos"),
            }
        else:
            logging.error(f"Failed to fetch user profile: {user_response.status_code} {user_response.text}")

        # Fetch repositories
        logging.info(f"Fetching repositories for {username}")
        repos_response = requests.get(repos_url, headers=headers)
        if repos_response.status_code == 200:
            repos = repos_response.json()
            user_repos = []

            for repo in repos:
                repo_data = {}
                # Check if the repo is a fork
                if repo.get("fork"):
                    # Fetch the parent repository details
                    parent_repo_url = repo.get("parent", {}).get("url")
                    if not parent_repo_url:
                        # Fetch detailed repo information to get parent URL
                        repo_details_url = f"https://api.github.com/repos/{username}/{repo['name']}"
                        repo_details_response = requests.get(repo_details_url, headers=headers)
                        if repo_details_response.status_code == 200:
                            repo_details = repo_details_response.json()
                            parent_repo_url = repo_details.get("parent", {}).get("url")
                        else:
                            logging.error(
                                f"Failed to fetch repo details for {repo['name']}: {repo_details_response.status_code}"
                            )

                    if parent_repo_url:
                        parent_response = requests.get(parent_repo_url, headers=headers)
                        if parent_response.status_code == 200:
                            parent_repo = parent_response.json()
                            logging.info(f"Fetched parent repo details for forked repo {repo['name']}")
                            repo_data = {
                                "name": parent_repo["name"],
                                "url": parent_repo["html_url"],
                                "language": parent_repo["language"],
                                "stars": parent_repo["stargazers_count"],
                                "forks": parent_repo["forks_count"],
                                "description": parent_repo["description"],
                                "topics": parent_repo.get("topics", []),
                            }
                        else:
                            logging.error(
                                f"Failed to fetch parent repo details for {repo['name']}: {parent_response.status_code}"
                            )
                            # Fallback to forked repo details
                            repo_data = {
                                "name": repo["name"],
                                "url": repo["html_url"],
                                "language": repo["language"],
                                "stars": repo["stargazers_count"],
                                "forks": repo["forks_count"],
                                "description": repo["description"],
                                "topics": repo.get("topics", []),
                            }
                    else:
                        logging.warning(f"No parent repo found for forked repo {repo['name']}")
                        repo_data = {
                            "name": repo["name"],
                            "url": repo["html_url"],
                            "language": repo["language"],
                            "stars": repo["stargazers_count"],
                            "forks": repo["forks_count"],
                            "description": repo["description"],
                            "topics": repo.get("topics", []),
                        }
                else:
                    # Regular repo, use its own details
                    repo_data = {
                        "name": repo["name"],
                        "url": repo["html_url"],
                        "language": repo["language"],
                        "stars": repo["stargazers_count"],
                        "forks": repo["forks_count"],
                        "description": repo["description"],
                        "topics": repo.get("topics", []),
                    }

                user_repos.append(repo_data)

            user_data["repositories"] = user_repos
        else:
            logging.error(f"Failed to fetch repositories: {repos_response.status_code} {repos_response.text}")

        # Fetch starred repositories
        logging.info(f"Fetching starred repositories for {username}")
        starred_response = requests.get(starred_url, headers=headers)
        if starred_response.status_code == 200:
            starred = starred_response.json()
            user_data["starred_repos"] = [
                {
                    "name": repo["name"],
                    "url": repo["html_url"],
                    "language": repo["language"],
                    "stars": repo["stargazers_count"],
                }
                for repo in starred
            ]
        else:
            logging.error(
                f"Failed to fetch starred repositories: {starred_response.status_code} {starred_response.text}"
            )

        # Fetch recent activity
        logging.info(f"Fetching recent activity for {username}")
        events_response = requests.get(events_url, headers=headers)
        if events_response.status_code == 200:
            events = events_response.json()
            user_data["recent_activity"] = [
                {
                    "type": event["type"],
                    "repo": event["repo"]["name"],
                    "created_at": event["created_at"],
                }
                for event in events
                if event["type"] in ["PushEvent", "PullRequestEvent", "IssuesEvent"]
            ]
        else:
            logging.error(f"Failed to fetch recent activity: {events_response.status_code} {events_response.text}")

        # Fetch language usage
        logging.info(f"Fetching language usage for {username}")
        language_usage = {}

        for repo in user_data.get("repositories", []):
            # Adjust repo owner and name in case of parent repos
            repo_url_parts = repo["url"].split("/")
            repo_owner = repo_url_parts[3]
            repo_name = repo_url_parts[4]

            repo_languages_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/languages"
            lang_response = requests.get(repo_languages_url, headers=headers)
            if lang_response.status_code == 200:
                lang_data = lang_response.json()
                for lang, bytes_used in lang_data.items():
                    language_usage[lang] = language_usage.get(lang, 0) + bytes_used
            else:
                logging.warning(f"Failed to fetch languages for {repo['name']}: {lang_response.status_code}")

        user_data["top_languages"] = sorted(language_usage.items(), key=lambda x: x[1], reverse=True)

        # Collect topics
        topics = [topic for repo in user_data.get("repositories", []) for topic in repo.get("topics", [])]
        user_data["top_topics"] = list(set(topics))

    except Exception as e:
        logging.exception("An error occurred while fetching GitHub user data")
        user_data["error"] = str(e)

    return user_data


def markdown_to_text(markdown_content):
    """Convert Markdown to plain text."""
    html_content = markdown.markdown(markdown_content)
    text_content = BeautifulSoup(html_content, "html.parser").get_text()
    return text_content


def ai_summary(text):
    """Generate an AI-driven summary using OpenAI's GPT"""
    try:
        prompt = (
            f"Generate a brief summary of the following text, focusing on key aspects such as purpose, "
            f"features, technologies used, and current status. Consider the following readme content: {text}"
        )

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


def get_page_votes(template_name):
    """
    Get the upvotes and downvotes for a specific template.

    Args:
        template_name (str): The name of the template to get votes for

    Returns:
        tuple: A tuple containing (upvotes, downvotes)
    """
    if not template_name:
        return 0, 0

    # Sanitize the template name to create a consistent key
    page_key = template_name.replace("/", "_").replace(".html", "")

    # Get today's stats for upvotes
    upvotes = (
        DailyStats.objects.filter(name=f"upvote_{page_key}")
        .values_list("value", flat=True)
        .aggregate(total=models.Sum("value"))["total"]
        or 0
    )

    # Get today's stats for downvotes
    downvotes = (
        DailyStats.objects.filter(name=f"downvote_{page_key}")
        .values_list("value", flat=True)
        .aggregate(total=models.Sum("value"))["total"]
        or 0
    )

    return upvotes, downvotes


def validate_screenshot_hash(screenshot_hash):
    """
    Validate that the screenshot_hash only contains alphanumeric characters,
    hyphens, or underscores.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", screenshot_hash):
        raise ValidationError(
            "Invalid screenshot hash. Only alphanumeric characters, hyphens, and underscores are allowed."
        )


# Twitter namespace
class twitter:
    @staticmethod
    def send_tweet(message, image_path=None):
        """
        Send a tweet using the Twitter API.

        Args:
            message (str): The message to tweet
            image_path (str, optional): Path to an image to include in the tweet

        Returns:
            dict: A dictionary containing:
                - success (bool): Whether the tweet was sent successfully
                - url (str): The URL of the tweet if successful
                - txid (str): The ID of the tweet if successful
                - error (str): Error message if unsuccessful
        """
        try:
            # Initialize Twitter API client
            auth = tweepy.OAuth1UserHandler(
                settings.APP_KEY, settings.APP_KEY_SECRET, settings.ACCESS_TOKEN, settings.ACCESS_TOKEN_SECRET
            )
            api = tweepy.API(auth)

            # Send tweet with or without media
            if image_path:
                status = api.update_status_with_media(status=message, filename=image_path)
            else:
                status = api.update_status(status=message)

            # Get tweet URL
            tweet_url = f"https://twitter.com/user/status/{status.id}"

            return {"success": True, "url": tweet_url, "txid": str(status.id), "error": None}
        except Exception as e:
            logging.error(f"Error sending tweet: {str(e)}")
            return {"success": False, "url": None, "txid": None, "error": str(e)}

    @staticmethod
    def send_to_discord(message, tweet_url=None, image_path=None, error=None):
        """
        Send a message to the #project-blt Discord channel.

        Args:
            message (str): The message to send
            tweet_url (str, optional): URL of the tweet
            image_path (str, optional): Path to an image
            error (str, optional): Error message if the tweet failed
        """
        try:
            # Get Discord webhook URL from environment
            webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
            if not webhook_url:
                logging.warning("Discord webhook URL not configured")
                return

            # Prepare the payload
            payload = {"content": f"**New Tweet**\n{message}", "embeds": []}

            # Add tweet URL if available
            if tweet_url:
                payload["content"] += f"\n{tweet_url}"

            # Add error information if available
            if error:
                payload["embeds"].append(
                    {
                        "title": "Error sending tweet",
                        "description": error,
                        "color": 0xE74C3C,  # Red color
                    }
                )

            # Send the request
            files = {}
            if image_path:
                with open(image_path, "rb") as img:
                    files = {"file": (os.path.basename(image_path), img)}
                    response = requests.post(webhook_url, data={"payload_json": str(payload)}, files=files)
            else:
                response = requests.post(webhook_url, json=payload)

            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Error sending to Discord: {str(e)}")
            return False

    @staticmethod
    def send_to_slack(message, tweet_url=None, image_path=None, error=None):
        """
        Send a message to the #project-blt Slack channel.

        Args:
            message (str): The message to send
            tweet_url (str, optional): URL of the tweet
            image_path (str, optional): Path to an image
            error (str, optional): Error message if the tweet failed
        """
        try:
            # Get the OWASP BLT organization's Slack integration
            from website.models import Organization, SlackIntegration

            # Find the OWASP BLT organization
            owasp_org = Organization.objects.filter(name__icontains="OWASP BLT").first()
            if not owasp_org:
                logging.warning("OWASP BLT organization not found")
                return False

            # Find the Slack integration for the organization
            slack_integration = SlackIntegration.objects.filter(integration__organization=owasp_org).first()

            if not slack_integration or not slack_integration.bot_access_token:
                logging.warning("Slack integration not found or token missing")
                return False

            # Get the bot token and channel ID
            bot_token = slack_integration.bot_access_token
            channel_id = slack_integration.default_channel_id

            # If no channel ID is set, try to find the #project-blt channel
            if not channel_id:
                try:
                    # Use Slack API to find the channel
                    headers = {"Authorization": f"Bearer {bot_token}", "Content-Type": "application/json"}
                    response = requests.get("https://slack.com/api/conversations.list", headers=headers)
                    response.raise_for_status()

                    data = response.json()
                    if data.get("ok"):
                        for channel in data.get("channels", []):
                            if channel.get("name") == "project-blt":
                                channel_id = channel.get("id")
                                break
                except Exception as e:
                    logging.error(f"Error finding #project-blt channel: {str(e)}")
                    return False

            if not channel_id:
                logging.warning("Could not find #project-blt channel")
                return False

            # Prepare the message blocks
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": f"*New Tweet*\n{message}"}}]

            # Add tweet URL if available
            if tweet_url:
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"<{tweet_url}|View Tweet>"}})

            # Add error information if available
            if error:
                blocks.append(
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*Error sending tweet:*\n{error}"}}
                )

            # Prepare the payload
            payload = {
                "channel": channel_id,
                "blocks": blocks,
                "text": f"New Tweet: {message}",  # Fallback text
            }

            # Send the message
            headers = {"Authorization": f"Bearer {bot_token}", "Content-Type": "application/json"}

            # If there's an image, upload it first
            if image_path:
                try:
                    # Upload the file
                    upload_response = requests.post(
                        "https://slack.com/api/files.upload",
                        headers={"Authorization": f"Bearer {bot_token}"},
                        files={"file": open(image_path, "rb")},
                        data={"channels": channel_id, "initial_comment": f"New Tweet: {message}"},
                    )

                    if not upload_response.json().get("ok"):
                        logging.warning(f"Error uploading image to Slack: {upload_response.json().get('error')}")
                except Exception as e:
                    logging.error(f"Error uploading image to Slack: {str(e)}")

            # Send the message
            response = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload)

            response.raise_for_status()

            if not response.json().get("ok"):
                logging.warning(f"Error sending message to Slack: {response.json().get('error')}")
                return False

            return True
        except Exception as e:
            logging.error(f"Error sending to Slack: {str(e)}")
            return False


def check_security_txt(domain_url):
    """
    Check if a domain has a security.txt file according to RFC 9116.
    Checks both /.well-known/security.txt and /security.txt locations.

    Args:
        domain_url (str): URL of the domain to check

    Returns:
        bool: True if security.txt is found, False otherwise
    """
    import requests

    # Ensure URL has a scheme
    if not domain_url.startswith(("http://", "https://")):
        domain_url = "https://" + domain_url

    # Remove trailing slash if present
    if domain_url.endswith("/"):
        domain_url = domain_url[:-1]

    # Check at well-known location first (/.well-known/security.txt)
    well_known_url = f"{domain_url}/.well-known/security.txt"

    try:
        response = requests.head(well_known_url, timeout=5)
        if response.status_code == 200:
            return True
    except requests.RequestException:
        pass

    # If not found, check at root location (/security.txt)
    root_url = f"{domain_url}/security.txt"

    try:
        response = requests.head(root_url, timeout=5)
        if response.status_code == 200:
            return True
    except requests.RequestException:
        pass

    # If we reach here, no security.txt was found
    return False


def analyze_contribution(instance, action_type):
    """
    Analyze a contribution using OpenAI to determine BACON token reward.
    Returns a score between 1-50 based on complexity, impact, and quality.
    """
    # If OpenAI client is not available, return default score
    if client is None:
        logging.warning("OpenAI client not available (missing or invalid API key), using default BACON score")
        model_name = instance._meta.model_name
        is_security = getattr(instance, "is_security", False)
        return get_default_bacon_score(model_name, is_security)

    try:
        # Extract relevant data from the instance
        model_name = instance._meta.model_name
        title = getattr(instance, "title", None) or getattr(instance, "description", None)
        description = getattr(instance, "content", None) or getattr(instance, "body", None)
        is_security = getattr(instance, "is_security", False)

        # Construct the analysis prompt
        prompt = f"""
        Analyze this contribution and assign a BACON token reward score between 1 and 50.
        
        Contribution Details:
        - Type: {model_name}
        - Action: {action_type}
        - Title: {title}
        - Description: {description}
        - Security Related: {is_security}

        Scoring Guidelines:
        - Basic contributions (simple issues, comments): 1-5 BACON
        - Standard contributions (well-documented issues, blog posts): 5-15 BACON
        - Valuable contributions (detailed bug reports, tutorials): 15-25 BACON
        - High-impact contributions (security vulnerabilities, major features): 25-50 BACON

        Evaluation Criteria:
        1. Technical complexity
        2. Documentation quality
        3. Security impact
        4. Community benefit
        5. Overall effort

        Return only a number between 1 and 50.
        """

        # Get response from OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are evaluating contributions to determine BACON token rewards."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=10,
        )

        # Extract and validate the score
        try:
            score = int(float(response.choices[0].message.content.strip()))
            # Ensure score is within bounds
            score = max(1, min(50, score))
            return score
        except (ValueError, AttributeError):
            # Default scores if parsing fails
            return get_default_bacon_score(model_name, is_security)

    except Exception as e:
        logging.error(f"Error analyzing contribution for BACON score: {str(e)}")
        return get_default_bacon_score(model_name, is_security)


def get_default_bacon_score(model_name, is_security=False):
    """
    Get default BACON score based on contribution type.
    """
    base_scores = {
        "issue": 5,
        "post": 10,
        "hunt": 15,
        "ipreport": 3,
        "organization": 10,
        "forumpost": 2,
    }

    # Get base score or default to 5
    score = base_scores.get(model_name.lower(), 5)

    # Add bonus for security-related content
    if is_security:
        score += 3

    return score
