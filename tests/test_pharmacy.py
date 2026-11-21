"""Service tests against an isolated SQLite file for each test case."""

import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from db import PharmacyError, connect, initialize_database
from low_stock import list_low_stock
from medicines import list_medicines, register_medicine
from prescriptions import create_prescription, dispense_prescription, list_prescriptions
from stock import create_branch, receive_stock


class PharmacyTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = self.enterContext(TemporaryDirectory())
        self.db_path = Path(temporary_directory) / "test-pharmacy.db"
        initialize_database(self.db_path)
        self.north = create_branch("Test North", db_path=self.db_path)
        self.south = create_branch("Test South", db_path=self.db_path)
        register_medicine("MED-A", "Sample A", "12.50", 3, "Ordinary", db_path=self.db_path)
        register_medicine("MED-B", "Sample B", "5", 2, "Controlled", db_path=self.db_path)
        with closing(connect(self.db_path)) as connection, connection:
            connection.execute("INSERT INTO prescribers (code, name) VALUES (?, ?)", ("DR001", "Test Prescriber"))

    def stock_quantities(self, branch_id):
        with closing(connect(self.db_path)) as connection:
            rows = connection.execute(
                "SELECT medicine_code, quantity FROM stock WHERE branch_id = ?", (branch_id,)
            ).fetchall()
        return {row["medicine_code"]: row["quantity"] for row in rows}

    def prescription_status(self, prescription_id):
        return next(
            record.status for record in list_prescriptions(db_path=self.db_path)
            if record.id == prescription_id
        )

    def test_duplicate_medicine_code_leaves_original_record(self):
        with self.assertRaises(PharmacyError):
            register_medicine(" med-a ", "Duplicate", "3", 1, "Ordinary", db_path=self.db_path)
        medicine = list_medicines(db_path=self.db_path)[0]
        self.assertEqual((medicine.code, medicine.name, medicine.unit_price_minor), ("MED-A", "Sample A", 1250))

    def test_stock_receipts_are_positive_and_branch_specific(self):
        receive_stock(self.north.id, "MED-A", 5, db_path=self.db_path)
        receive_stock(self.south.id, "MED-A", 2, db_path=self.db_path)
        self.assertEqual(receive_stock(self.north.id, " med-a ", 3, db_path=self.db_path), 8)
        with self.assertRaises(PharmacyError):
            receive_stock(self.north.id, "MED-A", 0, db_path=self.db_path)
        self.assertEqual(self.stock_quantities(self.north.id), {"MED-A": 8})
        self.assertEqual(self.stock_quantities(self.south.id), {"MED-A": 2})

    def test_ordinary_prescriptions_allow_blank_and_unapproved_prescribers(self):
        receive_stock(self.north.id, "MED-A", 5, db_path=self.db_path)
        for code in ("", "UNKNOWN"):
            with self.subTest(prescriber=code):
                prescription_id = create_prescription(
                    self.north.id, code, [("MED-A", 1)], db_path=self.db_path
                )
                dispense_prescription(prescription_id, db_path=self.db_path)
                self.assertEqual(self.prescription_status(prescription_id), "Dispensed")
        self.assertEqual(self.stock_quantities(self.north.id), {"MED-A": 3})

    def test_patient_identifier_is_required_when_supplied_and_survives_reconnect(self):
        prescription_id = create_prescription(
            self.north.id, "", [("MED-A", 1)], db_path=self.db_path,
            patient_id=" FICTIONAL-PATIENT-01 ",
        )
        for invalid_id in ("", "   ", None, 42):
            with self.subTest(patient_id=invalid_id), self.assertRaises(PharmacyError):
                create_prescription(
                    self.north.id, "", [("MED-A", 1)], db_path=self.db_path,
                    patient_id=invalid_id,
                )
        records = list_prescriptions(db_path=self.db_path)
        self.assertEqual(len(records), 1)
        self.assertEqual((records[0].id, records[0].patient_id),
                         (prescription_id, "FICTIONAL-PATIENT-01"))

    def test_legacy_callers_use_documented_fictional_patient_identifier(self):
        prescription_id = create_prescription(
            self.north.id, "", [("MED-A", 1)], db_path=self.db_path
        )
        record = list_prescriptions(db_path=self.db_path)[0]
        self.assertEqual((record.id, record.patient_id), (prescription_id, "FICTIONAL-LEGACY"))

    def test_controlled_prescriptions_check_allow_list_at_dispense(self):
        receive_stock(self.north.id, "MED-A", 9, db_path=self.db_path)
        receive_stock(self.north.id, "MED-B", 5, db_path=self.db_path)
        for code in ("", "UNKNOWN"):
            with self.subTest(prescriber=code):
                prescription_id = create_prescription(
                    self.north.id, code, [("MED-A", 2), ("MED-B", 1)], db_path=self.db_path,
                    patient_id="FICTIONAL-PATIENT-02",
                )
                with self.assertRaisesRegex(PharmacyError, "allow-list"):
                    dispense_prescription(prescription_id, db_path=self.db_path)
                self.assertEqual(self.stock_quantities(self.north.id), {"MED-A": 9, "MED-B": 5})
                self.assertEqual(self.prescription_status(prescription_id), "Pending")

    def test_removed_prescriber_cannot_authorize_a_pending_controlled_prescription(self):
        receive_stock(self.north.id, "MED-A", 9, db_path=self.db_path)
        receive_stock(self.north.id, "MED-B", 5, db_path=self.db_path)
        prescription_id = create_prescription(
            self.north.id, "DR001", [("MED-A", 2), ("MED-B", 1)], db_path=self.db_path
        )
        with closing(connect(self.db_path)) as connection, connection:
            connection.execute("DELETE FROM prescribers WHERE code = ?", ("DR001",))
        with self.assertRaisesRegex(PharmacyError, "allow-list"):
            dispense_prescription(prescription_id, db_path=self.db_path)
        self.assertEqual(self.stock_quantities(self.north.id), {"MED-A": 9, "MED-B": 5})
        self.assertEqual(self.prescription_status(prescription_id), "Pending")

    def test_cancelled_prescription_cannot_be_dispensed(self):
        receive_stock(self.north.id, "MED-A", 5, db_path=self.db_path)
        prescription_id = create_prescription(
            self.north.id, "", [("MED-A", 2)], db_path=self.db_path
        )
        with closing(connect(self.db_path)) as connection, connection:
            connection.execute(
                "UPDATE prescriptions SET status = 'Cancelled' WHERE id = ?", (prescription_id,)
            )
        with self.assertRaisesRegex(PharmacyError, "cancelled"):
            dispense_prescription(prescription_id, db_path=self.db_path)
        self.assertEqual(self.stock_quantities(self.north.id), {"MED-A": 5})
        self.assertEqual(self.prescription_status(prescription_id), "Cancelled")

    def test_seed_initialization_preserves_user_data_and_is_idempotent(self):
        receive_stock(self.north.id, "MED-A", 9, db_path=self.db_path)
        create_prescription(
            self.north.id, "", [("MED-A", 2)], db_path=self.db_path,
            patient_id="FICTIONAL-PATIENT-03",
        )
        initialize_database(self.db_path, seed=True)
        medicines = list_medicines(db_path=self.db_path)
        prescriptions = list_prescriptions(db_path=self.db_path)
        with closing(connect(self.db_path)) as connection:
            quantities = [tuple(row) for row in connection.execute(
                "SELECT branch_id, medicine_code, quantity FROM stock ORDER BY branch_id, medicine_code"
            )]
        initialize_database(self.db_path, seed=True)
        initialize_database(self.db_path, seed=True)
        self.assertEqual(list_medicines(db_path=self.db_path), medicines)
        self.assertEqual(list_prescriptions(db_path=self.db_path), prescriptions)
        with closing(connect(self.db_path)) as connection:
            self.assertEqual([tuple(row) for row in connection.execute(
                "SELECT branch_id, medicine_code, quantity FROM stock ORDER BY branch_id, medicine_code"
            )], quantities)

    def test_successful_dispense_aggregates_duplicate_lines_and_updates_selected_branch(self):
        receive_stock(self.north.id, "MED-A", 9, db_path=self.db_path)
        receive_stock(self.north.id, "MED-B", 5, db_path=self.db_path)
        receive_stock(self.south.id, "MED-A", 3, db_path=self.db_path)
        prescription_id = create_prescription(
            self.north.id, " dr001 ", [("MED-A", 2), ("med-a", 1), ("MED-B", 2)], db_path=self.db_path
        )

        dispense_prescription(prescription_id, db_path=self.db_path)

        self.assertEqual(self.stock_quantities(self.north.id), {"MED-A": 6, "MED-B": 3})
        self.assertEqual(self.stock_quantities(self.south.id), {"MED-A": 3})
        self.assertEqual(self.prescription_status(prescription_id), "Dispensed")

    def test_insufficient_second_line_preserves_both_quantities_and_status(self):
        receive_stock(self.north.id, "MED-A", 8, db_path=self.db_path)
        receive_stock(self.north.id, "MED-B", 1, db_path=self.db_path)
        receive_stock(self.south.id, "MED-B", 10, db_path=self.db_path)
        prescription_id = create_prescription(
            self.north.id, "DR001", [("MED-A", 3), ("MED-B", 2)], db_path=self.db_path
        )

        with self.assertRaises(PharmacyError):
            dispense_prescription(prescription_id, db_path=self.db_path)

        self.assertEqual(self.stock_quantities(self.north.id), {"MED-A": 8, "MED-B": 1})
        self.assertEqual(self.stock_quantities(self.south.id), {"MED-B": 10})
        self.assertEqual(self.prescription_status(prescription_id), "Pending")

        receive_stock(self.north.id, "MED-B", 1, db_path=self.db_path)
        dispense_prescription(prescription_id, db_path=self.db_path)
        self.assertEqual(self.stock_quantities(self.north.id), {"MED-A": 5, "MED-B": 0})

    def test_repeat_dispense_leaves_stock_unchanged(self):
        receive_stock(self.north.id, "MED-A", 7, db_path=self.db_path)
        prescription_id = create_prescription(self.north.id, "DR001", [("MED-A", 2)], db_path=self.db_path)
        dispense_prescription(prescription_id, db_path=self.db_path)

        with self.assertRaises(PharmacyError):
            dispense_prescription(prescription_id, db_path=self.db_path)

        self.assertEqual(self.stock_quantities(self.north.id), {"MED-A": 5})
        self.assertEqual(self.prescription_status(prescription_id), "Dispensed")

    def test_low_stock_includes_threshold_and_zero_for_tracked_medicines(self):
        receive_stock(self.north.id, "MED-A", 4, db_path=self.db_path)
        receive_stock(self.south.id, "MED-A", 3, db_path=self.db_path)
        receive_stock(self.south.id, "MED-B", 1, db_path=self.db_path)
        prescription_id = create_prescription(self.south.id, "DR001", [("MED-B", 1)], db_path=self.db_path)
        dispense_prescription(prescription_id, db_path=self.db_path)

        self.assertEqual(list_low_stock(self.north.id, db_path=self.db_path), [])
        items = list_low_stock(self.south.id, db_path=self.db_path)
        self.assertEqual([(item.medicine_code, item.quantity, item.reorder_level) for item in items],
                         [("MED-A", 3, 3), ("MED-B", 0, 2)])


class PrescriptionMigrationTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = self.enterContext(TemporaryDirectory())
        self.db_path = Path(temporary_directory) / "legacy-pharmacy.db"
        initialize_database(self.db_path)
        with closing(connect(self.db_path)) as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            with connection:
                connection.execute("DROP TABLE prescriptions")
                connection.execute(
                    """CREATE TABLE prescriptions (
                        id INTEGER PRIMARY KEY,
                        branch_id INTEGER NOT NULL REFERENCES branches(id),
                        prescriber_code TEXT NOT NULL REFERENCES prescribers(code),
                        status TEXT NOT NULL DEFAULT 'Pending'
                            CHECK (status IN ('Pending', 'Dispensed'))
                    )"""
                )
                connection.executemany(
                    "INSERT INTO branches (id, name) VALUES (?, ?)",
                    [(7, "Legacy North"), (9, "Legacy South")],
                )
                connection.executemany(
                    """INSERT INTO medicines
                       (code, name, unit_price_minor, reorder_level, medicine_type)
                       VALUES (?, ?, ?, ?, ?)""",
                    [("MED-A", "Legacy A", 1250, 3, "Ordinary"),
                     ("MED-B", "Legacy B", 500, 2, "Controlled")],
                )
                connection.executemany(
                    "INSERT INTO stock (branch_id, medicine_code, quantity) VALUES (?, ?, ?)",
                    [(7, "MED-A", 9), (7, "MED-B", 5), (9, "MED-A", 3)],
                )
                connection.execute(
                    "INSERT INTO prescribers (code, name) VALUES (?, ?)",
                    ("DR001", "Fictional Legacy Prescriber"),
                )
                connection.executemany(
                    "INSERT INTO prescriptions (id, branch_id, prescriber_code, status) VALUES (?, ?, ?, ?)",
                    [(41, 7, "DR001", "Pending"), (42, 9, "DR001", "Dispensed")],
                )
                connection.executemany(
                    "INSERT INTO prescription_lines (prescription_id, medicine_code, quantity) VALUES (?, ?, ?)",
                    [(41, "MED-A", 2), (41, "MED-B", 1), (42, "MED-A", 1)],
                )
        self.original_rows = self.database_rows()

    def database_rows(self):
        tables = ("medicines", "branches", "stock", "prescribers", "prescriptions", "prescription_lines")
        with closing(connect(self.db_path)) as connection:
            return {
                table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")]
                for table in tables
            }

    def test_migration_preserves_ids_lines_statuses_and_other_records(self):
        initialize_database(self.db_path)
        upgraded_rows = self.database_rows()
        for table in self.original_rows:
            if table != "prescriptions":
                self.assertEqual(upgraded_rows[table], self.original_rows[table], table)
        records = list_prescriptions(db_path=self.db_path)
        self.assertEqual(
            [(record.id, record.branch_id, record.prescriber_code, record.status, record.patient_id)
             for record in records],
            [(42, 9, "DR001", "Dispensed", "FICTIONAL-LEGACY-42"),
             (41, 7, "DR001", "Pending", "FICTIONAL-LEGACY-41")],
        )
        with closing(connect(self.db_path)) as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            foreign_keys = connection.execute("PRAGMA foreign_key_list(prescriptions)").fetchall()
        self.assertEqual([row["from"] for row in foreign_keys], ["branch_id"])

    def test_migrated_database_is_reusable_and_seed_initialization_is_idempotent(self):
        initialize_database(self.db_path, seed=True)
        upgraded_rows = self.database_rows()
        initialize_database(self.db_path, seed=True)
        initialize_database(self.db_path, seed=True)
        self.assertEqual(self.database_rows(), upgraded_rows)
        dispense_prescription(41, db_path=self.db_path)
        with closing(connect(self.db_path)) as connection:
            rows = connection.execute(
                "SELECT medicine_code, quantity FROM stock WHERE branch_id = 7 ORDER BY medicine_code"
            ).fetchall()
        self.assertEqual([tuple(row) for row in rows], [("MED-A", 7), ("MED-B", 4)])
        prescription_id = create_prescription(
            7, "", [("MED-A", 1)], db_path=self.db_path, patient_id="FICTIONAL-NEW"
        )
        self.assertEqual(prescription_id, 43)
        with closing(connect(self.db_path)) as connection, connection:
            connection.execute("UPDATE prescriptions SET status = 'Cancelled' WHERE id = ?", (prescription_id,))
        with self.assertRaisesRegex(PharmacyError, "cancelled"):
            dispense_prescription(prescription_id, db_path=self.db_path)

    def test_failed_initialization_rolls_back_legacy_schema_and_all_data(self):
        with closing(connect(self.db_path)) as connection:
            original_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE name = 'prescriptions'"
            ).fetchone()[0]
        with patch("db._seed_database", side_effect=RuntimeError("Simulated seed failure")):
            with self.assertRaisesRegex(RuntimeError, "Simulated seed failure"):
                initialize_database(self.db_path, seed=True)
        self.assertEqual(self.database_rows(), self.original_rows)
        with closing(connect(self.db_path)) as connection:
            self.assertEqual(connection.execute(
                "SELECT sql FROM sqlite_master WHERE name = 'prescriptions'"
            ).fetchone()[0], original_schema)
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        initialize_database(self.db_path)
        self.assertEqual(len(list_prescriptions(db_path=self.db_path)), 2)


if __name__ == "__main__":
    unittest.main()
