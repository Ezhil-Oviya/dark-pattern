def website_serializer(website):
    if not website:
        return None

    raw_id = website.get("_id") or website.get("id")
    return {
        "id": str(raw_id) if raw_id else "",
        "platform": website.get("platform", ""),
        "url": website.get("url", ""),
        "category": website.get("category", "Ecommerce"),
        "crawl_depth": website.get("crawl_depth", 3),
        "max_pages": website.get("max_pages", 10),
        "headless": website.get("headless", True),
        "capture_dom": website.get("capture_dom", True),
        "capture_screenshots": website.get("capture_screenshots", True),
        "login_required": website.get("login_required", False)
    }


def websites_serializer(websites):
    if not websites:
        return []
    return [website_serializer(i) for i in websites if i]