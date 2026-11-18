import tkinter as tk

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

tk.Button(window, text="Register", state=tk.DISABLED).pack()
window.mainloop()
