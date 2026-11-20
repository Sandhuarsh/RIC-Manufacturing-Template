"""Move rules saved under the old "RIC Naming Rule" DocType to "Item Naming Rule".

Runs after model sync, so the new DocType table already exists. Safe to run twice:
it does nothing when the old DocType is gone.
"""

import frappe

OLD = "RIC Naming Rule"
NEW = "Item Naming Rule"


def execute():
    if not frappe.db.exists("DocType", OLD):
        return

    if frappe.db.table_exists(OLD):
        for row in frappe.get_all(OLD, fields=["*"]):
            if frappe.db.exists(NEW, row.item_group):
                continue

            doc = frappe.new_doc(NEW)
            for field in (
                "item_group",
                "enabled",
                "prefix",
                "use_subgroup_abbr",
                "start_number",
                "end_number",
                "padding",
                "last_number",
            ):
                doc.set(field, row.get(field))
            doc.insert(ignore_permissions=True)

    frappe.delete_doc("DocType", OLD, force=True, ignore_missing=True)
    frappe.db.commit()
