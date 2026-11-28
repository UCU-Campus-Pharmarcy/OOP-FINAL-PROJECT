# Member 2 | SQLite and branch stock

Your complete source files are [db.py](../db.py), [schema.sql](../schema.sql), [stock.py](../stock.py), and [tests/test_database.py](../tests/test_database.py). Read the [shared interface](../docs/INTEGRATION.md) before merging changes. The other members call these modules to get database connections and branch IDs. Build or merge these files first.

The schema keeps a separate stock row for each branch and medicine. Its composite primary key prevents duplicate rows for that pair. SQLite independently enforces foreign keys, positive prices, whole nonnegative stock counts, and prescription status values. The service validation gives the user readable errors before a write reaches those constraints.

Every connection enables foreign keys. A connection context commits on success and rolls back on an exception, while `closing` releases the connection. Stock receipt uses `BEGIN IMMEDIATE` to reserve the writer while it verifies the branch and medicine, adds quantity, and reads the new total. The guarded update prevents an integer overflow from turning the total into a floating-point value.

The initializer reads `schema.sql` beside `db.py`. Keep both files together when sharing your work. Seed inserts use stable keys and preserve existing rows and balances. Repeated setup creates missing tables, while changed table definitions need a separately planned migration or a fresh demo file.

## Run and demo

Run these commands from the extracted application folder.

```powershell
python db.py --db member2-demo.db --seed
python -m unittest discover -s tests -p test_database.py -v
python gui.py --db member2-demo.db
```

In the Receive stock tab, choose Lake Campus and MED001. Receive 2 units. **Expected** total is 5. Cedar Campus still has 24. Close the application, run the seed command again, and reopen it. **Expected** Lake still has 5 and Cedar still has 24. Try a receipt of zero. **Expected** a clear error and unchanged balances. Choose a new demo filename for a fresh run.

## Suggested commits

- Add SQLite entities, connection helpers, and fictional seed data.
- Add branch creation and guarded branch stock receipts.
- Verify repeated initialization, stock isolation, and database constraints.

## Task log template

| Date | My change | Check and actual outcome | Commit or evidence |
| --- | --- | --- | --- |
| [date] | [specific file and change] | [command or inputs, then observed result] | [actual hash or screenshot] |

## Oral defence

1. Why does the stock key contain both branch ID and medicine code, and how does your receipt transaction use it?
2. Why does running the seed script twice preserve existing quantities, and what does `CREATE TABLE IF NOT EXISTS` do when a table already exists?
