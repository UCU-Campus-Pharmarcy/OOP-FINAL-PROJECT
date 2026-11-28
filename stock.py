"""Member 2: independent branch stock, guarded receipts, and stock lookups."""

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from db import (
    DB_PATH,
    MAX_SQLITE_INTEGER,
    PharmacyError,
    connect,
    normalize_code,
    require_positive_integer,
    require_text,
)


@dataclass(frozen=True)
class Branch:
    id: int
    name: str


@dataclass(frozen=True)
class StockItem:
    medicine_code: str
    name: str
    quantity: int
    reorder_level: int


def create_branch(name: str, *, db_path: str | Path = DB_PATH) -> Branch:
    """Save a uniquely named branch and return its generated ID."""
    name = require_text(name, "Branch name")
    with closing(connect(db_path)) as connection, connection:
        try:
            cursor = connection.execute("INSERT INTO branches (name) VALUES (?)", (name,))
        except sqlite3.IntegrityError as error:
            if error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
                raise PharmacyError(f"Branch {name!r} already exists.") from error
            raise
        return Branch(cursor.lastrowid, name)


def list_branches(*, db_path: str | Path = DB_PATH) -> list[Branch]:
    """Return branch IDs and labels for selectors in the app."""
    with closing(connect(db_path)) as connection:
        rows = connection.execute("SELECT id, name FROM branches ORDER BY name COLLATE NOCASE")
        return [Branch(row["id"], row["name"]) for row in rows]


def receive_stock(
    branch_id: int,
    medicine_code: str,
    quantity: int,
    *,
    db_path: str | Path = DB_PATH,
) -> int:
    """Add a positive quantity at one branch and return its new on-hand total."""
    require_positive_integer(branch_id, "Branch ID")
    medicine_code = normalize_code(medicine_code)
    require_positive_integer(quantity, "Receipt quantity")

    with closing(connect(db_path)) as connection, connection:
        # The writer reservation covers the lookups, update, and returned total.
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("SELECT 1 FROM branches WHERE id = ?", (branch_id,)).fetchone() is None:
            raise PharmacyError("The selected branch does not exist.")
        if connection.execute(
            "SELECT 1 FROM medicines WHERE code = ?", (medicine_code,)
        ).fetchone() is None:
            raise PharmacyError(f"Medicine {medicine_code} is not registered.")

        cursor = connection.execute(
            """INSERT INTO stock (branch_id, medicine_code, quantity) VALUES (?, ?, ?)
               ON CONFLICT (branch_id, medicine_code) DO UPDATE
               SET quantity = stock.quantity + excluded.quantity
               WHERE stock.quantity <= ? - excluded.quantity""",
            (branch_id, medicine_code, quantity, MAX_SQLITE_INTEGER),
        )
        if cursor.rowcount == 0:
            raise PharmacyError("The new stock total exceeds the database limit.")
        row = connection.execute(
            "SELECT quantity FROM stock WHERE branch_id = ? AND medicine_code = ?",
            (branch_id, medicine_code),
        ).fetchone()
        return row["quantity"]


def list_stock(branch_id: int, *, db_path: str | Path = DB_PATH) -> list[StockItem]:
    """List tracked stock rows for one existing branch, including zero rows."""
    require_positive_integer(branch_id, "Branch ID")
    with closing(connect(db_path)) as connection:
        if connection.execute("SELECT 1 FROM branches WHERE id = ?", (branch_id,)).fetchone() is None:
            raise PharmacyError("The selected branch does not exist.")
        rows = connection.execute(
            """SELECT s.medicine_code, m.name, s.quantity, m.reorder_level
               FROM stock AS s
               JOIN medicines AS m ON m.code = s.medicine_code
               WHERE s.branch_id = ? ORDER BY s.medicine_code""",
            (branch_id,),
        ).fetchall()
    return [StockItem(**row) for row in rows]
