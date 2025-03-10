import logging
import logging.config
import os
if not os.path.exists("logs"):
    os.makedirs("logs")

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
        },
        "telegram_manager_file": {
            "class": "logging.FileHandler",
            "filename": "logs/telegram_manager.log",
            "formatter": "standard",
            "level": "INFO",
        },
        "routes_file": {
            "class": "logging.FileHandler",
            "filename": "logs/routes.log",
            "formatter": "standard",
            "level": "INFO",
        },
    },
    "loggers": {
        "managers.telegram_manager": {
            "handlers": ["console", "telegram_manager_file"],
            "level": "INFO",
            "propagate": False
        },
        "api.routes": {
            "handlers": ["console", "routes_file"],
            "level": "INFO",
            "propagate": False
        },
    }
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
