"""Configurable Item code numbering for the RIC template.

How it works
------------
An enabled ``Item Naming Rule`` is attached to an Item Group (normally a Level 1
group such as "Finished Product"). When a new Item is saved without an item
code, the nearest rule found on the item's group or any of its parent groups is
used to build the code:

    <prefix>[<sub group abbreviation>-]<running number>

* The running number comes from the rule's own counter (``last_number``), is
  never lower than ``start_number`` and may not pass ``end_number``.
* The counter row is locked (``SELECT ... FOR UPDATE``) while the number is
  reserved, so two users saving at the same moment cannot get the same code.
* An item with no matching rule, or one saved with an item code already filled
  in (manual entry, data import), is left to standard ERPNext behaviour.
"""

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.nestedset import get_ancestors_of

RULE_DOCTYPE = "Item Naming Rule"
SETTINGS_DOCTYPE = "RIC Template Settings"


def get_setting(fieldname):
    """Settings are Check fields that default to ON until saved once."""
    value = frappe.db.get_single_value(SETTINGS_DOCTYPE, fieldname)
    return 1 if value is None else cint(value)


def get_rule_name(item_group):
    """Return the nearest enabled rule for an item group or one of its parents."""
    if not item_group:
        return None

    chain = [item_group] + list(get_ancestors_of("Item Group", item_group) or [])
    rules = frappe.get_all(
        RULE_DOCTYPE,
        filters={"enabled": 1, "item_group": ["in", chain]},
        fields=["name", "item_group"],
    )
    by_group = {r.item_group: r.name for r in rules}
    for group in chain:  # nearest group first
        if group in by_group:
            return by_group[group]
    return None


def format_code(rule, number, abbr=None):
    """Build the code text for a given number."""
    padded = str(cint(number)).zfill(cint(rule.padding))
    middle = f"{abbr}-" if abbr else ""
    return f"{rule.prefix}{middle}{padded}"


def _subgroup_abbr(rule, item_group):
    if not cint(rule.use_subgroup_abbr):
        return None

    abbr = frappe.db.get_value("Item Group", item_group, "ric_abbr")
    if not abbr:
        frappe.throw(
            _("Please set the RIC Abbreviation on Item Group {0}. Rule {1} needs it for the item code.").format(
                frappe.bold(item_group), frappe.bold(rule.name)
            ),
            title=_("Abbreviation Missing"),
        )
    return abbr.strip().upper()


def reserve_next_code(rule_name, item_group, commit_counter=True):
    """Return (number, code) for the next free number of a rule.

    With ``commit_counter`` the rule's counter is advanced inside the current
    transaction while its row is locked. Pass False to only preview the next
    code without consuming a number.
    """
    rule = frappe.get_doc(RULE_DOCTYPE, rule_name)
    abbr = _subgroup_abbr(rule, item_group)

    if commit_counter:
        row = frappe.db.sql(
            f"select last_number from `tab{RULE_DOCTYPE}` where name = %s for update",
            (rule.name,),
        )
        last_number = cint(row[0][0]) if row else 0
    else:
        last_number = cint(rule.last_number)

    number = max(last_number + 1, cint(rule.start_number))

    while True:
        if number > cint(rule.end_number):
            frappe.throw(
                _("Item code range exhausted for rule {0}. The maximum allowed number is {1}.").format(
                    frappe.bold(rule.name), cint(rule.end_number)
                ),
                title=_("Number Range Exhausted"),
            )

        code = format_code(rule, number, abbr)
        if not frappe.db.exists("Item", code):
            break
        number += 1  # skip codes that already exist (e.g. created manually)

    if commit_counter:
        frappe.db.set_value(RULE_DOCTYPE, rule.name, "last_number", number, update_modified=False)

    return number, code


def set_item_code(doc, method=None):
    """Item ``before_insert``: generate the item code from the matching rule."""
    if doc.get("item_code"):
        return

    rule_name = get_rule_name(doc.get("item_group"))
    if not rule_name:
        return

    _number, code = reserve_next_code(rule_name, doc.item_group)
    doc.item_code = code


def validate_item(doc, method=None):
    """Item ``validate``: optional guards that mirror proven MSME practice."""
    if get_setting("lock_item_group_after_creation") and not doc.is_new():
        old_group = frappe.db.get_value("Item", doc.name, "item_group")
        if old_group and old_group != doc.item_group and get_rule_name(old_group):
            frappe.throw(
                _("Item Group cannot be changed once the item code has been generated from it."),
                title=_("Item Group Locked"),
            )

    if get_setting("block_duplicate_item_name") and doc.get("item_name"):
        if doc.is_new() or doc.has_value_changed("item_name"):
            name = doc.item_name.strip()
            duplicate = frappe.db.get_value(
                "Item", {"item_name": name, "name": ["!=", doc.name or ""]}, "name"
            )
            if duplicate:
                frappe.throw(
                    _("Item Name {0} already exists (Item Code: {1}). Please use a different name.").format(
                        frappe.bold(name), frappe.bold(duplicate)
                    ),
                    title=_("Duplicate Item Name"),
                )
