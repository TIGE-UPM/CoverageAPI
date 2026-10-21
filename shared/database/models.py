from sqlalchemy import Column, Integer, Float, String, DateTime, BigInteger
from datetime import datetime
from .connection import Base


class ApiKey(Base):
    """API key model shared across all services."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    phone_identifier = Column(String, unique=True, index=True, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CoverageMeasurement(Base):
    """Coverage measurement model for storing collected data."""
    __tablename__ = "coverage_measurements"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String, index=True, nullable=False)
    phone_identifier = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Location data
    latitude = Column(Float)
    longitude = Column(Float)
    gps_accuracy = Column(Float)
    location_type = Column(String(10))  # 'gps' (client) or 'ip' (server-derived)
    location_accuracy = Column(Float)  # meters

    # Signal strength data
    signal_strength_dbm = Column(Integer)
    signal_strength_asu = Column(Integer)

    # Network information
    network_type = Column(String)
    data_network_type = Column(String)
    mcc = Column(Integer)  # Mobile Country Code
    mnc = Column(Integer)  # Mobile Network Code
    cell_id = Column(BigInteger)

    # Device information
    app_name = Column(String)
    app_version = Column(String)
    library_version = Column(String)

    # Performance data
    download_speed_kbps = Column(Float)
    upload_speed_kbps = Column(Float)
    latency_ms = Column(Integer)
    jitter_ms = Column(Integer)
