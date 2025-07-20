
-- dashboard database
\c dashboard

-- keys per minute
CREATE TABLE IF NOT EXISTS metric_data_kpm (
    id serial PRIMARY KEY,
    -- ISO8601 with time zone
    reading_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    val INTEGER
);

-- clicks per minute
CREATE TABLE IF NOT EXISTS metric_data_cpm (
    id serial PRIMARY KEY,
    -- ISO8601 with time zone
    reading_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    val INTEGER
);

-- pixels per minute
CREATE TABLE IF NOT EXISTS metric_data_pxm (
    id serial PRIMARY KEY,
    -- ISO8601 with time zone
    reading_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    val REAL
);

-- current media title
CREATE TABLE IF NOT EXISTS metric_data_title (
    id serial PRIMARY KEY,
    -- ISO8601 with time zone
    reading_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    val VARCHAR(30)
);
