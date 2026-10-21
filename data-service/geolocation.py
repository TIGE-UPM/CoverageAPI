"""
Approximate IP geolocation for measurements that carry no coordinates.

Uses a local MaxMind GeoLite2 City database (.mmdb). The IP address is only
used in memory to look up coordinates; it is never stored or logged. If the
database is missing or disabled, lookups return None and the measurement is
stored without a location.
"""
import ipaddress
import logging
import os
from dataclasses import dataclass
from typing import Optional

from fastapi import Request

try:
    import geoip2.database
    import geoip2.errors
except ImportError:  # pragma: no cover - geoip2 is in requirements.txt
    geoip2 = None

logger = logging.getLogger("data-service")


@dataclass
class IpLocation:
    latitude: float
    longitude: float
    accuracy_m: float


def get_client_ip(request: Request) -> Optional[str]:
    """
    Real client IP behind the reverse proxies.

    nginx appends its upstream to X-Forwarded-For, and Traefik (Dokploy) does
    the same before it, so the first entry is the original client. X-Real-IP
    and the socket peer are fallbacks for direct access.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return None


class IpGeolocator:
    """GeoLite2 reader with lazy open, reload on file change and quiet degradation."""

    def __init__(self, db_path: str, default_accuracy_m: float, enabled: bool = True):
        self.db_path = db_path
        self.default_accuracy_m = default_accuracy_m
        self.enabled = enabled and geoip2 is not None
        self._reader = None
        self._loaded_mtime = None
        self._missing_reported = False

    def _open_reader(self):
        try:
            mtime = os.path.getmtime(self.db_path)
        except OSError:
            self._close()
            if not self._missing_reported:
                logger.warning(
                    f"GeoIP database not found at {self.db_path}; "
                    "measurements without coordinates will be stored without location"
                )
                self._missing_reported = True
            return None

        if self._reader is not None and mtime == self._loaded_mtime:
            return self._reader

        # First open, or the file was replaced (e.g. by geoipupdate).
        self._close()
        try:
            self._reader = geoip2.database.Reader(self.db_path)
        except Exception as e:
            logger.error(f"Failed to open GeoIP database {self.db_path}: {e}")
            return None
        self._loaded_mtime = mtime
        self._missing_reported = False
        logger.info(f"GeoIP database loaded from {self.db_path}")
        return self._reader

    def _close(self):
        if self._reader is not None:
            try:
                self._reader.close()
            except Exception:
                pass
        self._reader = None
        self._loaded_mtime = None

    def locate(self, ip: Optional[str]) -> Optional[IpLocation]:
        """Coordinates for a public IP, or None when unknown or unavailable."""
        if not self.enabled or not ip:
            return None
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            return None
        if not address.is_global:
            return None

        reader = self._open_reader()
        if reader is None:
            return None
        try:
            response = reader.city(ip)
        except geoip2.errors.AddressNotFoundError:
            return None
        except Exception as e:
            logger.error(f"GeoIP lookup failed: {e}")
            return None

        location = response.location
        if location.latitude is None or location.longitude is None:
            return None
        accuracy_m = self.default_accuracy_m
        if location.accuracy_radius is not None:
            accuracy_m = float(location.accuracy_radius) * 1000.0  # km -> m
        return IpLocation(
            latitude=location.latitude,
            longitude=location.longitude,
            accuracy_m=accuracy_m,
        )
