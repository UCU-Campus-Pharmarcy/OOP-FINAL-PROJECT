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