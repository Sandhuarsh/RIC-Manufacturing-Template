"""Default numbering rules taken from the RIC "Master Data" sheet (manufacturing template)."""

import frappe

# (group to create, existing names to reuse instead, prefix, start, end, uses sub-group abbreviation)
# An existing group with any of the alias names is reused, so a site that already has
# "Sub Assemblies" or "Consumable" does not get a second, near-identical group.
DEFAULT_ITEM_RULES = [
    ("Finished Product", ("Finished Product", "Finished Products", "Products"), "IM-FG-", 100000, 199999, 1),
    ("Sub Assembly", ("Sub Assembly", "Sub Assemblies", "Semi Finished Goods"), "IM-SF-", 200000, 299999, 1),
    ("Raw Material", ("Raw Material", "Raw Materials"), "IM-RIM-", 300000, 399999, 1),
    ("Packing Material", ("Packing Material", "Packing Materials", "Packaging Material"), "IM-PIM-", 400000, 499999, 1),
    ("Consumables", ("Consumables", "Consumable"), "IM-CO-", 500000, 599999, 1),
    ("Services", ("Services", "Service"), "IM-SR-", 600000, 699999, 1),
]


def _find_group(names):
    for name in names:
        if frappe.db.exists("Item Group", name):
            return frappe.db.get_value("Item Group", name, "name")  # real spelling / case
    return None


def create_default_item_rules():
    """Create a numbering rule for each standard Level 1 group. Existing rules are untouched.

    Existing groups with similar names are reused (and turned into parent groups so
    sub-groups can be added). Missing groups are created. Returns what was done.
    """
    done = []
    for group, aliases, prefix, start, end, use_abbr in DEFAULT_ITEM_RULES:
        existing = _find_group(aliases)

        if existing:
            if frappe.db.exists("Item Naming Rule", existing):
                continue
            if not frappe.db.get_value("Item Group", existing, "is_group"):
                frappe.db.set_value("Item Group", existing, "is_group", 1)
            target = existing
            note = f"{target} (existing group)" if target != group else target
        else:
            frappe.get_doc(
                {
                    "doctype": "Item Group",
                    "item_group_name": group,
                    "parent_item_group": "All Item Groups",
                    "is_group": 1,
                }
            ).insert(ignore_permissions=True)
            target = group
            note = f"{target} (new group)"

        frappe.get_doc(
            {
                "doctype": "Item Naming Rule",
                "item_group": target,
                "enabled": 1,
                "prefix": prefix,
                "use_subgroup_abbr": use_abbr,
                "start_number": start,
                "end_number": end,
                "padding": 0,
            }
        ).insert(ignore_permissions=True)
        done.append(note)

    return done


# (document type, condition field, prefix, label)
# Frappe's own Document Naming Rule is used, so no custom code runs on save.
# The counter is deliberately not set: every rule starts from 1.
DEFAULT_RETURN_NOTE_RULES = [
    ("Sales Invoice", "is_return", "CDNR-.YY.-", "Sales Credit Note"),
    ("Sales Invoice", "is_debit_note", "DBNS-.YY.-", "Sales Debit Note"),
    ("Purchase Invoice", "is_return", "DBNR-.YY.-", "Purchase Debit Note (return to supplier)"),
    ("Purchase Invoice", "is_debit_note", "DBNP-.YY.-", "Purchase Debit Note (received from supplier)"),
]


def create_default_return_note_rules():
    """Create credit / debit note numbering rules. Existing rules are untouched.

    A rule is skipped when the document type does not have the condition field
    (for example ``is_debit_note`` needs India Compliance) or when a rule with the
    same document type and prefix already exists. Returns the labels created.
    """
    created = []
    for doctype, field, prefix, label in DEFAULT_RETURN_NOTE_RULES:
        if not frappe.get_meta(doctype).has_field(field):
            continue

        if frappe.db.exists("Document Naming Rule", {"document_type": doctype, "prefix": prefix}):
            continue

        frappe.get_doc(
            {
                "doctype": "Document Naming Rule",
                "document_type": doctype,
                "prefix": prefix,
                "prefix_digits": 4,
                "priority": 0,
                "conditions": [{"field": field, "condition": "=", "value": "1"}],
            }
        ).insert(ignore_permissions=True)
        created.append(label)

    return created
