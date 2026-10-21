"""
GIGA Coverage Shared Library

Common utilities and components shared across all microservices.
"""

__version__ = "1.0.0"

# Convenience imports for common functionality
from .database.connection import get_db, db_manager
from .database.models import ApiKey, CoverageMeasurement
from .auth.validation import validate_api_key
from .config.settings import settings, Settings, ServiceSettings
from .utils.logging import setup_logging, get_logger, setup_basic_logging
from .utils.cors import configure_cors
from .exceptions import (
    CoverageException,
    DatabaseConnectionError,
    InvalidAPIKeyError,
    ValidationError,
    ConfigurationError
)

__all__ = [
    "get_db",
    "db_manager",
    "ApiKey",
    "CoverageMeasurement",
    "validate_api_key",
    "settings",
    "Settings",
    "ServiceSettings",
    "setup_logging",
    "get_logger",
    "setup_basic_logging",
    "configure_cors",
    "CoverageException",
    "DatabaseConnectionError",
    "InvalidAPIKeyError",
    "ValidationError",
    "ConfigurationError"
]
