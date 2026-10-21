from datetime import datetime, timezone
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared import (
    get_db,
    db_manager,
    CoverageMeasurement,
    validate_api_key,
    setup_logging,
    configure_cors,
    ServiceSettings
)
from geolocation import IpGeolocator, get_client_ip
from migrate import run_migrations

SERVICE_NAME = "data-service"
service_settings = ServiceSettings(
    service_name=SERVICE_NAME,
    service_description="GIGA Coverage Data Collection Service"
)
logger = setup_logging(service_settings.service_name)

app = FastAPI(
    title="GIGA Coverage Data Service",
    version=service_settings.service_version
)
configure_cors(app)
run_migrations(db_manager.engine)

geolocator = IpGeolocator(
    db_path=service_settings.geoip_db_path,
    default_accuracy_m=service_settings.geoip_default_accuracy_m,
    enabled=service_settings.geoip_enabled,
)


class SendDataRequest(BaseModel):
    """
    One coverage measurement. Every optional field may be absent or null;
    both are stored as NULL. Unknown fields (e.g. Android's android_id and
    is_position_from_GPS) are ignored.
    """
    api_key: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_accuracy: Optional[float] = None
    location_type: Optional[Literal["gps", "ip"]] = None
    location_accuracy: Optional[float] = None
    signal_strength_dbm: Optional[int] = None
    signal_strength_asu: Optional[int] = None
    network_type: Optional[str] = None
    data_network_type: Optional[str] = None
    mobile_country_code: Optional[int] = None
    network_code: Optional[int] = None
    cell_id: Optional[int] = None
    app_name: Optional[str] = None
    app_version: Optional[str] = None
    library_version: Optional[str] = None
    download_speed: Optional[float] = None
    upload_speed: Optional[float] = None
    latency_ms: Optional[int] = None
    jitter_ms: Optional[int] = None
    timestamp: Optional[str] = None


class SendDataResponse(BaseModel):
    status: str
    message: str


def parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """
    Parse the client timestamp into a naive UTC datetime.

    Accepts ISO 8601 (with or without offset, "Z" included) as sent by the web
    plugin, and epoch milliseconds (or seconds) as a digit string as sent by
    the Android library. Returns None when empty or unparseable so the caller
    falls back to the server time.
    """
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        number = int(value)
        if number > 10 ** 11:  # milliseconds; seconds would be beyond year 5000
            number = number / 1000
        try:
            return datetime.fromtimestamp(number, tz=timezone.utc).replace(tzinfo=None)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


@app.post("/api/send-data", response_model=SendDataResponse)
async def send_coverage_data(
    request: SendDataRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Store coverage measurement data in the database.
    Validates API key against stored keys before accepting data.
    When no coordinates are sent, the location is approximated from the
    client IP (the IP itself is neither stored nor logged).
    """
    try:
        logger.info(
            f"Received send-data request: "
            f"api_key={request.api_key[:8]}..., "
            f"lat={request.latitude}, lon={request.longitude}, "
            f"gps_accuracy={request.gps_accuracy}, "
            f"location_type={request.location_type}, location_accuracy={request.location_accuracy}, "
            f"signal_dbm={request.signal_strength_dbm}, signal_asu={request.signal_strength_asu}, "
            f"network_type={request.network_type}, data_network_type={request.data_network_type}, "
            f"mcc={request.mobile_country_code}, mnc={request.network_code}, cell_id={request.cell_id}, "
            f"app={request.app_name} v{request.app_version}, lib_v={request.library_version}, "
            f"download={request.download_speed}, upload={request.upload_speed}, "
            f"latency={request.latency_ms}, jitter={request.jitter_ms}, "
            f"timestamp={request.timestamp}"
        )

        if not request.api_key:
            raise HTTPException(status_code=400, detail="API key is required")

        phone_identifier = await validate_api_key(request.api_key, db)

        parsed_timestamp = parse_timestamp(request.timestamp)
        if request.timestamp and parsed_timestamp is None:
            logger.warning(
                f"Invalid timestamp format: {request.timestamp}, using server time")

        latitude = request.latitude
        longitude = request.longitude
        location_type = request.location_type
        location_accuracy = request.location_accuracy
        if latitude is not None and longitude is not None:
            # Android sends 0.0/0.0 when it has no fix; keep the values as sent
            # but do not label them as a real position.
            if location_type is None and not (latitude == 0 and longitude == 0):
                location_type = "gps"
        else:
            ip_location = geolocator.locate(get_client_ip(http_request))
            if ip_location is not None:
                latitude = ip_location.latitude
                longitude = ip_location.longitude
                location_type = "ip"
                location_accuracy = ip_location.accuracy_m

        measurement = CoverageMeasurement(
            api_key=request.api_key,
            phone_identifier=phone_identifier,
            latitude=latitude,
            longitude=longitude,
            gps_accuracy=request.gps_accuracy,
            location_type=location_type,
            location_accuracy=location_accuracy,
            signal_strength_dbm=request.signal_strength_dbm,
            signal_strength_asu=request.signal_strength_asu,
            network_type=request.network_type,
            data_network_type=request.data_network_type,
            mcc=request.mobile_country_code,
            mnc=request.network_code,
            cell_id=request.cell_id,
            app_name=request.app_name,
            app_version=request.app_version,
            library_version=request.library_version,
            download_speed_kbps=request.download_speed,
            upload_speed_kbps=request.upload_speed,
            latency_ms=request.latency_ms,
            jitter_ms=request.jitter_ms,
            timestamp=parsed_timestamp
        )

        db.add(measurement)
        db.commit()
        db.refresh(measurement)

        logger.info(
            f"Stored measurement for phone: {phone_identifier[:8]}... (ID: {measurement.id})")

        return SendDataResponse(
            status="success",
            message="Coverage data stored successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing coverage data: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to store coverage data"
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
