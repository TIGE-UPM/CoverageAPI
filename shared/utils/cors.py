from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config.settings import settings


def configure_cors(app: FastAPI, origins: Optional[List[str]] = None) -> None:
    """
    Enable CORS so the web plugin can call the API from any page.

    The API key travels in the body or form data, never in a header or cookie,
    so no credentials are involved and a wildcard origin is safe. The allowed
    origins come from CORS_ALLOW_ORIGINS (comma-separated, default "*").
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or settings.cors_allow_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
