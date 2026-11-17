import tkinter as tk

window = tk.Tk()
window.title("Campus Pharmacy")
window.geometry("480x360")

tk.Label(window, text="Register Medicine").pack(pady=12)
tk.Label(window, text="Medicine code").pack()
medicine_code_entry = tk.Entry(window, width=30)
medicine_code_entry.pack(pady=(0, 12))
window.mainloop()
