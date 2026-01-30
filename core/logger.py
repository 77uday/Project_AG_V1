# ============================================================
# IMPORTS
# ============================================================

import logging
from typing import Any


# ============================================================
# LOGGER WRAPPER
# ============================================================

class Logger:
    """
    Lightweight structured logger wrapper.
    """

    def __init__(self, name: str = "ProjectAG"):
        self._logger = logging.getLogger(name)

        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] %(message)s"
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)
        
        self._correlation_id = None


    # ========================================================
    # PUBLIC LOGGING API
    # ========================================================

    def info(self, message: str, **context: Any) -> None:
        self._logger.info(self._format(message, context))

    def warning(self, message: str, **context: Any) -> None:
        self._logger.warning(self._format(message, context))

    def error(self, message: str, **context: Any) -> None:
        self._logger.error(self._format(message, context))

    def set_correlation_id(self, correlation_id: str) -> None:
        """
        Set correlation ID for subsequent logs.
        """
        self._correlation_id = correlation_id


    # ========================================================
    # INTERNAL HELPERS
    # ========================================================

    def _format(self, message: str, context: dict) -> str:
        parts = []

        if self._correlation_id:
            parts.append(f"cid={self._correlation_id}")

        if context:
            context_str = " ".join(
                f"{key}={value}" for key, value in context.items()
            )
            parts.append(context_str)

        if parts:
            return f"{message} | " + " ".join(parts)

        return message

