"""Default numbering rules taken from the RIC "Master Data" sheet (manufacturing template)."""

import frappe

# (item group, prefix, start, end, uses sub-group abbreviation)
DEFAULT_ITEM_RULES = [
    ("Finished Product", "IM-FG-", 100000, 199999, 1),
    ("Sub Assembly", "IM-SF-", 200000, 299999, 1),
    ("Raw Material", "IM-RIM-", 300000, 399999, 1),
    ("Packing Material", "IM-PIM-", 400000, 499999, 1),
    ("Consumables", "IM-CO-", 500000, 599999, 1),
    ("Services", "IM-SR-", 600000, 699999, 1),
]


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


def create_default_item_rules():
    """Create missing Level 1 item groups and their rules. Existing rules are untouched.

    Returns the names of the rules that were created.
    """
    created = []
    for group, prefix, start, end, use_abbr in DEFAULT_ITEM_RULES:
        if frappe.db.exists("RIC Naming Rule", group):
            continue

        if not frappe.db.exists("Item Group", group):
            frappe.get_doc(
                {
                    "doctype": "Item Group",
                    "item_group_name": group,
                    "parent_item_group": "All Item Groups",
                    "is_group": 1,
                }
            ).insert(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": "RIC Naming Rule",
                "item_group": group,
                "enabled": 1,
                "prefix": prefix,
                "use_subgroup_abbr": use_abbr,
                "start_number": start,
                "end_number": end,
                "padding": 0,
            }
        ).insert(ignore_permissions=True)
        created.append(group)

    return created
