# OOP-FINAL-PROJECT

## Run the application

Use Python 3.11 or later with tkinter installed. The application uses the Python standard library.

From the project folder, run the application.

```powershell
python gui.py
```

The application creates the SQLite database `pharmacy.db` when it starts.

Use the Register Medicine, Branches, Receive Stock, Create Prescription, and Dispense tabs to complete the pharmacy workflow. Use fictional patient IDs when creating prescriptions.

To load fictional sample data, run the following command before opening the application.

```powershell
python db.py --seed
```

The fictional sample prescriber code `DR001` authorizes controlled medicines. Ordinary medicines can be dispensed with a blank prescriber code.

Existing databases are upgraded when the application starts. Older prescription records without patient IDs receive fictional identifiers such as `FICTIONAL-LEGACY-1`.

## Run tests

The tests use temporary SQLite databases.

```powershell
python -m unittest discover -s tests -v
```

## Member 4 progress - Day 3, 19 November 2026

Connected the Register Medicine form to the existing medicine registration and SQLite modules.

- Enabled the Register button and read all five form values.
- Added clear error messages for missing code or name, invalid prices, and invalid reorder levels.
- Saved valid medicines to SQLite and displayed a success message.
- Verified duplicate-code rejection and persistence after restarting the application.
- Included the required supporting modules, corrected zero-price validation, and documented setup.

The task log records the implementation commit, checks performed, and Codex assistance with examples, debugging, verification, and Git. [View Member 4's task log](member4-task-log.md)

## Member 4 progress - Day 4, 20 November 2026

- Organized the application into Register Medicine, Branches, and Receive Stock tabs.
- Connected branch creation to the existing stock module and displayed duplicate-name errors.
- Loaded saved branches and medicines into dropdowns that refresh when switching tabs.
- Connected stock receipt to the selected branch's stored ID and displayed the updated quantity.
- Verified invalid-quantity rejection, separate stock balances per branch, and persistence after restarting.

The final database check showed 15 units at Day 4 clinic and 3 units at Day 4 satellite for DAY3-001. The task log records the implementation commit and Codex assistance. [View Member 4's task log](member4-task-log.md)

## Member 4 progress - Day 5, completed 22 November 2026

- Added fictional patient, branch, prescriber, and medicine fields with a list of draft prescription lines.
- Connected prescription saving to SQLite and displayed saved records with their patient, branch, and status.
- Connected the Dispense Selected button and verified successful dispensing and rejection of a second dispense through the app.
- Corrected supporting prescription rules for patient IDs, controlled-medicine authorization during dispensing, and cancelled status, including migration of existing databases.
- Passed 16 automated tests covering authorization, ordinary medicines, multi-line rollback, repeat dispensing, persistence, and migration. Additional callback checks used mocked widgets and temporary databases.

The task log records the code contribution, checks, and Codex assistance. [View Member 4's task log](member4-task-log.md)
