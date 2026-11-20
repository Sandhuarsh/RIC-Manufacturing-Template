import frappe

try:  # Frappe v16
    from frappe.tests import IntegrationTestCase as FrappeTestCase
except ImportError:  # Frappe v15
    from frappe.tests.utils import FrappeTestCase

from ric_template.naming import format_code, get_rule_name, reserve_next_code


class TestRICItemNaming(FrappeTestCase):
    def setUp(self):
        for name in ("RICTEST Level 1", "RICTEST Level 2"):
            if not frappe.db.exists("Item Group", name):
                frappe.get_doc(
                    {
                        "doctype": "Item Group",
                        "item_group_name": name,
                        "parent_item_group": "All Item Groups" if name.endswith("1") else "RICTEST Level 1",
                        "is_group": 0 if name.endswith("2") else 1,
                    }
                ).insert()
        frappe.db.set_value("Item Group", "RICTEST Level 2", "ric_abbr", "ABC")

        if frappe.db.exists("Item Naming Rule", "RICTEST Level 1"):
            frappe.delete_doc("Item Naming Rule", "RICTEST Level 1", force=True)

        self.rule = frappe.get_doc(
            {
                "doctype": "Item Naming Rule",
                "item_group": "RICTEST Level 1",
                "prefix": "TT-",
                "use_subgroup_abbr": 1,
                "start_number": 500,
                "end_number": 502,
                "padding": 4,
            }
        ).insert()

    def test_format(self):
        self.assertEqual(format_code(self.rule, 7, "ABC"), "TT-ABC-0007")
        self.assertEqual(format_code(self.rule, 7), "TT-0007")

    def test_rule_found_through_parent_group(self):
        self.assertEqual(get_rule_name("RICTEST Level 2"), "RICTEST Level 1")

    def test_numbers_increase_and_stop_at_end(self):
        number, code = reserve_next_code("RICTEST Level 1", "RICTEST Level 2")
        self.assertEqual((number, code), (500, "TT-ABC-0500"))

        number, _code = reserve_next_code("RICTEST Level 1", "RICTEST Level 2")
        self.assertEqual(number, 501)

        reserve_next_code("RICTEST Level 1", "RICTEST Level 2")  # 502
        with self.assertRaises(frappe.ValidationError):
            reserve_next_code("RICTEST Level 1", "RICTEST Level 2")

    def test_item_gets_code_on_insert(self):
        item = frappe.get_doc(
            {
                "doctype": "Item",
                "item_name": "RICTEST Widget",
                "item_group": "RICTEST Level 2",
                "stock_uom": "Nos",
            }
        ).insert()
        self.assertEqual(item.item_code, "TT-ABC-0500")

    def test_overlapping_range_rejected(self):
        other = frappe.get_doc(
            {
                "doctype": "Item Naming Rule",
                "item_group": "All Item Groups",
                "prefix": "TT-",
                "start_number": 501,
                "end_number": 900,
            }
        )
        with self.assertRaises(frappe.ValidationError):
            other.insert()
