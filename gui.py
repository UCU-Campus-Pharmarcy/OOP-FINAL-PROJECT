import tkinter as tk
import sqlite3
from db import initialize_database
from medicines import register_medicine
from tkinter import messagebox
from decimal import Decimal, InvalidOperation

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
initialize_database()
window = tk.Tk()
window.title("Campus Pharmacy")
window.geometry("480x440")

tk.Label(window, text="Register Medicine").pack(pady=12)
tk.Label(window, text="Medicine code").pack()
medicine_code_entry = tk.Entry(window, width=30)
medicine_code_entry.pack(pady=(0, 12))
tk.Label(window, text="Name").pack()
medicine_name_entry = tk.Entry(window, width=30)
medicine_name_entry.pack(pady=(0, 12))
tk.Label(window, text="Unit price").pack()
unit_price_entry = tk.Entry(window, width=30)
unit_price_entry.pack(pady=(0, 12))

tk.Label(window, text="Reorder level").pack()
reorder_level_entry = tk.Entry(window, width=30)
reorder_level_entry.pack(pady=(0, 12))
tk.Label(window, text="Medicine type").pack()
medicine_type = tk.StringVar(value="Ordinary")
tk.OptionMenu(window, medicine_type, "Ordinary", "Controlled").pack(pady=(0, 12))

tk.Button(window, text="Register", command=handle_register).pack()
window.mainloop()
