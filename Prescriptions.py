"""Multi-line prescriptions and atomic, branch-specific dispensing."""

from collections.abc import Iterable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from db import (
    DB_PATH,
    PharmacyError,
    connect,
    normalize_code,
    require_positive_integer,
    require_text,
)
from medicines import medicine_from_row


@dataclass(frozen=True)
class Prescriber:
    code: str
    name: str


@dataclass(frozen=True)
class Prescription:
    id: int
    branch_id: int
    patient_id: str
    prescriber_code: str | None
    status: str


@dataclass(frozen=True)
class PrescriptionLine:
    medicine_code: str
    quantity: int


def create_prescription(
    branch_id: int,
    patient_id: str,
    lines: Iterable[tuple[str, int]],
    *,
     prescriber_code: str | None = None,
    db_path: str | Path = DB_PATH,
) -> int:
    """Save a pending header and aggregated lines together and return its ID.

    A prescriber code is optional while recording a prescription. Controlled
    medicines require an allow-listed code when dispensing is attempted.
    """
    branch_id = require_positive_integer(branch_id, "Branch ID")
    patient_id = require_text(patient_id, "Fictional patient identifier")
    if prescriber_code is not None:
        if not isinstance(prescriber_code, str):
            raise PharmacyError("Prescriber code must be text or left blank.")
        prescriber_code = prescriber_code.strip().upper() or None

    try:
        iterator = iter(lines)
    except TypeError as error:
        raise PharmacyError("Add one or more medicine and quantity lines.") from error

    quantities: dict[str, int] = {}
    for line in iterator:
        try:
            code, quantity = line
        except (TypeError, ValueError) as error:
            raise PharmacyError("Each prescription line needs a medicine code and quantity.") from error
        code = normalize_code(code)
        quantity = require_positive_integer(quantity, "Line quantity")
        quantities[code] = require_positive_integer(
            quantities.get(code, 0) + quantity, f"Total quantity for {code}"
        )
    if not quantities:
        raise PharmacyError("Add at least one medicine to the prescription.")

    with closing(connect(db_path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("SELECT 1 FROM branches WHERE id = ?", (branch_id,)).fetchone() is None:
            raise PharmacyError("Select an existing branch.")
        for code in quantities:
            if connection.execute("SELECT 1 FROM medicines WHERE code = ?", (code,)).fetchone() is None:
                raise PharmacyError(f"Medicine {code} is not registered.")

        cursor = connection.execute(
            """INSERT INTO prescriptions (branch_id, patient_id, prescriber_code)
            VALUES (?, ?, ?)""",
                        (branch_id, patient_id, prescriber_code),
        )
        prescription_id = cursor.lastrowid
        connection.executemany(
            """INSERT INTO prescription_lines (prescription_id, medicine_code, quantity)
               VALUES (?, ?, ?)""",
            ((prescription_id, code, quantity) for code, quantity in quantities.items()),
        )
    return prescription_id


def dispense_prescription(prescription_id: int, *, db_path: str | Path = DB_PATH) -> None:
    """Deduct every line and change status in one transaction, or roll back all."""
    prescription_id = require_positive_integer(prescription_id, "Prescription ID")
    with closing(connect(db_path)) as connection, connection:
        # Acquire SQLite's write reservation before reading the current status.
        connection.execute("BEGIN IMMEDIATE")
        prescription = connection.execute(
            "SELECT branch_id, prescriber_code, status FROM prescriptions WHERE id = ?",
            (prescription_id,),
        ).fetchone()
        if prescription is None:
            raise PharmacyError(f"Prescription {prescription_id} does not exist.")
        if prescription["status"] == "Dispensed":
            raise PharmacyError(f"Prescription {prescription_id} was already dispensed.")
        if prescription["status"] == "Cancelled":
            raise PharmacyError(f"Prescription {prescription_id} is cancelled and cannot be dispensed.")

        lines = connection.execute(
            """SELECT m.code, m.name, m.unit_price_minor, m.reorder_level,
                      m.medicine_type, l.quantity
               FROM prescription_lines AS l
               JOIN medicines AS m ON m.code = l.medicine_code
               WHERE l.prescription_id = ? ORDER BY m.code""",
            (prescription_id,),
        ).fetchall()
        if not lines:
            raise PharmacyError("The prescription has no medicine lines.")

        # The same call dispatches to the ordinary or controlled implementation.
        medicines = [medicine_from_row(line) for line in lines]
        if any(medicine.requires_authorized_prescriber() for medicine in medicines):
            approved = connection.execute(
                "SELECT 1 FROM prescribers WHERE code = ?", (prescription["prescriber_code"],)
            ).fetchone()
            if approved is None:
                raise PharmacyError("Controlled medicines require a prescriber code on the allow-list.")
            
            branch_id = prescription["branch_id"]
        for line in lines:
            code = line["code"]
            quantity = line["quantity"]
            result = connection.execute(
                """UPDATE stock SET quantity = quantity - ?
                   WHERE branch_id = ? AND medicine_code = ? AND quantity >= ?""",
                (quantity, branch_id, code, quantity),
            )
            if result.rowcount == 0:
                stock = connection.execute(
                    "SELECT quantity FROM stock WHERE branch_id = ? AND medicine_code = ?",
                    (branch_id, code),
                ).fetchone()
                available = stock["quantity"] if stock else 0
                # Let this escape the connection context to roll back earlier lines.
                raise PharmacyError(
                    f"Insufficient stock for {code} at this branch. "
                    f"Need {quantity}, available {available}."
                )

        connection.execute(
            "UPDATE prescriptions SET status = 'Dispensed' WHERE id = ?", (prescription_id,)
        )
