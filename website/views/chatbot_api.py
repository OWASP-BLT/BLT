import json
import logging
import os

from django.http import JsonResponse

logger = logging.getLogger(__name__)

# -------------------------------------
# OpenAI Configuration (Optional)
# -------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_OPENAI = bool(OPENAI_API_KEY)

if USE_OPENAI:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)


# -------------------------------------
#            Chatbot API
# -------------------------------------
def chatbot_api(request):
    if request.method != "POST":
        return JsonResponse({"reply": "Only POST requests allowed."}, status=405)

    try:
        body = json.loads(request.body)
        message = (body.get("message") or "").strip()

        if not message:
            return JsonResponse({"reply": "Please enter a message."})

        # Always generate fallback response
        fallback_reply = fallback_blt_bot(message)

        # Slash commands ALWAYS use fallback only
        if message.startswith("/"):
            return JsonResponse({"reply": fallback_reply})

        # Use OpenAI if key is present
        if USE_OPENAI:
            reply = ai_answer(message)
            if reply:
                return JsonResponse({"reply": reply})

            # If OpenAI fails → fallback
            return JsonResponse({"reply": fallback_reply})

        # No key → fallback only
        return JsonResponse({"reply": fallback_reply})

    except json.JSONDecodeError:
        return JsonResponse({"reply": "Invalid JSON format."}, status=400)
    except Exception as e:
        logger.error(f"Chatbot error: {e}", exc_info=True)
        return JsonResponse(
            {"reply": "Something went wrong. Please try again later."},
            status=500,
        )


# -------------------------------------
#           OpenAI Response
# -------------------------------------
def ai_answer(message: str) -> str | None:
    """
    Calls the OpenAI API with a system prompt ensuring the bot behaves
    ONLY as the OWASP BLT assistant.
    """

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are BLT Bot — the official assistant for the OWASP "
                        "Bug Logging Tool (BLT). You must answer strictly about: "
                        "BLT features, hunts, bounties, leaderboards, bids, "
                        "Bacon Tokens, dashboards, contributions, GitHub syncing, "
                        "and the BLT repository structure."
                    ),
                },
                {"role": "user", "content": message},
            ],
        )

        return completion.choices[0].message.content

    except Exception as e:
        logger.error(f"OpenAI chatbot error: {e}", exc_info=True)
        return None


# -------------------------------------
#      Rule-Based Fallback BLT Bot
# -------------------------------------
def fallback_blt_bot(message: str) -> str:
    msg = message.lower().strip()

    greetings = ["hello", "hi", "hey", "yo", "hola"]
    if any(word in msg for word in greetings):
        return (
            "Hello! I'm the BLT Bot. Ask me about BLT features, leaderboards, bids, "
            "Bacon Tokens, hunts, dashboards, or use /help."
        )

    # Commands
    if msg.startswith("/help"):
        return (
            "Available commands:\n"
            "• /help — Show help\n"
            "• /stats — Leaderboard & stats info\n"
            "• /bid — Bidding system details\n"
            "• /bacon — Bacon Token explanation\n\n"
            "You can also ask: features, leaderboards, bounties, hunts, or repo info."
        )

    if msg.startswith("/stats") or "leaderboard" in msg:
        return (
            "BLT leaderboards highlight contributors and organizations based on "
            "their activity, providing transparency and motivation across the platform."
        )

    if msg.startswith("/bid") or "bid" in msg:
        return (
            "The BLT bidding system allows contributors to place bids on issues. "
            "Maintainers choose contributors based on their bid context and profile."
        )

    if msg.startswith("/bacon") or "bacon" in msg:
        return (
            "Bacon Tokens are BLT's internal reward currency given for resolving "
            "issues, participating in hunts, and contributing to the community."
        )

    # General BLT topics
    if "feature" in msg:
        return (
            "BLT includes issue tracking, bounties & hunts, dashboards, leaderboards, "
            "GitHub syncing, Slack integration, and reward mechanics like Bacon Tokens."
        )

    if "hunt" in msg or "bounty" in msg:
        return (
            "BLT Hunts group high-impact issues into special events where contributors "
            "can earn Bacon Tokens and leaderboard points."
        )

    if "dashboard" in msg or "org" in msg:
        return (
            "BLT dashboards display organization metrics, contributor stats, issue "
            "activity, bounty engagement, and hunt performance."
        )

    if "repo" in msg or "github" in msg:
        return (
            "The BLT GitHub repository contains the complete Bug Logging Tool codebase, "
            "including APIs, models, dashboards, hunts, and integrations."
        )

    if "blt" in msg or "owasp" in msg:
        return (
            "OWASP BLT is an open-source tool for managing issues, bounties, hunts, "
            "leaderboards, and contributions. Use /help to see commands."
        )

    # Default fallback
    return "Ask me something related to the OWASP BLT project. Use /help to see commands " "and example questions."
