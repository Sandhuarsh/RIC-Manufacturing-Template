// The three buttons live in the form body (Button fields); Frappe fires an event named after each fieldname.
frappe.ui.form.on("Naming Settings", {
	create_default_item_rules(frm) {
		frappe.confirm(
			__(
				"This creates the standard manufacturing item groups (Finished Product, Sub Assembly, Raw Material, Packing Material, Consumables, Services) and a numbering rule for each. Similar existing groups are reused. Existing rules are not changed. Continue?"
			),
			() => {
				frappe.call({
					method: "ric_template.api.create_default_item_rules",
					freeze: true,
				});
			}
		);
	},

	create_default_return_note_rules(frm) {
		frappe.confirm(
			__(
				"This creates numbering rules for credit and debit notes on Sales Invoice and Purchase Invoice (CDNR-, DBNS-, DBNR-, DBNP-). Counters start at 1. Existing rules are not changed. Continue?"
			),
			() => {
				frappe.call({
					method: "ric_template.api.create_default_return_note_rules",
					freeze: true,
				});
			}
		);
	},

	open_numbering_rules(frm) {
		frappe.set_route("List", "Item Naming Rule");
	},
});
