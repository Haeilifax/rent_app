-- pragmas chosen inspired by https://briandouglas.ie/sqlite-defaults/
-- These are the pragmas expected to be used by clients interacting with this
-- database
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA cache_size = -20000;
PRAGMA foreign_keys = ON;
PRAGMA auto_vacuum = INCREMENTAL;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 2147483648;
PRAGMA page_size = 8192;
PRAGMA journal_mode = WAL;


CREATE TABLE IF NOT EXISTS Unit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL,
    created_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_on DATETIME
);

CREATE TABLE IF NOT EXISTS Tenant (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unit NOT NULL REFERENCES Unit (id) ON DELETE RESTRICT,
    created_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_on DATETIME
);

CREATE TABLE IF NOT EXISTS Lease (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant NOT NULL REFERENCES Tenant (id) ON DELETE RESTRICT, 
    rent REAL NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    created_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_on DATETIME
);

CREATE TABLE IF NOT EXISTS CollectedRent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lease NOT NULL REFERENCES Lease (id) ON DELETE RESTRICT,
    amount REAL NOT NULL,
    collected_for DATE NOT NULL,
    collected_on DATE NOT NULL,
    created_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_on DATETIME
);