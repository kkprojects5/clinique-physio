"""Log messages of the application itself (not only uvicorn's request lines).

Without this, Python shows only warnings, so lines such as "email queued" never reached
Render's log. Messages never contain personal information: emails are masked (NFR-13).
"""

import logging

APP_LOGGER = "app"


class HideQueryString(logging.Filter):
    """uvicorn's request lines without the query string (challenge B-C7).

    The front desk searches patients with GET /desk/patients?q=<name, phone or birth date>:
    without this filter, Render's log would keep those searches. The path is kept, the part
    after "?" is replaced by "?…".
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            path = args[2]
            if "?" in path:
                record.args = (*args[:2], path.split("?", 1)[0] + "?…", *args[3:])
        return True


def setup_logging() -> None:
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, HideQueryString) for f in access.filters):
        access.addFilter(HideQueryString())
    logger = logging.getLogger(APP_LOGGER)
    if logger.handlers:  # already set up (tests import the app many times)
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
