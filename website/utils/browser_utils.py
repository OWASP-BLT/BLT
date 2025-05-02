def normalize_browser_name(browser_family):
    """
    Normalize browser family names to match browser-logos package conventions.
    """
    browser_map = {
        "comodo dragon": "comodo-dragon",
        "google chrome": "chrome",
        "microsoft edge": "edge",
        "internet explorer": "ie",
    }
    normalized = browser_family.lower()
    if normalized in browser_map:
        return browser_map[normalized]
    return normalized.replace(" ", "-")