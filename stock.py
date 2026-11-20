"""Branch creation and branch-specific stock receipts."""

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from db import DB_PATH, MAX_SQLITE_INTEGER, PharmacyError, connect


@dataclass(frozen=True)
class Branch:
    id: int
    name: str


def create_branch(name: str, *, db_path: str | Path = DB_PATH) -> Branch:
    """Create a uniquely named branch and return its generated ID and name."""
    if not isinstance(name, str) or not name.strip():
        raise PharmacyError("Enter a branch name.")
    name = name.strip()
    with closing(connect(db_path)) as connection, connection:
        try:
            cursor = connection.execute("INSERT INTO branches (name) VALUES (?)", (name,))
        except sqlite3.IntegrityError as error:
            if error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
                raise PharmacyError(f"Branch {name!r} already exists.") from error
            raise
        return Branch(cursor.lastrowid, name)


def list_branches(*, db_path: str | Path = DB_PATH) -> list[Branch]:
    """List branches in name order for the GUI."""
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
    """Add stock to one branch and return that branch's new quantity."""
    if type(branch_id) is not int or not 1 <= branch_id <= MAX_SQLITE_INTEGER:
        raise PharmacyError("Select a valid branch.")
    if not isinstance(medicine_code, str) or not medicine_code.strip():
        raise PharmacyError("Select a medicine.")
    if type(quantity) is not int or not 1 <= quantity <= MAX_SQLITE_INTEGER:
        raise PharmacyError("Enter a positive whole-number quantity within the database limit.")
    medicine_code = medicine_code.strip().upper()

    with closing(connect(db_path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("SELECT 1 FROM branches WHERE id = ?", (branch_id,)).fetchone() is None:
            raise PharmacyError("The selected branch does not exist.")
        if connection.execute(
            "SELECT 1 FROM medicines WHERE code = ?", (medicine_code,)
        ).fetchone() is None:
            raise PharmacyError("The selected medicine does not exist.")

        cursor = connection.execute(
            """
            INSERT INTO stock (branch_id, medicine_code, quantity) VALUES (?, ?, ?)
            ON CONFLICT (branch_id, medicine_code) DO UPDATE
                SET quantity = stock.quantity + excluded.quantity
                WHERE stock.quantity <= ? - excluded.quantity
            """,
            (branch_id, medicine_code, quantity, MAX_SQLITE_INTEGER),
        )
        if cursor.rowcount == 0:
            raise PharmacyError("The new stock total exceeds the database limit.")

        row = connection.execute(
            "SELECT quantity FROM stock WHERE branch_id = ? AND medicine_code = ?",
            (branch_id, medicine_code),
        ).fetchone()
        return row["quantity"]
