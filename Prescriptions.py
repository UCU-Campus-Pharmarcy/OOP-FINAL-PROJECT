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