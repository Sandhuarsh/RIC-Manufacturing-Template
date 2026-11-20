import frappe
from frappe import _

from ric_template.naming import get_rule_name, reserve_next_code
from ric_template.seed import create_default_item_rules as _create_default_item_rules
from ric_template.seed import create_default_return_note_rules as _create_default_return_note_rules


@frappe.whitelist()
def get_next_item_code(item_group):
    """Preview the next item code for a group without using up a number."""
    frappe.has_permission("Item", "read", throw=True)

    rule_name = get_rule_name(item_group)
    if not rule_name:
        return None

    try:
        _number, code = reserve_next_code(rule_name, item_group, commit_counter=False)
    except frappe.ValidationError:
        # e.g. abbreviation missing or range exhausted: the real error is shown on save
        frappe.clear_last_message()
        return None

    return code


@frappe.whitelist()
def get_rule_info(item_group):
    """Numbering rule that applies to an Item Group, for the panel on the Item Group form."""
    frappe.has_permission("Item Group", "read", throw=True)

    rule_name = get_rule_name(item_group)
    if not rule_name:
        return None

    rule = frappe.get_doc("Item Naming Rule", rule_name)
    return {
        "rule": rule.name,
        "inherited": rule.item_group != item_group,
        "prefix": rule.prefix,
        "start_number": rule.start_number,
        "end_number": rule.end_number,
        "last_number": rule.last_number,
        "padding": rule.padding,
        "use_subgroup_abbr": rule.use_subgroup_abbr,
        "example": rule.example_code,
    }


@frappe.whitelist()
def create_default_return_note_rules():
    """Create the standard credit / debit note numbering rules (counters start at 1)."""
    frappe.only_for("System Manager")
    created = _create_default_return_note_rules()
    if created:
        frappe.msgprint(_("Created rules: {0}").format(", ".join(created)), alert=True)
    else:
        frappe.msgprint(_("All credit / debit note rules already exist."), alert=True)
    return created


@frappe.whitelist()
def create_default_item_rules():
    """Create the standard MSME manufacturing rules from the RIC Master Data sheet."""
    frappe.only_for("System Manager")
    created = _create_default_item_rules()
    if created:
        frappe.msgprint(_("Created rules: {0}").format(", ".join(created)), alert=True)
    else:
        frappe.msgprint(_("All default rules already exist."), alert=True)
    return created
