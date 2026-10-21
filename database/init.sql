-- GIGA Coverage Database Initialization Script

-- Create the API keys table for phone_identifier to API key mapping
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    phone_identifier VARCHAR(255) UNIQUE NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the coverage measurements table
CREATE TABLE IF NOT EXISTS coverage_measurements (
    id SERIAL PRIMARY KEY,
    api_key VARCHAR(255) NOT NULL,
    phone_identifier VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Location data
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    gps_accuracy DOUBLE PRECISION,
    location_type VARCHAR(10),  -- 'gps' (sent by the client) or 'ip' (derived by the server)
    location_accuracy DOUBLE PRECISION,  -- meters
    
    -- Signal strength data
    signal_strength_dbm INTEGER,
    signal_strength_asu INTEGER,
    
    -- Network information
    network_type VARCHAR(50),
    mcc INTEGER,  -- Mobile Country Code
    mnc INTEGER,  -- Mobile Network Code
    cell_id BIGINT,
    
    -- Device information
    app_name VARCHAR(255),
    app_version VARCHAR(100),
    library_version VARCHAR(100),
    
    -- Performance data of the cellular network
    data_network_type VARCHAR(50),
    download_speed_kbps DOUBLE PRECISION,
    upload_speed_kbps DOUBLE PRECISION,
    latency_ms INTEGER,
    jitter_ms INTEGER,
    
    -- Foreign key constraint
    CONSTRAINT fk_api_key FOREIGN KEY (api_key) REFERENCES api_keys(api_key) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_api_keys_phone_identifier ON api_keys(phone_identifier);
CREATE INDEX IF NOT EXISTS idx_api_keys_api_key ON api_keys(api_key);

CREATE INDEX IF NOT EXISTS idx_coverage_phone_identifier ON coverage_measurements(phone_identifier);
CREATE INDEX IF NOT EXISTS idx_coverage_timestamp ON coverage_measurements(timestamp);
CREATE INDEX IF NOT EXISTS idx_coverage_location ON coverage_measurements(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_coverage_network_type ON coverage_measurements(network_type);
CREATE INDEX IF NOT EXISTS idx_coverage_mcc_mnc ON coverage_measurements(mcc, mnc);
CREATE INDEX IF NOT EXISTS idx_coverage_api_key ON coverage_measurements(api_key);