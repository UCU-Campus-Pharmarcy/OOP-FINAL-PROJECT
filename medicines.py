"""Medicine records and catalogue registration."""

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from db import DB_PATH, PharmacyError, connect


MAX_SQLITE_INTEGER = (1 << 63) - 1


class MedicineType(StrEnum):
    ORDINARY = "Ordinary"
    CONTROLLED = "Controlled"


@dataclass(frozen=True)
class Medicine:
    code: str
    name: str
    unit_price_minor: int
    reorder_level: int
    medicine_type: MedicineType


def _parse_unit_price(unit_price: str) -> int:
    price_text = unit_price.strip() if isinstance(unit_price, str) else ""
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", price_text):
        raise PharmacyError("Enter a positive unit price with up to two decimal places.")

    price = Decimal(price_text)
    if price <= 0:
        raise PharmacyError("Unit price must be greater than zero.")
    if price > Decimal(MAX_SQLITE_INTEGER).scaleb(-2):
        raise PharmacyError("The unit price is too large.")
    return int(price.scaleb(2))


def register_medicine(
    code: str,
    name: str,
    unit_price: str,
    reorder_level: int,
    medicine_type: str,
    *,
    db_path=DB_PATH,
) -> Medicine:
    """Validate the form values, save a new medicine, and return its record."""
    code = code.strip().upper() if isinstance(code, str) else ""
    name = name.strip() if isinstance(name, str) else ""
    medicine_type = medicine_type.strip().capitalize() if isinstance(medicine_type, str) else ""

    if not code or not name:
        raise PharmacyError("Medicine code and name are required.")
    if type(reorder_level) is not int or not 0 <= reorder_level <= MAX_SQLITE_INTEGER:
        raise PharmacyError("Enter a nonnegative whole number for the reorder level.")
    try:
        category = MedicineType(medicine_type)
    except ValueError as error:
        raise PharmacyError("Choose Ordinary or Controlled as the medicine type.") from error

    medicine = Medicine(code, name, _parse_unit_price(unit_price), reorder_level, category)
    with closing(connect(db_path)) as connection, connection:
        cursor = connection.execute(
            """INSERT INTO medicines (code, name, unit_price_minor, reorder_level, medicine_type)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (code) DO NOTHING""",
            (medicine.code, medicine.name, medicine.unit_price_minor,
             medicine.reorder_level, medicine.medicine_type),
        )
        if cursor.rowcount == 0:
            raise PharmacyError(f"Medicine code {medicine.code} already exists.")
    return medicine


def list_medicines(*, db_path=DB_PATH) -> list[Medicine]:
    """Return catalogue records in code order for the selection forms."""
    with closing(connect(db_path)) as connection:
        rows = connection.execute(
            """SELECT code, name, unit_price_minor, reorder_level, medicine_type
               FROM medicines ORDER BY code"""
        ).fetchall()
    return [
        Medicine(row["code"], row["name"], row["unit_price_minor"], row["reorder_level"],
                 MedicineType(row["medicine_type"]))
        for row in rows
    ]
