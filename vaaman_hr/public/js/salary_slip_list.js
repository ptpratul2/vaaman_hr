frappe.listview_settings["Salary Slip"] = frappe.listview_settings["Salary Slip"] || {};

(() => {
	const settings = frappe.listview_settings["Salary Slip"];
	const previous_onload = settings.onload;

	settings.onload = function (listview) {
		if (previous_onload) {
			previous_onload(listview);
		}
		if (!frappe.model.can_write("Salary Slip")) {
			return;
		}

		listview.page.add_actions_menu_item(__("Recalculate"), () => {
			const names = listview.get_checked_items(true);
			if (!names.length) {
				frappe.msgprint(__("Please select the salary slips to recalculate"));
				return;
			}

			frappe.confirm(
				__(
					"Recalculate {0} selected salary slip(s) from the latest attendance, overtime, weekly off and additional salary? Submitted slips will be skipped.",
					[names.length]
				),
				() => {
					frappe.call({
						method: "vaaman_hr.overrides.salary_slip.recalculate_salary_slips",
						args: { names },
						freeze: true,
						freeze_message: __("Recalculating Salary Slips..."),
						callback(r) {
							if (!r.message) {
								return;
							}
							const updated = r.message.updated || [];
							const skipped = r.message.skipped || [];
							let message = __("{0} salary slip(s) recalculated.", [updated.length]);
							if (skipped.length) {
								message += " " + __("{0} skipped because they are not draft.", [skipped.length]);
							}
							frappe.show_alert({ message, indicator: updated.length ? "green" : "orange" });
							listview.refresh();
						},
					});
				}
			);
		});
	};
})();
