"""Prescription behavior checked through public services and a temporary DB."""

from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
import unittest

from db import MAX_SQLITE_INTEGER, PharmacyError, connect, initialize_database
from prescriptions import (
    cancel_prescription,
    create_prescription,
    dispense_prescription,
    list_prescribers,
    list_prescription_lines,
    list_prescriptions,
)
from stock import list_branches, list_stock, receive_stock


class PrescriptionTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.path = Path(directory) / "prescriptions.db"
        initialize_database(self.path, seed=True)
        branches = {branch.name: branch.id for branch in list_branches(db_path=self.path)}
        self.cedar = branches["Cedar Campus"]
        self.lake = branches["Lake Campus"]

    def create(self, lines, prescriber_code=None):
        return create_prescription(
            self.cedar, "PAT-TEST-001", lines,
            prescriber_code=prescriber_code, db_path=self.path,
        )

    def quantities(self, branch):
        return {item.medicine_code: item.quantity for item in list_stock(branch, db_path=self.path)}

    def status(self, prescription_id):
        return next(
            record.status for record in list_prescriptions(db_path=self.path)
            if record.id == prescription_id
        )

    def test_multi_line_dispense_changes_selected_branch_and_status(self):
        prescription_id = self.create([("MED001", 2), ("MED002", 3)], " dr001 ")
        dispense_prescription(prescription_id, db_path=self.path)
        self.assertEqual(self.quantities(self.cedar), {"MED001": 22, "MED002": 9})
        self.assertEqual(self.quantities(self.lake), {"MED001": 3, "MED002": 8})
        self.assertEqual(self.status(prescription_id), "Dispensed")
        record = list_prescriptions(db_path=self.path)[0]
        self.assertEqual((record.patient_id, record.prescriber_code), ("PAT-TEST-001", "DR001"))

    def test_second_line_failure_rolls_back_and_retry_can_succeed(self):
        prescription_id = self.create([("MED001", 2), ("MED002", 13)], "DR001")
        with self.assertRaisesRegex(PharmacyError, "Insufficient stock for MED002"):
            dispense_prescription(prescription_id, db_path=self.path)
        self.assertEqual(self.quantities(self.cedar), {"MED001": 24, "MED002": 12})
        self.assertEqual(self.quantities(self.lake), {"MED001": 3, "MED002": 8})
        self.assertEqual(self.status(prescription_id), "Pending")
        receive_stock(self.cedar, "MED002", 1, db_path=self.path)
        dispense_prescription(prescription_id, db_path=self.path)
        self.assertEqual(self.quantities(self.cedar), {"MED001": 22, "MED002": 0})
        self.assertEqual(self.status(prescription_id), "Dispensed")

    def test_duplicate_codes_are_aggregated_before_saving(self):
        prescription_id = self.create([("MED001", 2), (" med001 ", 3)])
        lines = list_prescription_lines(prescription_id, db_path=self.path)
        self.assertEqual([(line.medicine_code, line.quantity) for line in lines], [("MED001", 5)])
        dispense_prescription(prescription_id, db_path=self.path)
        self.assertEqual(self.quantities(self.cedar)["MED001"], 19)
