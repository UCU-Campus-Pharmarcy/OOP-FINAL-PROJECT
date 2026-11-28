# OOP-FINAL-PROJECT
# CSC2105 Campus Pharmacy System

## Shared project setup

This folder contains the complete Python application, SQLite schema, five member handoffs, and executable tests. Start with the commands below, then read your member's handoff and the shared integration contract before modifying a public interface.

```text
Campus Pharmacy System/
├── README.md
├── db.py                       Member 2
├── schema.sql                  Member 2
├── stock.py                    Member 2
├── medicines.py                Member 1
├── prescriptions.py            Member 3
├── gui.py                      Member 4
├── low_stock.py                Member 5
├── low_stock_view.py           Member 5
├── tests/
│   ├── test_database.py        Member 2
│   ├── test_medicines.py       Member 1
│   ├── test_prescriptions.py   Member 3
│   ├── test_gui.py             Member 4
│   └── test_low_stock.py       Member 5
├── handoffs/
│   ├── member-1.md
│   ├── member-2.md
│   ├── member-3.md
│   ├── member-4.md
│   └── member-5.md
└── docs/
    ├── INTEGRATION.md
    ├── DESIGN.md
    ├── REPORT_OUTLINE.md
    └── VERIFICATION.md
```

### File ownership and integration

| Member | Main responsibility and files | Public interface and callers |
| --- | --- | --- |
| 1 | Design and registration in `medicines.py`, `docs/DESIGN.md`, and catalogue tests | Medicine subclasses and `register_medicine`, `get_medicine`, `list_medicines`, `medicine_from_row`. Member 4 calls catalogue services. Member 3 reconstructs subclasses and calls their authorization policy. |
| 2 | SQLite, branches, and stock in `db.py`, `schema.sql`, `stock.py`, and database tests | Shared connection, setup, validation, and `PharmacyError`. `create_branch`, `list_branches`, `receive_stock`, and `list_stock` support Members 4 and 5. All services use the shared connection helper. |
| 3 | Prescriptions in `prescriptions.py` and its tests | Create, dispense, cancel, and list prescriptions, lines, and prescribers. Member 4 calls these services. Dispensing uses Member 1's policy and Member 2's schema. |
| 4 | Desktop application in `gui.py` and GUI tests | `PharmacyApp(db_path=...)` builds the app. `main()` is its command-line entry. The app calls services and embeds Member 5's report frame. |
| 5 | Reports and final evidence in `low_stock.py`, `low_stock_view.py`, report tests, README, and report outline | `list_low_stock(branch_id, *, db_path=...)` returns report records. `LowStockView(parent, *, db_path=...)` and `refresh()` are used by Member 4. Coordinate the complete test run and actual group evidence. |

[INTEGRATION.md](docs/INTEGRATION.md) defines the complete signatures, record fields, schema, return values, error conventions, and scope choices. [DESIGN.md](docs/DESIGN.md) contains the requirements, UML, workflow, and traceability.

## Run the application

Extract the ZIP, open PowerShell in this folder, and run the following commands. Python 3.11 or newer with Tkinter is required.

```powershell
python --version
python db.py --seed
python gui.py
```

The first command checks your Python version. `db.py --seed` creates `pharmacy.db` and inserts fictional samples. `gui.py` opens the desktop app using that same file. Changes survive closing and reopening the app. Repeating initialization or seeding preserves current stock balances.

For an independent demo file, pass the same path to both commands.

```powershell
python db.py --db demo.db --seed
python gui.py --db demo.db
```

All paths are relative to the folder where you run the command, except the default `pharmacy.db`, which is always beside `db.py`. Keep `schema.sql` beside `db.py`. The new project starts with a fresh schema. Existing databases from another version require a reviewed migration or a separate demo filename.

### Dependencies

The runtime and tests use Python's standard library, including `sqlite3`, `tkinter`, `decimal`, `dataclasses`, `argparse`, and `unittest`. No pip packages are required. If your Python installation lacks Tkinter, install your Python distribution's Tk support. `python -m tkinter` opens a small installation-check window.

## Run all tests

```powershell
python -m unittest discover -s tests -v
```

Each test creates a temporary database. GUI tests exercise real Tkinter widgets and callbacks with message boxes mocked. On a machine without a graphical display, those tests report a skip. The service and database tests still run. [VERIFICATION.md](docs/VERIFICATION.md) records the checks actually performed on this delivered package.

## Five member handoffs

Each handoff links to the full source files owned by that member. It also explains dependencies, how the code works, a demo with expected results, suggested commits, a task-log template, and two oral defence questions. Keep the shared folder structure when combining the files.

1. [Member 1 — Design and medicine registration](handoffs/member-1.md)
2. [Member 2 — SQLite and branch stock](handoffs/member-2.md)
3. [Member 3 — Prescriptions and dispensing](handoffs/member-3.md)
4. [Member 4 — Tkinter desktop app](handoffs/member-4.md)
5. [Member 5 — Low stock, tests, and report](handoffs/member-5.md)

## Fictional sample data

| Branch | Medicine | Quantity | Reorder level |
| --- | --- | --- | --- |
| Cedar Campus | MED001 — Demo Relief, Ordinary | 24 | 5 |
| Cedar Campus | MED002 — Demo Control, Controlled | 12 | 3 |
| Lake Campus | MED001 — Demo Relief, Ordinary | 3 | 5 |
| Lake Campus | MED002 — Demo Control, Controlled | 8 | 3 |

`DR001` is the simulated approved prescriber. Use invented patient IDs such as `PAT-DEMO-001`. Controlled or mixed prescriptions need a code currently on the allow-list when dispensing. Ordinary prescriptions can be dispensed without one. Repeated medicine lines are combined by normalized code before saving. The prescribed branch supplies every line.

Low stock means a tracked branch item whose quantity is at or below its medicine's reorder level. A row at zero is included. A missing stock row represents an item that branch does not track. Prices use exact two-decimal minor units without assuming a currency. The application includes cancellation of pending prescriptions as an optional extension from the brief. Advanced transfers and an allow-list editor are outside this implementation's scope.

## Suggested merge order

Agree on `docs/INTEGRATION.md`. Merge Member 2's schema and helpers first, Member 1's model second, and Member 3's prescriptions third. Merge Member 5's report service and frame before Member 4's GUI. The completed files in this package already use those interfaces. Individual tests can develop in parallel. Run the full suite after combining changes. Each group member should record their actual work, commits, tests, and demo evidence.

## End-to-end smoke test

Use a fresh demo filename so the initial quantities are reproducible. The following are **expected results** for a group demonstration. Record your own observations in the report.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | Create `Workshop Demo` on Branches. Register `DEMO-A`, Ordinary, price `12.50`, reorder 3, and `DEMO-B`, Controlled, price `25.00`, reorder 1. | The new branch and medicines appear in selection lists. |
| 2 | Receive 5 of A and 2 of B at Workshop Demo. | The stock table shows A=5 and B=2. |
| 3 | Create a prescription for `PAT-DEMO-001`, Workshop Demo, code `DR001`, with A=2 and B=2. Dispense it. | Status becomes `Dispensed`. A=3 and B=0. |
| 4 | Open Low stock and choose Workshop Demo. | A appears at its threshold and B appears at zero. Selecting a different branch shows that branch's report. |
| 5 | Try to dispense the same prescription again. | A clear error appears and stock stays A=3, B=0. |
| 6 | Close and reopen the app on that same database. | The stock and dispensed status persist. |

Also demonstrate three rejection paths. A zero unit price fails registration. A controlled prescription with an unknown prescriber code remains pending when dispensing fails. A multi-line prescription whose second line exceeds stock leaves both quantities and the pending status intact. The tests include these cases.

## Report and contribution evidence

[REPORT_OUTLINE.md](docs/REPORT_OUTLINE.md) provides the final report structure and places for actual results and evidence. The brief requires Trebuchet MS, 12 pt, 1.5 spacing, justified body text, and IEEE referencing in the submitted report. Its milestone dates are published on Moodle.

This package's implementation, tests, and explanatory material were generated with AI assistance. Record that assistance accurately in the group's declaration, identify any later AI-assisted changes, and cite reused code sources in the report. Each member should understand, review, modify as needed, and defend the files assigned to them.
