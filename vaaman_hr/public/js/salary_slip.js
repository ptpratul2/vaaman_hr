frappe.ui.form.on("Salary Slip", {
	refresh(frm) {
		if (frm.doc.docstatus !== 0 || frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Recalculate"), () => {
			frappe.confirm(
				__(
					"Recalculate this draft from the latest attendance, overtime, weekly off and additional salary? Component rows will be rebuilt from the salary structure."
				),
				() => {
					frm.call({
						method: "recalculate_salary_slip",
						doc: frm.doc,
						freeze: true,
						freeze_message: __("Recalculating Salary Slip..."),
						callback() {
							frm.reload_doc().then(() => {
								frappe.show_alert({
									message: __("Salary Slip recalculated"),
									indicator: "green",
								});
							});
						},
					});
				}
			);
		});
	},
});
