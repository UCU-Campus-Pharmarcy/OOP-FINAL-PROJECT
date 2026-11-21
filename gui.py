import tkinter as tk
import sqlite3
draft_lines =[]
from prescriptions import create_prescription, list_prescriptions, dispense_prescription
from stock import create_branch, list_branches, receive_stock
from db import initialize_database
from medicines import register_medicine, list_medicines
from tkinter import messagebox, ttk
from decimal import Decimal, InvalidOperation
from low_stock_view import LowStockView


def handle_register():
    code = medicine_code_entry.get().strip()
    name = medicine_name_entry.get().strip()
    price = unit_price_entry.get().strip()
    reorder = reorder_level_entry.get().strip()
    category = medicine_type.get()

    if not code or not name:
        messagebox.showerror("Missing information", "Enter the medicine code and name.")
        return

    try:
        price_number = Decimal(price)
    except InvalidOperation:
        messagebox.showerror("Invalid price", "Unit price must be a number.")
        return

    if not price_number.is_finite() or price_number <= 0:
        messagebox.showerror("Invalid price", "Unit price must be greater than zero.")
        return

    if not reorder.isdecimal():
        messagebox.showerror(
            "Invalid reorder level",
            "Reorder level must be a whole number of zero or more."
        )
        return

    try:
        medicine = register_medicine(
            code=code,
            name=name,
            unit_price=price,
            reorder_level=int(reorder),
            medicine_type=category,
        )
    except ValueError as error:
        messagebox.showerror("Registration error", str(error))
        return
    except sqlite3.Error:
        messagebox.showerror(
            "Database error",
            "Could not save the medicine. Please try again."
        )
        return

    messagebox.showinfo(
        "Medicine saved",
        f"Medicine {medicine.code} was saved successfully."
    )
def handle_create_branch():
    try:
        branch = create_branch(branch_name_entry.get())
    except ValueError as error:
        messagebox.showerror("Branch error", str(error))
        return
    except sqlite3.Error:
        messagebox.showerror(
            "Database error",
            "Could not save the branch. Please try again."
        )
        return


    messagebox.showinfo(
        "Branch saved",
        f"Branch {branch.name} was saved successfully."
    )
def refresh_stock_choices(event=None):
    try:
        branches = list_branches()
        medicines = list_medicines()
    except sqlite3.Error:
        messagebox.showerror(
           "Database error",
           "Could not load branches and medicines."
        )
        return
    stock_branch_combo["values"] = [branch.name for branch in branches]
    stock_medicine_combo["values"] = [medicine.code for medicine in medicines]
    prescription_branch_combo["values"] = [branch.name for branch in branches]
    prescription_medicine_combo["values"] = [medicine.code for medicine in medicines]
def handle_receive_stock():
    branch_name = stock_branch_combo.get()
    medicine_code = stock_medicine_combo.get()
    quantity_text = stock_quantity_entry.get().strip()

    if not branch_name or not medicine_code:
        messagebox.showerror("Stock error", "Select a branch and medicine.")
        return

    try:
        quantity = int(quantity_text)
    except ValueError:
        messagebox.showerror(
            "Stock error",
            "Quantity must be a positive whole number."
        )
        return

    try:
        branch_ids = {
            branch.name: branch.id for branch in list_branches()
        }

        if branch_name not in branch_ids:
            messagebox.showerror("Stock error", "Select an existing branch.")
            return

        total = receive_stock(
            branch_ids[branch_name],
            medicine_code,
            quantity
        )
    except ValueError as error:
        messagebox.showerror("Stock error", str(error))
        return
    except sqlite3.Error:
        messagebox.showerror("Database error", "Could not receive stock.")
        return

    messagebox.showinfo(
        "Stock received",
        f"{medicine_code} at {branch_name}\nNew quantity: {total}"
    )
def handle_add_line():
    medicine_code = prescription_medicine_combo.get()

    if not medicine_code:
        messagebox.showerror("Prescription error", "Select a medicine.")
        return

    try:
        quantity = int(prescription_quantity_entry.get())
    except ValueError:
        messagebox.showerror("Prescription error", "Enter a whole-number quantity.")
        return

    if quantity <= 0:
        messagebox.showerror("Prescription error", "Quantity must be greater than zero.")
        return

    draft_lines.append((medicine_code, quantity))
    prescription_lines_list.insert(tk.END, f"{medicine_code} - {quantity}")
    prescription_quantity_entry.delete(0, tk.END)
def handle_save_prescription():
    patient_id = prescription_patient_entry.get().strip()
    branch_name = prescription_branch_combo.get()
    prescriber_code = prescription_prescriber_entry.get().strip()

    if not patient_id or not branch_name or not draft_lines:
        messagebox.showerror(
            "Prescription error",
            "Enter a fictional patient ID, select a branch, and add medicine lines."
        )
        return

    try:
        branch_ids = {
            branch.name: branch.id for branch in list_branches()
        }

        if branch_name not in branch_ids:
            messagebox.showerror("Prescription error", "Select an existing branch.")
            return

        prescription_id = create_prescription(
            branch_ids[branch_name],
            prescriber_code,
            list(draft_lines),
            patient_id=patient_id
        )
    except ValueError as error:
        messagebox.showerror("Prescription error", str(error))
        return
    except sqlite3.Error:
        messagebox.showerror("Database error", "Could not save the prescription.")
        return

    draft_lines.clear()
    prescription_lines_list.delete(0, tk.END)
    messagebox.showinfo(
        "Prescription saved",
        f"Prescription {prescription_id} saved as Pending."
    )
def refresh_prescriptions(event=None):
    try:
        records = list_prescriptions()
        branch_names = {
            branch.id: branch.name for branch in list_branches()
        }
    except sqlite3.Error:
        messagebox.showerror("Database error", "Could not load prescriptions.")
        return

    dispense_tree.delete(*dispense_tree.get_children())

    for record in records:
        dispense_tree.insert(
            "",
            tk.END,
            iid=str(record.id),
            values=(
                record.id,
                record.patient_id,
                branch_names.get(record.branch_id, record.branch_id),
                record.status
            )
        )
def handle_dispense():
    selected = dispense_tree.selection()

    if not selected:
        messagebox.showerror("Dispense error", "Select a prescription first.")
        return

    prescription_id = int(selected[0])

    try:
        dispense_prescription(prescription_id)
    except ValueError as error:
        messagebox.showerror("Dispense error", str(error))
    except sqlite3.Error:
        messagebox.showerror("Database error", "Could not dispense the prescription.")
    else:
        messagebox.showinfo(
            "Dispensed",
            f"Prescription {prescription_id} was dispensed successfully."
        )

    refresh_prescriptions()
initialize_database()
window = tk.Tk()
window.title("Campus Pharmacy")
window.geometry("900x650")
notebook = ttk.Notebook(window)
notebook.pack(fill="both", expand=True, padx=12, pady=12)

medicine_tab = ttk.Frame(notebook)
branch_tab = ttk.Frame(notebook)
stock_tab = ttk.Frame(notebook)
prescription_tab = ttk.Frame(notebook)
dispense_tab = ttk.Frame(notebook)
low_stock_tab = LowStockView(notebook)

notebook.add(medicine_tab, text="Register Medicine")
notebook.add(branch_tab, text="Branches")
notebook.add(stock_tab, text="Receive Stock")
notebook.add(prescription_tab, text="Create Prescription")
notebook.add(dispense_tab, text="Dispense")
notebook.add(low_stock_tab, text="Low Stock")

tk.Label(medicine_tab, text="Register Medicine").pack(pady=12)
tk.Label(medicine_tab, text="Medicine code").pack()
medicine_code_entry = tk.Entry(medicine_tab, width=30)
medicine_code_entry.pack(pady=(0, 12))
tk.Label(medicine_tab, text="Name").pack()
medicine_name_entry = tk.Entry(medicine_tab, width=30)
medicine_name_entry.pack(pady=(0, 12))
tk.Label(medicine_tab, text="Unit price").pack()
unit_price_entry = tk.Entry(medicine_tab, width=30)
unit_price_entry.pack(pady=(0, 12))

tk.Label(medicine_tab, text="Reorder level").pack()
reorder_level_entry = tk.Entry(medicine_tab, width=30)
reorder_level_entry.pack(pady=(0, 12))
tk.Label(medicine_tab, text="Medicine type").pack()
medicine_type = tk.StringVar(value="Ordinary")
tk.OptionMenu(medicine_tab, medicine_type, "Ordinary", "Controlled").pack(pady=(0, 12))

tk.Button(medicine_tab, text="Register", command=handle_register).pack()
tk.Label(branch_tab, text= "Branch name").pack(pady=(20,4))

branch_name_entry = tk.Entry(branch_tab, width=30)
branch_name_entry.pack(pady=(0,12))

tk.Button(
    branch_tab,
    text="Create Branch",
    command=handle_create_branch
).pack()
tk.Label(stock_tab, text="Branch").pack(pady=(20, 4))
stock_branch_combo = ttk.Combobox(stock_tab, state="readonly", width=30)
stock_branch_combo.pack(pady=(0, 12))

tk.Label(stock_tab, text="Medicine code").pack()
stock_medicine_combo = ttk.Combobox(stock_tab, state="readonly", width=30)
stock_medicine_combo.pack(pady=(0, 12))

tk.Label(stock_tab, text="Quantity received").pack()
stock_quantity_entry = tk.Entry(stock_tab, width=30)
stock_quantity_entry.pack(pady=(0, 12))
tk.Button(
    stock_tab,
    text="Receive Stock",
    command=handle_receive_stock
).pack()
tk.Label(prescription_tab, text="Fictional patient ID").pack(pady=(16, 4))
prescription_patient_entry = tk.Entry(prescription_tab, width=30)
prescription_patient_entry.pack(pady=(0, 8))

tk.Label(prescription_tab, text="Branch").pack()
prescription_branch_combo = ttk.Combobox(
    prescription_tab, state="readonly", width=30
)
prescription_branch_combo.pack(pady=(0, 8))

tk.Label(prescription_tab, text="Prescriber code").pack()
prescription_prescriber_entry = tk.Entry(prescription_tab, width=30)
prescription_prescriber_entry.pack(pady=(0, 8))

tk.Label(prescription_tab, text="Medicine code").pack()
prescription_medicine_combo = ttk.Combobox(
    prescription_tab, state="readonly", width=30
)
prescription_medicine_combo.pack(pady=(0, 8))

tk.Label(prescription_tab, text="Quantity").pack()
prescription_quantity_entry = tk.Entry(prescription_tab, width=30)
prescription_quantity_entry.pack(pady=(0, 8))

tk.Button(
    prescription_tab,
    text="Add Line",
    command=handle_add_line
).pack(pady=(0, 8))

prescription_lines_list = tk.Listbox(prescription_tab, width=55, height=5)
prescription_lines_list.pack(pady=(0, 8))

tk.Button(
    prescription_tab,
    text="Save Prescription",
    command=handle_save_prescription
).pack()
dispense_tree = ttk.Treeview(
    dispense_tab,
    columns=("id", "patient", "branch", "status"),
    show="headings",
    selectmode="browse",
    height=10
)

for column, heading, width in (
    ("id", "ID", 80),
    ("patient", "Patient ID", 220),
    ("branch", "Branch", 220),
    ("status", "Status", 120)
):
    dispense_tree.heading(column, text=heading)
    dispense_tree.column(column, width=width, anchor="w")

dispense_tree.pack(fill="x", padx=16, pady=16)
tk.Button(
    dispense_tab,
    text="Dispense Selected",
    command=handle_dispense
).pack()
notebook.bind("<<NotebookTabChanged>>", refresh_stock_choices)
notebook.bind("<<NotebookTabChanged>>", refresh_prescriptions, add="+")
notebook.bind(
    "<<NotebookTabChanged>>",
    lambda event: low_stock_tab.refresh(),
    add="+"
)
window.mainloop()
