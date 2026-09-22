"""SQLite schema definitions for local database."""

from __future__ import annotations

# SQL statements for table creation
CREATE_PAPERS_TABLE = """
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doi TEXT UNIQUE,
    arxiv_id TEXT,
    title TEXT NOT NULL,
    authors TEXT,
    year INTEGER,
    venue TEXT,
    abstract TEXT,
    categories TEXT,
    external_ids TEXT,
    source TEXT DEFAULT 'api',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT papers_doi_unique UNIQUE (doi),
    CONSTRAINT papers_arxiv_unique UNIQUE (arxiv_id)
);
"""

CREATE_QUERY_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT NOT NULL,
    found INTEGER DEFAULT 0,
    source TEXT,
    paper_id INTEGER REFERENCES papers(id) ON DELETE SET NULL,
    queried_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Index creation statements
CREATE_PAPERS_INDEXES = """
-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_arxiv ON papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title);
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);

-- Index for query log
CREATE INDEX IF NOT EXISTS idx_query_log_hash ON query_log(query_hash);
CREATE INDEX IF NOT EXISTS idx_query_log_found ON query_log(found);
"""

# Full-text search setup
CREATE_FTS_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
    title,
    authors,
    abstract,
    content='papers',
    content_rowid='id',
    tokenize='porter unicode61'
);
"""

# Triggers to keep FTS in sync
CREATE_FTS_INSERT_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS papers_fts_insert AFTER INSERT ON papers BEGIN
    INSERT INTO papers_fts(rowid, title, authors, abstract)
    VALUES (new.id, new.title, new.authors, new.abstract);
END;
"""

CREATE_FTS_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS papers_fts_delete AFTER DELETE ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, title, authors, abstract)
    VALUES ('delete', old.id, old.title, old.authors, old.abstract);
END;
"""

CREATE_FTS_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS papers_fts_update AFTER UPDATE ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, title, authors, abstract)
    VALUES ('delete', old.id, old.title, old.authors, old.abstract);
    INSERT INTO papers_fts(rowid, title, authors, abstract)
    VALUES (new.id, new.title, new.authors, new.abstract);
END;
"""

# All statements to run on initialization
INIT_STATEMENTS = [
    CREATE_PAPERS_TABLE,
    CREATE_QUERY_LOG_TABLE,
    CREATE_PAPERS_INDEXES,
    CREATE_FTS_TABLE,
    CREATE_FTS_INSERT_TRIGGER,
    CREATE_FTS_DELETE_TRIGGER,
    CREATE_FTS_UPDATE_TRIGGER,
]
