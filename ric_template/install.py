from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
    "Item Group": [
        {
            "fieldname": "ric_abbr",
            "label": "Item Abbreviation",
            "fieldtype": "Data",
            "insert_after": "parent_item_group",
            "depends_on": "eval:!doc.is_group",
            "description": "Short code added to item codes when the numbering rule uses sub-group abbreviations (for example HYD).",
        },
        {
            "fieldname": "ric_numbering_section",
            "label": "Item Code Numbering",
            "fieldtype": "Section Break",
            "insert_after": "ric_abbr",
            "depends_on": "eval:doc.is_group && !doc.__islocal",
        },
        {
            "fieldname": "ric_rule_html",
            "label": "Numbering Rule",
            "fieldtype": "HTML",
            "insert_after": "ric_numbering_section",
        },
    ]
}


def after_install():
    ensure_custom_fields()


def ensure_custom_fields():
    """Idempotent: also runs after every migrate so the field is never lost."""
    create_custom_fields(CUSTOM_FIELDS, update=True)
