import json
import os

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Load OpenAI key (optional)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_OPENAI = bool(OPENAI_API_KEY)

# Import OpenAI only when key exists
if USE_OPENAI:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)


@csrf_exempt
def chatbot_api(request):
    if request.method != "POST":
        return JsonResponse({"reply": "Only POST requests allowed."}, status=405)

    try:
        body = json.loads(request.body)
        message = (body.get("message") or "").strip()

        if not message:
            return JsonResponse({"reply": "Please enter a message."})

        # Fallback reply always available
        fallback_reply = fallback_blt_bot(message)

        # Commands ALWAYS use fallback
        if message.startswith("/"):
            return JsonResponse({"reply": fallback_reply})

        # Use real OpenAI if available
        if USE_OPENAI:
            reply = ai_answer(message)
            if reply is not None:
                return JsonResponse({"reply": reply})
            # If AI failed → fallback
            return JsonResponse({"reply": fallback_reply})

        # No API key → fallback
        return JsonResponse({"reply": fallback_reply})

    except json.JSONDecodeError:
        return JsonResponse({"reply": "Invalid JSON format."}, status=400)
    except Exception as e:
        return JsonResponse({"reply": f"Server error: {str(e)}"}, status=500)


# -------------------------
#     OpenAI Answer
# -------------------------
def ai_answer(message: str) -> str | None:
    prompt = f"""
You are BLT Bot — an assistant for the OWASP Bug Logging Tool (BLT).
Answer STRICTLY about BLT features, hunts, leaderboards, bids, bacon tokens,
projects, contributions, dashboards, GitHub syncing, and repository structure.

User message: "{message}"
"""

    try:
        completion = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )
        return completion.output_text
    except Exception:
        return None


# -------------------------
#  Fallback BLT Assistant
# -------------------------
def fallback_blt_bot(message: str) -> str:
    msg = message.lower().strip()

    greetings = ["hello", "hi", "hey", "yo", "hola"]
    if any(word in msg for word in greetings):
        return (
            "Hello! I'm the BLT Bot. Ask me about BLT features, leaderboards, bids, "
            "bacon tokens, hunts, dashboards, or /help."
        )

    if msg.startswith("/help"):
        return (
            "Available commands:\n"
            "• /help → Show help\n"
            "• /stats → Leaderboard & stats info\n"
            "• /bid → Bidding system details\n"
            "• /bacon → Bacon token explanation\n"
            "Ask me: features, leaderboards, hunts, repo, dashboard…"
        )

    if msg.startswith("/stats") or "leaderboard" in msg:
        return (
            "BLT leaderboards highlight top contributors, organizations, and activity. "
            "They help maintain transparency and motivation for contributors."
        )

    if msg.startswith("/bid") or "bid" in msg:
        return (
            "The BLT bidding system lets contributors place bids on issues. "
            "Maintainers can choose contributors based on bid context."
        )

    if msg.startswith("/bacon") or "bacon" in msg:
        return (
            "Bacon Tokens are BLT’s internal reward currency for contributing to issues, "
            "hunts, and community events."
        )

    if "feature" in msg:
        return (
            "BLT includes issue tracking, bounties/hunts, dashboards, leaderboards, "
            "GitHub syncing, Slack integration, and reward mechanics."
        )

    if "hunt" in msg or "bounty" in msg:
        return (
            "BLT Hunts are collections of high-impact issues grouped into special events. "
            "Contributors earn Bacon Tokens and leaderboard points."
        )

    if "dashboard" in msg or "org" in msg:
        return (
            "BLT dashboards show organization metrics, contributor stats, issue activity, "
            "and hunt performance."
        )

    if "repo" in msg or "github" in msg:
        return (
            "The BLT GitHub repository contains all source code for the Bug Logging Tool: "
            "APIs, models, dashboards, hunts, integrations, and tools."
        )

    if "blt" in msg or "owasp" in msg:
        return (
            "OWASP BLT is an open-source tool for managing issues, bounties, hunts, "
            "leaderboards, and contributions. Use /help for commands."
        )

    return (
        "Ask me something related to the OWASP BLT project. Use /help to see commands "
        "and example questions."
    )
