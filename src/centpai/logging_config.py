from logging.config import dictConfig

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    # -------------------------------------------------------------------------
    # FORMATTERS
    # -------------------------------------------------------------------------
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },

    # -------------------------------------------------------------------------
    # HANDLERS (where logs go)
    # -------------------------------------------------------------------------
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "./app.log",
            "mode": "a",
            "level": "DEBUG",
            "formatter": "default",
        }
    },

    # -------------------------------------------------------------------------
    # ROOT LOGGER
    # -------------------------------------------------------------------------
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },

    # -------------------------------------------------------------------------
    # PER-MODULE LOGGERS (optional)
    # -------------------------------------------------------------------------
    "loggers": {
        "telegram": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        }
    }
}

def setup_logging():
    dictConfig(LOGGING_CONFIG)
