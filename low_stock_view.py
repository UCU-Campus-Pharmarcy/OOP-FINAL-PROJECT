"""Tkinter low-stock tab, embedded by the main application."""

import sqlite3
import tkinter as tk
from tkinter import ttk

from db import DB_PATH, PharmacyError
from low_stock import list_low_stock
from stock import list_branches


class LowStockView(ttk.Frame):
    def __init__(self, parent, *, db_path=DB_PATH):
        super().__init__(parent, padding=16)
        self.db_path = db_path
        self.branch_ids = {}

        ttk.Label(self, text="Branch").grid(row=0, column=0, sticky="w")
        self.branch_selector = ttk.Combobox(self, state="readonly", width=42)
        self.branch_selector.grid(row=1, column=0, sticky="w", pady=(4, 12))
        self.branch_selector.bind("<<ComboboxSelected>>", self._load_report)
        ttk.Button(self, text="Refresh", command=self.refresh).grid(row=1, column=1, sticky="e")

        columns = ("code", "name", "quantity", "reorder_level")
        self.report = ttk.Treeview(self, columns=columns, show="headings", height=10)
        for column, title, width in zip(
            columns, ("Medicine code", "Name", "On hand", "Reorder level"), (125, 220, 90, 105)
        ):
            self.report.heading(column, text=title)
            self.report.column(column, width=width, anchor="center" if column in columns[2:] else "w")
        self.report.grid(row=2, column=0, columnspan=2, sticky="nsew")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.report.yview)
        scrollbar.grid(row=2, column=2, sticky="ns")
        self.report.configure(yscrollcommand=scrollbar.set)

        self.status = tk.StringVar(master=self)
        ttk.Label(self, textvariable=self.status, wraplength=520).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

    def refresh(self):
        """Reload branch choices and keep the current branch selected when possible."""
        selected = self.branch_selector.get()
        try:
            branches = list_branches(db_path=self.db_path)
        except sqlite3.Error as error:
            self._clear_report()
            self.status.set(f"Could not load branches. {error}")
            return

        self.branch_ids = {f"{branch.name} (#{branch.id})": branch.id for branch in branches}
        self.branch_selector.configure(values=tuple(self.branch_ids))
        self.branch_selector.set(selected if selected in self.branch_ids else next(iter(self.branch_ids), ""))
        self._load_report()

    def _clear_report(self):
        for row in self.report.get_children():
            self.report.delete(row)

    def _load_report(self, _event=None):
        self._clear_report()
        branch_id = self.branch_ids.get(self.branch_selector.get())
        if branch_id is None:
            self.status.set("Create a branch to view its low-stock report.")
            return

        try:
            items = list_low_stock(branch_id, db_path=self.db_path)
        except (PharmacyError, sqlite3.Error) as error:
            self.status.set(f"Could not load the low-stock report. {error}")
            return

        for item in items:
            self.report.insert("", "end", values=(item.medicine_code, item.name, item.quantity, item.reorder_level))
        count = len(items)
        if count == 1:
            self.status.set("1 tracked medicine is at or below its reorder level.")
        else:
            self.status.set(f"{count} tracked medicines are at or below their reorder levels.")
