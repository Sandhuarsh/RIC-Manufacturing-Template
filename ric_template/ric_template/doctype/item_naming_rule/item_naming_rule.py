import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class ItemNamingRule(Document):
    def validate(self):
        self.prefix = (self.prefix or "").strip()

        if not self.prefix:
            frappe.throw(_("Prefix is required."))

        if cint(self.start_number) < 0 or cint(self.end_number) < 0:
            frappe.throw(_("Start Number and End Number cannot be negative."))

        if cint(self.end_number) < cint(self.start_number):
            frappe.throw(_("End Number must be greater than or equal to Start Number."))

        if cint(self.padding) < 0:
            frappe.throw(_("Number Padding cannot be negative."))

        if cint(self.last_number) > cint(self.end_number):
            frappe.throw(_("Last Number Used cannot be greater than End Number."))

        self.validate_overlap()
        self.set_example()

    def validate_overlap(self):
        """Two rules with the same prefix must not share numbers, or codes could clash."""
        others = frappe.get_all(
            "Item Naming Rule",
            filters={"prefix": self.prefix, "name": ["!=", self.name or ""], "enabled": 1},
            fields=["name", "start_number", "end_number"],
        )
        for other in others:
            if cint(self.start_number) <= cint(other.end_number) and cint(self.end_number) >= cint(other.start_number):
                frappe.throw(
                    _("Number range overlaps with rule {0} that uses the same prefix.").format(frappe.bold(other.name))
                )

    def set_example(self):
        from ric_template.naming import format_code

        number = max(cint(self.last_number) + 1, cint(self.start_number))
        abbr = "ABC" if cint(self.use_subgroup_abbr) else None
        self.example_code = format_code(self, number, abbr)
