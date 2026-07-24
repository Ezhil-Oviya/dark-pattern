from fastapi import APIRouter

from app.api.v1.routes import (
    audit_routes,
    auth_routes,
    automation_routes,
    bot_routes,
    compliance_routes,
    dark_pattern_routes,
    dashboard_routes,
    evidence_routes,
    report_routes,
)

api_router = APIRouter()
api_router.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(audit_routes.router, prefix="/audits", tags=["Audits"])
api_router.include_router(automation_routes.router, prefix="/automation", tags=["Automation"])
api_router.include_router(compliance_routes.router, prefix="/compliance", tags=["Compliance"])
api_router.include_router(dark_pattern_routes.router, prefix="/dark-patterns", tags=["Dark Patterns"])
api_router.include_router(evidence_routes.router, prefix="/evidence", tags=["Evidence"])
api_router.include_router(report_routes.router, prefix="/reports", tags=["Reports"])
api_router.include_router(dashboard_routes.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(bot_routes.router, prefix="/bot", tags=["AI Compliance Bot"])
