frappe.pages["vaaman-hr-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Vaaman HR"),
		single_column: true,
	});

	frappe.require("/assets/vaaman_hr/css/vaaman_hr_dashboard.css", () => {
		const dashboard = new VaamanHrDashboard(page);
		$(wrapper).bind("show", () => dashboard.refresh());
		dashboard.refresh();
	});
};

class VaamanHrDashboard {
	constructor(page) {
		this.page = page;
		this.wrapper = $(page.body);
		this.refresh_interval_sec = 60;
		this.refresh_timer = null;
		this.charts = {};
		this.render_layout();
	}

	render_layout() {
		this.wrapper.html(`
			<div class="vaaman-hr-dashboard">
				<div class="vhr-header">
					<div>
						<div class="vhr-section-title" style="font-size:16px;margin-bottom:4px;">
							${__("Vaaman HR")}
						</div>
						<div class="text-muted small">${__("Attendance, leave and headcount")}</div>
						<div class="vhr-meta vhr-refreshed-at"></div>
					</div>
					<div class="vhr-header-actions">
						<button class="btn btn-default btn-sm btn-clear-filters">${__("Clear Filters")}</button>
						<button class="btn btn-default btn-sm btn-refresh">${__("Refresh")}</button>
					</div>
				</div>

				<div class="vhr-filters-card">
					<div class="vhr-filters-toolbar">
						<div class="vhr-section-title">${__("Filters")}</div>
						<div class="vhr-filters-actions">
							<button type="button" class="btn btn-default btn-sm btn-clear-filters">${__("Clear")}</button>
							<button type="button" class="btn btn-primary btn-sm btn-apply-filters">${__("Apply Filters")}</button>
						</div>
					</div>
					<div class="vhr-filters-row"></div>
				</div>

				<div class="vhr-kpi-grid"></div>

				<div class="vhr-charts">
					<div class="vhr-chart-box">
						<div class="vhr-section-title">${__("Attendance by Status")}</div>
						<div id="vhr-chart-status" class="chart-container"></div>
					</div>
					<div class="vhr-chart-box">
						<div class="vhr-section-title">${__("Attendance Mix")}</div>
						<div id="vhr-chart-mix" class="chart-container"></div>
					</div>
					<div class="vhr-chart-box">
						<div class="vhr-section-title">${__("Attendance Over Time")}</div>
						<div id="vhr-chart-timeline" class="chart-container"></div>
					</div>
					<div class="vhr-chart-box">
						<div class="vhr-section-title">${__("Late Entry Over Time")}</div>
						<div id="vhr-chart-late" class="chart-container"></div>
					</div>
					<div class="vhr-chart-box">
						<div class="vhr-section-title">${__("Present vs Absent by Department")}</div>
						<div id="vhr-chart-department" class="chart-container"></div>
					</div>
					<div class="vhr-chart-box">
						<div class="vhr-section-title">${__("Present vs Absent by Branch")}</div>
						<div id="vhr-chart-branch" class="chart-container"></div>
					</div>
					<div class="vhr-chart-box">
						<div class="vhr-section-title">${__("Active Employees by Department")}</div>
						<div id="vhr-chart-headcount" class="chart-container"></div>
					</div>
					<div class="vhr-chart-box">
						<div class="vhr-section-title">${__("Approved Leave by Type")}</div>
						<div id="vhr-chart-leave" class="chart-container"></div>
					</div>
					<div class="vhr-chart-box">
						<div class="vhr-section-title">${__("Leave Applications by Status")}</div>
						<div id="vhr-chart-leave-status" class="chart-container"></div>
					</div>
					<div class="vhr-chart-box">
						<div class="vhr-section-title">${__("Attendance Rate")}</div>
						<div id="vhr-chart-rate" class="chart-container"></div>
					</div>
				</div>

				<div class="vhr-charts vhr-tables">
					<div class="vhr-table-box">
						<div class="vhr-section-title">${__("By Department")}</div>
						<div class="vhr-table-wrap vhr-table-department"></div>
					</div>
					<div class="vhr-table-box">
						<div class="vhr-section-title">${__("By Branch")}</div>
						<div class="vhr-table-wrap vhr-table-branch"></div>
					</div>
					<div class="vhr-table-box">
						<div class="vhr-section-title">${__("By Company")}</div>
						<div class="vhr-table-wrap vhr-table-company"></div>
					</div>
				</div>
			</div>
		`);

		this.wrapper.find(".btn-refresh, .btn-apply-filters").on("click", () => this.refresh());
		this.wrapper.find(".btn-clear-filters").on("click", () => this.clear_filters());
		this.render_filters();
	}

	render_filters() {
		const $row = this.wrapper.find(".vhr-filters-row");
		$row.empty();
		this.filter_fields = {};

		const field_defs = [
			{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
			{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
			{ fieldname: "branch", label: __("Branch"), fieldtype: "Link", options: "Branch" },
			{
				fieldname: "from_date",
				label: __("From Date"),
				fieldtype: "Date",
				default: frappe.datetime.month_start(),
			},
			{
				fieldname: "to_date",
				label: __("To Date"),
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
			},
		];

		field_defs.forEach((df) => {
			const $item = $(`
				<div class="vhr-filter-item">
					<label class="vhr-filter-label">${df.label}</label>
					<div class="vhr-filter-control"></div>
				</div>
			`);
			$row.append($item);

			const control = frappe.ui.form.make_control({
				df: {
					fieldtype: df.fieldtype,
					fieldname: df.fieldname,
					options: df.options,
					default: df.default,
				},
				parent: $item.find(".vhr-filter-control")[0],
				render_input: true,
			});
			control.make();
			if (df.default) {
				control.set_value(df.default);
			}
			control.refresh();
			this.filter_fields[df.fieldname] = control;
		});
	}

	clear_filters() {
		Object.entries(this.filter_fields || {}).forEach(([fieldname, control]) => {
			if (fieldname === "from_date") {
				control.set_value(frappe.datetime.month_start());
			} else if (fieldname === "to_date") {
				control.set_value(frappe.datetime.get_today());
			} else {
				control.set_value("");
			}
		});
		this.refresh();
	}

	get_filters() {
		const filters = {};
		Object.entries(this.filter_fields || {}).forEach(([fieldname, control]) => {
			const value = control.get_value();
			if (value) {
				filters[fieldname] = value;
			}
		});
		return filters;
	}

	refresh() {
		this.wrapper.find(".vhr-kpi-grid").html(
			`<div class="vhr-loading" style="grid-column: 1 / -1;">${__("Loading...")}</div>`
		);

		frappe.call({
			method: "vaaman_hr.hr_dashboard.get_dashboard_stats",
			args: { filters: this.get_filters() },
			callback: (r) => {
				if (!r.message) {
					frappe.msgprint(__("Could not load Vaaman HR dashboard."));
					return;
				}
				this.render_data(r.message);
				this.schedule_auto_refresh();
			},
			error: () => {
				this.wrapper.find(".vhr-kpi-grid").html(
					`<div class="vhr-no-data" style="grid-column: 1 / -1;">${__("Failed to load data. Please refresh.")}</div>`
				);
			},
		});
	}

	schedule_auto_refresh() {
		if (this.refresh_timer) clearInterval(this.refresh_timer);
		this.refresh_timer = setInterval(() => {
			if (frappe.get_route_str() === "vaaman-hr-dashboard") {
				this.refresh();
			}
		}, this.refresh_interval_sec * 1000);
	}

	format_kpi(value) {
		return frappe.format(cint(value), { fieldtype: "Int" });
	}

	render_data(data) {
		const s = data.summary || {};
		this.wrapper.find(".vhr-refreshed-at").text(
			__("Auto-refresh every {0}s · {1} to {2} · Last updated: {3}", [
				this.refresh_interval_sec,
				frappe.datetime.str_to_user(data.from_date),
				frappe.datetime.str_to_user(data.to_date),
				frappe.datetime.str_to_user(data.refreshed_at),
			])
		);

		const kpis = [
			{ label: __("Active Employees"), value: s.active_employees },
			{ label: __("Present"), value: s.present },
			{ label: __("Absent"), value: s.absent, alert: true },
			{ label: __("On Leave"), value: s.on_leave },
			{ label: __("Half Day"), value: s.half_day },
			{ label: __("Late Entry"), value: s.late_entry, alert: true },
			{ label: __("Weekly Off"), value: s.weekly_off },
			{ label: __("Pending Leave Applications"), value: s.pending_leaves, alert: true },
		];

		this.wrapper.find(".vhr-kpi-grid").html(
			kpis
				.map(
					(k) => `
				<div class="vhr-kpi${k.alert ? " alert" : ""}">
					<div class="label">${k.label}</div>
					<div class="value">${this.format_kpi(k.value)}</div>
				</div>`
				)
				.join("")
		);

		const timeline = data.timeline || [];
		this.render_chart("vhr-chart-status", data.by_status || [], "bar");
		this.render_chart("vhr-chart-mix", data.by_status || [], "donut");
		this.render_timeline(timeline);
		this.render_series("vhr-chart-late", timeline, [
			{ name: __("Late Entry"), key: "late_entry", color: "#ed8936" },
		], "line");
		this.render_compare("vhr-chart-department", (data.by_department || []).slice(0, 8));
		this.render_compare("vhr-chart-branch", (data.by_branch || []).slice(0, 8));
		this.render_chart("vhr-chart-headcount", data.headcount_by_department || [], "bar");
		this.render_chart("vhr-chart-leave", data.leave_by_type || [], "bar");
		this.render_chart("vhr-chart-leave-status", data.leave_by_status || [], "donut");
		this.render_rate(timeline);

		const columns = [
			{ key: "label", label: __("Name") },
			{ key: "present", label: __("Present") },
			{ key: "absent", label: __("Absent") },
			{ key: "on_leave", label: __("On Leave") },
			{ key: "late_entry", label: __("Late Entry") },
		];
		this.render_table(".vhr-table-department", data.by_department || [], [
			{ key: "label", label: __("Department") },
			...columns.slice(1),
		]);
		this.render_table(".vhr-table-branch", data.by_branch || [], [
			{ key: "label", label: __("Branch") },
			...columns.slice(1),
		]);
		this.render_table(".vhr-table-company", data.by_company || [], [
			{ key: "label", label: __("Company") },
			...columns.slice(1),
		]);
	}

	short_label(value) {
		const text = String(value || __("Not Set"));
		return text.length > 22 ? `${text.slice(0, 20)}…` : text;
	}

	render_timeline(rows) {
		this.render_series(
			"vhr-chart-timeline",
			rows,
			[
				{ name: __("Present"), key: "present", color: "#38a169" },
				{ name: __("Absent"), key: "absent", color: "#e53e3e" },
				{ name: __("On Leave"), key: "on_leave", color: "#ed8936" },
			],
			rows.length === 1 ? "bar" : "line"
		);
	}

	render_rate(rows) {
		const rated = rows.map((row) => {
			const base = cint(row.present) + cint(row.absent) + cint(row.on_leave) + cint(row.half_day);
			return {
				date: row.date,
				rate: base ? Math.round((cint(row.present) / base) * 100) : 0,
			};
		});
		this.render_series(
			"vhr-chart-rate",
			rated,
			[{ name: __("Present %"), key: "rate", color: "#2490ef" }],
			rated.length === 1 ? "bar" : "line"
		);
	}

	render_series(element_id, rows, series, type) {
		const parent = this.wrapper.find(`#${element_id}`)[0];
		if (!parent) return;
		this.destroy_chart(element_id);

		const datasets = series.map((item) => ({
			name: item.name,
			values: rows.map((row) => cint(row[item.key])),
		}));
		const has_value = datasets.some((set) => set.values.some((value) => value > 0));
		if (!rows.length || !has_value) {
			$(parent).html(`<div class="vhr-no-data">${__("No data for current filters")}</div>`);
			return;
		}

		$(parent).empty();
		try {
			this.charts[element_id] = new frappe.Chart(`#${element_id}`, {
				type,
				height: 250,
				data: {
					labels: rows.map((row) => frappe.datetime.str_to_user(row.date)),
					datasets,
				},
				colors: series.map((item) => item.color),
				axisOptions: { xIsSeries: type === "line" && rows.length > 1 },
			});
		} catch (e) {
			$(parent).html(`<div class="vhr-no-data">${__("Chart could not be rendered")}</div>`);
		}
	}

	render_compare(element_id, rows) {
		const parent = this.wrapper.find(`#${element_id}`)[0];
		if (!parent) return;
		this.destroy_chart(element_id);

		if (!rows.length) {
			$(parent).html(`<div class="vhr-no-data">${__("No data for current filters")}</div>`);
			return;
		}

		$(parent).empty();
		try {
			this.charts[element_id] = new frappe.Chart(`#${element_id}`, {
				type: "bar",
				height: 250,
				data: {
					labels: rows.map((row) => this.short_label(row.label)),
					datasets: [
						{ name: __("Present"), values: rows.map((row) => cint(row.present)) },
						{ name: __("Absent"), values: rows.map((row) => cint(row.absent)) },
					],
				},
				colors: ["#38a169", "#e53e3e"],
			});
		} catch (e) {
			$(parent).html(`<div class="vhr-no-data">${__("Chart could not be rendered")}</div>`);
		}
	}

	render_chart(element_id, rows, type) {
		const parent = this.wrapper.find(`#${element_id}`)[0];
		if (!parent) return;
		this.destroy_chart(element_id);

		const values = rows.map((row) => cint(row.value));
		if (!rows.length || values.every((value) => value === 0)) {
			$(parent).html(`<div class="vhr-no-data">${__("No data for current filters")}</div>`);
			return;
		}

		$(parent).empty();
		try {
			this.charts[element_id] = new frappe.Chart(`#${element_id}`, {
				type,
				height: 250,
				data: {
					labels: rows.map((row) => this.short_label(row.label)),
					datasets: [{ name: __("Count"), values }],
				},
				colors: ["#2490ef", "#38a169", "#ed8936", "#9f7aea", "#e53e3e", "#319795", "#d53f8c"],
				maxSlices: 8,
			});
		} catch (e) {
			$(parent).html(`<div class="vhr-no-data">${__("Chart could not be rendered")}</div>`);
		}
	}

	destroy_chart(element_id) {
		if (!this.charts[element_id]) return;
		try {
			this.charts[element_id].destroy?.();
		} catch (e) {
			/* ignore */
		}
		this.charts[element_id] = null;
	}

	render_table(selector, rows, columns) {
		const wrap = this.wrapper.find(selector);
		if (!rows.length) {
			wrap.html(`<div class="vhr-no-data">${__("No data for current filters")}</div>`);
			return;
		}

		const head = columns.map((c) => `<th>${c.label}</th>`).join("");
		const body = rows
			.map((row) => {
				const cells = columns
					.map((c) => {
						const val = row[c.key];
						const display =
							typeof val === "number" || c.key !== "label"
								? frappe.format(cint(val), { fieldtype: "Int" })
								: frappe.utils.escape_html(String(val ?? ""));
						return `<td>${c.key === "label" ? frappe.utils.escape_html(String(val ?? "")) : display}</td>`;
					})
					.join("");
				return `<tr>${cells}</tr>`;
			})
			.join("");

		wrap.html(`<table class="vhr-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`);
	}
}

function cint(v) {
	return parseInt(v, 10) || 0;
}
