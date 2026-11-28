-- Member 2: persistent entities and independent database invariants.
CREATE TABLE IF NOT EXISTS medicines (
    code TEXT PRIMARY KEY NOT NULL CHECK (length(trim(code)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    unit_price_minor INTEGER NOT NULL
        CHECK (typeof(unit_price_minor) = 'integer' AND unit_price_minor > 0),
    reorder_level INTEGER NOT NULL
        CHECK (typeof(reorder_level) = 'integer' AND reorder_level >= 0),
    medicine_type TEXT NOT NULL CHECK (medicine_type IN ('Ordinary', 'Controlled'))
);

CREATE TABLE IF NOT EXISTS branches (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS stock (
    branch_id INTEGER NOT NULL REFERENCES branches(id),
    medicine_code TEXT NOT NULL REFERENCES medicines(code),
    quantity INTEGER NOT NULL CHECK (typeof(quantity) = 'integer' AND quantity >= 0),
    PRIMARY KEY (branch_id, medicine_code)
);

-- Each row in this fictional table represents an approved prescriber.
CREATE TABLE IF NOT EXISTS prescribers (
    code TEXT PRIMARY KEY NOT NULL CHECK (length(trim(code)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS prescriptions (
    id INTEGER PRIMARY KEY,
    branch_id INTEGER NOT NULL REFERENCES branches(id),
    patient_id TEXT NOT NULL CHECK (length(trim(patient_id)) > 0),
    -- Membership is required only for controlled medicines at dispense time.
    prescriber_code TEXT CHECK (prescriber_code IS NULL OR length(trim(prescriber_code)) > 0),
    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending', 'Dispensed', 'Cancelled'))
);

CREATE TABLE IF NOT EXISTS prescription_lines (
    prescription_id INTEGER NOT NULL REFERENCES prescriptions(id),
    medicine_code TEXT NOT NULL REFERENCES medicines(code),
    quantity INTEGER NOT NULL CHECK (typeof(quantity) = 'integer' AND quantity > 0),
    PRIMARY KEY (prescription_id, medicine_code)
);
