from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
    "Item Group": [
        {
            "fieldname": "ric_abbr",
            "label": "RIC Abbreviation",
            "fieldtype": "Data",
            "insert_after": "parent_item_group",
            "description": "Short code added to item codes when the numbering rule uses sub-group abbreviations (for example HYD).",
        }
    ]
}


def after_install():
    ensure_custom_fields()


def ensure_custom_fields():
    """Idempotent: also runs after every migrate so the field is never lost."""
    create_custom_fields(CUSTOM_FIELDS, update=True)
