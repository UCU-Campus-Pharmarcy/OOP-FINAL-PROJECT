"""Member 2: shared SQLite setup, validation helpers, and fictional sample data."""

import argparse
from contextlib import closing
from pathlib import Path
import sqlite3


DB_PATH = Path(__file__).resolve().with_name("pharmacy.db")
MAX_SQLITE_INTEGER = (1 << 63) - 1
SCHEMA_PATH = Path(__file__).resolve().with_name("schema.sql")


class PharmacyError(ValueError):
    """A rejected form value or business rule with a user-facing message."""


def require_text(value: str, label: str) -> str:
    """Return trimmed, required text or reject an absent value."""
    if not isinstance(value, str) or not value.strip():
        raise PharmacyError(f"{label} is required.")
    return value.strip()


def normalize_code(value: str, label: str = "Medicine code") -> str:
    """Use one code representation in every service and lookup."""
    return require_text(value, label).upper()


def require_positive_integer(value: int, label: str) -> int:
    """Reject booleans, fractions, nonpositive amounts, and integer overflow."""
    if type(value) is not int or not 1 <= value <= MAX_SQLITE_INTEGER:
        raise PharmacyError(f"{label} must be a positive whole number within the database limit.")
    return value


def require_nonnegative_integer(value: int, label: str) -> int:
    """Validate counts such as a medicine's reorder level."""
    if type(value) is not int or not 0 <= value <= MAX_SQLITE_INTEGER:
        raise PharmacyError(f"{label} must be a nonnegative whole number within the database limit.")
    return value


def connect(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    """Open a row-based connection with foreign-key enforcement enabled."""
    connection = sqlite3.connect(db_path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _seed_database(connection: sqlite3.Connection) -> None:
    """Insert missing fictional examples while preserving changed records."""
    connection.executemany(
        """INSERT INTO medicines
               (code, name, unit_price_minor, reorder_level, medicine_type)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT (code) DO NOTHING""",
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
        """INSERT INTO stock (branch_id, medicine_code, quantity)
           SELECT id, ?, ? FROM branches WHERE name = ?
           ON CONFLICT (branch_id, medicine_code) DO NOTHING""",
        [
            ("MED001", 24, "Cedar Campus"),
            ("MED002", 12, "Cedar Campus"),
            ("MED001", 3, "Lake Campus"),
            ("MED002", 8, "Lake Campus"),
        ],
    )


def initialize_database(db_path: str | Path = DB_PATH, *, seed: bool = False) -> None:
    """Create missing tables and optionally seed them in one transaction.

    Repeated setup preserves existing data. Existing tables keep their original
    definitions, so use a fresh file when trying a changed schema.
    """
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with closing(connect(db_path)) as connection, connection:
        connection.executescript("BEGIN IMMEDIATE;\n" + schema)
        if seed:
            _seed_database(connection)


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the Campus Pharmacy SQLite database.")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="database file path")
    parser.add_argument("--seed", action="store_true", help="load missing fictional sample data")
    args = parser.parse_args()
    try:
        initialize_database(args.db, seed=args.seed)
    except (OSError, sqlite3.Error) as error:
        parser.exit(1, f"Database initialization failed. {error}\n")
    print(f"Database ready at {args.db.resolve()}")


if __name__ == "__main__":
    main()
