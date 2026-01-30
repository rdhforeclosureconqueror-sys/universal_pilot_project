import logging

logger = logging.getLogger(__name__)


def log_error(row: list, exception: Exception) -> None:
    logger.warning(
        "Dallas PDF row rejected: %s",
        exception,
        extra={"row": row, "error": str(exception)},
    )
