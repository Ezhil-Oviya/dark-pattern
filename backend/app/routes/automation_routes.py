from fastapi import APIRouter, HTTPException

from app.services.website_service import get_website
from app.services.automation.playwright_service import run_browser_audit

router = APIRouter()


@router.post("/automation/start/{website_id}")

def start_automation(website_id: str):

    website = get_website(website_id)

    if not website:

        raise HTTPException(
            status_code=404,
            detail="Website not found"
        )

    result = run_browser_audit(website)

    return result