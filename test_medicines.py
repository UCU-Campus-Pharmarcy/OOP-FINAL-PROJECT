"""Catalogue behavior, exact money, and reconstructed OOP policies."""

from dataclasses import FrozenInstanceError
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from db import MAX_SQLITE_INTEGER, PharmacyError, initialize_database
from medicines import (
    ControlledMedicine,
    Medicine,
    OrdinaryMedicine,
    get_medicine,
    list_medicines,
    register_medicine,
)


class MedicineTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.path = Path(directory) / "medicines.db"
        initialize_database(self.path)

    def test_register_normalizes_and_reloads_exact_price(self):
        medicine = register_medicine(" med-a ", " Demo Tablet ", "12.50", 0, "ordinary", db_path=self.path)
        self.assertEqual((medicine.code, medicine.name), ("MED-A", "Demo Tablet"))
        self.assertEqual(medicine.unit_price_minor, 1250)
        self.assertEqual(medicine.unit_price, Decimal("12.50"))
        self.assertEqual(get_medicine(" med-a ", db_path=self.path), medicine)
        self.assertIsInstance(medicine, OrdinaryMedicine)

    def test_duplicate_code_preserves_original(self):
        original = register_medicine("MED-A", "Original", "1", 3, "Ordinary", db_path=self.path)
        with self.assertRaisesRegex(PharmacyError, "already exists"):
            register_medicine(" med-a ", "Replacement", "2", 4, "Controlled", db_path=self.path)
        self.assertEqual(list_medicines(db_path=self.path), [original])

    def test_invalid_prices_save_no_records(self):
        for price in ("0", "0.00", "-1", "", "1.234", "NaN", "Infinity", "1e2", "1,000", "1.", ".50", 1, None):
            with self.subTest(price=price), self.assertRaises(PharmacyError):
                register_medicine("BAD", "Bad price", price, 0, "Ordinary", db_path=self.path)
        self.assertEqual(list_medicines(db_path=self.path), [])

    def test_price_database_limit_is_exact(self):
        medicine = register_medicine(
            "MAX", "Boundary", "92233720368547758.07", 0, "Ordinary", db_path=self.path
        )
        self.assertEqual(medicine.unit_price_minor, MAX_SQLITE_INTEGER)
        with self.assertRaises(PharmacyError):
            register_medicine("TOO-BIG", "Boundary", "92233720368547758.08", 0, "Ordinary", db_path=self.path)
        small = register_medicine("SMALL", "Minimum", "0.01", 0, "Ordinary", db_path=self.path)
        self.assertEqual(small.unit_price_minor, 1)

    def test_fields_and_reorder_level_are_validated(self):
        for code, name, level, kind in (
            ("", "Name", 0, "Ordinary"),
            ("CODE", " ", 0, "Ordinary"),
            ("CODE", "Name", -1, "Ordinary"),
            ("CODE", "Name", True, "Ordinary"),
            ("CODE", "Name", 1.5, "Ordinary"),
            ("CODE", "Name", "1", "Ordinary"),
            ("CODE", "Name", MAX_SQLITE_INTEGER + 1, "Ordinary"),
            ("CODE", "Name", 0, "Unknown"),
        ):
            with self.subTest(code=code, name=name, level=level, kind=kind), self.assertRaises(PharmacyError):
                register_medicine(code, name, "1", level, kind, db_path=self.path)
        self.assertEqual(list_medicines(db_path=self.path), [])

    def test_loaded_subclasses_have_distinct_polymorphic_policy(self):
        register_medicine("A", "Ordinary sample", "1", 0, "Ordinary", db_path=self.path)
        register_medicine("B", "Controlled sample", "2", 1, "Controlled", db_path=self.path)
        medicines = list_medicines(db_path=self.path)
        self.assertEqual([item.medicine_type for item in medicines], ["Ordinary", "Controlled"])
        self.assertEqual([item.requires_authorized_prescriber() for item in medicines], [False, True])
        self.assertIsInstance(medicines[1], ControlledMedicine)

    def test_constructor_enforces_invariants_and_objects_are_read_only(self):
        with self.assertRaises(TypeError):
            Medicine("A", "Base", 1, 0)
        for price, level in ((0, 0), (-1, 0), (True, 0), (1, -1), (1, True)):
            with self.subTest(price=price, level=level), self.assertRaises(PharmacyError):
                OrdinaryMedicine("A", "Demo", price, level)
        medicine = OrdinaryMedicine(" a ", " Demo ", 50, 0)
        self.assertEqual((medicine.code, medicine.name), ("A", "Demo"))
        with self.assertRaises(FrozenInstanceError):
            medicine.unit_price_minor = 0

    def test_unknown_medicine_has_clear_error(self):
        with self.assertRaisesRegex(PharmacyError, "not registered"):
            get_medicine("UNKNOWN", db_path=self.path)


if __name__ == "__main__":
    unittest.main()
