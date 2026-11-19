# OOP-FINAL-PROJECT

## Run medicine registration

Use Python 3.11 or later with tkinter installed. The application uses the Python standard library.

From the project folder, run the application.

```powershell
python gui.py
```

The application creates the SQLite database `pharmacy.db` when it starts.

To load fictional sample data, run the following command before opening the application.

```powershell
python db.py --seed
```

## Member 4 progress - Day 3, 19 November 2026

Connected the Register Medicine form to the existing medicine registration and SQLite modules.

- Enabled the Register button and read all five form values.
- Added clear error messages for missing code or name, invalid prices, and invalid reorder levels.
- Saved valid medicines to SQLite and displayed a success message.
- Verified duplicate-code rejection and persistence after restarting the application.
- Included the required supporting modules, corrected zero-price validation, and documented setup.

The task log records the implementation commit, checks performed, and Codex assistance with examples, debugging, verification, and Git. [View Member 4's task log](member4-task-log.md)
