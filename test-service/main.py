import os
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared import (
    get_db,
    db_manager,
    validate_api_key,
    setup_logging,
    configure_cors,
    ServiceSettings
)


SERVICE_NAME = "test-service"
service_settings = ServiceSettings(
    service_name=SERVICE_NAME,
    service_description="GIGA Coverage API Speed Testing Service"
)

logger = setup_logging(service_settings.service_name)

app = FastAPI(
    title="GIGA Coverage Test Service",
    version=service_settings.service_version
)
configure_cors(app)
db_manager.create_tables()

DOWNLOAD_CHUNK_BYTES = 64 * 1024
NO_STORE = {"Cache-Control": "no-store"}


class UploadTestResponse(BaseModel):
    status: str
    message: str
    file_size_bytes: int


@app.get("/api/test-ping", status_code=204)
async def test_ping(t: Optional[str] = None):
    """
    Minimal endpoint for round-trip time measurement.
    No API key: it returns nothing and must be as cheap as possible.
    The `t` query parameter is a cache-buster and is ignored.
    """
    return Response(status_code=204, headers=NO_STORE)


async def random_chunks(total: int):
    remaining = total
    while remaining > 0:
        size = min(DOWNLOAD_CHUNK_BYTES, remaining)
        remaining -= size
        yield os.urandom(size)


@app.get("/api/test-data-download")
async def test_data_download(
    size: int = Query(..., alias="bytes", description="Payload size in bytes"),
    t: Optional[str] = None,
    api_key: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Serve `bytes` bytes of incompressible random data for download speed
    measurement. Streamed in chunks with an exact Content-Length and no
    caching. The API key is optional; when given it is validated.
    """
    max_bytes = service_settings.max_download_bytes
    if size < 1 or size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"bytes must be an integer between 1 and {max_bytes}"
        )
    if api_key:
        await validate_api_key(api_key, db)

    return StreamingResponse(
        random_chunks(size),
        media_type="application/octet-stream",
        headers={"Content-Length": str(size), **NO_STORE},
    )


@app.post("/api/test-data-upload", response_model=UploadTestResponse)
async def test_data_upload(
    api_key: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accept file upload for speed testing purposes.
    Validates API key and consumes uploaded data without storing it.
    The client library calculates upload speed based on timing.
    """
    try:
        if not api_key:
            raise HTTPException(status_code=400, detail="API key is required")

        if not file:
            raise HTTPException(status_code=400, detail="File is required")

        # Validate API key
        phone_identifier = await validate_api_key(api_key, db)

        # Read and discard the uploaded file data
        total_bytes = 0
        is_all_file_read = False
        while not is_all_file_read:
            chunk = await file.read(8192)  # 8KB chunks
            if not chunk:
                is_all_file_read = True
            total_bytes += len(chunk)
            # Data is discarded - not stored anywhere

        logger.info(
            f"Upload test completed for phone {phone_identifier[:8]}...: received {total_bytes} bytes"
        )

        return UploadTestResponse(
            status="success",
            message="Upload test completed successfully",
            file_size_bytes=total_bytes
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during upload test: {e}")
        raise HTTPException(
            status_code=500,
            detail="Upload test failed",
        )


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer"""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"GIGA Coverage - {service_settings.service_description}",
        "version": service_settings.service_version
    }
