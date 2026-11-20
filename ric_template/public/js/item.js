// On a new Item: Item Code is not mandatory on the form (the server generates it on save),
// and the next code is shown while the item group is chosen.
// Same approach as the Supreme "Item Naming Series" client script: reqd off on load and refresh.
frappe.ui.form.on("Item", {
	onload(frm) {
		ric_template_item_code_fields(frm);
	},

	refresh(frm) {
		ric_template_item_code_fields(frm);
		ric_template_preview(frm);
	},

	item_group(frm) {
		ric_template_preview(frm);
	},
});

function ric_template_item_code_fields(frm) {
	if (frm.is_new()) {
		frm.set_df_property("item_code", "reqd", 0);
	}
}

function ric_template_preview(frm) {
	if (!frm.is_new() || !frm.doc.item_group || frm.doc.item_code) {
		return;
	}

	frappe
		.call({
			method: "ric_template.api.get_next_item_code",
			args: { item_group: frm.doc.item_group },
		})
		.then((r) => {
			const code = r.message;
			ric_template_item_code_fields(frm);
			// With a numbering rule the code is generated, so lock the field.
			// Without one the field stays editable for a manual code.
			frm.set_df_property("item_code", "read_only", code ? 1 : 0);
			frm.set_df_property(
				"item_code",
				"description",
				code ? __("Generated on save. Next code: {0}", [code]) : ""
			);
		});
}
