# GIGA Coverage Shared Library

Common utilities and components shared across all GIGA Coverage microservices.

## Features

### Database Management

-   **Connection handling**: Centralized database connection management
-   **Model definitions**: Shared SQLAlchemy models (ApiKey, CoverageMeasurement)
-   **Session management**: Database session dependency injection

### Authentication

-   **API key validation**: Shared validation logic for API keys
-   **Both sync/async support**: Functions for different contexts

### Configuration

-   **Environment-based settings**: Centralized configuration management
-   **Service-specific settings**: Extensible settings for individual services

### CORS

-   **`configure_cors(app)`**: Enables browser access (web plugin) with the origins from `CORS_ALLOW_ORIGINS`

### Logging

-   **Standardized logging**: Consistent log formatting across services
-   **Service identification**: Clear service names in log output

## Usage

### Quick Start

```python
from shared import get_db, ApiKey, validate_api_key, setup_logging

# Setup logging
logger = setup_logging("my-service")

# Use database dependency
@app.post("/endpoint")
async def my_endpoint(db: Session = Depends(get_db)):
    # Database operations here
    pass

# Validate API keys
phone_id = await validate_api_key(api_key, db)
```

### Database Models

```python
from shared.database.models import ApiKey, CoverageMeasurement

# Models are automatically available for use
api_key = ApiKey(phone_identifier="123", api_key="key")
measurement = CoverageMeasurement(api_key="key", latitude=40.7)
```

### Configuration

```python
from shared.config.settings import settings, ServiceSettings

# Global settings
db_url = settings.database_url
is_prod = settings.is_production

# Service-specific settings
service_settings = ServiceSettings("my-service", "My Service Description")
port = service_settings.service_port
```

## Installation

Install in development mode for easy updates:

```bash
cd shared
pip install -e .
```

Or install from requirements:

```bash
pip install -r shared/requirements.txt
```

## Structure

```
shared/
├── __init__.py          # Main exports
├── database/
│   ├── connection.py    # Database connection management
│   └── models.py        # SQLAlchemy models
├── auth/
│   └── validation.py    # API key validation
├── config/
│   └── settings.py      # Configuration management
└── utils/
    ├── cors.py          # CORS middleware setup
    └── logging.py       # Logging utilities
```
