"""Move saved values from the old "RIC Template Settings" to "Naming Settings".

Runs after model sync, so the new DocType already exists. Safe to run twice.
"""

import frappe

OLD = "RIC Template Settings"
NEW = "Naming Settings"
FIELDS = ("block_duplicate_item_name", "lock_item_group_after_creation")


def execute():
    if not frappe.db.exists("DocType", OLD):
        return

    old_values = frappe.db.get_singles_dict(OLD) or {}
    for field in FIELDS:
        if field in old_values:
            frappe.db.set_single_value(NEW, field, old_values[field])

    frappe.delete_doc("DocType", OLD, force=True, ignore_missing=True)
    frappe.db.commit()
