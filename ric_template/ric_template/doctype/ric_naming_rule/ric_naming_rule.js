frappe.ui.form.on("RIC Naming Rule", {
	refresh(frm) {
		frm.set_intro(
			__(
				"When a new Item is saved without an item code, the rule on its Item Group (or the nearest parent group) builds the code as Prefix + [Sub-Group Abbreviation] + Number."
			),
			"blue"
		);
	},
});
