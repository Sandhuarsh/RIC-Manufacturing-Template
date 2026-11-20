frappe.ui.form.on("RIC Template Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Create Default Item Rules"), () => {
			frappe.confirm(
				__(
					"This creates the standard manufacturing item groups (Finished Product, Sub Assembly, Raw Material, Packing Material, Consumables, Services) and a numbering rule for each. Existing rules are not changed. Continue?"
				),
				() => {
					frappe.call({
						method: "ric_template.api.create_default_item_rules",
						freeze: true,
					});
				}
			);
		});

		frm.add_custom_button(__("Create Credit/Debit Note Rules"), () => {
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
		});

		frm.add_custom_button(__("Open Numbering Rules"), () => frappe.set_route("List", "Item Naming Rule"));
	},
});
