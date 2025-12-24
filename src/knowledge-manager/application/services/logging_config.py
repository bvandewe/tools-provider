"""Logging configuration for Knowledge Manager."""

import logging
import sys


def configure_logging(log_level: str = "INFO") -> None:
    """Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,  # Force reconfiguration
    )

    # Reduce noise from verbose libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
