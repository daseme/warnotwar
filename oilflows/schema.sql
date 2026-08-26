CREATE TABLE IF NOT EXISTS ports (
    port_id TEXT PRIMARY KEY,
    port_name TEXT NOT NULL,
    country TEXT NOT NULL,
    role TEXT NOT NULL,
    include_group TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    locode TEXT,
    approved INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS portwatch_daily (
    date TEXT NOT NULL,
    port_id TEXT NOT NULL,
    port_name TEXT,
    country TEXT,
    tanker_calls INTEGER,
    import_tanker_mt REAL,
    export_tanker_mt REAL,
    retrieved_at TEXT NOT NULL,
    PRIMARY KEY (date, port_id)
);

CREATE TABLE IF NOT EXISTS hormuz_daily (
    date TEXT PRIMARY KEY,
    tanker_count INTEGER,
    total_ship_count INTEGER,
    tanker_capacity_mt REAL,
    total_capacity_mt REAL,
    retrieved_at TEXT NOT NULL
);
