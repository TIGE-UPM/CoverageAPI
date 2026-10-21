# GIGA Coverage API

Open source backend services for the GIGA Coverage Library (Android) and the GIGA Coverage web plugin. This microservices architecture provides the endpoints for network coverage data collection: API key generation, measurement ingestion and the latency/download/upload speed tests.

## Architecture

### Services

1. **key-service** - Lightweight service for API key generation
   - Endpoint: `POST /api/generate-key`
   - Resources: 256MB RAM
   - Purpose: Generate UUID-based API keys linked to a device's `phone_identifier`

2. **data-service** - Data ingestion and storage service
   - Endpoint: `POST /api/send-data`
   - Resources: 512MB–1GB RAM
   - Purpose: Validate API key and store coverage measurements in PostgreSQL

3. **test-service** - Speed testing service (formerly `upload-service`)
   - Endpoints: `GET /api/test-ping`, `GET /api/test-data-download`, `POST /api/test-data-upload`
   - Resources: 1–2GB RAM, 1 CPU core
   - Purpose: Serve the client-side latency, download and upload measurements (nothing is stored)

4. **geoipupdate** (optional sidecar) - Keeps the MaxMind GeoLite2 City database up to date for IP geolocation in data-service. See [IP geolocation](#ip-geolocation).

All services answer CORS preflight requests so the web plugin can call them from any page (see `CORS_ALLOW_ORIGINS`). The API key always travels in the JSON body, form data or query string, never in a header.

### Technology Stack

- **FastAPI** - Python web framework
- **PostgreSQL** - Database for API keys and coverage data
- **SQLAlchemy** - ORM for database access
- **Docker & Docker Compose** - Containerization and orchestration
- **Nginx** - Reverse proxy routing requests to the correct service

## Quick Start

### Development Setup

```bash
# Clone and start all services
cd CoverageAPI
docker-compose up -d

# API will be available at:
# http://localhost/api/generate-key
# http://localhost/api/send-data
# http://localhost/api/test-ping
# http://localhost/api/test-data-download?bytes=1000000
# http://localhost/api/test-data-upload

# Optionally, with MaxMind credentials in .env, add the GeoLite2 updater:
docker-compose --profile geoip up -d
```

### Production Setup

```bash
# Copy environment file and configure
cp .env.example .env
# Edit .env with your production values

# Start production stack
docker-compose -f docker-compose.prod.yml up -d
```

## API Endpoints

### 1. Generate API Key

Generates (or retrieves) a UUID-based API key for a device. If the `phone_identifier` already has a key, the existing key is returned.

```
POST /api/generate-key
Content-Type: application/json
```

Request body:

```json
{
  "phone_identifier": "your-device-id"
}
```

Response (`200 OK`):

```json
{
  "api_key": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success"
}
```

| Field              | Type   | Required | Description                          |
|--------------------|--------|----------|--------------------------------------|
| `phone_identifier` | string | Yes      | Unique device identifier (e.g. Android ID, IDFV) |

### 2. Send Coverage Data

Stores a coverage measurement. The API key is validated before accepting data.

```
POST /api/send-data
Content-Type: application/json
```

Request body:

```json
{
  "api_key": "550e8400-e29b-41d4-a716-446655440000",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "gps_accuracy": 12.5,
  "signal_strength_dbm": -70,
  "signal_strength_asu": 15,
  "network_type": "LTE",
  "data_network_type": "NR",
  "mobile_country_code": 310,
  "network_code": 260,
  "cell_id": 12345678,
  "app_name": "GigaCoverage",
  "app_version": "1.0.0",
  "library_version": "1.0.0",
  "download_speed": 15000.0,
  "upload_speed": 5000.0,
  "timestamp": "2026-02-15T10:00:00"
}
```

Response (`200 OK`):

```json
{
  "status": "success",
  "message": "Coverage data stored successfully"
}
```

| Field                 | Type   | Required | Description                                        |
|-----------------------|--------|----------|----------------------------------------------------|
| `api_key`             | string | Yes      | API key obtained from `/api/generate-key`          |
| `latitude`            | float  | No       | GPS latitude                                       |
| `longitude`           | float  | No       | GPS longitude                                      |
| `gps_accuracy`        | float  | No       | GPS accuracy in meters                             |
| `signal_strength_dbm` | int    | No       | Signal strength in dBm                             |
| `signal_strength_asu` | int    | No       | Signal strength in ASU                             |
| `network_type`        | string | No       | Radio access type (e.g. `GSM`, `CDMA`, `LTE`, `NR`) |
| `data_network_type`   | string | No       | Data connection type                               |
| `mobile_country_code` | int    | No       | MCC (digit strings such as `"214"` are accepted)   |
| `network_code`        | int    | No       | MNC (digit strings such as `"01"` are accepted; stored as an integer) |
| `cell_id`             | int    | No       | Cell tower ID                                      |
| `app_name`            | string | No       | Client application name, or site hostname for the web plugin |
| `app_version`         | string | No       | Client application version                         |
| `library_version`     | string | No       | Coverage library version (`v0.1` Android, `web-<semver>` web plugin) |
| `download_speed`      | float  | No       | Download speed in kbps                             |
| `upload_speed`        | float  | No       | Upload speed in kbps                               |
| `latency_ms`          | int    | No       | Median round-trip time to `/api/test-ping` (web plugin) |
| `jitter_ms`           | int    | No       | Mean absolute difference between consecutive RTTs (web plugin) |
| `location_type`       | string | No       | `gps` when the client sent coordinates, `ip` when the server derived them. Set by the server when absent |
| `location_accuracy`   | float  | No       | Position accuracy in meters (web plugin sends the browser's estimate; the server sets its own for `ip` rows) |
| `timestamp`           | string | No       | ISO 8601 (`2026-09-07T10:51:54.503Z`, offsets accepted) or epoch milliseconds as a string (`"1757242314503"`). Defaults to server time when absent or unparseable |

Every optional field may be omitted or sent as `null`; both are stored as `NULL`. Unknown fields (e.g. Android's `android_id` and `is_position_from_GPS`) are ignored.

**Location.** When `latitude` and `longitude` are present they are stored as sent and `location_type` defaults to `gps` (Android's `0.0`/`0.0` "no fix" values are kept but not labelled). When they are absent, data-service derives an approximate position from the client IP and stores it with `location_type = "ip"` and its accuracy estimate; see [IP geolocation](#ip-geolocation). The IP address itself is never stored.

### 3. Test Latency

Minimal endpoint for round-trip time measurement. No API key is needed; it returns nothing and is as cheap as possible. The web plugin calls it several times and computes latency (median) and jitter.

```
GET /api/test-ping?t=<cache-buster>
```

Response: `204 No Content` with `Cache-Control: no-store`. The `t` parameter is ignored.

### 4. Test Download Speed

Serves `bytes` bytes of incompressible random data so the client can time a download.

```
GET /api/test-data-download?bytes=1000000&t=<cache-buster>
```

| Query param | Type   | Required | Description                                                          |
|-------------|--------|----------|----------------------------------------------------------------------|
| `bytes`     | int    | Yes      | Payload size, between 1 and `MAX_DOWNLOAD_BYTES` (default 10 000 000). Larger values get `400` |
| `t`         | string | No       | Cache-buster, ignored                                                |
| `api_key`   | string | No       | Optional. When present it is validated (`401` if invalid)            |

Response: `200` with `Content-Type: application/octet-stream`, an exact `Content-Length`, `Cache-Control: no-store` and no `Content-Encoding`. The payload is streamed in 64 KB chunks, so large sizes do not allocate memory.

### 5. Test Upload Speed

Accepts a multipart file upload for client-side upload speed measurement. The file data is consumed and discarded — nothing is stored. The client library times the request to calculate upload speed.

```
POST /api/test-data-upload
Content-Type: multipart/form-data
```

Form fields:

| Field     | Type   | Required | Description                           |
|-----------|--------|----------|---------------------------------------|
| `api_key` | string | Yes      | API key obtained from `/api/generate-key` |
| `file`    | file   | Yes      | Binary file payload for speed testing |

Response (`200 OK`):

```json
{
  "status": "success",
  "message": "Upload test completed successfully",
  "file_size_bytes": 1048576
}
```

### Error Responses

All endpoints return standard HTTP error codes:

| Code | Meaning                                  |
|------|------------------------------------------|
| 400  | Bad request (missing required fields, download size out of range) |
| 401  | Invalid API key                          |
| 422  | Validation error (wrong field types)     |
| 500  | Internal server error                    |

## Health Checks

| Endpoint         | Service        | Notes                       |
|------------------|----------------|-----------------------------|
| `/health/key`    | key-service    | Includes database connectivity |
| `/health/data`   | data-service   | Includes database connectivity |
| `/health/test`   | test-service   | Service availability only   |
| `/health/upload` | test-service   | Alias of `/health/test`, kept for existing monitors |

## IP Geolocation

Measurements sent without coordinates (the web plugin when the visitor denies the browser's geolocation prompt) are located approximately from the client IP, using a local copy of the free [MaxMind GeoLite2 City](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) database. Only the resulting coordinates and an accuracy estimate are stored (`location_type = "ip"`); the IP is neither stored nor logged by the services. Lookups never leave the server.

data-service reads the database from `GEOIP_DB_PATH` (default `/geoip/GeoLite2-City.mmdb`, the `geoip_data` volume). The file is provided and refreshed by the `geoipupdate` container, MaxMind's official updater:

1. Create a free MaxMind account and generate a license key.
2. Set `GEOIPUPDATE_ACCOUNT_ID` and `GEOIPUPDATE_LICENSE_KEY` in the environment (`.env` locally, the environment tab in Dokploy).
3. Start the updater: locally `docker-compose --profile geoip up -d`; in Dokploy it is part of the stack.

The updater downloads the database on start and checks for a new version every 72 hours (`GEOIPUPDATE_FREQUENCY`). data-service reopens the file automatically when it changes, so no restart is needed. Without the database (no credentials, updater not running, `GEOIP_ENABLED=false`) data-service logs one warning and stores such measurements without a location. The accuracy stored for IP rows is MaxMind's `accuracy_radius` converted to meters, or `GEOIP_DEFAULT_ACCURACY_M` (25 000 m) when the database gives none.

The client IP is taken from the first entry of `X-Forwarded-For` (set by Traefik and nginx), then `X-Real-IP`, then the socket peer. Private addresses are not looked up, so measurements from the local network are stored without a location. Note that nginx's default access log records client addresses like any web server; set `access_log off;` in `nginx/nginx.conf` if that is not wanted.

## Database Migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/), configured in `data-service/alembic/`. data-service runs `alembic upgrade head` programmatically every time it starts (`data-service/migrate.py`), so redeploying the stack is enough to migrate; no manual step is needed and running it again is a no-op. The applied revision is recorded in the `alembic_version` table.

Revisions:

| Revision | Content |
|----------|---------|
| `0001`   | Baseline: `api_keys` and `coverage_measurements` as created by `create_all()` before migrations existed. Tables are only created when missing, so on an existing database this revision just records the baseline |
| `0002`   | Web plugin columns `latency_ms`, `jitter_ms`, `location_type`, `location_accuracy` (skipped for columns that already exist) |

`init.sql` is only used by the development `postgres` container on a brand-new volume; keep it in sync with the models so a fresh development database matches production.

To add a schema change: edit `shared/database/models.py` and `database/init.sql`, then generate and review a revision from the data-service directory (needs `DATABASE_URL` pointing at a migrated database):

```bash
cd data-service
DATABASE_URL=postgresql://coverage:coverage@localhost:5432/coverage_db alembic revision --autogenerate -m "describe the change"
```

Other useful commands from the same directory: `alembic current`, `alembic history`, `alembic upgrade head`, `alembic downgrade -1`.

## Dokploy Deployment

The `docker-compose.dokploy.yml` file is the deployment configuration used by [Dokploy](https://dokploy.com), a self-hosted PaaS. It differs from the development compose file in a few key ways:

- **No PostgreSQL container** — the `DATABASE_URL` environment variable is injected externally (e.g. a managed database or a separate Dokploy-managed Postgres instance), so no `postgres` service is defined.
- **External network** — all services join the `dokploy-network` (marked `external: true`), which is the shared Docker network managed by Dokploy and Traefik. This allows Traefik to route traffic to the Nginx container automatically.
- **Nginx as the entrypoint** — Traefik forwards incoming HTTP traffic to the `nginx` container, which then reverse-proxies each path to the correct internal service.
- **Resource limits** — each service has explicit memory and CPU limits/reservations to prevent a single service from exhausting the host:

| Service        | Memory Limit | Memory Reserved | CPU Limit | CPU Reserved |
|----------------|-------------|-----------------|-----------|-------------|
| key-service    | 256 MB      | 128 MB          | —         | —           |
| data-service   | 1 GB        | 512 MB          | —         | —           |
| test-service   | 2 GB        | 1 GB            | 1.0 core  | 0.5 core    |

- **Restart policy** — all services use `restart: unless-stopped` so they recover from crashes automatically.
- **GeoIP** — the `geoipupdate` container needs `GEOIPUPDATE_ACCOUNT_ID` and `GEOIPUPDATE_LICENSE_KEY` in the Dokploy environment; without them it keeps restarting and data-service works without IP geolocation. The database lives in the `geoip_data` volume.

### HTTPS

The web plugin runs inside HTTPS pages, and browsers block calls from an HTTPS page to a plain `http://` API (mixed content), so the API must be served over HTTPS. Nothing changes in this repository: Traefik terminates TLS and forwards plain HTTP to nginx on the internal network. To enable it in Dokploy:

1. Point a DNS name (an `A` record) at the server. Let's Encrypt needs a real public hostname; the `*.traefik.me` name used during development is not suitable for production certificates.
2. In the Dokploy application, open **Domains**, add the hostname with the `nginx` service on port 80, enable **HTTPS** and select **Let's Encrypt** as the certificate provider. Dokploy configures Traefik and renews the certificate automatically. Ports 80 and 443 must be reachable from the internet for the challenge.
3. Enable the HTTP to HTTPS redirect on the same domain so old links keep working.

Afterwards, use `https://<hostname>` as `baseUrl` in the web plugin and in the Android library configuration.

## Mobile Integration Examples

### Android (Kotlin)

The examples below use [OkHttp](https://square.github.io/okhttp/) and [Gson](https://github.com/google/gson). Add these dependencies to your `build.gradle.kts`:

```kotlin
implementation("com.squareup.okhttp3:okhttp:4.12.0")
implementation("com.google.code.gson:gson:2.11.0")
```

#### Generate API Key

```kotlin
import com.google.gson.Gson
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody

data class GenerateKeyRequest(val phone_identifier: String)
data class GenerateKeyResponse(val api_key: String, val status: String)

fun generateApiKey(baseUrl: String, phoneId: String, callback: (String?) -> Unit) {
    val client = OkHttpClient()
    val gson = Gson()
    val json = gson.toJson(GenerateKeyRequest(phoneId))
    val body = json.toRequestBody("application/json".toMediaType())

    val request = Request.Builder()
        .url("$baseUrl/api/generate-key")
        .post(body)
        .build()

    client.newCall(request).enqueue(object : Callback {
        override fun onFailure(call: Call, e: java.io.IOException) {
            callback(null)
        }

        override fun onResponse(call: Call, response: Response) {
            response.body?.string()?.let { responseBody ->
                val result = gson.fromJson(responseBody, GenerateKeyResponse::class.java)
                callback(result.api_key)
            } ?: callback(null)
        }
    })
}
```

#### Send Coverage Data

```kotlin
data class SendDataRequest(
    val api_key: String,
    val latitude: Double?,
    val longitude: Double?,
    val gps_accuracy: Float?,
    val signal_strength_dbm: Int?,
    val signal_strength_asu: Int?,
    val network_type: String?,
    val data_network_type: String?,
    val mobile_country_code: Int?,
    val network_code: Int?,
    val cell_id: Long?,
    val app_name: String?,
    val app_version: String?,
    val library_version: String?,
    val download_speed: Double?,
    val upload_speed: Double?,
    val timestamp: String?
)

fun sendCoverageData(baseUrl: String, data: SendDataRequest, callback: (Boolean) -> Unit) {
    val client = OkHttpClient()
    val gson = Gson()
    val json = gson.toJson(data)
    val body = json.toRequestBody("application/json".toMediaType())

    val request = Request.Builder()
        .url("$baseUrl/api/send-data")
        .post(body)
        .build()

    client.newCall(request).enqueue(object : Callback {
        override fun onFailure(call: Call, e: java.io.IOException) {
            callback(false)
        }

        override fun onResponse(call: Call, response: Response) {
            callback(response.isSuccessful)
        }
    })
}
```

#### Test Upload Speed

```kotlin
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

fun testUploadSpeed(baseUrl: String, apiKey: String, payload: ByteArray, callback: (Int?) -> Unit) {
    val client = OkHttpClient()
    val startTime = System.currentTimeMillis()

    val requestBody = MultipartBody.Builder()
        .setType(MultipartBody.FORM)
        .addFormDataPart("api_key", apiKey)
        .addFormDataPart("file", "upload_test.bin", payload.toRequestBody())
        .build()

    val request = Request.Builder()
        .url("$baseUrl/api/test-data-upload")
        .post(requestBody)
        .build()

    client.newCall(request).enqueue(object : Callback {
        override fun onFailure(call: Call, e: java.io.IOException) {
            callback(null)
        }

        override fun onResponse(call: Call, response: Response) {
            val elapsedMs = System.currentTimeMillis() - startTime
            val speedKbps = if (elapsedMs > 0) {
                (payload.size * 8.0 / elapsedMs).toInt() // kbps
            } else null
            callback(speedKbps)
        }
    })
}
```

### iOS (Swift)

The examples below use Foundation's `URLSession` (no third-party dependencies required).

#### Generate API Key

```swift
import Foundation

struct GenerateKeyRequest: Codable {
    let phone_identifier: String
}

struct GenerateKeyResponse: Codable {
    let api_key: String
    let status: String
}

func generateApiKey(baseURL: String, phoneId: String, completion: @escaping (String?) -> Void) {
    guard let url = URL(string: "\(baseURL)/api/generate-key") else {
        completion(nil)
        return
    }

    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try? JSONEncoder().encode(GenerateKeyRequest(phone_identifier: phoneId))

    URLSession.shared.dataTask(with: request) { data, response, error in
        guard let data = data,
              let result = try? JSONDecoder().decode(GenerateKeyResponse.self, from: data) else {
            completion(nil)
            return
        }
        completion(result.api_key)
    }.resume()
}
```

#### Send Coverage Data

```swift
struct SendDataRequest: Codable {
    let api_key: String
    let latitude: Double?
    let longitude: Double?
    let gps_accuracy: Double?
    let signal_strength_dbm: Int?
    let signal_strength_asu: Int?
    let network_type: String?
    let data_network_type: String?
    let mobile_country_code: Int?
    let network_code: Int?
    let cell_id: Int?
    let app_name: String?
    let app_version: String?
    let library_version: String?
    let download_speed: Double?
    let upload_speed: Double?
    let timestamp: String?
}

struct SendDataResponse: Codable {
    let status: String
    let message: String
}

func sendCoverageData(baseURL: String, data: SendDataRequest, completion: @escaping (Bool) -> Void) {
    guard let url = URL(string: "\(baseURL)/api/send-data") else {
        completion(false)
        return
    }

    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try? JSONEncoder().encode(data)

    URLSession.shared.dataTask(with: request) { _, response, _ in
        let httpResponse = response as? HTTPURLResponse
        completion(httpResponse?.statusCode == 200)
    }.resume()
}
```

#### Test Upload Speed

```swift
func testUploadSpeed(baseURL: String, apiKey: String, payload: Data, completion: @escaping (Double?) -> Void) {
    guard let url = URL(string: "\(baseURL)/api/test-data-upload") else {
        completion(nil)
        return
    }

    let boundary = UUID().uuidString
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

    var body = Data()
    // api_key field
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"api_key\"\r\n\r\n".data(using: .utf8)!)
    body.append("\(apiKey)\r\n".data(using: .utf8)!)
    // file field
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"file\"; filename=\"upload_test.bin\"\r\n".data(using: .utf8)!)
    body.append("Content-Type: application/octet-stream\r\n\r\n".data(using: .utf8)!)
    body.append(payload)
    body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
    request.httpBody = body

    let startTime = Date()

    URLSession.shared.dataTask(with: request) { _, response, _ in
        let elapsed = Date().timeIntervalSince(startTime)
        let httpResponse = response as? HTTPURLResponse
        guard httpResponse?.statusCode == 200, elapsed > 0 else {
            completion(nil)
            return
        }
        let speedKbps = Double(payload.count * 8) / elapsed / 1000.0
        completion(speedKbps)
    }.resume()
}
```

## Development

### Local Development

```bash
# Start database only
docker-compose up postgres

# Install dependencies and run individual services
cd key-service && pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8001

cd data-service && pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8002

cd test-service && pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8003
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U coverage -d coverage_db

# View measurements
SELECT COUNT(*) FROM coverage_measurements;

# View registered API keys
SELECT COUNT(*) FROM api_keys;
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and adjust as needed.

| Variable          | Default                                                  | Description                     |
|-------------------|----------------------------------------------------------|---------------------------------|
| `DATABASE_URL`    | `postgresql://coverage:coverage@postgres:5432/coverage_db` | PostgreSQL connection string  |
| `POSTGRES_DB`     | `coverage_db`                                            | Database name                   |
| `POSTGRES_USER`   | `coverage`                                               | Database user                   |
| `POSTGRES_PASSWORD` | `coverage`                                             | Database password               |
| `LOG_LEVEL`       | `INFO`                                                   | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `SERVICE_VERSION` | `1.0.0`                                                  | Version reported by services    |
| `ENVIRONMENT`     | `development`                                            | Runtime environment             |
| `DEBUG`           | `false`                                                  | Enable debug mode               |
| `CORS_ALLOW_ORIGINS` | `*`                                                   | Origins allowed to call the API from a browser; `*` or a comma-separated list |
| `MAX_DOWNLOAD_BYTES` | `10000000`                                            | Maximum size of `/api/test-data-download` |
| `GEOIP_ENABLED`   | `true`                                                   | Locate measurements without coordinates by IP |
| `GEOIP_DB_PATH`   | `/geoip/GeoLite2-City.mmdb`                              | Path of the GeoLite2 City database inside data-service |
| `GEOIP_DEFAULT_ACCURACY_M` | `25000`                                         | Accuracy stored for IP rows when the database gives none |
| `GEOIPUPDATE_ACCOUNT_ID` | —                                                 | MaxMind account id for the `geoipupdate` container |
| `GEOIPUPDATE_LICENSE_KEY` | —                                                | MaxMind license key for the `geoipupdate` container |

## Monitoring & Maintenance

### Logs

```bash
# View all service logs
docker-compose logs -f

# View specific service
docker-compose logs -f data-service
```

### Backup Database

```bash
# Create backup
docker-compose exec postgres pg_dump -U coverage coverage_db > backup.sql

# Restore backup
docker-compose exec postgres psql -U coverage coverage_db < backup.sql
```

### Scaling Services

```bash
# Scale data service for high load
docker-compose up -d --scale data-service=3

# Scale test service
docker-compose up -d --scale test-service=2
```

## Security Considerations

- Change default PostgreSQL credentials in production
- Serve the API over HTTPS (see [HTTPS](#https)); the web plugin requires it
- CORS is open (`*`) by default because no cookies or credentials are used; restrict `CORS_ALLOW_ORIGINS` if the API should only serve known sites
- Consider rate limiting for public-facing endpoints (`/api/generate-key` and the test endpoints are callable from any browser)
- API keys authenticate devices but are not a substitute for transport-layer security

## Contributing

This is an open source project. Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Submit a pull request

## License

Open Source - MIT License
