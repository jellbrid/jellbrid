import logging
import sys

import structlog


def setup_logging(level: int):
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            # structlog.processors.JSONRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # configure the root logger
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=level,
    )

    # disable other loggers
    for v in logging.Logger.manager.loggerDict.values():
        name = getattr(v, "name", "")
        if not name.startswith("jellbrid") and isinstance(v, logging.Logger):
            v.disabled = True
