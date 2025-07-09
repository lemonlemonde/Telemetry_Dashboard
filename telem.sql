

-- telemetry database
\c telemetry;


-- Same thing as telemetry.proto
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'system_type') THEN
        CREATE TYPE system_type AS ENUM (
            'UNKNOWN_SYSTEM',
            'ENGINE',
            'FUEL_TANK',
            'AVIONICS',
            'TURBOPUMP',
            'GUIDANCE',
            'STAGE1',
            'STAGE2'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'telemetry_type') THEN
        CREATE TYPE telemetry_type AS ENUM (
            'TEMPERATURE', 
            'PRESSURE', 
            'VELOCITY'
        );
    END IF;
END $$;


-- from telemetry.proto:
    -- string timestamp = 1;
    -- TelemetryType type = 4;

    -- message TemperatureData {
    --     string sensor_id = 1;
    --     System subsystem = 2;

    --     float temperature = 3;
    --     string unit = 4;
    --     uint32 status_bitmask = 5;
        
    --     int32 sequence_number = 6;
    -- }

    -- message PressureData {
    --     string sensor_id = 1;
    --     System subsystem = 2;
        
    --     float pressure = 3;
    --     string unit = 4;
    --     uint32 status_bitmask = 5;
    --     bool leak_detected = 6;
        
    --     int32 sequence_number = 7;
    -- }

    -- message VelocityData {
    --     string sensor_id = 1;
    --     System subsystem = 2;
        
    --     float velocity_x = 3;
    --     float velocity_y = 4;
    --     float velocity_z = 5;
    --     string unit = 6;
    --     float vibration_mag = 7;
        
    --     uint32 status_bitmask = 8;
    --     int32 sequence_number = 9;
    -- }
CREATE TABLE IF NOT EXISTS telemetry_data (
    id serial PRIMARY KEY,

    -- shared values:
    -- ISO8601 with time zone
    reading_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    telemetry_type telemetry_type NOT NULL,

    sensor_id VARCHAR(50) NOT NULL,
    subsystem system_type NOT NULL,
    
    sequence_number INTEGER,
    status_bitmask SMALLINT,
    

    -- only temp
        -- float, 4-bytes
    temperature REAL,
        -- str (short)
    temp_unit VARCHAR(10),
    
    -- only pressure
        -- float, 4-bytes
    pressure REAL,
        -- str (short)
    pressure_unit VARCHAR(10),
        -- TODO: not used yet
    leak_detected BOOLEAN,
    
    -- only velo
        -- float, 4-bytes
    velocity_x REAL,
    velocity_y REAL,
    velocity_z REAL,
        -- str (short)
    velocity_unit VARCHAR(10),
        -- TODO: not used yet
    vibration_magnitude REAL
);


-- mhm
-- DROP VIEW IF EXISTS latest_telemetry;

-- -- ease of use for dashboard
-- CREATE VIEW latest_telemetry AS
--     SELECT DISTINCT ON (sensor_id, telemetry_type) *
--         FROM telemetry_data
--         ORDER BY sensor_id, telemetry_type, reading_timestamp DESC;





-- increase performance with larger tables
    -- but probably worse off with my basic simulation project
    -- because it'll duplicate data and just take up more storage
    -- also takes up more time during insertion time
        -- and my simulation project should ideally be running on real-time data
-- https://stackoverflow.com/questions/13234812/improving-query-speed-simple-select-in-big-postgres-table
-- https://wiki.postgresql.org/wiki/What%27s_new_in_PostgreSQL_9.2#Index-only_scans
-- CREATE INDEX idx_telemetry_timestamp ON telemetry_data(timestamp);
-- CREATE INDEX idx_telemetry_type ON telemetry_data(telemetry_type);
-- CREATE INDEX idx_telemetry_subsystem ON telemetry_data(subsystem);
-- CREATE INDEX idx_telemetry_sensor ON telemetry_data(sensor_id);