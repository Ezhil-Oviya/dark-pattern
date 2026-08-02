from pydantic import BaseModel

class Website(BaseModel):

    platform: str

    url: str

    category: str

    crawl_depth: int

    max_pages: int

    headless: bool

    capture_dom: bool

    capture_screenshots: bool

    login_required: bool