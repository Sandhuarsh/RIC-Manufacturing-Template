// Shows the item code numbering rule (prefix and number range) on the Item Group form.
frappe.ui.form.on("Item Group", {
	refresh(frm) {
		const field = frm.fields_dict.ric_rule_html;
		if (!field || frm.is_new()) {
			return;
		}

		frappe
			.call({
				method: "ric_template.api.get_rule_info",
				args: { item_group: frm.doc.name },
			})
			.then((r) => {
				const info = r.message;
				if (!info) {
					field.$wrapper.html(
						`<p class="text-muted">${__("No item code numbering rule applies to this group.")}</p>`
					);
					frm.add_custom_button(__("Create Numbering Rule"), () => {
						frappe.new_doc("Item Naming Rule", { item_group: frm.doc.name });
					}, __("RIC"));
					return;
				}

				const row = (label, value) =>
					`<tr><td class="text-muted" style="width:40%">${label}</td><td><b>${frappe.utils.escape_html(String(value))}</b></td></tr>`;

				field.$wrapper.html(`
					<table class="table table-bordered" style="max-width:520px">
						${row(__("Rule"), info.rule + (info.inherited ? " (" + __("inherited from parent group") + ")" : ""))}
						${row(__("Prefix"), info.prefix)}
						${row(__("Start Number"), info.start_number)}
						${row(__("End Number"), info.end_number)}
						${row(__("Last Number Used"), info.last_number)}
						${row(__("Sub-Group Abbreviation in Code"), info.use_subgroup_abbr ? __("Yes") : __("No"))}
						${row(__("Example Next Code"), info.example || "")}
					</table>`);

				frm.add_custom_button(__("Open Numbering Rule"), () => {
					frappe.set_route("Form", "Item Naming Rule", info.rule);
				}, __("RIC"));
			});
	},
});
