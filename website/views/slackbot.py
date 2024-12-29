import logging
import os

import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from slack_bolt import App
from slack_bolt.adapter.django import SlackRequestHandler

if os.getenv("ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"), signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)
handler = SlackRequestHandler(app)


@app.command("/discover")
def handle_discover_command(ack, client, command):
    try:
        ack()
        try:
            client.conversations_join(channel=command["channel_id"])
        except Exception as channel_error:
            logger.debug(f"Could not join channel: {channel_error}")

        try:
            gh_response = requests.get("https://api.github.com/orgs/OWASP-BLT/repos")
            if gh_response.status_code == 200:
                repos = gh_response.json()
                if not repos:
                    send_dm(client, command["user_id"], "No repositories found for OWASP-BLT.")
                else:
                    repo_list = []
                    for idx, repo in enumerate(repos, start=1):
                        desc = (
                            repo["description"]
                            if repo["description"]
                            else "No description provided."
                        )
                        repo_list.append(f"{idx}. <{repo['html_url']}|{repo['name']}> - {desc}")

                    blocks = [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "Here are the OWASP BLT project repositories:\n"
                                + "\n".join(repo_list),
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
                                            "value": f"{repo['name']}",
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
                send_dm(client, command["user_id"], "Failed to fetch repositories from OWASP-BLT.")
        except Exception as e:
            logger.error(f"Error processing repositories: {e}")
            send_dm(client, command["user_id"], "An error occurred while processing your request.")

    except Exception as e:
        logger.error(f"Error handling /discover command: {e}")


@app.action("select_repository")
def handle_repository_selection(ack, body, client):
    try:
        ack()
        user_id = body["user"]["id"]
        selected_repo = body["actions"][0]["selected_option"]["value"]
        logger.debug(f"User {user_id} selected repository: {selected_repo}")

        issues_response = requests.get(
            f"https://api.github.com/repos/OWASP-BLT/{selected_repo}/issues"
        )
        if issues_response.status_code == 200:
            issues = [issue for issue in issues_response.json() if "pull_request" not in issue]
            if not issues:
                send_dm(client, user_id, "No issues found for this repository.")
            else:
                issues_list = [
                    f"- <{issue['html_url']}|{issue['title']}> (#{issue['number']})"
                    for issue in issues[:5]
                ]
                issues_text = "Here are the latest issues:\n" + "\n".join(issues_list)
                send_dm(client, user_id, issues_text)
        else:
            send_dm(client, user_id, "Failed to fetch issues for the selected repository.")
    except Exception as e:
        logger.error(f"Error handling repository selection: {e}")


def send_dm(client, user_id, text, blocks=None):
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
    except Exception as e:
        logger.error(f"Error sending DM to user {user_id}: {e}")


@csrf_exempt
def slack_commands(request):
    logger.debug(f"Received Slack command with content type: {request.content_type}")

    if request.method == "POST":
        if request.content_type != "application/x-www-form-urlencoded":
            return JsonResponse({"error": "Invalid content type"}, status=415)

        return HttpResponse(handler.handle(request))
    return JsonResponse({"error": "Method not allowed"}, status=405)
