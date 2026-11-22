from collections.abc import Iterable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from db import DB_PATH, MAX_SQLITE_INTEGER, PharmacyError, connect


LEGACY_PATIENT_ID = "FICTIONAL-LEGACY"


@dataclass(frozen=True)
class Prescriber:
    code: str
    name: str


@dataclass(frozen=True)
class Prescription:
    id: int
    branch_id: int
    prescriber_code: str
    status: str
    patient_id: str = LEGACY_PATIENT_ID


def _positive_integer(value: int, label: str) -> None:
    if type(value) is not int or not 1 <= value <= MAX_SQLITE_INTEGER:
        raise PharmacyError(f"{label} must be a positive whole number supported by SQLite.")


def create_prescription(
    branch_id: int,
    prescriber_code: str,
    lines: Iterable[tuple[str, int]],
    *,
    db_path: str | Path = DB_PATH,
    patient_id: str = LEGACY_PATIENT_ID,
) -> int:
    """Save a pending prescription with a fictional patient ID and return its ID.

    Older callers that omit patient_id use FICTIONAL-LEGACY. New forms should
    supply the fictional identifier entered by the user.
    """
    _positive_integer(branch_id, "Branch ID")
    if not isinstance(patient_id, str) or not patient_id.strip():
        raise PharmacyError("Enter a fictional patient identifier.")
    patient_id = patient_id.strip()
    if not isinstance(prescriber_code, str):
        raise PharmacyError("Prescriber code must be text and may be blank for ordinary medicines.")
    prescriber_code = prescriber_code.strip().upper()

    quantities: dict[str, int] = {}
    for medicine_code, quantity in lines:
        if not isinstance(medicine_code, str) or not medicine_code.strip():
            raise PharmacyError("Each prescription line needs a medicine code.")
        medicine_code = medicine_code.strip().upper()
        _positive_integer(quantity, "Line quantity")
        total_quantity = quantities.get(medicine_code, 0) + quantity
        _positive_integer(total_quantity, f"Total quantity for {medicine_code}")
        quantities[medicine_code] = total_quantity
    if not quantities:
        raise PharmacyError("Add at least one medicine to the prescription.")

    with closing(connect(db_path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("SELECT 1 FROM branches WHERE id = ?", (branch_id,)).fetchone() is None:
            raise PharmacyError("Select an existing branch.")
        for medicine_code in quantities:
            medicine = connection.execute(
                "SELECT 1 FROM medicines WHERE code = ?", (medicine_code,)
            ).fetchone()
            if medicine is None:
                raise PharmacyError(f"Medicine {medicine_code} is not registered.")

        cursor = connection.execute(
            "INSERT INTO prescriptions (branch_id, prescriber_code, patient_id) VALUES (?, ?, ?)",
            (branch_id, prescriber_code, patient_id),
        )
        prescription_id = cursor.lastrowid
        connection.executemany(
            "INSERT INTO prescription_lines (prescription_id, medicine_code, quantity) VALUES (?, ?, ?)",
            ((prescription_id, code, quantity) for code, quantity in quantities.items()),
        )
    return prescription_id


def dispense_prescription(prescription_id: int, *, db_path: str | Path = DB_PATH) -> None:
    """Deduct all prescription quantities and mark it dispensed in one transaction."""
    _positive_integer(prescription_id, "Prescription ID")
    with closing(connect(db_path)) as connection, connection:
        # Reserve SQLite's writer before checking status or changing stock.
        connection.execute("BEGIN IMMEDIATE")
        prescription = connection.execute(
            "SELECT branch_id, prescriber_code, status FROM prescriptions WHERE id = ?",
            (prescription_id,),
        ).fetchone()
        if prescription is None:
            raise PharmacyError(f"Prescription {prescription_id} does not exist.")
        if prescription["status"] != "Pending":
            raise PharmacyError(
                f"Prescription {prescription_id} is {prescription['status'].lower()} "
                "and cannot be dispensed."
            )

        lines = connection.execute(
            """
            SELECT p.medicine_code, p.quantity, m.medicine_type
            FROM prescription_lines AS p
            JOIN medicines AS m ON m.code = p.medicine_code
            WHERE p.prescription_id = ?
            ORDER BY p.medicine_code
            """,
            (prescription_id,),
        ).fetchall()
        if not lines:
            raise PharmacyError(f"Prescription {prescription_id} has no medicine lines.")

        if any(line["medicine_type"] == "Controlled" for line in lines):
            approved_prescriber = connection.execute(
                "SELECT 1 FROM prescribers WHERE code = ?", (prescription["prescriber_code"],)
            ).fetchone()
            if approved_prescriber is None:
                raise PharmacyError(
                    "Controlled medicines require a prescriber on the simulated allow-list."
                )

        branch_id = prescription["branch_id"]
        for line in lines:
            code = line["medicine_code"]
            quantity = line["quantity"]
            result = connection.execute(
                """
                UPDATE stock SET quantity = quantity - ?
                WHERE branch_id = ? AND medicine_code = ? AND quantity >= ?
                """,
                (quantity, branch_id, code, quantity),
            )
            if result.rowcount == 0:
                stock = connection.execute(
                    "SELECT quantity FROM stock WHERE branch_id = ? AND medicine_code = ?",
                    (branch_id, code),
                ).fetchone()
                available = stock["quantity"] if stock else 0
                # This exception rolls back earlier lines through the connection context manager.
                raise PharmacyError(
                    f"Insufficient stock for {code} at this branch. "
                    f"Need {quantity}, available {available}."
                )

        connection.execute(
            "UPDATE prescriptions SET status = 'Dispensed' WHERE id = ?", (prescription_id,)
        )


def list_prescribers(*, db_path: str | Path = DB_PATH) -> list[Prescriber]:
    with closing(connect(db_path)) as connection:
        rows = connection.execute(
            "SELECT code, name FROM prescribers ORDER BY name COLLATE NOCASE, code"
        )
        return [Prescriber(code=row["code"], name=row["name"]) for row in rows]


def list_prescriptions(*, db_path: str | Path = DB_PATH) -> list[Prescription]:
    with closing(connect(db_path)) as connection:
        rows = connection.execute(
            """SELECT id, branch_id, prescriber_code, status, patient_id
               FROM prescriptions ORDER BY id DESC"""
        )
        return [
            Prescription(
                id=row["id"],
                branch_id=row["branch_id"],
                prescriber_code=row["prescriber_code"],
                status=row["status"],
                patient_id=row["patient_id"],
            )
            for row in rows
        ]
