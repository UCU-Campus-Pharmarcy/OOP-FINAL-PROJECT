"""Shared SQLite schema, connection setup, and fictional sample data."""

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path


DB_PATH = Path(__file__).resolve().with_name("pharmacy.db")
MAX_SQLITE_INTEGER = 2**63 - 1

PRESCRIPTION_SCHEMA = """
CREATE TABLE IF NOT EXISTS prescriptions (
    id INTEGER PRIMARY KEY,
    branch_id INTEGER NOT NULL REFERENCES branches(id),
    prescriber_code TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending', 'Dispensed', 'Cancelled')),
    patient_id TEXT NOT NULL DEFAULT 'FICTIONAL-LEGACY'
        CHECK (length(trim(patient_id)) > 0)
);
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS medicines (
    code TEXT PRIMARY KEY NOT NULL CHECK (length(trim(code)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    unit_price_minor INTEGER NOT NULL
        CHECK (typeof(unit_price_minor) = 'integer' AND unit_price_minor > 0),
    reorder_level INTEGER NOT NULL
        CHECK (typeof(reorder_level) = 'integer' AND reorder_level >= 0),
    medicine_type TEXT NOT NULL CHECK (medicine_type IN ('Ordinary', 'Controlled'))
);

CREATE TABLE IF NOT EXISTS branches (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS stock (
    branch_id INTEGER NOT NULL REFERENCES branches(id),
    medicine_code TEXT NOT NULL REFERENCES medicines(code),
    quantity INTEGER NOT NULL CHECK (typeof(quantity) = 'integer' AND quantity >= 0),
    PRIMARY KEY (branch_id, medicine_code)
);

CREATE TABLE IF NOT EXISTS prescribers (
    code TEXT PRIMARY KEY NOT NULL CHECK (length(trim(code)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0)
);

""" + PRESCRIPTION_SCHEMA + """
CREATE TABLE IF NOT EXISTS prescription_lines (
    prescription_id INTEGER NOT NULL REFERENCES prescriptions(id),
    medicine_code TEXT NOT NULL REFERENCES medicines(code),
    quantity INTEGER NOT NULL CHECK (typeof(quantity) = 'integer' AND quantity > 0),
    PRIMARY KEY (prescription_id, medicine_code)
);
"""


class PharmacyError(ValueError):
    """An input or business rule failure that the app can show to the user."""


def connect(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    """Open a connection with foreign-key checking enabled."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _seed_database(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT INTO medicines (code, name, unit_price_minor, reorder_level, medicine_type)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (code) DO NOTHING
        """,
        [
            ("MED001", "Demo Relief", 1250, 5, "Ordinary"),
            ("MED002", "Demo Control", 2500, 3, "Controlled"),
        ],
    )
    connection.executemany(
        "INSERT INTO branches (name) VALUES (?) ON CONFLICT (name) DO NOTHING",
        [("Cedar Campus",), ("Lake Campus",)],
    )
    connection.execute(
        """INSERT INTO prescribers (code, name) VALUES (?, ?)
           ON CONFLICT (code) DO NOTHING""",
        ("DR001", "Dr. Example"),
    )
    connection.executemany(
        """
        INSERT INTO stock (branch_id, medicine_code, quantity)
        SELECT id, ?, ? FROM branches WHERE name = ?
        ON CONFLICT (branch_id, medicine_code) DO NOTHING
        """,
        [
            ("MED001", 24, "Cedar Campus"),
            ("MED002", 12, "Cedar Campus"),
            ("MED001", 3, "Lake Campus"),
            ("MED002", 8, "Lake Campus"),
        ],
    )


def _migrate_prescriptions(connection: sqlite3.Connection) -> None:
    """Upgrade the original table without changing prescription IDs or lines."""
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(prescriptions)")}
    foreign_keys = connection.execute("PRAGMA foreign_key_list(prescriptions)").fetchall()
    table_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'prescriptions'"
    ).fetchone()["sql"]
    has_prescriber_foreign_key = any(row["from"] == "prescriber_code" for row in foreign_keys)
    if "patient_id" in columns and "'Cancelled'" in table_sql and not has_prescriber_foreign_key:
        return

    connection.execute(
        PRESCRIPTION_SCHEMA.replace("IF NOT EXISTS prescriptions", "prescriptions_migrated", 1)
    )
    patient_expression = "'FICTIONAL-LEGACY-' || id"
    if "patient_id" in columns:
        patient_expression = (
            "CASE WHEN patient_id IS NOT NULL AND length(trim(patient_id)) > 0 "
            "THEN patient_id ELSE 'FICTIONAL-LEGACY-' || id END"
        )
    connection.execute(
        f"""INSERT INTO prescriptions_migrated
                (id, branch_id, prescriber_code, status, patient_id)
            SELECT id, branch_id, prescriber_code, status, {patient_expression}
            FROM prescriptions"""
    )
    connection.execute("DROP TABLE prescriptions")
    connection.execute("ALTER TABLE prescriptions_migrated RENAME TO prescriptions")


def initialize_database(db_path: str | Path = DB_PATH, *, seed: bool = False) -> None:
    """Create or upgrade tables and optionally insert missing sample records."""
    with closing(connect(db_path)) as connection:
        # Replacing a referenced table requires disabling foreign keys before BEGIN.
        connection.execute("PRAGMA foreign_keys = OFF")
        try:
            with connection:
                connection.executescript("BEGIN IMMEDIATE;\n" + SCHEMA)
                _migrate_prescriptions(connection)
                if seed:
                    _seed_database(connection)
                if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    raise sqlite3.IntegrityError("Database initialization found invalid foreign keys.")
        finally:
            connection.execute("PRAGMA foreign_keys = ON")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the Campus Pharmacy database.")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite database path")
    parser.add_argument("--seed", action="store_true", help="insert fictional sample data")
    args = parser.parse_args()
    initialize_database(args.db, seed=args.seed)
    print(f"Database ready at {args.db.resolve()}")


if __name__ == "__main__":
    main()
