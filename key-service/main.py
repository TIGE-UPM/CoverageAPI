from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uuid

from shared import (
    get_db,
    db_manager,
    ApiKey,
    setup_logging,
    configure_cors,
    ServiceSettings
)
SERVICE_NAME = "key-service"
service_settings = ServiceSettings(
    service_name=SERVICE_NAME,
    service_description="GIGA Coverage API Key Generation Service"
)

logger = setup_logging(service_settings.service_name)

app = FastAPI(
    title="GIGA Coverage Key Service",
    version=service_settings.service_version
)
configure_cors(app)
db_manager.create_tables()


class GenerateKeyRequest(BaseModel):
    phone_identifier: str


class GenerateKeyResponse(BaseModel):
    api_key: str
    status: str


@app.post("/api/generate-key", response_model=GenerateKeyResponse)
async def generate_api_key(request: GenerateKeyRequest, db: Session = Depends(get_db)):
    """
    Generate and store an API key for a device based on phone_identifier.
    Links the phone_identifier to a unique API key for identification and privacy.
    """
    try:
        if not request.phone_identifier:
            raise HTTPException(
                status_code=400, detail="Phone identifier is required")

        # Check if this phone_identifier already has an API key
        existing_key = db.query(ApiKey).filter(
            ApiKey.phone_identifier == request.phone_identifier
        ).first()

        if existing_key:
            logger.info(
                f"Returning existing API key for phone: {request.phone_identifier[:8]}...")
            return GenerateKeyResponse(
                api_key=existing_key.api_key,
                status="success"
            )

        # Generate new UUID-based API key
        api_key = str(uuid.uuid4())
        new_api_key = ApiKey(
            phone_identifier=request.phone_identifier,
            api_key=api_key
        )
        db.add(new_api_key)
        db.commit()
        db.refresh(new_api_key)

        logger.info(
            f"Generated new API key for phone: {request.phone_identifier[:8]}..."
        )
        return GenerateKeyResponse(
            api_key=api_key,
            status="success"
        )
    except HTTPException:
        # Let client errors through unchanged. Without this, an empty
        # phone_identifier would raise the 400 "Phone identifier is required"
        # above, be caught by the generic handler below and reach the client
        # as a 500 "Failed to generate API key".
        raise
    except Exception as e:
        logger.error(f"Error generating API key: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to generate API key"
        )


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with database connectivity test"""
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": SERVICE_NAME,
            "database": "connected",
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": SERVICE_NAME,
            "database": "disconnected",
        }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"GIGA Coverage - {service_settings.service_description}",
        "version": service_settings.service_version
    }
