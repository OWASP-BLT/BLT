import logging
import math
import os
import re
import time

import requests
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from slack_bolt import App
from slack_bolt.adapter.django import SlackRequestHandler

if os.getenv("ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET:
    logger.warning("Slack environment not set. Slack integration disabled.")
    app = None
    handler = None
else:
    app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
    handler = SlackRequestHandler(app)

pagination_data = {}

repo_cache = {"timestamp": 0, "data": []}
CACHE_DURATION = 3600


def get_all_owasp_repos():
    """Fetch ALL repos from the OWASP org by paginating through the results."""
    current_time = time.time()
    if repo_cache["data"] and (current_time - repo_cache["timestamp"] < CACHE_DURATION):
        logger.debug("Using cached OWASP repositories.")
        return repo_cache["data"]

    all_repos = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/orgs/OWASP/repos?page={page}&per_page=100",
            headers={"Accept": "application/vnd.github.mercy-preview+json"},
        )
        if resp.status_code != 200:
            logger.error(f"Failed to fetch repos (page {page}): {resp.text}")
            break

        page_data = resp.json()
        if not page_data:
            break  # no more repositories
        all_repos.extend(page_data)
        page += 1

    repo_cache["data"] = all_repos
    repo_cache["timestamp"] = current_time
    logger.debug("Fetched and cached OWASP repositories.")

    return all_repos


if app:

    @app.command("/discover")
    def handle_discover_command(ack, client, command):
        try:
            ack()

            # Extract the search term from the command text
            search_term = command.get("text", "").strip()

            # If search term exists then search for OWASP projects
            if search_term:
                repos = get_all_owasp_repos()
                if not repos:
                    send_dm(client, command["user_id"], "Failed to fetch OWASP repositories.")
                    return

                matched = []
                url_pattern = re.compile(r"https?://\S+")

                for idx, repo in enumerate(repos, start=1):
                    name_desc = (repo["name"] + " " + (repo["description"] or "")).lower()
                    lang = (repo["language"] or "").lower()
                    topics = [t.lower() for t in repo.get("topics", [])]

                    if search_term.lower() in name_desc or search_term.lower() in lang or search_term.lower() in topics:
                        desc = repo["description"] or "No description provided."

                        found_urls = url_pattern.findall(desc)
                        if found_urls:
                            link = found_urls[0]
                            link_label = "Website"
                        else:
                            link = f"https://owasp.org/www-project-{repo['name'].lower()}"
                            link_label = "Wiki"

                        matched.append(
                            {
                                "owner_repo": repo["full_name"],
                                "name": repo["name"],
                                "description": desc,
                                "link_label": link_label,
                                "link": link,
                                "html_url": repo["html_url"],
                            }
                        )

                if not matched:
                    send_dm(
                        client,
                        command["user_id"],
                        f"No OWASP projects found matching '{search_term}'.",
                    )
                    return

                pagination_data[command["user_id"]] = {
                    "matched": matched,
                    "current_page": 0,
                    "page_size": 8,
                }

                send_paged_results(client, command["user_id"], search_term)

            else:
                try:
                    client.conversations_join(channel=command["channel_id"])
                except Exception as channel_error:
                    logger.debug(f"Could not join channel: {channel_error}")
                    pass

                try:
                    gh_response = requests.get("https://api.github.com/orgs/OWASP-BLT/repos")
                    if gh_response.status_code == 200:
                        repos = gh_response.json()
                        if not repos:
                            send_dm(client, command["user_id"], "No repositories found for OWASP-BLT.")
                        else:
                            repo_list = []
                            for idx, repo in enumerate(repos, start=1):
                                desc = repo["description"] if repo["description"] else "No description provided."
                                repo_list.append(f"{idx}. <{repo['html_url']}|{repo['name']}> - {desc}")

                            blocks = [
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": "Here are the OWASP BLT project repositories:\n" + "\n".join(repo_list),
                                    },
                                },
                                {
                                    "type": "actions",
                                    "elements": [
                                        {
                                            "type": "static_select",
                                            "placeholder": {
                                                "type": "plain_text",
                                                "text": "Select a repository to view issues",
                                            },
                                            "options": [
                                                {
                                                    "text": {
                                                        "type": "plain_text",
                                                        "text": f"{repo['name']}",
                                                    },
                                                    "value": f"OWASP-BLT/{repo['name']}",
                                                }
                                                for repo in repos
                                            ],
                                            "action_id": "select_repository",
                                        }
                                    ],
                                },
                            ]

                            send_dm(
                                client,
                                command["user_id"],
                                "Please select a repository to view its latest issues:",
                                blocks,
                            )
                    else:
                        send_dm(
                            client,
                            command["user_id"],
                            "Failed to fetch repositories from OWASP-BLT.",
                        )

                except Exception as e:
                    logger.error(f"Error processing repositories: {e}")
                    send_dm(
                        client,
                        command["user_id"],
                        "An error occurred while processing your request.",
                    )

        except Exception as e:
            logger.error(f"Error handling /discover command: {e}")

    app.action("select_repository")

    def handle_repository_selection(ack, body, client):
        try:
            ack()
            user_id = body["user"]["id"]
            selected_repo = body["actions"][0]["selected_option"]["value"]
            logger.debug(f"User {user_id} selected repository: {selected_repo}")

            # Fetch latest issues from the selected GitHub repository
            issues_response = requests.get(f"https://api.github.com/repos/{selected_repo}/issues")
            if issues_response.status_code == 200:
                issues = issues_response.json()
                issues = [issue for issue in issues if "pull_request" not in issue]
                if not issues:
                    send_dm(client, user_id, "No issues found for this repository.")
                else:
                    issues_list = [
                        f"- <{issue['html_url']}|{issue['title']}> (#{issue['number']})" for issue in issues[:5]
                    ]
                    issues_text = "Here are the latest issues:\n" + "\n".join(issues_list)
                    send_dm(client, user_id, issues_text)

            else:
                send_dm(client, user_id, "Failed to fetch issues for the selected repository.")

        except Exception as e:
            logger.error(f"Error handling repository selection: {e}")

    @app.action("pagination_prev")
    def handle_pagination_prev(ack, body, client):
        """Handles the 'Previous' pagination button."""
        try:
            ack()
            user_id = body["user"]["id"]
            search_term = body.get("state", {}).get("values", {}).get("search_term", "Topic")

            if user_id not in pagination_data:
                send_dm(client, user_id, "No pagination data found.")
                return

            data = pagination_data[user_id]
            data["current_page"] = max(0, data["current_page"] - 1)

            send_paged_results(client, user_id, search_term)

        except Exception as e:
            logger.error(f"Error handling pagination action: {e}")

    @app.action("pagination_next")
    def handle_pagination_next(ack, body, client):
        """Handles the 'Next' pagination button"""
        try:
            ack()
            user_id = body["user"]["id"]
            search_term = body.get("state", {}).get("values", {}).get("search_term", "Topic")

            if user_id not in pagination_data:
                send_dm(client, user_id, "No pagination data found.")
                return

            data = pagination_data[user_id]
            data["current_page"] += 1

            total_pages = math.ceil(len(data["matched"]) / data["page_size"])

            data["current_page"] = min(data["current_page"], total_pages - 1)
            send_paged_results(client, user_id, search_term)

        except Exception as e:
            logger.error(f"Error handling pagination action: {e}")

    def send_paged_results(client, user_id, search_term):
        """Sends the current page of matched projects to the user with next/prev buttons if needed."""
        data = pagination_data[user_id]
        matched = data["matched"]
        page_size = data["page_size"]
        total_pages = math.ceil(len(matched) / page_size)
        current_page = data["current_page"]

        start_idx = current_page * page_size
        end_idx = start_idx + page_size
        chunk = matched[start_idx:end_idx]

        text_chunk = "\n".join(
            [
                f"{idx + start_idx + 1}. <{project['html_url']}|{project['name']}> - {project['description']}\n   {project['link_label']}: <{project['link']}|Link>"
                for idx, project in enumerate(chunk)
            ]
        )

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"Here are the OWASP Projects matching *{search_term}* "
                        f"(page {current_page + 1}/{total_pages}):\n{text_chunk}"
                    ),
                },
            },
            {"type": "actions", "elements": []},
        ]

        # Add Prev button if not on the first page already
        if current_page > 0:
            blocks[1]["elements"].append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Previous"},
                    "value": "PREV",
                    "action_id": "pagination_prev",
                }
            )

        # Next button if not on last page already
        if current_page < (total_pages - 1):
            blocks[1]["elements"].append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Next"},
                    "value": "NEXT",
                    "action_id": "pagination_next",
                }
            )

        options = [
            {
                "text": {"type": "plain_text", "text": project["name"]},
                "value": project["owner_repo"],
            }
            for project in chunk
        ]

        # Also keep the static_select for issues
        if options:
            blocks[1]["elements"].append(
                {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a repository to view its latest issues",
                    },
                    "options": options,
                    "action_id": "select_repository",
                }
            )
        send_dm(client, user_id, f"Found {len(matched)} matching OWASP projects.", blocks)

    def send_dm(client, user_id, text, blocks=None):
        """Utility function to open a DM channel with user and send them a message."""
        try:
            dm_response = client.conversations_open(users=[user_id])
            if not dm_response["ok"]:
                logger.error(f"Failed to open DM channel: {dm_response['error']}")
                return

            dm_channel_id = dm_response["channel"]["id"]
            message_response = client.chat_postMessage(
                channel=dm_channel_id,
                text=text,
                blocks=blocks,
                mrkdwn=True,
                unfurl_links=False,
                unfurl_media=False,
            )
            if not message_response["ok"]:
                logger.error(f"Failed to send DM: {message_response.get('error', 'Unknown error')}")
                return

            logger.debug(f"Successfully sent DM to user {user_id} in channel {dm_channel_id}")

        except Exception as e:
            logger.error(f"Error sending DM to user {user_id}: {e}")


def slack_landing_page(request):
    """Landing page for Slack bot with features and installation button."""
    slack_client_id = os.environ.get("SLACK_ID_CLIENT")
    context = {
        "slack_client_id": slack_client_id,
    }
    return render(request, "slack.html", context)


@csrf_exempt
def slack_commands(request):
    logger.debug(f"Received Slack command with content type: {request.content_type}")
    if not handler:
        return JsonResponse({"error": "Slack integration is disabled."}, status=400)
    if request.method == "POST":
        if request.content_type != "application/x-www-form-urlencoded":
            return JsonResponse({"error": "Invalid content type"}, status=415)
        return HttpResponse(handler.handle(request))
    return JsonResponse({"error": "Method not allowed"}, status=405)
