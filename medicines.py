"""Validated medicine objects and SQLite catalogue services owned by Member 1."""

from abc import ABC, abstractmethod
from contextlib import closing
from dataclasses import dataclass
from decimal import Decimal
import re

from db import (
    DB_PATH,
    MAX_SQLITE_INTEGER,
    PharmacyError,
    connect,
    normalize_code,
    require_nonnegative_integer,
    require_positive_integer,
    require_text,
)


@dataclass(frozen=True)
class Medicine(ABC):
    """Read-only domain fields keep every constructed medicine valid."""

    code: str
    name: str
    unit_price_minor: int
    reorder_level: int

    def __post_init__(self):
        # Frozen dataclasses permit normalization during construction only.
        object.__setattr__(self, "code", normalize_code(self.code))
        object.__setattr__(self, "name", require_text(self.name, "Medicine name"))
        require_positive_integer(self.unit_price_minor, "Unit price in minor units")
        require_nonnegative_integer(self.reorder_level, "Reorder level")

    @property
    def unit_price(self) -> Decimal:
        """Return an exact two-decimal value without binary floating point."""
        return Decimal(self.unit_price_minor).scaleb(-2)

    @property
    @abstractmethod
    def medicine_type(self) -> str:
        """Return the discriminator stored by the persistence layer."""

    def requires_authorized_prescriber(self) -> bool:
        """Ordinary medicines use the default authorization policy."""
        return False


@dataclass(frozen=True)
class OrdinaryMedicine(Medicine):
    @property
    def medicine_type(self) -> str:
        return "Ordinary"


@dataclass(frozen=True)
class ControlledMedicine(Medicine):
    @property
    def medicine_type(self) -> str:
        return "Controlled"

    def requires_authorized_prescriber(self) -> bool:
        """Override the policy used polymorphically by the dispensing service."""
        return True


def medicine_from_row(row) -> Medicine:
    """Restore the appropriate subclass from a sqlite3.Row or keyed mapping."""
    category = require_text(row["medicine_type"], "Medicine type").capitalize()
    classes = {"Ordinary": OrdinaryMedicine, "Controlled": ControlledMedicine}
    if category not in classes:
        raise PharmacyError("Choose Ordinary or Controlled as the medicine type.")
    return classes[category](
        code=row["code"],
        name=row["name"],
        unit_price_minor=row["unit_price_minor"],
        reorder_level=row["reorder_level"],
    )


def _parse_unit_price(unit_price: str) -> int:
    """Parse a positive price supplied as text with at most two decimals."""
    price_text = require_text(unit_price, "Unit price")
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", price_text):
        raise PharmacyError("Enter a positive unit price with up to two decimal places.")
    price = Decimal(price_text)
    if price <= 0:
        raise PharmacyError("Unit price must be greater than zero.")
    if price > Decimal(MAX_SQLITE_INTEGER).scaleb(-2):
        raise PharmacyError("The unit price exceeds the database limit.")
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
    """Validate, save, and return one new medicine or raise PharmacyError."""
    medicine = medicine_from_row({
        "code": code,
        "name": name,
        "unit_price_minor": _parse_unit_price(unit_price),
        "reorder_level": reorder_level,
        "medicine_type": medicine_type,
    })
    with closing(connect(db_path)) as connection, connection:
        cursor = connection.execute(
            """INSERT INTO medicines
               (code, name, unit_price_minor, reorder_level, medicine_type)
               VALUES (?, ?, ?, ?, ?) ON CONFLICT (code) DO NOTHING""",
            (medicine.code, medicine.name, medicine.unit_price_minor,
             medicine.reorder_level, medicine.medicine_type),
        )
        if cursor.rowcount == 0:
            raise PharmacyError(f"Medicine code {medicine.code} already exists.")
    return medicine


def list_medicines(*, db_path=DB_PATH) -> list[Medicine]:
    """Return catalogue objects in code order for selection forms."""
    with closing(connect(db_path)) as connection:
        rows = connection.execute(
            """SELECT code, name, unit_price_minor, reorder_level, medicine_type
               FROM medicines ORDER BY code"""
        ).fetchall()
    return [medicine_from_row(row) for row in rows]


def get_medicine(code: str, *, db_path=DB_PATH) -> Medicine:
    """Return one normalized code or raise a user-facing unknown-code error."""
    code = normalize_code(code)
    with closing(connect(db_path)) as connection:
        row = connection.execute(
            """SELECT code, name, unit_price_minor, reorder_level, medicine_type
               FROM medicines WHERE code = ?""",
            (code,),
        ).fetchone()
    if row is None:
        raise PharmacyError(f"Medicine {code} is not registered.")
    return medicine_from_row(row)
