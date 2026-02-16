# ==============================================================================
# DATABASE CONNECTION CONFIGURATION
# ==============================================================================
# Lokalnie: SQLite (DATA/codify.db).
# Na Streamlit Cloud: ustaw w Secrets lub zmiennej DATABASE_URL adres PostgreSQL,
# np. z Supabase/Neon – wtedy użytkownicy i historia są trwale zapisane.
# ==============================================================================

import os
import sqlite3
from pathlib import Path

_DB_TYPE = None  # "sqlite" | "postgres"
_ENGINE = None   # dla PostgreSQL (psycopg2 connection pool / single conn)

def _get_database_url():
    """Pobiera URL bazy z Streamlit Secrets (Cloud) lub zmiennej środowiska."""
    try:
        import streamlit as st
        url = (st.secrets.get("database") or {}).get("url") if hasattr(st, "secrets") else None
    except Exception:
        url = None
    return url or os.environ.get("DATABASE_URL")

def _is_postgres(url):
    if not url:
        return False
    u = (url or "").strip().lower()
    return u.startswith("postgresql://") or u.startswith("postgres://")

def get_db_type():
    """Zwraca 'sqlite' lub 'postgres' w zależności od konfiguracji."""
    global _DB_TYPE
    if _DB_TYPE is not None:
        return _DB_TYPE
    url = _get_database_url()
    _DB_TYPE = "postgres" if _is_postgres(url) else "sqlite"
    return _DB_TYPE


class _PgCursorWrapper:
    """Cursor dla PostgreSQL: zamienia ? na %s i emuluje lastrowid (RETURNING id)."""
    def __init__(self, real_cursor):
        self._cursor = real_cursor
        self._lastrowid = None

    def _convert_sql(self, sql):
        if isinstance(sql, str) and "?" in sql:
            return sql.replace("?", "%s")
        return sql

    def execute(self, sql, params=None):
        sql = self._convert_sql(sql)
        self._lastrowid = None
        if params is not None:
            self._cursor.execute(sql, params)
        else:
            self._cursor.execute(sql)
        # Po INSERT bez RETURNING – spróbuj pobrać id (np. z RETURNING w nadpisanej kwerendzie)
        if sql.strip().upper().startswith("INSERT"):
            try:
                row = self._cursor.fetchone()
                if row is not None:
                    self._lastrowid = row[0] if isinstance(row, (tuple, list)) else row
            except Exception:
                pass
        return self._cursor

    def executemany(self, sql, params_list):
        sql = self._convert_sql(sql)
        return self._cursor.executemany(sql, params_list)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        return self._lastrowid

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _PgConnWrapper:
    """Połączenie PostgreSQL z cursorem zamieniającym ? na %s i lastrowid."""
    def __init__(self, conn, db_url):
        self._conn = conn
        self._url = db_url

    def cursor(self):
        return _PgCursorWrapper(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _pg_connect(url):
    """Nawiązuje połączenie PostgreSQL z URL (postgresql://user:pass@host:port/dbname?sslmode=require)."""
    import urllib.parse
    import psycopg2
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "postgres":
        url = "postgresql" + url[8:]
        parsed = urllib.parse.urlparse(url)
    kwargs = dict(
        host=parsed.hostname or "localhost",
        port=parsed.port or 5432,
        dbname=(parsed.path or "/").strip("/") or "postgres",
        user=parsed.username,
        password=urllib.parse.unquote(parsed.password or "") or None,
    )
    # Parametry z query string (np. sslmode=require dla Neon/Supabase)
    if parsed.query:
        opts = urllib.parse.parse_qs(parsed.query)
        for key, val in opts.items():
            if key in ("sslmode", "sslcert", "sslkey", "sslrootcert") and val:
                kwargs[key] = val[0]
    conn = psycopg2.connect(**kwargs)
    return conn


def _run_pg_insert_with_returning(cursor, sql, params):
    """Wykonuje INSERT na PostgreSQL i ustawia lastrowid (RETURNING id)."""
    sql = sql.replace("?", "%s").strip().rstrip(";")
    if "RETURNING" not in sql.upper():
        sql = sql + " RETURNING id"
    cursor._cursor.execute(sql, params)
    row = cursor._cursor.fetchone()
    if row is not None:
        cursor._lastrowid = row[0]
    return cursor._cursor


# Nadpisanie metody execute w wrapperze, żeby dla INSERT dodawać RETURNING id i ustawiać lastrowid
def _pg_cursor_execute(self, sql, params=None):
    sql_converted = self._convert_sql(sql)
    self._lastrowid = None
    is_insert = sql_converted.strip().upper().startswith("INSERT")
    if is_insert and "RETURNING" not in sql_converted.upper():
        sql_converted = sql_converted.strip().rstrip(";") + " RETURNING id"
    if params is not None:
        self._cursor.execute(sql_converted, params)
    else:
        self._cursor.execute(sql_converted)
    if is_insert:
        try:
            row = self._cursor.fetchone()
            if row is not None:
                self._lastrowid = row[0]
        except Exception:
            pass
    return self._cursor


# Podmieniamy execute w _PgCursorWrapper na wersję z RETURNING
_PgCursorWrapper.execute = _pg_cursor_execute


# Ścieżka SQLite (lokalnie)
SQLITE_PATH = Path("DATA/codify.db")
SQLITE_PATH.parent.mkdir(exist_ok=True)


def get_connection():
    """Zwraca połączenie z bazą: SQLite (lokalnie) lub PostgreSQL (gdy ustawiony DATABASE_URL / Secrets)."""
    url = _get_database_url()
    if _is_postgres(url):
        conn = _pg_connect(url)
        return _PgConnWrapper(conn, url)
    return sqlite3.connect(str(SQLITE_PATH))
