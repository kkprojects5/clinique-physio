"""Log messages of the application itself (not only uvicorn's request lines).

Without this, Python shows only warnings, so lines such as "email queued" never reached
Render's log. Messages never contain personal information: emails are masked (NFR-13).
"""

import logging

APP_LOGGER = "app"


def setup_logging() -> None:
    logger = logging.getLogger(APP_LOGGER)
    if logger.handlers:  # already set up (tests import the app many times)
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
