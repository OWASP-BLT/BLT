import hashlib
import hmac
import json
import math
import os
import re
import threading
import time

import requests
from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from slack import WebClient
from slack_sdk.errors import SlackApiError

from website.models import Domain, Hunt, Issue, Project, SlackBotActivity, SlackIntegration, User

if os.getenv("ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
client = WebClient(token=SLACK_TOKEN)

# Add at the top with other environment variables
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Replace GSoC cache with hardcoded project data
GSOC_PROJECTS = [
    {
        "title": "BLT (Bug Logging Tool)",
        "tech": "Python, Django, Flutter, Blockchain",
        "mentor": "Donnie, Yash Pandey",
        "repo": "https://github.com/OWASP-BLT/BLT",
    },
    {
        "title": "OWASP Juice Shop",
        "tech": "TypeScript, JavaScript",
        "mentor": "Bjoern Kimminich, Shubham Palriwala, Jannik Hollenbach",
        "repo": "https://github.com/juice-shop/juice-shop",
    },
    {
        "title": "OWASP DevSecOps Maturity Model",
        "tech": "TypeScript, HTML",
        "mentor": "Timo Pagel, Aryan Prasad",
        "repo": "https://github.com/devsecopsmaturitymodel/DevSecOps-MaturityModel",
    },
    {
        "title": "OWASP OWTF",
        "tech": "Python, TypeScript, JavaScript",
        "mentor": "Viyat Bhalodia, Abraham Aranguran",
        "repo": "https://github.com/owtf/owtf",
    },
    {
        "title": "OWASP secureCodeBox",
        "tech": "JavaScript, Go, Python, Java",
        "mentor": "Jannik Hollenbach, Robert Felber",
        "repo": "https://github.com/secureCodeBox/secureCodeBox",
    },
    {
        "title": "OWASP Nettacker",
        "tech": "Python, Css, JavaScript",
        "mentor": "Sam Stepanyan, Ali Razmjoo, Arkadii Yakovets",
        "repo": "https://github.com/OWASP/Nettacker",
    },
    {
        "title": "OWASP Threat Dragon",
        "tech": "JavaScript, Vue.js",
        "mentor": "Jon Gadsden",
        "repo": "https://github.com/OWASP/threat-dragon",
    },
    {
        "title": "OWASP Website",
        "tech": "HTML, CSS, JavaScript, Github",
        "mentor": "Donnie",
        "repo": "https://github.com/orgs/OWASP",
    },
]


def verify_slack_signature(request):
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Check if required headers are present
    if not timestamp or not signature:
        return False

    try:
        # Verify timestamp to prevent replay attacks
        current_time = time.time()
        request_time = float(timestamp)
        time_diff = abs(current_time - request_time)

        if time_diff > 60 * 5:
            return False

        # Create the signature base string
        sig_basestring = f"v0:{timestamp}:{request.body.decode()}"

        # Calculate our signature
        my_signature = "v0=" + hmac.new(SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()

        # Compare signatures
        is_valid = hmac.compare_digest(my_signature, signature)
        return is_valid

    except (ValueError, TypeError) as e:
        return False


@csrf_exempt
def slack_events(request):
    """Handle incoming Slack events and interactions"""
    if request.method == "POST":
        if not verify_slack_signature(request):
            return HttpResponse(status=403)

        if request.content_type == "application/x-www-form-urlencoded":
            try:
                # Handle Interactive Components
                payload = json.loads(request.POST.get("payload", "{}"))
                team_id = payload.get("team", {}).get("id")
                user_id = payload.get("user", {}).get("id")

                # Get the correct token for the workspace
                try:
                    slack_integration = SlackIntegration.objects.get(workspace_name=team_id)
                    workspace_token = slack_integration.bot_access_token
                except SlackIntegration.DoesNotExist:
                    if team_id == "T04T40NHX":  # OWASP workspace
                        workspace_token = SLACK_TOKEN
                    else:
                        return JsonResponse(
                            {
                                "response_type": "ephemeral",
                                "text": "⚠️ This workspace is not properly configured. Please reinstall the app.",
                            }
                        )

                # Create workspace-specific client
                workspace_client = WebClient(token=workspace_token)

                # Verify user exists in the workspace
                try:
                    user_info = workspace_client.users_info(user=user_id)
                    if not user_info["ok"]:
                        return JsonResponse(
                            {"response_type": "ephemeral", "text": "⚠️ Unable to verify user in workspace."}
                        )
                except SlackApiError:
                    return JsonResponse({"response_type": "ephemeral", "text": "⚠️ Unable to verify user in workspace."})

                action_type = payload.get("type")
                if action_type == "block_actions":
                    action_id = payload["actions"][0]["action_id"]
                    if action_id == "select_repository":
                        return handle_repository_selection(ack=lambda: None, body=payload, client=workspace_client)
                    elif action_id == "pagination_prev":
                        return handle_pagination_prev(ack=lambda: None, body=payload, client=workspace_client)
                    elif action_id == "pagination_next":
                        return handle_pagination_next(ack=lambda: None, body=payload, client=workspace_client)

            except json.JSONDecodeError:
                return JsonResponse({"response_type": "ephemeral", "text": "⚠️ Invalid request format."}, status=400)

        elif request.content_type == "application/json":
            # Handle Events API requests
            data = json.loads(request.body)

            # Check if this is a retry event
            is_retry = request.headers.get("X-Slack-Retry-Num")
            if is_retry:
                return HttpResponse(status=200)

            if "challenge" in data:
                return JsonResponse({"challenge": data["challenge"]})

            event = data.get("event", {})
            event_type = event.get("type")

            if event_type == "team_join":
                user_data = event.get("user", {})
                if isinstance(user_data, dict):
                    user_id = user_data.get("id")
                else:
                    user_id = event.get("user")

                if user_id:
                    _handle_team_join(user_id, request)

        return HttpResponse(status=200)
    return HttpResponse(status=405)


def _handle_team_join(user_id, request):
    try:
        event_data = json.loads(request.body)
        team_id = event_data["team_id"]

        # Log the activity at the start
        activity = SlackBotActivity.objects.create(
            workspace_id=team_id, activity_type="team_join", user_id=user_id, details={"event_data": event_data}
        )

        try:
            slack_integration = SlackIntegration.objects.get(workspace_name=team_id)
            activity.workspace_name = slack_integration.integration.organization.name
            activity.save()

            # If integration exists and has welcome message
            if slack_integration.welcome_message:
                welcome_message = slack_integration.welcome_message
                workspace_client = WebClient(token=slack_integration.bot_access_token)
            else:
                # If no welcome message but it's OWASP workspace
                if team_id == "T04T40NHX":
                    workspace_client = WebClient(token=SLACK_TOKEN)
                    welcome_message = (
                        f":tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:\n\n"
                        "We're thrilled to have you here! Whether you're new to OWASP or a long-time contributor, "
                        "this Slack workspace is the perfect place to connect, collaborate, and stay informed about all things OWASP.\n\n"
                        ":small_blue_diamond: *Get Involved:*\n"
                        "• Check out the *#contribute* channel to find ways to get involved with OWASP projects and initiatives.\n"
                        "• Explore individual project channels, which are named *#project-name*, to dive into specific projects that interest you.\n"
                        "• Join our chapter channels, named *#chapter-name*, to connect with local OWASP members in your area.\n\n"
                        ":small_blue_diamond: *Stay Updated:*\n"
                        "• Visit *#newsroom* for the latest updates and announcements.\n"
                        "• Follow *#external-activities* for news about OWASP's engagement with the wider security community.\n\n"
                        ":small_blue_diamond: *Connect and Learn:*\n"
                        "• *#jobs*: Looking for new opportunities? Check out the latest job postings here.\n"
                        "• *#leaders*: Connect with OWASP leaders and stay informed about leadership activities.\n"
                        "• *#project-committee*: Engage with the committee overseeing OWASP projects.\n"
                        "• *#gsoc*: Stay updated on Google Summer of Code initiatives.\n"
                        "• *#github-admins*: Get support and discuss issues related to OWASP's GitHub repositories.\n"
                        "• *#learning*: Share and find resources to expand your knowledge in the field of application security.\n\n"
                        "We're excited to see the amazing contributions you'll make. If you have any questions or need assistance, don't hesitate to ask. "
                        "Let's work together to make software security visible and improve the security of the software we all rely on.\n\n"
                        "Welcome aboard! :rocket:"
                    )
                else:
                    workspace_client = WebClient(token=slack_integration.bot_access_token)
                    welcome_message = (
                        f"Welcome <@{user_id}>! 👋\n\n"
                        "Your workspace admin hasn't set up a custom welcome message yet. "
                        "They can configure this in the organization's integration settings."
                    )

        except SlackIntegration.DoesNotExist:
            # If no integration exists but it's OWASP workspace
            if team_id == "T04T40NHX":
                workspace_client = WebClient(token=SLACK_TOKEN)
                # Use the default OWASP welcome message
                welcome_message = (
                    f":tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:\n\n"
                    "We're thrilled to have you here! Whether you're new to OWASP or a long-time contributor, "
                    "this Slack workspace is the perfect place to connect, collaborate, and stay informed about all things OWASP.\n\n"
                    ":small_blue_diamond: *Get Involved:*\n"
                    "• Check out the *#contribute* channel to find ways to get involved with OWASP projects and initiatives.\n"
                    "• Explore individual project channels, which are named *#project-name*, to dive into specific projects that interest you.\n"
                    "• Join our chapter channels, named *#chapter-name*, to connect with local OWASP members in your area.\n\n"
                    ":small_blue_diamond: *Stay Updated:*\n"
                    "• Visit *#newsroom* for the latest updates and announcements.\n"
                    "• Follow *#external-activities* for news about OWASP's engagement with the wider security community.\n\n"
                    ":small_blue_diamond: *Connect and Learn:*\n"
                    "• *#jobs*: Looking for new opportunities? Check out the latest job postings here.\n"
                    "• *#leaders*: Connect with OWASP leaders and stay informed about leadership activities.\n"
                    "• *#project-committee*: Engage with the committee overseeing OWASP projects.\n"
                    "• *#gsoc*: Stay updated on Google Summer of Code initiatives.\n"
                    "• *#github-admins*: Get support and discuss issues related to OWASP's GitHub repositories.\n"
                    "• *#learning*: Share and find resources to expand your knowledge in the field of application security.\n\n"
                    "We're excited to see the amazing contributions you'll make. If you have any questions or need assistance, don't hesitate to ask. "
                    "Let's work together to make software security visible and improve the security of the software we all rely on.\n\n"
                    "Welcome aboard! :rocket:"
                )
            else:
                return

        # Add delay to ensure user is fully joined
        time.sleep(2)  # Wait 2 seconds before sending message

        # Try to open DM first
        try:
            dm_response = workspace_client.conversations_open(users=[user_id])
            if not dm_response["ok"]:
                return

            dm_channel = dm_response["channel"]["id"]

            welcome_blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": welcome_message}}]

            # Send message using appropriate client
            welcome_response = workspace_client.chat_postMessage(
                channel=dm_channel, text=welcome_message, blocks=welcome_blocks
            )

        except SlackApiError as e:
            activity.success = False
            activity.error_message = str(e)
            activity.save()
            return

    except Exception as e:
        SlackBotActivity.objects.create(
            workspace_id=team_id if "team_id" in locals() else "unknown",
            activity_type="team_join",
            user_id=user_id,
            success=False,
            error_message=str(e),
        )
        return


@csrf_exempt
def slack_commands(request):
    """Handle Slack slash commands"""
    if request.method == "POST":
        # Verify the request is from Slack
        is_valid = verify_slack_signature(request)

        if not is_valid:
            return HttpResponse(status=403)

        command = request.POST.get("command")
        user_id = request.POST.get("user_id")
        team_id = request.POST.get("team_id")
        team_domain = request.POST.get("team_domain")  # Get the team domain

        # Log the command activity
        activity = SlackBotActivity.objects.create(
            workspace_id=team_id,
            workspace_name=team_domain,
            activity_type="command",
            user_id=user_id,
            details={"command": command, "channel_id": request.POST.get("channel_id")},
        )

        # Initialize workspace client
        try:
            slack_integration = SlackIntegration.objects.get(workspace_name=team_id)
            workspace_client = WebClient(token=slack_integration.bot_access_token)
        except SlackIntegration.DoesNotExist:
            if team_id == "T04T40NHX":
                workspace_client = WebClient(token=SLACK_TOKEN)
            else:
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "This workspace is not properly configured. Please contact the workspace admin.",
                    }
                )

        if command == "/discover":
            try:
                search_term = request.POST.get("text", "").strip()

                # First, send an immediate response to avoid timeout
                initial_response = {
                    "response_type": "ephemeral",
                    "text": "🔍 Searching OWASP projects... I'll send you the results in a DM shortly!",
                }

                if search_term:
                    # Return immediate response to Slack
                    response = JsonResponse(initial_response)

                    # Then process the search asynchronously
                    def process_search():
                        try:
                            repos = get_all_owasp_repos()
                            if not repos:
                                send_dm(workspace_client, user_id, "❌ Failed to fetch OWASP repositories.")
                                return

                            matched = []
                            url_pattern = re.compile(r"https?://\S+")

                            # Improve the display of search results with emojis and formatting
                            for idx, repo in enumerate(repos, start=1):
                                name_desc = (repo["name"] + " " + (repo["description"] or "")).lower()
                                lang = (repo["language"] or "").lower()
                                topics = [t.lower() for t in repo.get("topics", [])]

                                if (
                                    search_term.lower() in name_desc
                                    or search_term.lower() in lang
                                    or search_term.lower() in topics
                                ):
                                    desc = repo["description"] or "No description provided."
                                    found_urls = url_pattern.findall(desc)
                                    if found_urls:
                                        link = found_urls[0]
                                        link_label = "🌐 Website"
                                    else:
                                        link = f"https://owasp.org/www-project-{repo['name'].lower()}"
                                        link_label = "📚 Wiki"

                                    # Add language and topics info
                                    extra_info = []
                                    if repo["language"]:
                                        extra_info.append(f"💻 {repo['language']}")
                                    if repo.get("topics"):
                                        topics_str = ", ".join(f"#{topic}" for topic in repo["topics"][:3])
                                        if len(repo["topics"]) > 3:
                                            topics_str += f" +{len(repo['topics']) - 3} more"
                                        extra_info.append(f"🏷️ {topics_str}")

                                    matched.append(
                                        {
                                            "owner_repo": repo["full_name"],
                                            "name": repo["name"],
                                            "description": desc,
                                            "link_label": link_label,
                                            "link": link,
                                            "html_url": repo["html_url"],
                                            "extra_info": " | ".join(extra_info) if extra_info else None,
                                        }
                                    )

                            if not matched:
                                send_dm(
                                    workspace_client,
                                    user_id,
                                    f"❌ No OWASP projects found matching '*{search_term}*'.\nTry searching with different keywords!",
                                )
                                return

                            pagination_data[user_id] = {
                                "matched": matched,
                                "current_page": 0,
                                "page_size": 10,
                            }

                            send_paged_results(workspace_client, user_id, search_term)

                        except requests.RequestException as e:
                            send_dm(
                                workspace_client, user_id, "❌ Failed to fetch repositories: Network error occurred."
                            )
                        except json.JSONDecodeError as e:
                            send_dm(workspace_client, user_id, "❌ Failed to parse repository data.")
                        except (KeyError, AttributeError) as e:
                            send_dm(workspace_client, user_id, "❌ Invalid repository data format received.")

                    # Start processing in a separate thread
                    thread = threading.Thread(target=process_search)
                    thread.start()

                    return response

                else:
                    # Handle showing OWASP-BLT repositories
                    try:
                        headers = {"Accept": "application/vnd.github.v3+json"}
                        if GITHUB_TOKEN:
                            print("************************************")
                            print(f"GITHUB_TOKEN: {GITHUB_TOKEN}")
                            print("************************************")
                            headers["Authorization"] = f"token {GITHUB_TOKEN}"
                        else:
                            # If no token, return a message about rate limiting
                            return JsonResponse(
                                {
                                    "response_type": "ephemeral",
                                    "text": "⚠️ GitHub API token not configured. Please contact the administrator.",
                                }
                            )

                        gh_response = requests.get(
                            "https://api.github.com/orgs/OWASP-BLT/repos",
                            headers=headers,
                            timeout=10,  # Add timeout
                        )

                        if gh_response.status_code == 403:
                            if "rate limit exceeded" in gh_response.text.lower():
                                return JsonResponse(
                                    {
                                        "response_type": "ephemeral",
                                        "text": "⚠️ GitHub API rate limit exceeded. Please try again later.",
                                    }
                                )
                            return JsonResponse(
                                {
                                    "response_type": "ephemeral",
                                    "text": "⚠️ Access to GitHub API denied. Please check the token configuration.",
                                }
                            )
                        if gh_response.status_code == 200:
                            repos = gh_response.json()
                            if not repos:
                                send_dm(workspace_client, user_id, "No repositories found for OWASP-BLT.")
                            else:
                                # Create header block
                                blocks = [
                                    {
                                        "type": "header",
                                        "text": {"type": "plain_text", "text": "🔍 OWASP BLT Projects", "emoji": True},
                                    },
                                    {
                                        "type": "context",
                                        "elements": [{"type": "mrkdwn", "text": f"Found {len(repos)} repositories"}],
                                    },
                                    {"type": "divider"},
                                ]

                                # Add repository blocks
                                for idx, repo in enumerate(repos, start=1):
                                    desc = repo["description"] if repo["description"] else "No description provided."

                                    # Add language and topics info
                                    extra_info = []
                                    if repo.get("language"):
                                        extra_info.append(f"💻 {repo['language']}")
                                    if repo.get("topics"):
                                        topics_str = ", ".join(f"#{topic}" for topic in repo["topics"][:3])
                                        if len(repo["topics"]) > 3:
                                            topics_str += f" +{len(repo['topics']) - 3} more"
                                        extra_info.append(f"🏷️ {topics_str}")

                                    blocks.extend(
                                        [
                                            {
                                                "type": "section",
                                                "text": {
                                                    "type": "mrkdwn",
                                                    "text": (
                                                        f"*{idx}. <{repo['html_url']}|{repo['name']}>*\n"
                                                        f"{desc}\n"
                                                        f"{' | '.join(extra_info) if extra_info else ''}"
                                                    ),
                                                },
                                            },
                                            {"type": "divider"} if idx < len(repos) else None,
                                        ]
                                    )

                                # Remove None blocks
                                blocks = [b for b in blocks if b is not None]

                                # Add repository selector
                                blocks.append(
                                    {
                                        "type": "actions",
                                        "elements": [
                                            {
                                                "type": "static_select",
                                                "placeholder": {
                                                    "type": "plain_text",
                                                    "text": "View Repository Issues",
                                                    "emoji": True,
                                                },
                                                "options": [
                                                    {
                                                        "text": {
                                                            "type": "plain_text",
                                                            "text": repo["name"],
                                                            "emoji": True,
                                                        },
                                                        "value": f"OWASP-BLT/{repo['name']}",
                                                    }
                                                    for repo in repos
                                                ],
                                                "action_id": "select_repository",
                                            }
                                        ],
                                    }
                                )

                                send_dm(workspace_client, user_id, "Here are the OWASP BLT repositories:", blocks)
                                return JsonResponse(
                                    {
                                        "response_type": "ephemeral",
                                        "text": "I've sent you the repository list in a DM! 📚",
                                    }
                                )
                        else:
                            return JsonResponse(
                                {
                                    "response_type": "ephemeral",
                                    "text": "❌ Failed to fetch repositories from OWASP-BLT.",
                                }
                            )

                    except Exception as e:
                        activity.success = False
                        activity.error_message = str(e)
                        activity.save()
                        return JsonResponse(
                            {
                                "response_type": "ephemeral",
                                "text": "❌ An error occurred while processing your request.",
                            }
                        )

            except Exception as e:
                activity.success = False
                activity.error_message = str(e)
                activity.save()
                return JsonResponse(
                    {"response_type": "ephemeral", "text": "An error occurred while processing your request."}
                )

        elif command == "/stats":
            try:
                # Get project counts by status
                project_stats = Project.objects.values("status").annotate(count=Count("id"))
                stats_by_status = {stat["status"]: stat["count"] for stat in project_stats}
                total_projects = sum(stats_by_status.values())
                total_views = Project.objects.aggregate(total_views=Sum("project_visit_count"))["total_views"] or 0

                # Create interactive blocks for better visualization
                stats_blocks = [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "📊 OWASP Platform Statistics", "emoji": True},
                    },
                    {"type": "divider"},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*🎯 Project Categories*"}},
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Flagship:*\n{stats_by_status.get('flagship', 0)} projects 🏆",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Production:*\n{stats_by_status.get('production', 0)} projects ⚡",
                            },
                        ],
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Incubator:*\n{stats_by_status.get('incubator', 0)} projects 🌱",
                            },
                            {"type": "mrkdwn", "text": f"*Lab:*\n{stats_by_status.get('lab', 0)} projects 🔬"},
                        ],
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Inactive:*\n{stats_by_status.get('inactive', 0)} projects 💤",
                            },
                            {"type": "mrkdwn", "text": f"*Total Projects:*\n{total_projects} projects 📈"},
                        ],
                    },
                    {"type": "divider"},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*🔍 Project Activity*"}},
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"Total Project Views: *{total_views:,}* 👀"},
                    },
                    {"type": "divider"},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*📈 Platform Overview*"}},
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Issues:*\n{Issue.objects.count():,} 🐛"},
                            {"type": "mrkdwn", "text": f"*Users:*\n{User.objects.count():,} 👥"},
                        ],
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Domains:*\n{Domain.objects.count():,} 🌐"},
                            {"type": "mrkdwn", "text": f"*Hunts:*\n{Hunt.objects.count():,} 🎯"},
                        ],
                    },
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": "🕒 Stats generated at " + time.strftime("%Y-%m-%d %H:%M UTC")}
                        ],
                    },
                ]

                try:
                    # Open DM channel first
                    dm_response = workspace_client.conversations_open(users=[user_id])
                    if not dm_response["ok"]:
                        return JsonResponse(
                            {"response_type": "ephemeral", "text": "Sorry, I couldn't open a DM channel."}
                        )

                    dm_channel = dm_response["channel"]["id"]

                    # Send message to DM channel using the new blocks
                    workspace_client.chat_postMessage(
                        channel=dm_channel,
                        blocks=stats_blocks,
                        text="OWASP Platform Statistics",  # Fallback text
                    )

                    return JsonResponse(
                        {"response_type": "ephemeral", "text": "I've sent you the detailed statistics in a DM! 📊"}
                    )

                except SlackApiError as e:
                    activity.success = False
                    activity.error_message = f"Slack API error: {str(e)}"
                    activity.save()
                    return JsonResponse(
                        {
                            "response_type": "ephemeral",
                            "text": "Sorry, there was an error sending the statistics. Please try again later.",
                        }
                    )

            except (
                Project.DoesNotExist,
                Issue.DoesNotExist,
                User.DoesNotExist,
                Domain.DoesNotExist,
                Hunt.DoesNotExist,
            ) as e:
                activity.success = False
                activity.error_message = f"Database error: {str(e)}"
                activity.save()
                return JsonResponse(
                    {"response_type": "ephemeral", "text": "Sorry, there was an error retrieving the statistics."}
                )

        elif command == "/contrib":
            try:
                contribute_message = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":rocket: *Contributing to OWASP Projects*\n\n"
                            "    🔹 *Join the OWASP Slack Channel:* Find guidance and check pinned posts for projects seeking contributors.\n"
                            "    🔹 *Explore OWASP Projects Page:* Identify projects that align with your skills and interests.",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":loudspeaker: *Engaging on Slack*\n\n"
                            "    Many projects have dedicated project channels for collaboration.\n\n"
                            "   🔍 *Find and Join a Project Channel:*",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "To find project channels:\n\n"
                            + "1️⃣ Use Slack's channel browser (Ctrl/Cmd + K)\n"
                            + "2️⃣ Type *#project-* to see all project channels\n"
                            + "3️⃣ Join the channels that interest you\n\n"
                            + "_All OWASP project channels start with *#project-*_",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "    🛠 *GSOC Projects:* View this year's participating GSOC projects https://owasp.org/www-community/initiatives/gsoc/gsoc2025ideas",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":busts_in_silhouette: *Identifying Key People and Activity*\n\n"
                            "    • Visit the *OWASP Projects* page to find project leaders and contributors.\n"
                            "    • Review *GitHub commit history* for active developers.\n"
                            "    • Check *Slack activity* for updates on project progress.",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":pushpin: *Communication Guidelines*\n\n"
                            "    ✅ *Check pinned messages* in project channels for updates.\n"
                            "    ✅ *Ask questions* in relevant project channels.\n"
                            "    ✅ *Introduce yourself* while keeping personal details private.",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":hammer_and_wrench: *How to Contribute*\n\n"
                            "     1️⃣ *Select a project* and review its contribution guidelines.\n"
                            "     2️⃣ *Work on an open GitHub issue* or propose a new one.\n"
                            "     3️⃣ *Coordinate with project leaders* to prevent overlaps.\n"
                            "     4️⃣ *Submit a pull request* and keep the team informed.\n\n"
                            "    💡 *Focus on clear communication and teamwork!* 🚀",
                        },
                    },
                ]

                # Open DM channel first
                dm_response = workspace_client.conversations_open(users=[user_id])
                if not dm_response["ok"]:
                    return HttpResponse(status=500)

                dm_channel = dm_response["channel"]["id"]

                # Send message to DM channel
                message_response = workspace_client.chat_postMessage(
                    channel=dm_channel, blocks=contribute_message, mrkdwn=True
                )

                # Send ephemeral message in the channel where command was used
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "I've sent you a DM with information about contributing! 🚀",
                    }
                )

            except SlackApiError as e:
                activity.success = False
                activity.error_message = str(e)
                activity.save()
                return HttpResponse(status=500)

        elif command == "/gsoc25":
            try:
                search_term = request.POST.get("text", "").strip()
                team_id = request.POST.get("team_id")
                user_id = request.POST.get("user_id")

                # Prepare base blocks
                blocks = [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "🎓 Google Summer of Code 2025 - OWASP", "emoji": True},
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*Welcome to OWASP's GSoC 2025 Program!* 🚀"},
                    },
                ]

                # Add workspace-specific content
                if team_id == "T04T40NHX":  # OWASP workspace
                    blocks.extend(
                        [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": (
                                        "*Important Links:*\n"
                                        "• Join <#CFJLZNFN1|gsoc> for program discussions 💬\n"
                                        "• Check <#C04DH8HEPTR|contribute> for contribution guidelines 📝\n"
                                        "• View project ideas: <https://owasp.org/www-community/initiatives/gsoc/gsoc2025ideas|GSoC 2025 Ideas> 💡"
                                    ),
                                },
                            }
                        ]
                    )
                else:
                    blocks.extend(
                        [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": (
                                        "*Get Started:*\n"
                                        "1. Join OWASP Slack: <https://join.slack.com/t/owasp/shared_invite/zt-2y4cvxl3l-_S~G_iKEShwmbQACu~QRyQ|Click to Join> 🔗\n"
                                        "2. Once joined, check #gsoc and #contribute channels 📢\n"
                                        "3. View project ideas: <https://owasp.org/www-community/initiatives/gsoc/gsoc2025ideas|GSoC 2025 Ideas> 💡"
                                    ),
                                },
                            }
                        ]
                    )

                # Add search tip
                blocks.extend(
                    [
                        {"type": "divider"},
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    "*🔍 Search Tips:*\n"
                                    "• Search by technology: `/gsoc25 python`\n"
                                    "• Search by mentor: `/gsoc25 mentor:donnie`\n"
                                    "• Search by project: `/gsoc25 security`"
                                ),
                            },
                        },
                    ]
                )

                # Show search results or default projects
                if search_term:
                    matched_projects = filter_gsoc_projects(search_term)
                    if matched_projects:
                        blocks.extend(
                            [
                                {"type": "divider"},
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"*🎯 Found {len(matched_projects)} matching projects:*",
                                    },
                                },
                            ]
                        )

                        for project in matched_projects[:5]:
                            blocks.append(
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": (
                                            f"*{project['title']}* 📚\n"
                                            f"🔧 *Tech Stack:* {project['tech']}\n"
                                            f"👥 *Mentors:* {project['mentor']}\n"
                                            f"🔗 *Repository:* <{project['repo']}|View Project>"
                                        ),
                                    },
                                }
                            )

                        if len(matched_projects) > 5:
                            blocks.append(
                                {
                                    "type": "context",
                                    "elements": [
                                        {"type": "mrkdwn", "text": f"_Showing 5 of {len(matched_projects)} matches_"}
                                    ],
                                }
                            )
                    else:
                        blocks.append(
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "❌ No matching projects found. Try different search terms or check the full project list.",
                                },
                            }
                        )
                else:
                    # Show first 3 projects by default
                    blocks.extend(
                        [
                            {"type": "divider"},
                            {"type": "section", "text": {"type": "mrkdwn", "text": "*🌟 Featured Projects:*"}},
                        ]
                    )

                    for project in GSOC_PROJECTS[:3]:
                        blocks.append(
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": (
                                        f"*{project['title']}* 📚\n"
                                        f"🔧 *Tech Stack:* {project['tech']}\n"
                                        f"👥 *Mentors:* {project['mentor']}\n"
                                        f"🔗 *Repository:* <{project['repo']}|View Project>"
                                    ),
                                },
                            }
                        )

                    blocks.extend(
                        [
                            {"type": "divider"},
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "_💡 *Tip:* Use `/gsoc25 <technology>` to find projects matching your skills! For example: `/gsoc25 python` or `/gsoc25 javascript`_",
                                },
                            },
                        ]
                    )

                # Send response
                send_dm(workspace_client, user_id, "GSoC 2025 Information", blocks)
                return JsonResponse(
                    {"response_type": "ephemeral", "text": "I've sent you GSoC information in a DM! 📚"}
                )

            except (SlackApiError, KeyError, ValueError) as e:
                activity.success = False
                activity.error_message = str(e)
                activity.save()
                return JsonResponse({"response_type": "ephemeral", "text": f"❌ Error: {str(e)}"}, status=400)

    return HttpResponse(status=405)


def get_github_headers():
    """Helper function to get GitHub API headers with authentication"""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def get_all_owasp_repos():
    """Fetch ALL repos from the OWASP org by paginating through the results."""
    current_time = time.time()

    # Return cached data if available and not expired
    if repo_cache["data"] and (current_time - repo_cache["timestamp"]) < CACHE_DURATION:
        return repo_cache["data"]

    all_repos = []
    page = 1

    headers = get_github_headers()
    if not GITHUB_TOKEN:
        return []  # Return empty if no token available

    while True:
        try:
            resp = requests.get(
                f"https://api.github.com/orgs/OWASP/repos?page={page}&per_page=100", headers=headers, timeout=10
            )

            if resp.status_code == 403:
                if "rate limit exceeded" in resp.text.lower():
                    return []  # Handle rate limiting
                return []  # Handle other 403 errors

            if resp.status_code != 200:
                return []

            page_data = resp.json()
            if not page_data:
                break

            all_repos.extend(page_data)
            page += 1

        except (requests.RequestException, json.JSONDecodeError) as e:
            return []

    repo_cache["data"] = all_repos
    repo_cache["timestamp"] = current_time
    return all_repos


# Add other necessary helper functions and variables
pagination_data = {}
repo_cache = {"timestamp": 0, "data": []}
CACHE_DURATION = 3600


def send_dm(client, user_id, text, blocks=None):
    """Utility function to open a DM channel with user and send them a message."""
    try:
        dm_response = client.conversations_open(users=[user_id])
        if not dm_response["ok"]:
            return JsonResponse(
                {
                    "response_type": "ephemeral",
                    "text": f"❌ Failed to open DM channel: {dm_response.get('error', 'Unknown error')}",
                },
                status=503,
            )

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
            return JsonResponse(
                {
                    "response_type": "ephemeral",
                    "text": f"❌ Failed to send message: {message_response.get('error', 'Unknown error')}",
                },
                status=500,
            )

    except SlackApiError as e:
        if e.response["error"] == "ratelimited":
            return JsonResponse(
                {"response_type": "ephemeral", "text": "❌ Rate limit exceeded. Please try again later."}, status=429
            )
        return JsonResponse(
            {"response_type": "ephemeral", "text": f"❌ Slack API error: {e.response.get('error', 'Unknown error')}"},
            status=503,
        )
    except (KeyError, AttributeError) as e:
        return JsonResponse(
            {"response_type": "ephemeral", "text": "❌ Invalid response format from Slack API."}, status=500
        )


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

    # Create header block
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🔍 OWASP Projects matching '{search_term}'", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Found {len(matched)} projects • Page {current_page + 1} of {total_pages}"}
            ],
        },
        {"type": "divider"},
    ]

    # Add project blocks
    for idx, project in enumerate(chunk, start=start_idx + 1):
        blocks.extend(
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{idx}. <{project['html_url']}|{project['name']}>*\n"
                            f"{project['description']}\n"
                            f"{project.get('extra_info', '')}\n"
                            f"{project['link_label']}: <{project['link']}|Link>"
                        ),
                    },
                },
                {"type": "divider"} if idx < end_idx else None,
            ]
        )

    # Remove None blocks
    blocks = [b for b in blocks if b is not None]

    # Add navigation buttons
    navigation = {"type": "actions", "elements": []}

    if current_page > 0:
        navigation["elements"].append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "◀️ Previous", "emoji": True},
                "value": "PREV",
                "action_id": "pagination_prev",
            }
        )

    if current_page < (total_pages - 1):
        navigation["elements"].append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Next ▶️", "emoji": True},
                "value": "NEXT",
                "action_id": "pagination_next",
            }
        )

    # Add repository selector
    if chunk:
        navigation["elements"].append(
            {
                "type": "static_select",
                "placeholder": {"type": "plain_text", "text": "View Repository Issues", "emoji": True},
                "options": [
                    {
                        "text": {"type": "plain_text", "text": project["name"], "emoji": True},
                        "value": project["owner_repo"],
                    }
                    for project in chunk
                ],
                "action_id": "select_repository",
            }
        )

    blocks.append(navigation)

    send_dm(client, user_id, f"Found {len(matched)} matching OWASP projects.", blocks)


# Add the action handlers
def handle_repository_selection(ack, body, client):
    """Handles repository selection from dropdown"""
    try:
        user_id = body["user"]["id"]
        selected_repo = body["actions"][0]["selected_option"]["value"]

        headers = get_github_headers()
        if not GITHUB_TOKEN:
            send_dm(client, user_id, "⚠️ GitHub API token not configured. Please contact the administrator.")
            return HttpResponse()

        # Fetch latest issues from the selected GitHub repository
        issues_response = requests.get(
            f"https://api.github.com/repos/{selected_repo}/issues", headers=headers, timeout=10
        )

        if issues_response.status_code == 403:
            if "rate limit exceeded" in issues_response.text.lower():
                send_dm(client, user_id, "⚠️ GitHub API rate limit exceeded. Please try again later.")
            else:
                send_dm(client, user_id, "⚠️ Access to GitHub API denied. Please check the token configuration.")
            return HttpResponse()

        if issues_response.status_code == 200:
            issues = issues_response.json()
            issues = [issue for issue in issues if "pull_request" not in issue]
            if not issues:
                send_dm(client, user_id, "No open issues found for this repository.")
            else:
                blocks = [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"Latest Issues for {selected_repo}", "emoji": True},
                    },
                    {"type": "divider"},
                ]

                for issue in issues[:5]:
                    blocks.append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*<{issue['html_url']}|{issue['title']}>* (#{issue['number']})\n"
                                    f"👤 Opened by: {issue.get('user', {}).get('login', 'Unknown')}\n"
                                    f"📅 Created: {issue['created_at'][:10]}"
                                ),
                            },
                        }
                    )

                if len(issues) > 5:
                    blocks.append(
                        {
                            "type": "context",
                            "elements": [{"type": "mrkdwn", "text": f"_Showing 5 of {len(issues)} issues_"}],
                        }
                    )

                send_dm(client, user_id, f"Found {len(issues)} open issues:", blocks)
        else:
            send_dm(client, user_id, "Failed to fetch issues. Please try again later.")

        return HttpResponse()

    except (KeyError, IndexError) as e:
        return JsonResponse({"response_type": "ephemeral", "text": "❌ Invalid request format."}, status=400)
    except requests.RequestException as e:
        return JsonResponse(
            {"response_type": "ephemeral", "text": "❌ Failed to fetch issues: Network error occurred."}, status=503
        )


def handle_pagination_prev(ack, body, client):
    """Handles the 'Previous' pagination button."""
    try:
        user_id = body["user"]["id"]
        search_term = body.get("state", {}).get("values", {}).get("search_term", "Topic")

        if user_id not in pagination_data:
            send_dm(client, user_id, "No pagination data found.")
            return HttpResponse()

        data = pagination_data[user_id]
        data["current_page"] = max(0, data["current_page"] - 1)
        send_paged_results(client, user_id, search_term)
        return HttpResponse()

    except KeyError as e:
        return JsonResponse({"response_type": "ephemeral", "text": "❌ Invalid request format."}, status=400)
    except SlackApiError as e:
        return JsonResponse({"response_type": "ephemeral", "text": "❌ Failed to send message to Slack."}, status=503)


def handle_pagination_next(ack, body, client):
    """Handles the 'Next' pagination button"""
    try:
        user_id = body["user"]["id"]
        search_term = body.get("state", {}).get("values", {}).get("search_term", "Topic")

        if user_id not in pagination_data:
            send_dm(client, user_id, "No pagination data found.")
            return HttpResponse()

        data = pagination_data[user_id]
        data["current_page"] += 1
        total_pages = math.ceil(len(data["matched"]) / data["page_size"])
        data["current_page"] = min(data["current_page"], total_pages - 1)
        send_paged_results(client, user_id, search_term)
        return HttpResponse()

    except KeyError as e:
        return JsonResponse({"response_type": "ephemeral", "text": "❌ Invalid request format."}, status=400)
    except SlackApiError as e:
        return JsonResponse({"response_type": "ephemeral", "text": "❌ Failed to send message to Slack."}, status=503)


def filter_gsoc_projects(search_term):
    """Filter GSoC projects based on search term"""
    search_term = search_term.lower()
    if search_term.startswith("mentor:"):
        mentor_name = search_term[7:].strip()
        return [p for p in GSOC_PROJECTS if mentor_name in p["mentor"].lower()]

    return [p for p in GSOC_PROJECTS if search_term in p["title"].lower() or search_term in p["tech"].lower()]
