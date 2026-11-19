// Shows the next auto-generated code on a new Item and lets the code stay empty.
frappe.ui.form.on("Item", {
	onload(frm) {
		if (frm.is_new()) {
			frm.set_df_property("item_code", "reqd", 0);
		}
	},

	refresh(frm) {
		ric_template_preview(frm);
	},

	item_group(frm) {
		ric_template_preview(frm);
	},
});

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
			frm.set_df_property(
				"item_code",
				"description",
				code ? __("Generated on save. Next code: {0}", [code]) : ""
			);
		});
}
