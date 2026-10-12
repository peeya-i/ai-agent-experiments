"""Callback logging module.

Re-exports setup_logging, log_query_to_model, and log_model_response from adk_utils.callback_logging.
"""

import sys
from pathlib import Path

# Ensure adk_utils is discoverable
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from adk_utils.callback_logging import (
    setup_logging,
    log_query_to_model,
    log_model_response,
)

__all__ = ["setup_logging", "log_query_to_model", "log_model_response"]
