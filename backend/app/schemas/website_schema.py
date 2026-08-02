def website_serializer(website):

    return {

        "id": str(website["_id"]),

        "platform": website["platform"],

        "url": website["url"],

        "category": website["category"],

        "crawl_depth": website["crawl_depth"],

        "max_pages": website["max_pages"],

        "headless": website["headless"],

        "capture_dom": website["capture_dom"],

        "capture_screenshots": website["capture_screenshots"],

        "login_required": website["login_required"]

    }


def websites_serializer(websites):

    return [website_serializer(i) for i in websites]