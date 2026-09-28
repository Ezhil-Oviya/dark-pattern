from typing import List, Optional
from pydantic import BaseModel, Field


class Website(BaseModel):
    platform: str
    url: str
    category: str = "Ecommerce"
    crawl_depth: int = 3
    max_pages: int = 10
    headless: bool = True
    capture_dom: bool = True
    capture_screenshots: bool = True
    login_required: bool = False
    cart_workflow_enabled: bool = True
    product_selection_enabled: bool = True
    add_to_cart_selectors: List[str] = Field(default_factory=list)
    cart_selectors: List[str] = Field(default_factory=list)