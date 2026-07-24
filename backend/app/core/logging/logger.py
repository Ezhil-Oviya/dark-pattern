import logging

from app.core.config.settings import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(settings.app_name)
