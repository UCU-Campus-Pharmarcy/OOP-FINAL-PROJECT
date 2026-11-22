"""Read the quantities that have reached a branch's reorder level."""

from contextlib import closing
from dataclasses import dataclass

from db import DB_PATH, PharmacyError, connect


@dataclass(frozen=True)
class LowStockItem:
    medicine_code: str
    name: str
    quantity: int
    reorder_level: int


def list_low_stock(branch_id: int, *, db_path=DB_PATH) -> list[LowStockItem]:
    """Return tracked medicines with on-hand quantity at or below their reorder level."""
    if type(branch_id) is not int or not 0 < branch_id <= (1 << 63) - 1:
        raise PharmacyError("Choose a valid branch.")

    with closing(connect(db_path)) as connection:
        if connection.execute("SELECT 1 FROM branches WHERE id = ?", (branch_id,)).fetchone() is None:
            raise PharmacyError("The selected branch does not exist.")
        rows = connection.execute(
            """SELECT s.medicine_code, m.name, s.quantity, m.reorder_level
               FROM stock AS s
               JOIN medicines AS m ON m.code = s.medicine_code
               WHERE s.branch_id = ? AND s.quantity <= m.reorder_level
               ORDER BY s.medicine_code""",
            (branch_id,),
        ).fetchall()
    return [LowStockItem(**row) for row in rows]
