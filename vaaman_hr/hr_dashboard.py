# Copyright (c) 2026, Vaaman Engineers and contributors
# License: MIT

import frappe
from frappe import _
from frappe.utils import cint, get_first_day, getdate, now_datetime, today

HR_ROLES = {
	"System Manager",
	"HR Manager",
	"HR User",
	"HO HR Manager",
	"HO HR User",
	"Site HR Manager",
	"Site HR User",
}

ATTENDANCE_STATUSES = (
	"Present",
	"Absent",
	"On Leave",
	"Half Day",
	"Work From Home",
	"Weekly Off",
	"Holiday",
)


def has_app_permission():
	"""Show Vaaman HR on the apps screen for HR users."""
	return bool(set(frappe.get_roles()) & HR_ROLES)


def _parse_filters(filters=None):
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	filters = frappe._dict(filters or {})
	filters.from_date = getdate(filters.from_date or get_first_day(today()))
	filters.to_date = getdate(filters.to_date or today())
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be after To Date"))
	if (filters.to_date - filters.from_date).days > 366:
		frappe.throw(_("Date range cannot be more than 366 days"))
	return filters


def _employee_filters(filters, alias="emp"):
	conditions = []
	values = []
	for field in ("company", "department", "branch"):
		if filters.get(field):
			conditions.append(f"{alias}.{field} = %s")
			values.append(filters.get(field))
	return conditions, values


@frappe.whitelist()
def get_dashboard_stats(filters=None):
	"""Attendance and leave KPIs for the Vaaman HR dashboard."""
	if not has_app_permission():
		frappe.throw(_("Not permitted to view the Vaaman HR dashboard"), frappe.PermissionError)

	filters = _parse_filters(filters)
	emp_conditions, emp_values = _employee_filters(filters)
	emp_sql = (" AND " + " AND ".join(emp_conditions)) if emp_conditions else ""

	active_employees = frappe.db.sql(
		f"""
		SELECT COUNT(*) AS count
		FROM `tabEmployee` emp
		WHERE emp.status = 'Active'
		{emp_sql}
		""",
		emp_values,
	)[0][0]

	status_select = ", ".join(
		f"SUM(CASE WHEN att.status = %s THEN 1 ELSE 0 END) AS `{status}`" for status in ATTENDANCE_STATUSES
	)
	attendance = frappe.db.sql(
		f"""
		SELECT
			COUNT(*) AS marked,
			SUM(CASE WHEN att.late_entry = 1 THEN 1 ELSE 0 END) AS late_entry,
			{status_select}
		FROM `tabAttendance` att
		INNER JOIN `tabEmployee` emp ON emp.name = att.employee
		WHERE att.docstatus = 1
			AND att.attendance_date BETWEEN %s AND %s
			{emp_sql}
		""",
		[*ATTENDANCE_STATUSES, filters.from_date, filters.to_date, *emp_values],
		as_dict=True,
	)[0]

	pending_leaves = frappe.db.sql(
		f"""
		SELECT COUNT(*) AS count
		FROM `tabLeave Application` la
		INNER JOIN `tabEmployee` emp ON emp.name = la.employee
		WHERE la.docstatus = 0
			AND la.status = 'Open'
			{emp_sql}
		""",
		emp_values,
	)[0][0]

	timeline = frappe.db.sql(
		f"""
		SELECT
			att.attendance_date AS date,
			SUM(CASE WHEN att.status = 'Present' THEN 1 ELSE 0 END) AS present,
			SUM(CASE WHEN att.status = 'Absent' THEN 1 ELSE 0 END) AS absent,
			SUM(CASE WHEN att.status = 'On Leave' THEN 1 ELSE 0 END) AS on_leave,
			SUM(CASE WHEN att.status = 'Half Day' THEN 1 ELSE 0 END) AS half_day,
			SUM(CASE WHEN att.late_entry = 1 THEN 1 ELSE 0 END) AS late_entry
		FROM `tabAttendance` att
		INNER JOIN `tabEmployee` emp ON emp.name = att.employee
		WHERE att.docstatus = 1
			AND att.attendance_date BETWEEN %s AND %s
			{emp_sql}
		GROUP BY att.attendance_date
		ORDER BY att.attendance_date
		""",
		[filters.from_date, filters.to_date, *emp_values],
		as_dict=True,
	)

	leave_by_type = frappe.db.sql(
		f"""
		SELECT la.leave_type AS label, COUNT(*) AS value
		FROM `tabLeave Application` la
		INNER JOIN `tabEmployee` emp ON emp.name = la.employee
		WHERE la.docstatus = 1
			AND la.status = 'Approved'
			AND la.from_date <= %s
			AND la.to_date >= %s
			{emp_sql}
		GROUP BY la.leave_type
		ORDER BY value DESC
		LIMIT 12
		""",
		[filters.to_date, filters.from_date, *emp_values],
		as_dict=True,
	)

	def breakdown(column):
		return frappe.db.sql(
			f"""
			SELECT
				IFNULL(NULLIF(emp.{column}, ''), 'Not Set') AS label,
				SUM(CASE WHEN att.status = 'Present' THEN 1 ELSE 0 END) AS present,
				SUM(CASE WHEN att.status = 'Absent' THEN 1 ELSE 0 END) AS absent,
				SUM(CASE WHEN att.status = 'On Leave' THEN 1 ELSE 0 END) AS on_leave,
				SUM(CASE WHEN att.late_entry = 1 THEN 1 ELSE 0 END) AS late_entry
			FROM `tabAttendance` att
			INNER JOIN `tabEmployee` emp ON emp.name = att.employee
			WHERE att.docstatus = 1
				AND att.attendance_date BETWEEN %s AND %s
				{emp_sql}
			GROUP BY label
			ORDER BY present DESC
			LIMIT 15
			""",
			[filters.from_date, filters.to_date, *emp_values],
			as_dict=True,
		)

	leave_by_status = frappe.db.sql(
		f"""
		SELECT la.status AS label, COUNT(*) AS value
		FROM `tabLeave Application` la
		INNER JOIN `tabEmployee` emp ON emp.name = la.employee
		WHERE la.docstatus < 2
			AND la.from_date <= %s
			AND la.to_date >= %s
			{emp_sql}
		GROUP BY la.status
		ORDER BY value DESC
		""",
		[filters.to_date, filters.from_date, *emp_values],
		as_dict=True,
	)

	headcount_by_department = frappe.db.sql(
		f"""
		SELECT IFNULL(NULLIF(emp.department, ''), 'Not Set') AS label, COUNT(*) AS value
		FROM `tabEmployee` emp
		WHERE emp.status = 'Active'
			{emp_sql}
		GROUP BY label
		ORDER BY value DESC
		LIMIT 10
		""",
		emp_values,
		as_dict=True,
	)

	by_status = [
		{"label": status, "value": cint(attendance.get(status))}
		for status in ATTENDANCE_STATUSES
		if cint(attendance.get(status))
	]

	return {
		"refreshed_at": now_datetime(),
		"from_date": str(filters.from_date),
		"to_date": str(filters.to_date),
		"summary": {
			"active_employees": cint(active_employees),
			"present": cint(attendance.get("Present")),
			"absent": cint(attendance.get("Absent")),
			"on_leave": cint(attendance.get("On Leave")),
			"half_day": cint(attendance.get("Half Day")),
			"late_entry": cint(attendance.late_entry),
			"weekly_off": cint(attendance.get("Weekly Off")),
			"pending_leaves": cint(pending_leaves),
			"marked": cint(attendance.marked),
		},
		"by_status": by_status,
		"timeline": timeline,
		"leave_by_type": leave_by_type,
		"leave_by_status": leave_by_status,
		"headcount_by_department": headcount_by_department,
		"by_department": breakdown("department"),
		"by_branch": breakdown("branch"),
		"by_company": breakdown("company"),
	}
