import os
import re
import time
from collections import deque
from urllib.parse import urlparse, urlsplit, urlunparse

import markdown
import openai
import requests
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import HttpRequest, HttpResponseBadRequest
from django.shortcuts import redirect

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
        new_emails = set(
            re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", response.text, re.I)
        )
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
        error = "invalid image content-type"
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
            safe_url = urlunparse(
                (referer_url.scheme, referer_url.netloc, referer_url.path, "", "", "")
            )
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


def markdown_to_text(markdown_content):
    """Convert Markdown to plain text."""
    html_content = markdown.markdown(markdown_content)
    text_content = BeautifulSoup(html_content, "html.parser").get_text()
    return text_content


openai.api_key = os.getenv("OPENAI_API_KEY")


def generate_labels(readme_content, github_topics):
    prompt = f"""
    You are an AI that assigns relevant labels to GitHub projects based on their readme content and github topics.

    ### Input:
    - **README Content:** {readme_content}
    - **GitHub Topics:** {github_topics}

    ### Task:
    Analyze the input and assign appropriate labels. 
    Labels should include:
    1. **Technology Stacks** (e.g., Python, JavaScript, Java).
    2. **Project Type** (e.g., Web Application, CLI Tool, Library).
    3. **OWASP Relevance** (e.g., Security Testing, Secure Coding).
    4. Any other relevant labels.

    ### Output:
    Provide the labels in JSON format like this:
    {{
      "tech-stack": ["Python", "JavaScript"],
      "project-type": ["Web Application"],
      "owasp-relevance": ["Secure Coding"],
      "other": ["Machine Learning", "Data Processing"]
    }}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant for labeling projects."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )

    return response["choices"][0]["message"]["content"]


def ai_summary(text, topics=None):
    """Generate an AI-driven summary using OpenAI's GPT, including GitHub topics."""
    try:
        topics_str = ", ".join(topics) if topics else "No topics provided."
        prompt = f"Generate a brief summary of the following text, focusing on key aspects such as purpose, features, technologies used, and current status. Consider the following GitHub topics to enhance the context: {topics_str}\n\n{text}"
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            temperature=0.5,
        )
        summary = response.choices[0].text.strip()
        return summary
    except Exception as e:
        return f"Error generating summary: {str(e)}"
