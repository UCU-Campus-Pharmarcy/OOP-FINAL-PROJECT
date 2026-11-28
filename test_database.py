"""Member 2: SQLite invariants, persistent state, receipts, and seed safety."""

from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from db import MAX_SQLITE_INTEGER, PharmacyError, connect, initialize_database
from stock import create_branch, list_branches, list_stock, receive_stock


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.path = Path(directory) / "test.db"
        initialize_database(self.path, seed=True)
        branches = {branch.name: branch.id for branch in list_branches(db_path=self.path)}
        self.cedar = branches["Cedar Campus"]
        self.lake = branches["Lake Campus"]

    def quantities(self, branch_id):
        return {item.medicine_code: item.quantity for item in list_stock(branch_id, db_path=self.path)}

    def test_receipts_are_branch_specific_and_survive_reopen(self):
        self.assertEqual(receive_stock(self.lake, " med001 ", 2, db_path=self.path), 5)
        self.assertEqual(self.quantities(self.cedar)["MED001"], 24)
        self.assertEqual(self.quantities(self.lake)["MED001"], 5)
        with closing(connect(self.path)) as connection:
            row = connection.execute(
                "SELECT quantity FROM stock WHERE branch_id = ? AND medicine_code = ?",
                (self.lake, "MED001"),
            ).fetchone()
        self.assertEqual(row["quantity"], 5)

    def test_reinitialization_and_seed_preserve_existing_balances(self):
        receive_stock(self.lake, "MED001", 2, db_path=self.path)
        initialize_database(self.path, seed=True)
        initialize_database(self.path)
        self.assertEqual(self.quantities(self.lake)["MED001"], 5)
        self.assertEqual(len(list_branches(db_path=self.path)), 2)
        with closing(connect(self.path)) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM medicines").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT count(*) FROM prescribers").fetchone()[0], 1)

    def test_branch_names_are_trimmed_unique_and_case_insensitive(self):
        branch = create_branch("  East Test  ", db_path=self.path)
        self.assertEqual(branch.name, "East Test")
        with self.assertRaises(PharmacyError):
            create_branch("east test", db_path=self.path)
        with self.assertRaises(PharmacyError):
            create_branch("   ", db_path=self.path)

    def test_receipt_rejects_invalid_amounts_without_changing_stock(self):
        for quantity in (0, -1, True, 1.5, "2", MAX_SQLITE_INTEGER + 1):
            with self.subTest(quantity=quantity), self.assertRaises(PharmacyError):
                receive_stock(self.lake, "MED001", quantity, db_path=self.path)
        self.assertEqual(self.quantities(self.lake)["MED001"], 3)

    def test_unknown_branch_and_medicine_have_no_side_effect(self):
        with self.assertRaises(PharmacyError):
            receive_stock(999, "MED001", 2, db_path=self.path)
        with self.assertRaises(PharmacyError):
            receive_stock(self.lake, "UNKNOWN", 2, db_path=self.path)
        with self.assertRaises(PharmacyError):
            list_stock(999, db_path=self.path)
        self.assertEqual(self.quantities(self.lake), {"MED001": 3, "MED002": 8})

    def test_stock_total_limit_is_exact_and_overflow_is_atomic(self):
        branch = create_branch("Integer Boundary", db_path=self.path)
        self.assertEqual(
            receive_stock(branch.id, "MED001", MAX_SQLITE_INTEGER, db_path=self.path),
            MAX_SQLITE_INTEGER,
        )
        with self.assertRaises(PharmacyError):
            receive_stock(branch.id, "MED001", 1, db_path=self.path)
        self.assertEqual(self.quantities(branch.id)["MED001"], MAX_SQLITE_INTEGER)

    def test_foreign_keys_are_enabled_for_each_connection(self):
        for _ in range(2):
            with closing(connect(self.path)) as connection, connection:
                self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO stock (branch_id, medicine_code, quantity) VALUES (?, ?, ?)",
                        (999, "MED001", 1),
                    )

    def test_sqlite_independently_rejects_invalid_medicine_values(self):
        bad_values = ((0, 1), (-1, 1), (1.5, 1), (100, -1), (100, 1.5))
        with closing(connect(self.path)) as connection, connection:
            for price, reorder in bad_values:
                with self.subTest(price=price, reorder=reorder), self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """INSERT INTO medicines
                           (code, name, unit_price_minor, reorder_level, medicine_type)
                           VALUES (?, ?, ?, ?, ?)""",
                        ("BAD", "Invalid Demo", price, reorder, "Ordinary"),
                    )

    def test_sqlite_rejects_negative_or_fractional_stock(self):
        with closing(connect(self.path)) as connection, connection:
            for quantity in (-1, 1.5):
                with self.subTest(quantity=quantity), self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "UPDATE stock SET quantity = ? WHERE branch_id = ? AND medicine_code = ?",
                        (quantity, self.lake, "MED001"),
                    )
        self.assertEqual(self.quantities(self.lake)["MED001"], 3)

    def test_sqlite_validates_patient_and_status_without_blanket_prescriber_fk(self):
        with closing(connect(self.path)) as connection, connection:
            for patient_id, status in ((" ", "Pending"), ("PAT-TEST", "Unknown")):
                with self.subTest(patient=patient_id, status=status), self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """INSERT INTO prescriptions (branch_id, patient_id, prescriber_code, status)
                           VALUES (?, ?, ?, ?)""",
                        (self.cedar, patient_id, None, status),
                    )
            connection.execute(
                """INSERT INTO prescriptions (branch_id, patient_id, prescriber_code, status)
                   VALUES (?, ?, ?, ?)""",
                (self.cedar, "PAT-FICTIONAL", "UNLISTED", "Cancelled"),
            )


if __name__ == "__main__":
    unittest.main()
