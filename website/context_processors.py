from django.core.cache import cache
from .utils import get_navigation_click_counts

MENU_ITEMS = {
    "/companies/": {"name": "Organizations", "icon": "🏛️"},
    "/sponsor/": {"name": "Sponsor", "icon": "🤝"},
    "/scoreboard/": {"name": "Scoreboard", "icon": "🏆"},
    "/leaderboard/": {"name": "Leaderboard", "icon": "🏅"},
    "/users/": {"name": "Users", "icon": "🧑‍🤝‍🧑"},
    "/hunts/": {"name": "Bug Bounties", "icon": "🐛"},
    "/projects/": {"name": "Projects", "icon": "📦"},
    "/apps/": {"name": "Apps", "icon": "📱"},
    "/deletions/": {"name": "Deletions", "icon": "🗑️"},
    "/trademarks/": {"name": "Trademarks", "icon": "™️"},
    "/bacon/": {"name": "BACON", "icon": "🥓"},
    "/sitemap/": {"name": "Sitemap", "icon": "🗺️"},
    "/bltv/": {"name": "BLTV", "icon": "📺"},
    "/contribute/": {"name": "Contribute", "icon": "✋"},
    "/contributors/": {"name": "Contributors", "icon": "💻"},
    "/contributor-stats/": {"name": "Weekly Activity", "icon": "📅"},
    "/contributor-stats/today/": {"name": "Daily Activity", "icon": "🗓️"},
    "/about/": {"name": "About Us", "icon": "ℹ️"},
    "/bidding/": {"name": "Bid on Bugs", "icon": "💰"},
    "/terms/": {"name": "Terms", "icon": "📜"},
    "/stats/": {"name": "Stats", "icon": "📊"},
    "/blt-tomato/": {"name": "BLT Tomato", "icon": "🍅"},
    "/view-suggestion/": {"name": "Suggestions", "icon": "💬"},
    "/status/": {"name": "Status", "icon": "✅"},
    "/": {
        "name": "Issues",
        "icon": "⚠️",
    }
}


def navigation_click_counts(request):
    cache_key = "navigation_click_counts"
    click_counts = cache.get(cache_key)

    if not click_counts:
        click_counts = get_navigation_click_counts()
        cache.set(cache_key, click_counts, 60 * 15)

    menu_items_dict = {}
    for item in click_counts:
        if item["path"] in MENU_ITEMS:
            menu_item = MENU_ITEMS[item["path"]].copy()
            menu_item["clicks"] = item["clicks"]
            menu_item["url"] = item["path"]
            menu_items_dict[item["path"]] = menu_item

    for path, details in MENU_ITEMS.items():
        if path not in menu_items_dict:
            menu_item = details.copy()
            menu_item["clicks"] = 0
            menu_item["url"] = path
            menu_items_dict[path] = menu_item

    sorted_menu_items = sorted(menu_items_dict.values(), key=lambda x: x["clicks"], reverse=True)

    return {"menu_items": sorted_menu_items}

